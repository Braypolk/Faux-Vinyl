package main

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha1"
	"crypto/sha256"
	"encoding/binary"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"golang.org/x/crypto/pbkdf2"
	"image"
	"image/color"
	"image/png"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"testing"
	"time"
)

const testOrigin = "https://vinyl.example"

func testApp(t *testing.T) *App {
	t.Helper()
	hash := "pbkdf2:sha256:1000$salt$" + hex.EncodeToString(pbkdf2.Key([]byte("correct"), []byte("salt"), 1000, 32, sha256.New))
	a, e := newApp(Config{DataDir: t.TempDir(), PublicURL: testOrigin, PasswordHash: hash, Root: "."}, PreviewPlayer{})
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() { a.store.db.Close() })
	return a
}

type browser struct {
	a      *App
	cookie *http.Cookie
}

func (b *browser) request(method, path string, values url.Values, headers map[string]string) *httptest.ResponseRecorder {
	var body io.Reader
	if values != nil {
		body = strings.NewReader(values.Encode())
	}
	req := httptest.NewRequest(method, testOrigin+path, body)
	if body != nil {
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		req.Header.Set("Origin", testOrigin)
	}
	if b.cookie != nil {
		req.AddCookie(b.cookie)
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	w := httptest.NewRecorder()
	b.a.ServeHTTP(w, req)
	for _, c := range w.Result().Cookies() {
		if c.Name == "fauxvinyl_session" {
			b.cookie = c
		}
	}
	return w
}

var csrfRE = regexp.MustCompile(`name="csrf" value="([^"]+)"`)

func csrfOf(t *testing.T, w *httptest.ResponseRecorder) string {
	t.Helper()
	m := csrfRE.FindStringSubmatch(w.Body.String())
	if m == nil {
		t.Fatalf("no CSRF: %s", w.Body.String())
	}
	return m[1]
}
func signIn(t *testing.T, b *browser) string {
	t.Helper()
	csrf := csrfOf(t, b.request("GET", "/login", nil, nil))
	w := b.request("POST", "/login", url.Values{"csrf": {csrf}, "password": {"correct"}, "next": {"/"}}, nil)
	if w.Code != 303 || w.Header().Get("Location") != "/" {
		t.Fatalf("login: %d %s", w.Code, w.Body.String())
	}
	return csrfOf(t, b.request("GET", "/", nil, nil))
}
func TestLoginAndSecurity(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	w := b.request("GET", "/", nil, nil)
	if w.Code != 303 || !strings.HasPrefix(w.Header().Get("Location"), "/login") {
		t.Fatal("private shelf exposed")
	}
	csrf := csrfOf(t, b.request("GET", "/login?next=https://evil.example", nil, nil))
	w = b.request("POST", "/login", url.Values{"csrf": {csrf}, "password": {"wrong"}}, nil)
	if w.Code != 401 || !strings.Contains(w.Body.String(), `id="login-error"`) {
		t.Fatal("wrong password not explained")
	}
	if !b.cookie.Secure || !b.cookie.HttpOnly || b.cookie.SameSite != http.SameSiteLaxMode {
		t.Fatal("cookie flags")
	}
	w = b.request("POST", "/login", url.Values{"password": {"correct"}}, nil)
	if w.Code != 400 {
		t.Fatal("missing CSRF accepted")
	}
	w = b.request("POST", "/login", url.Values{"csrf": {csrf}, "password": {"correct"}}, map[string]string{"Origin": "https://evil.example"})
	if w.Code != 403 {
		t.Fatal("foreign origin accepted")
	}
	w = b.request("POST", "/login", url.Values{"csrf": {csrf}, "password": {"correct"}}, map[string]string{"Origin": "null"})
	if w.Code != 403 {
		t.Fatal("opaque origin without metadata")
	}
	w = b.request("POST", "/login", url.Values{"csrf": {csrf}, "password": {"correct"}, "next": {"//evil.example"}}, map[string]string{"Origin": "null", "Sec-Fetch-Site": "same-origin"})
	if w.Code != 303 || w.Header().Get("Location") != "/" {
		t.Fatal("login with opaque same origin failed")
	}
	if csrfOf(t, b.request("GET", "/", nil, nil)) == csrf {
		t.Fatal("CSRF not rotated")
	}
	if !strings.Contains(w.Header().Get("Content-Security-Policy"), "script-src 'self'") {
		t.Fatal("CSP missing")
	}
	oldAuth := a.auth
	a.auth = "password-changed"
	if b.request("GET", "/", nil, nil).Code != 303 {
		t.Fatal("password change did not invalidate session")
	}
	a.auth = oldAuth
}
func TestLoginLimitPersists(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	csrf := csrfOf(t, b.request("GET", "/login", nil, nil))
	for i := 0; i < 30; i++ {
		if w := b.request("POST", "/login", url.Values{"csrf": {csrf}, "password": {"wrong"}}, nil); w.Code != 401 {
			t.Fatal(i, w.Code)
		}
	}
	if b.request("POST", "/login", url.Values{"csrf": {csrf}, "password": {"correct"}}, nil).Code != 429 {
		t.Fatal("rate limit missing")
	}
	a.store.db.Exec("UPDATE login_failures SET created=?", time.Now().Unix()-901)
	if b.request("POST", "/login", url.Values{"csrf": {csrf}, "password": {"correct"}}, nil).Code != 303 {
		t.Fatal("rate limit did not expire")
	}
}
func TestLegacyFlaskSession(t *testing.T) {
	a := testApp(t)
	raw, _ := json.Marshal(map[string]any{"auth": a.auth, "csrf": "legacy-token", "shelf_sort": "newest", "_permanent": true})
	timestamp := make([]byte, 8)
	binary.BigEndian.PutUint64(timestamp, uint64(time.Now().Unix()))
	timestamp = bytes.TrimLeft(timestamp, "\x00")
	value := b64.EncodeToString(raw) + "." + b64.EncodeToString(timestamp)
	h := hmac.New(sha1.New, a.key)
	h.Write([]byte("cookie-session"))
	h2 := hmac.New(sha1.New, h.Sum(nil))
	h2.Write([]byte(value))
	b := &browser{a: a, cookie: &http.Cookie{Name: "fauxvinyl_session", Value: value + "." + b64.EncodeToString(h2.Sum(nil))}}
	w := b.request("GET", "/", nil, nil)
	if w.Code != 200 || !strings.Contains(w.Body.String(), `value="newest" selected`) {
		t.Fatal("Flask session was lost")
	}
	if !strings.HasPrefix(b.cookie.Value, "v1.") {
		t.Fatal("legacy session was not upgraded")
	}
}
func TestShelfSortEditsExportAndRestart(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	csrf := signIn(t, b)
	cards, e := a.store.cards("title")
	if e != nil || len(cards) != 59 {
		t.Fatal("seed count", len(cards), e)
	}
	w := b.request("GET", "/", nil, nil)
	if strings.Count(w.Body.String(), `data-record-id=`) != 59 || strings.Count(w.Body.String(), `data-front="/static/covers/`) != 56 {
		t.Fatal("shelf artwork contract")
	}
	for _, sort := range []string{"title", "title-desc", "newest", "oldest"} {
		w = b.request("GET", "/?sort="+sort+"&q=test", nil, nil)
		if w.Code != 200 || !strings.Contains(w.Body.String(), `value="`+sort+`" selected`) {
			t.Fatal("sort", sort)
		}
	}
	c := cards[0]
	w = b.request("POST", "/cards/"+c.ID+"/edit", url.Values{"csrf": {csrf}, "title": {"=new <script>"}, "uri": {c.URI}}, nil)
	if w.Code != 303 {
		t.Fatal("edit", w.Code, w.Body.String())
	}
	edited, _ := a.store.card(c.ID)
	if edited.ID != c.ID || edited.Created != c.Created {
		t.Fatal("edit changed stable fields")
	}
	if strings.Contains(b.request("GET", "/cards/"+c.ID+"/edit", nil, nil).Body.String(), "=new <script>") {
		t.Fatal("unescaped title")
	}
	w = b.request("GET", "/cards.csv", nil, nil)
	rows, e := csv.NewReader(strings.NewReader(w.Body.String())).ReadAll()
	if e != nil || len(rows) != 60 {
		t.Fatal("CSV", e)
	}
	found := false
	for _, row := range rows[1:] {
		if row[0] == c.ID {
			found = true
			if row[1] != "'=new <script>" || row[3] != testOrigin+"/c/"+c.ID {
				t.Fatal("CSV stable URL/formula protection")
			}
		}
	}
	if !found {
		t.Fatal("edited card missing")
	}
	if e = a.store.seed([]byte(`[]`)); e != nil {
		t.Fatal(e)
	}
	edited, _ = a.store.card(c.ID)
	if edited.Title != "=new <script>" {
		t.Fatal("seed overwrote edits")
	}
	other, e := openStore(a.cfg.DataDir)
	if e != nil {
		t.Fatal(e)
	}
	defer other.db.Close()
	persisted, _ := other.card(c.ID)
	if persisted.Title != edited.Title {
		t.Fatal("edit not persisted")
	}
}
func upload(t *testing.T, b *browser, id, csrf string, front, back []byte, reset bool) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	m := multipart.NewWriter(&buf)
	m.WriteField("csrf", csrf)
	m.WriteField("title", "Artwork record")
	m.WriteField("uri", "spotify:album:1234567890123456789012")
	if reset {
		m.WriteField("reset_front", "1")
	}
	for side, data := range map[string][]byte{"front": front, "back": back} {
		if data != nil {
			part, _ := m.CreateFormFile(side, "cover.png")
			part.Write(data)
		}
	}
	m.Close()
	r := httptest.NewRequest("POST", testOrigin+"/cards/"+id+"/edit", &buf)
	r.Header.Set("Content-Type", m.FormDataContentType())
	r.Header.Set("Origin", testOrigin)
	r.AddCookie(b.cookie)
	w := httptest.NewRecorder()
	b.a.ServeHTTP(w, r)
	for _, c := range w.Result().Cookies() {
		b.cookie = c
	}
	return w
}
func TestArtworkUploadAtomicResetAndAccess(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	csrf := signIn(t, b)
	cards, _ := a.store.cards("title")
	id := cards[0].ID
	img := image.NewNRGBA(image.Rect(0, 0, 1600, 800))
	for y := 0; y < 800; y++ {
		for x := 0; x < 1600; x++ {
			img.Set(x, y, color.NRGBA{R: 70, G: 160, B: 200, A: 255})
		}
	}
	var buf bytes.Buffer
	png.Encode(&buf, img)
	raw := buf.Bytes()
	w := upload(t, b, id, csrf, raw, []byte("bad image"), false)
	if w.Code != 400 {
		t.Fatal("bad back accepted", w.Code)
	}
	c, _ := a.store.card(id)
	if c.Title != cards[0].Title {
		t.Fatal("invalid back changed record")
	}
	files, _ := os.ReadDir(filepath.Join(a.cfg.DataDir, "artwork"))
	if len(files) != 0 {
		t.Fatal("partial files saved")
	}
	w = upload(t, b, id, csrf, raw, raw, false)
	if w.Code != 303 {
		t.Fatal("upload", w.Code, w.Body.String())
	}
	art, _ := a.store.artwork(id)
	if art["front"] == "" || art["back"] == "" {
		t.Fatal("sides not saved")
	}
	w = b.request("GET", "/artwork/"+art["front"], nil, nil)
	if w.Code != 200 || w.Header().Get("Cache-Control") != "private, max-age=31536000, immutable" {
		t.Fatal("private art", w.Code)
	}
	decoded, _, e := image.DecodeConfig(bytes.NewReader(w.Body.Bytes()))
	if e != nil || decoded.Width != 1280 || decoded.Height != 640 {
		t.Fatal("resize", decoded, e)
	}
	anon := &browser{a: a}
	if anon.request("GET", "/artwork/"+art["front"], nil, nil).Code != 303 {
		t.Fatal("private art exposed")
	}
	w = upload(t, b, id, csrf, []byte("ignored invalid upload"), nil, true)
	if w.Code != 303 {
		t.Fatal("reset", w.Code)
	}
	art, _ = a.store.artwork(id)
	if art["front"] != "" || art["back"] == "" {
		t.Fatal("reset changed wrong side")
	}
	if b.request("GET", "/artwork/../../session.key", nil, nil).Code != 404 {
		t.Fatal("path traversal")
	}
}
func TestImageLimitsOrientationAndAnimation(t *testing.T) {
	if _, _, e := prepareCover(bytes.NewReader(make([]byte, coverLimit+1))); e == nil {
		t.Fatal("oversize accepted")
	}
	img := image.NewNRGBA(image.Rect(0, 0, 4001, 3000))
	var raw bytes.Buffer
	png.Encode(&raw, img)
	if _, _, e := prepareCover(bytes.NewReader(raw.Bytes())); e == nil {
		t.Fatal("pixel limit accepted")
	}
	small := image.NewNRGBA(image.Rect(0, 0, 2, 3))
	small.Set(0, 0, color.NRGBA{R: 255, A: 255})
	o := orientedImage{small, 6}
	if o.Bounds().Dx() != 3 || o.Bounds().Dy() != 2 || o.At(2, 0) != (color.NRGBA{R: 255, A: 255}) {
		t.Fatal("orientation")
	}
	var pngBuf bytes.Buffer
	png.Encode(&pngBuf, small)
	base := pngBuf.Bytes()
	chunk := []byte{0, 0, 0, 0, 'a', 'c', 'T', 'L', 0, 0, 0, 0}
	animated := append(append(append([]byte{}, base[:33]...), chunk...), base[33:]...)
	if _, _, e := prepareCover(bytes.NewReader(animated)); e == nil {
		t.Fatal("animated PNG accepted")
	}
}
func TestOneTimePlaybackAndTemplates(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	csrf := signIn(t, b)
	cards, _ := a.store.cards("title")
	id := cards[0].ID
	w := b.request("GET", "/c/"+id, nil, nil)
	m := regexp.MustCompile(`name="action_token" value="([^"]+)"`).FindStringSubmatch(w.Body.String())
	if w.Code != 200 || m == nil {
		t.Fatal("play page", w.Code, w.Body.String())
	}
	form := url.Values{"csrf": {csrf}, "action_token": {m[1]}}
	w = b.request("POST", "/c/"+id+"/play", form, nil)
	if w.Code != 303 || w.Header().Get("Location") != "/#record="+id {
		t.Fatal("play", w.Code, w.Body.String())
	}
	if b.request("POST", "/c/"+id+"/play", form, nil).Code != 409 {
		t.Fatal("play replay")
	}
	if b.request("POST", "/c/"+cards[1].ID+"/play", form, nil).Code != 400 {
		t.Fatal("token allowed different card")
	}
	for _, path := range []string{"/settings", "/cards/" + id + "/edit"} {
		w = b.request("GET", path, nil, nil)
		if w.Code != 200 || strings.Contains(w.Body.String(), "Template error") {
			t.Fatal(path, w.Code, w.Body.String())
		}
	}
	w = b.request("POST", "/settings", url.Values{"csrf": {csrf}, "device": {"Living Room TV"}, "shuffle": {"on"}}, nil)
	if w.Code != 303 || a.store.setting("device", "") != "Living Room TV" {
		t.Fatal("settings")
	}
	a.store.set("device", "auto")
	a.store.set("shuffle", false)
	w = b.request("GET", "/settings", nil, nil)
	if w.Code != 200 || strings.Contains(w.Body.String(), `name="shuffle" checked`) {
		t.Fatal("shuffle setting")
	}
}
func TestConcurrentPlayNonce(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	csrf := signIn(t, b)
	cards, _ := a.store.cards("title")
	id := cards[0].ID
	token := a.action(id, csrf)
	cookie := *b.cookie
	var wg sync.WaitGroup
	codes := make(chan int, 8)
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			client := &browser{a: a, cookie: &cookie}
			codes <- client.request("POST", "/c/"+id+"/play", url.Values{"csrf": {csrf}, "action_token": {token}}, jsonHeaders).Code
		}()
	}
	wg.Wait()
	close(codes)
	success := 0
	for c := range codes {
		if c == 200 {
			success++
		} else if c != 409 {
			t.Fatal("unexpected", c)
		}
	}
	if success != 1 {
		t.Fatal("duplicate playback", success)
	}
}
func TestSpotifyTransportRotationAndRetry(t *testing.T) {
	a := testApp(t)
	refreshes, plays := 0, 0
	var calls []string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls = append(calls, r.Method+" "+r.URL.Path)
		switch r.URL.Path {
		case "/api/token":
			r.ParseForm()
			refreshes++
			want := "initial"
			if refreshes > 1 {
				want = "rotated"
			}
			if r.PostForm.Get("refresh_token") != want {
				t.Error("rotated refresh not used")
			}
			u, p, ok := r.BasicAuth()
			if !ok || u != "id" || p != "secret" {
				t.Error("basic auth")
			}
			io.WriteString(w, `{"access_token":"token","refresh_token":"rotated","expires_in":3600}`)
		case "/me/player/devices":
			if refreshes == 1 {
				w.WriteHeader(401)
				return
			}
			io.WriteString(w, `{"devices":[{"id":"blocked","name":"Restricted","is_restricted":true},{"id":"tv","name":"Living Room TV","is_active":false}]}`)
		case "/me/player":
			w.WriteHeader(204)
		case "/me/player/play":
			plays++
			var body map[string]any
			json.NewDecoder(r.Body).Decode(&body)
			if body["context_uri"] != "spotify:album:1234567890123456789012" || r.URL.Query().Get("device_id") != "tv" {
				t.Error("play body/query")
			}
			w.WriteHeader(204)
		case "/me/player/shuffle":
			if r.URL.Query().Get("state") != "true" {
				t.Error("shuffle")
			}
			w.WriteHeader(429)
		default:
			t.Error("unexpected endpoint", r.URL.Path)
			w.WriteHeader(404)
		}
	}))
	defer server.Close()
	s := &Spotify{store: a.store, clientID: "id", clientSecret: "secret", initialRefresh: "initial", http: server.Client(), api: server.URL, accounts: server.URL}
	device, warning, e := s.Play("spotify:album:1234567890123456789012", "auto", true)
	if e != nil || device != "Living Room TV" || warning == "" || plays != 1 || refreshes != 2 {
		t.Fatal(device, warning, e, plays, refreshes, calls)
	}
	if a.store.setting("spotify_refresh_token", "") != "rotated" {
		t.Fatal("refresh not persisted")
	}
	want := []string{"POST /api/token", "GET /me/player/devices", "POST /api/token", "GET /me/player/devices", "PUT /me/player", "PUT /me/player/play", "PUT /me/player/shuffle"}
	if strings.Join(calls, "|") != strings.Join(want, "|") {
		t.Fatal("play sequencing", calls)
	}
}
