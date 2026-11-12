package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"
)

func listing(uri, kind, title, subtitle string) string {
	entity := map[string]any{"uri": uri, "type": kind, "title": title, "subtitle": subtitle,
		"trackList": []map[string]string{{"title": "BIRDS OF A FEATHER", "subtitle": "Billie Eilish"}, {"title": "BLUE", "subtitle": "Billie Eilish"}}}
	data := map[string]any{"props": map[string]any{"pageProps": map[string]any{"state": map[string]any{"data": map[string]any{"entity": entity}}}}}
	raw, _ := json.Marshal(data)
	return `<script type="application/json" id="__NEXT_DATA__">` + string(raw) + `</script>`
}

func TestTrackMetadataCacheDoesNotRequireAnAlbum(t *testing.T) {
	a := testApp(t)
	uri := "spotify:track:one"
	m, err := parseSearchMetadata([]byte(listing(uri, "track", "BLUE", "Billie Eilish")), uri)
	if err != nil || m.Album != "" || m.Artist == "" || m.Songs == "" {
		t.Fatal("invalid track metadata", m, err)
	}
	if err := a.store.cacheMetadata(uri, m, true); err != nil {
		t.Fatal(err)
	}
	old := time.Now().Add(-30 * 24 * time.Hour).Unix()
	if _, err := a.store.db.Exec("UPDATE search_metadata SET checked_at=? WHERE uri=?", old, uri); err != nil {
		t.Fatal(err)
	}
	if a.store.metadataDue(uri) {
		t.Fatal("successful track metadata should remain cached")
	}
	if err := a.store.cacheMetadata("spotify:track:missing", SearchMetadata{}, false); err != nil {
		t.Fatal(err)
	}
	if _, err := a.store.db.Exec("UPDATE search_metadata SET checked_at=? WHERE uri=?", old, "spotify:track:missing"); err != nil {
		t.Fatal(err)
	}
	if !a.store.metadataDue("spotify:track:missing") {
		t.Fatal("failed track metadata should be retried")
	}
}

func TestPublicSearchMetadata(t *testing.T) {
	uri := "spotify:album:4444444444444444444444"
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" || r.URL.Path != "/embed/album/4444444444444444444444" || r.Header.Get("Authorization") != "" {
			t.Error("Unexpected catalogue request", r.Method, r.URL.Path)
		}
		w.Write([]byte(listing(uri, "album", "HIT ME HARD AND SOFT", "Billie Eilish")))
	}))
	defer server.Close()
	m, e := fetchSearchMetadata(context.Background(), server.Client(), server.URL, uri)
	if e != nil || m.Artist != "Billie Eilish" || m.Album != "HIT ME HARD AND SOFT" || m.Songs != "BIRDS OF A FEATHER\nBLUE" {
		t.Fatal(m, e)
	}
	if _, e = parseSearchMetadata([]byte(listing(uri, "album", "Title", "Artist")), "spotify:album:other"); e == nil {
		t.Fatal("Accepted wrong item")
	}
	if _, e = parseSearchMetadata([]byte(`<html>No public listing</html>`), uri); e == nil {
		t.Fatal("Accepted missing metadata")
	}
	p, e := parseSearchMetadata([]byte(listing(uri, "playlist", "Favorites", "Playlist owner")), uri)
	if e != nil || p.Artist != "Billie Eilish" || strings.Contains(p.Artist, "Playlist owner") {
		t.Fatal(p, e)
	}
}

func TestSearchMetadataPersistenceAndManualCorrections(t *testing.T) {
	a := testApp(t)
	uri := "spotify:album:4444444444444444444444"
	m, e := a.store.metadata(uri)
	if e != nil || !strings.Contains(m.Songs, "BIRDS OF A FEATHER") {
		t.Fatal("Bundled index missing", m, e)
	}
	if a.store.metadataDue(uri) {
		t.Fatal("Cached album would fetch on startup")
	}
	if e = a.store.cacheMetadata(uri, SearchMetadata{}, false); e != nil {
		t.Fatal(e)
	}
	preserved, _ := a.store.metadata(uri)
	if preserved != m {
		t.Fatal("Network failure discarded cached details")
	}
	cards, _ := a.store.cards("title")
	c := cards[0]
	c.URI, c.MetadataEdited = uri, true
	c.Metadata = SearchMetadata{Artist: `Artist <script>alert(1)</script>`, Album: "Hand-entered album", Songs: "A personal song"}
	if e = a.store.save(c, nil, nil); e != nil {
		t.Fatal(e)
	}
	if e = a.store.cacheMetadata(uri, m, true); e != nil {
		t.Fatal(e)
	}
	got, _ := a.store.metadata(uri)
	if got != c.Metadata || a.store.metadataDue(uri) {
		t.Fatal("Automatic refresh overwrote manual details", got)
	}
	if e = a.store.seedCatalogue(testCatalogue(t)); e != nil {
		t.Fatal(e)
	}
	got, _ = a.store.metadata(uri)
	if got != c.Metadata {
		t.Fatal("Upgrade overwrote manual metadata")
	}
	b := &browser{a: a}
	signIn(t, b)
	page := b.request("GET", "/", nil, nil).Body.String()
	if !strings.Contains(page, "A personal song") || strings.Contains(page, "Artist <script>") {
		t.Fatal("Search metadata missing or not escaped")
	}
}

func TestSearchDetailsEditAndLinkChange(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	token := signIn(t, b)
	c, _ := a.store.card("demo-album")
	path := "/cards/" + c.ID + "/edit"
	values := url.Values{"csrf": {token}, "title": {c.Title}, "uri": {c.URI}, "search_details": {"1"}, "artist": {"Personal artist"}, "album": {"Personal album"}, "songs": {"First song\nSecond song"}}
	if w := b.request("POST", path, values, nil); w.Code != 303 {
		t.Fatal(w.Code, w.Body.String())
	}
	m, _ := a.store.metadata(c.URI)
	if m.Artist != "Personal artist" || m.Songs != "First song\nSecond song" {
		t.Fatal(m)
	}
	values.Del("search_details")
	if w := b.request("POST", path, values, nil); w.Code != 303 {
		t.Fatal(w.Code)
	}
	got, _ := a.store.metadata(c.URI)
	if got != m {
		t.Fatal("Artwork-only form removed search details")
	}
	values.Set("search_details", "1")
	values.Set("uri", "spotify:album:3333333333333333333333")
	if w := b.request("POST", path, values, nil); w.Code != 303 {
		t.Fatal(w.Code)
	}
	got, _ = a.store.metadata(values.Get("uri"))
	if got.Artist == "Personal artist" || !strings.Contains(got.Album, "Another Album") {
		t.Fatal("Link change retained unrelated metadata", got)
	}
}
