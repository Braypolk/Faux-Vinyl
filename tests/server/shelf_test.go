package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"sync"
	"testing"
	"time"
)

var jsonHeaders = map[string]string{"Accept": "application/json"}

func TestShelfDetailsPreserveOrderingAndArtworkOverrides(t *testing.T) {
	a := testApp(t)
	cards, err := a.store.cards("title")
	if err != nil {
		t.Fatal(err)
	}
	c := cards[0]
	c.MetadataEdited = true
	c.Metadata = SearchMetadata{Artist: "Personal artist", Album: "Personal album", Songs: "Personal song"}
	if err := a.store.save(c, map[string]string{"front": "front.jpg", "back": "back.png"}, nil); err != nil {
		t.Fatal(err)
	}
	// A record without metadata/artwork must survive the outer joins.
	missing := Card{ID: "missing-details", Title: "Missing", URI: "spotify:track:missing"}
	if err := a.store.save(missing, nil, nil); err != nil {
		t.Fatal(err)
	}
	for order := range orders {
		want, err := a.store.cards(order)
		if err != nil {
			t.Fatal(err)
		}
		got, err := a.store.shelfCards(order)
		if err != nil || len(got) != len(want) {
			t.Fatal(order, len(got), len(want), err)
		}
		for i, card := range got {
			if card.ID != want[i].ID {
				t.Fatal("shelf details changed order", order, i)
			}
			if card.ID == c.ID {
				art := a.cardArt(card, card.CustomArtwork)
				if card.Metadata != c.Metadata || art["front"] != "/artwork/front.jpg" || art["back"] != "/artwork/back.png" {
					t.Fatal("lost manual shelf details", card, art)
				}
			}
			if card.ID == missing.ID && (card.Metadata != (SearchMetadata{}) || len(card.CustomArtwork) != 0) {
				t.Fatal("missing details must remain empty", card)
			}
		}
	}
}

func TestDevelopmentRevisionIsSharedAndRefreshesAfterChanges(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "views"), 0700); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(root, "views", "index.html")
	if err := os.WriteFile(path, []byte("before"), 0600); err != nil {
		t.Fatal(err)
	}
	a := &App{cfg: Config{Root: root}}
	now := time.Now()
	before := a.assetRevision(now)
	if err := os.WriteFile(path, []byte("after with changed size"), 0600); err != nil {
		t.Fatal(err)
	}
	if a.assetRevision(now.Add(time.Second)) != before {
		t.Fatal("requests within the refresh interval should share one revision")
	}
	if a.assetRevision(now.Add(3*time.Second)) == before {
		t.Fatal("changed assets were not detected after the refresh interval")
	}
}

func jsonBody(t *testing.T, w *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	if !strings.Contains(w.Header().Get("Content-Type"), "application/json") {
		t.Fatal("Expected JSON", w.Code, w.Body.String())
	}
	var data map[string]any
	if e := json.Unmarshal(w.Body.Bytes(), &data); e != nil {
		t.Fatal(e)
	}
	return data
}

type controlledPlayer struct {
	calls   int
	failure bool
	mu      sync.Mutex
}

func (p *controlledPlayer) Devices() ([]Device, error) {
	return []Device{{ID: "tv", Name: "TV", Active: true}}, nil
}
func (p *controlledPlayer) Play(string, string, bool) (string, string, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.calls++
	if p.failure {
		return "", "", errors.New("Your selected device is offline.")
	}
	return "TV", "Shuffle could not be updated.", nil
}
func TestShelfPlaybackJSONAndNFCFallback(t *testing.T) {
	a := testApp(t)
	p := &controlledPlayer{}
	a.player = p
	b := &browser{a: a}
	csrf := signIn(t, b)
	cards, _ := a.store.cards("title")
	path := "/c/" + cards[0].ID
	w := b.request("GET", path, nil, jsonHeaders)
	data := jsonBody(t, w)
	if w.Code != 200 || data["card_id"] != cards[0].ID || data["csrf"] != csrf || p.calls != 0 {
		t.Fatal("Preparing action played music", w.Code, data, p.calls)
	}
	form := url.Values{"csrf": {csrf}, "action_token": {data["action_token"].(string)}}
	w = b.request("POST", path+"/play", form, jsonHeaders)
	data = jsonBody(t, w)
	if w.Code != 200 || data["status"] != "playing" || data["device"] != "TV" || data["warning"] == "" || p.calls != 1 {
		t.Fatal("inline result", w.Code, data)
	}
	w = b.request("POST", path+"/play", form, jsonHeaders)
	if w.Code != 409 || jsonBody(t, w)["error"] == nil || p.calls != 1 {
		t.Fatal("JSON duplicate played twice")
	}
	p.failure = true
	data = jsonBody(t, b.request("GET", path, nil, jsonHeaders))
	form.Set("action_token", data["action_token"].(string))
	w = b.request("POST", path+"/play", form, jsonHeaders)
	if w.Code != 503 || jsonBody(t, w)["error"] != "Your selected device is offline." {
		t.Fatal("inline failure", w.Code, w.Body.String())
	}
	// Retrying explicitly obtains another action; NFC opens the same shelf.
	p.failure = false
	data = jsonBody(t, b.request("GET", path, nil, jsonHeaders))
	form.Set("action_token", data["action_token"].(string))
	w = b.request("POST", path+"/play", form, jsonHeaders)
	if w.Code != 200 {
		t.Fatal("fresh retry failed")
	}
	w = b.request("GET", path, nil, nil)
	if w.Code != 200 || !strings.Contains(w.Body.String(), `data-record-browser`) || !strings.Contains(w.Body.String(), `data-autoplay-id="`+cards[0].ID+`"`) || !strings.Contains(w.Body.String(), `id="autoplay"`) || p.calls != 3 {
		t.Fatal("NFC did not open shelf without server-side playback", w.Code, p.calls)
	}
	if !strings.Contains(w.Header().Get("Vary"), "Accept") {
		t.Fatal("Missing content negotiation cache header")
	}
}
func TestJSONAuthAndCSRF(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	cards, _ := a.store.cards("title")
	path := "/c/" + cards[0].ID
	w := b.request("GET", path, nil, jsonHeaders)
	if w.Code != 401 || jsonBody(t, w)["login_url"] != "/login?next=/" {
		t.Fatal("expired session did not provide inline sign-in")
	}
	csrf := signIn(t, b)
	w = b.request("POST", "/shelf/order", url.Values{"csrf": {"bad"}}, jsonHeaders)
	if w.Code != 400 || jsonBody(t, w)["error"] == nil {
		t.Fatal("missing order CSRF accepted")
	}
	w = b.request("POST", path+"/play", url.Values{"csrf": {csrf}}, map[string]string{"Accept": "application/json", "Origin": "https://elsewhere.example"})
	if w.Code != 403 || jsonBody(t, w)["error"] == nil {
		t.Fatal("foreign origin accepted")
	}
	a.auth = "changed"
	w = b.request("GET", path, nil, jsonHeaders)
	if w.Code != 401 {
		t.Fatal("stale auth accepted")
	}
}
func TestNFCShelfAfterSignIn(t *testing.T) {
	a := testApp(t)
	p := &controlledPlayer{}
	a.player = p
	b := &browser{a: a}
	cards, _ := a.store.cards("title")
	path := "/c/" + cards[2].ID
	w := b.request("GET", path, nil, nil)
	if w.Code != 303 || w.Header().Get("Location") != "/login?next="+url.QueryEscape(path) {
		t.Fatal("NFC sign-in destination lost", w.Code, w.Header())
	}
	csrf := csrfOf(t, b.request("GET", w.Header().Get("Location"), nil, nil))
	w = b.request("POST", "/login", url.Values{"csrf": {csrf}, "password": {"correct"}, "next": {path}}, nil)
	if w.Code != 303 || w.Header().Get("Location") != path {
		t.Fatal("Sign-in did not return to scanned record")
	}
	w = b.request("GET", path, nil, nil)
	if w.Code != 200 || !strings.Contains(w.Body.String(), `data-record-browser`) || !strings.Contains(w.Body.String(), `data-autoplay-id="`+cards[2].ID+`"`) || p.calls != 0 {
		t.Fatal("Signed-in NFC page did not render the shelf safely", w.Code, p.calls)
	}
	w = b.request("GET", "/", nil, nil)
	if !strings.Contains(w.Body.String(), `data-autoplay-id=""`) || strings.Contains(w.Body.String(), `id="autoplay"`) {
		t.Fatal("Normal shelf navigation must not repeat NFC playback")
	}
}
func reverseIDs(ids []string) []string {
	out := append([]string(nil), ids...)
	for i, j := 0, len(out)-1; i < j; i, j = i+1, j-1 {
		out[i], out[j] = out[j], out[i]
	}
	return out
}
func TestCustomOrderPersistenceAndNewRecords(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	csrf := signIn(t, b)
	old, _ := a.store.cards("custom")
	ids := reverseIDs(cardIDs(old))
	version := orderVersion(cardIDs(old))
	form := url.Values{"csrf": {csrf}, "order_version": {version}, "card_id": ids}
	baseline := b.request("GET", "/cards.csv", nil, nil).Body.String()
	w := b.request("POST", "/shelf/order", form, jsonHeaders)
	data := jsonBody(t, w)
	if w.Code != 200 || data["order_version"] != orderVersion(ids) {
		t.Fatal("save failed", w.Code, data)
	}
	got, _ := a.store.cards("custom")
	if !reflect.DeepEqual(cardIDs(got), ids) {
		t.Fatal("order not applied")
	}
	home := b.request("GET", "/", nil, nil).Body.String()
	if !strings.Contains(home, `value="custom" selected`) || strings.Index(home, `data-record-id="`+ids[0]+`"`) > strings.Index(home, `data-record-id="`+ids[1]+`"`) {
		t.Fatal("session custom order not rendered")
	}
	other, e := openStore(a.cfg.DataDir)
	if e != nil {
		t.Fatal(e)
	}
	got, _ = other.cards("custom")
	other.db.Close()
	if !reflect.DeepEqual(cardIDs(got), ids) {
		t.Fatal("restart lost order")
	}
	if b.request("GET", "/cards.csv", nil, nil).Body.String() != baseline {
		t.Fatal("ordering changed NFC export")
	}
	renamed, _ := a.store.card(ids[0])
	renamed.Title = "ZZZ renamed"
	if e = a.store.save(renamed, nil, nil); e != nil {
		t.Fatal(e)
	}
	got, _ = a.store.cards("custom")
	if !reflect.DeepEqual(cardIDs(got), ids) {
		t.Fatal("rename changed custom position")
	}
	if e = a.store.save(Card{ID: "new-record", Title: "A new record", URI: old[0].URI}, nil, nil); e != nil {
		t.Fatal(e)
	}
	got, _ = a.store.cards("custom")
	if got[len(got)-1].ID != "new-record" {
		t.Fatal("new record not appended")
	}
	w = b.request("POST", "/shelf/order", url.Values{"csrf": {csrf}, "order_version": {orderVersion(ids)}, "card_id": ids}, jsonHeaders)
	if w.Code != 409 || jsonBody(t, w)["error"] == nil {
		t.Fatal("stale tab hid new record")
	}
}
func TestOrderValidationIsAtomic(t *testing.T) {
	a := testApp(t)
	cards, _ := a.store.cards("custom")
	ids := cardIDs(cards)
	version := orderVersion(ids)
	for _, bad := range [][]string{ids[:len(ids)-1], append(append([]string{}, ids[1:]...), ids[1]), append(append([]string{}, ids[1:]...), "unknown")} {
		if e := a.store.saveOrder(bad, version); !errors.Is(e, errInvalidOrder) {
			t.Fatal("invalid order accepted", e)
		}
		got, _ := a.store.cards("custom")
		if !reflect.DeepEqual(cardIDs(got), ids) {
			t.Fatal("invalid order partially persisted")
		}
	}
	reversed := reverseIDs(ids)
	if e := a.store.saveOrder(reversed, version); e != nil {
		t.Fatal(e)
	}
	if e := a.store.saveOrder(ids, version); !errors.Is(e, errOrderConflict) {
		t.Fatal("stale order clobbered new order", e)
	}
	// A fresh version can intentionally restore the previous order.
	if e := a.store.saveOrder(ids, orderVersion(reversed)); e != nil {
		t.Fatal(e)
	}
}
func TestLegacyDatabaseOrderMigration(t *testing.T) {
	dir := t.TempDir()
	db, e := sql.Open("sqlite3", filepath.Join(dir, "fauxvinyl.sqlite3"))
	if e != nil {
		t.Fatal(e)
	}
	_, e = db.Exec(`CREATE TABLE cards(id TEXT PRIMARY KEY,title TEXT NOT NULL,uri TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);INSERT INTO cards(id,title,uri) VALUES('z','Z album','spotify:album:1234567890123456789012'),('a','A album','spotify:album:1234567890123456789012'),('m','M album','spotify:album:1234567890123456789012');`)
	db.Close()
	if e != nil {
		t.Fatal(e)
	}
	store, e := openStore(dir)
	if e != nil {
		t.Fatal(e)
	}
	cards, _ := store.cards("custom")
	if !reflect.DeepEqual(cardIDs(cards), []string{"a", "m", "z"}) {
		t.Fatal("legacy migration initial order", cardIDs(cards))
	}
	if e = store.saveOrder([]string{"m", "z", "a"}, orderVersion(cardIDs(cards))); e != nil {
		t.Fatal(e)
	}
	store.db.Close()
	store, e = openStore(dir)
	if e != nil {
		t.Fatal(e)
	}
	defer store.db.Close()
	cards, _ = store.cards("custom")
	if !reflect.DeepEqual(cardIDs(cards), []string{"m", "z", "a"}) {
		t.Fatal("migration overwrote saved order")
	}
}
