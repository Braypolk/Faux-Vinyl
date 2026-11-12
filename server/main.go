package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"embed"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"html/template"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"path/filepath"
	"regexp"
	"runtime/debug"
	"strings"
	"sync"
	"syscall"
	"time"
	"unicode/utf8"
)

//go:embed views/*.html
var resources embed.FS

type Config struct {
	DataDir, PublicURL, PasswordHash, Root string
	CollectionDir, PreferencesFile         string
	Dev                                    bool
}
type App struct {
	cfg                Config
	host               string
	key                []byte
	auth               string
	store              *Store
	player             Player
	art                map[string]map[string]string
	glow               map[string]*GlowEffect
	discs              map[string][]DiscArtwork
	variants           map[string][]ImageVariant
	uploadVariants     sync.Map
	templates          map[string]*template.Template
	uploadMu           sync.Mutex
	loginMu            sync.Mutex
	metadataQueue      chan string
	devRevisionMu      sync.Mutex
	devRevision        string
	devRevisionChecked time.Time
}
type Page struct {
	Page, Title, CSRF, PublicURL, Notice, Next, LoginError, Error, Preference, ActionToken, Sort, Q, OrderVersion string
	Authenticated, Dev, Shuffle, Offline                                                                          bool
	Cards                                                                                                         []Card
	Card                                                                                                          Card
	Art, Custom                                                                                                   map[string]string
	Devices                                                                                                       []Device
	DevicePriority                                                                                                string
}

func settingEnv(name string) string {
	if p := os.Getenv(name + "_FILE"); p != "" {
		b, e := os.ReadFile(p)
		if e != nil {
			log.Fatalf("Cannot read %s_FILE", name)
		}
		return strings.TrimSpace(string(b))
	}
	return os.Getenv(name)
}
func newApp(cfg Config, player Player) (*App, error) {
	public, e := url.Parse(cfg.PublicURL)
	if e != nil || public.Hostname() == "" || (public.Scheme != "https" && public.Scheme != "http") || (public.Path != "" && public.Path != "/") || public.RawQuery != "" || public.Fragment != "" || public.User != nil {
		return nil, errors.New("PUBLIC_URL must be a web origin")
	}
	if cfg.PasswordHash == "" && !cfg.Dev {
		return nil, errors.New("APP_PASSWORD_HASH is required")
	}
	if cfg.CollectionDir == "" {
		cfg.CollectionDir = filepath.Join(cfg.Root, "collection")
	}
	if cfg.PreferencesFile == "" {
		cfg.PreferencesFile = filepath.Join(cfg.Root, "preferences.json")
	}
	catalogue, e := loadCatalogue(cfg.CollectionDir)
	if e != nil {
		return nil, e
	}
	cfg.PublicURL = strings.TrimRight(cfg.PublicURL, "/")
	if e = os.MkdirAll(filepath.Join(cfg.DataDir, "artwork"), 0700); e != nil {
		return nil, e
	}
	keyPath := filepath.Join(cfg.DataDir, "session.key")
	f, e := os.OpenFile(keyPath, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if e == nil {
		_, e = f.WriteString(hex.EncodeToString([]byte(randomToken(32))))
		f.Close()
		if e != nil {
			return nil, e
		}
	} else if !os.IsExist(e) {
		return nil, e
	}
	key, e := os.ReadFile(keyPath)
	if e != nil {
		return nil, e
	}
	key = bytes.TrimSpace(key)
	if len(key) < 32 {
		return nil, errors.New("Session key is too short")
	}
	store, e := openStore(cfg.DataDir)
	if e != nil {
		return nil, e
	}
	fail := func(e error) (*App, error) { store.db.Close(); return nil, e }
	if e = store.seedCatalogue(catalogue); e != nil {
		return fail(e)
	}
	if e = store.importPreferences(cfg.PreferencesFile); e != nil {
		return fail(e)
	}
	a := &App{cfg: cfg, host: public.Hostname(), key: key, auth: hex.EncodeToString(mac(key, cfg.PasswordHash)), store: store, player: player, templates: map[string]*template.Template{}, metadataQueue: make(chan string, 64), art: map[string]map[string]string{}, discs: map[string][]DiscArtwork{}, glow: map[string]*GlowEffect{}}
	for uri, item := range catalogue.Items {
		if item.Glow != nil {
			a.glow[uri] = item.Glow
		}
		if len(item.Artwork) > 0 {
			a.art[uri] = item.Artwork
		}
		if len(item.Discs) > 0 {
			a.discs[uri] = item.Discs
		}
	}
	if e = a.loadBundledVariants(); e != nil {
		return fail(e)
	}
	// Existing personal uploads gain thumbnails once during the upgrade.
	entries, _ := os.ReadDir(filepath.Join(cfg.DataDir, "artwork"))
	for _, entry := range entries {
		if uploadPattern.MatchString(entry.Name()) {
			prepareUploadVariants(filepath.Join(cfg.DataDir, "artwork"), entry.Name())
		}
	}
	if len(entries) > 0 {
		debug.FreeOSMemory()
	}
	for _, name := range []string{"index", "login", "edit", "settings", "result", "error"} {
		t, e := template.ParseFS(resources, "views/base.html", "views/"+name+".html")
		if e != nil {
			return fail(e)
		}
		a.templates[name] = t
	}
	if a.player == nil {
		if cfg.Dev {
			a.player = PreviewPlayer{}
		} else {
			a.player = &Spotify{store: store, clientID: settingEnv("SPOTIFY_CLIENT_ID"), clientSecret: settingEnv("SPOTIFY_CLIENT_SECRET"), initialRefresh: settingEnv("SPOTIFY_REFRESH_TOKEN"), api: "https://api.spotify.com/v1", accounts: "https://accounts.spotify.com", http: &http.Client{Timeout: 15 * time.Second}}
		}
	}
	return a, nil
}
func main() {
	dev := flag.Bool("dev", false, "Local preview: fake playback and automatic sign-in")
	addr := flag.String("listen", ":8787", "HTTP listen address")
	health := flag.Bool("healthcheck", false, "Check local server health and exit")
	flag.Parse()
	if *health {
		c := http.Client{Timeout: 4 * time.Second}
		r, e := c.Get("http://127.0.0.1:8787/healthz")
		if e != nil || r.StatusCode != 200 {
			os.Exit(1)
		}
		r.Body.Close()
		return
	}
	cfg := Config{DataDir: os.Getenv("DATA_DIR"), PublicURL: os.Getenv("PUBLIC_URL"), PasswordHash: settingEnv("APP_PASSWORD_HASH"), Root: ".", Dev: *dev}
	cfg.CollectionDir = os.Getenv("COLLECTION_DIR")
	cfg.PreferencesFile = os.Getenv("PREFERENCES_FILE")
	if cfg.DataDir == "" {
		cfg.DataDir = "data"
	}
	if *dev {
		host, _, e := net.SplitHostPort(*addr)
		ip := net.ParseIP(host)
		if e != nil || ip == nil || !ip.IsLoopback() {
			log.Fatal("Dev mode requires a loopback listen address")
		}
		cfg.PublicURL = "http://" + *addr
		if os.Getenv("DATA_DIR") == "" {
			cfg.DataDir = ".dev-data"
		}
	}
	if os.Getenv("GOMEMLIMIT") == "" {
		debug.SetMemoryLimit(96 << 20)
	}
	if os.Getenv("GOGC") == "" {
		debug.SetGCPercent(50)
	}
	a, e := newApp(cfg, nil)
	if e != nil {
		log.Fatal(e)
	}
	defer a.store.db.Close()
	srv := &http.Server{Addr: *addr, Handler: a, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 45 * time.Second, WriteTimeout: 120 * time.Second, IdleTimeout: 30 * time.Second, MaxHeaderBytes: 32 << 10}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	a.startMetadata(ctx)
	go func() {
		<-ctx.Done()
		c, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		srv.Shutdown(c)
	}()
	log.Printf("FauxVinyl listening on %s (dev=%t)", *addr, *dev)
	if e = srv.ListenAndServe(); e != nil && e != http.ErrServerClosed {
		log.Fatal(e)
	}
}
func (a *App) page(w http.ResponseWriter, r *http.Request, s *Session, name string, p Page, status int) {
	p.Page = name
	p.CSRF = s.CSRF
	p.PublicURL = a.cfg.PublicURL
	p.Authenticated = equal(s.Auth, a.auth)
	p.Dev = a.cfg.Dev
	if p.Notice == "" {
		p.Notice = s.Notice
	}
	s.Notice = ""
	if p.Title == "" {
		p.Title = "FauxVinyl"
	}
	t := a.templates[name]
	if a.cfg.Dev {
		var e error
		t, e = template.ParseFiles(filepath.Join(a.cfg.Root, "views/base.html"), filepath.Join(a.cfg.Root, "views/"+name+".html"))
		if e != nil {
			log.Printf("template %s failed to parse", name)
			http.Error(w, "Template error", 500)
			return
		}
	}
	var b bytes.Buffer
	if e := t.ExecuteTemplate(&b, "base", p); e != nil {
		log.Printf("template %s failed to render", name)
		http.Error(w, "Template error", 500)
		return
	}
	a.cookie(w, s)
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(status)
	w.Write(b.Bytes())
}
func (a *App) fail(w http.ResponseWriter, r *http.Request, s *Session, status int, message string) {
	if wantsJSON(r) {
		writeJSON(w, status, map[string]string{"error": message})
		return
	}
	a.page(w, r, s, "error", Page{Title: "One moment · FauxVinyl", Error: message}, status)
}
func (a *App) redirect(w http.ResponseWriter, r *http.Request, s *Session, to string) {
	a.cookie(w, s)
	http.Redirect(w, r, to, 303)
}

var cardIDPattern = regexp.MustCompile(`^[a-z0-9-]+$`)
var uploadPattern = regexp.MustCompile(`^[a-f0-9]{64}\.(webp|jpg|png)$`)
var uploadAssetPattern = regexp.MustCompile(`^[a-f0-9]{64}(-w(160|320|640))?\.(webp|jpg|png)$`)
var uriPattern = regexp.MustCompile(`^spotify:(album|playlist|track):[A-Za-z0-9]{22}$`)
var spotifyPath = regexp.MustCompile(`^/(?:intl-[a-z]{2}/)?(album|playlist|track)/([A-Za-z0-9]{22})/?$`)
var slugPattern = regexp.MustCompile(`[^a-z0-9]+`)

func spotifyURI(v string) (string, error) {
	v = strings.TrimSpace(v)
	if uriPattern.MatchString(v) {
		return v, nil
	}
	u, e := url.Parse(v)
	if e == nil && u.Scheme == "https" && u.Host == "open.spotify.com" && u.User == nil {
		m := spotifyPath.FindStringSubmatch(u.Path)
		if m != nil {
			return "spotify:" + m[1] + ":" + m[2], nil
		}
	}
	return "", errors.New("Use a Spotify album, playlist, or track link.")
}
func safeNext(v string) string {
	if v == "/" || v == "/settings" {
		return v
	}
	if strings.HasPrefix(v, "/c/") && cardIDPattern.MatchString(strings.TrimPrefix(v, "/c/")) {
		return v
	}
	return "/"
}
func validTitle(v string) bool {
	return utf8.RuneCountInString(v) > 0 && utf8.RuneCountInString(v) <= 140
}
func (a *App) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Add("Vary", "Accept")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
	w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
	host := r.Host
	if h, _, e := net.SplitHostPort(host); e == nil {
		host = h
	}
	if host != a.host && !(r.URL.Path == "/healthz" && (host == "127.0.0.1" || host == "localhost")) {
		http.Error(w, "Unrecognized host", 400)
		return
	}
	s := a.readSession(r)
	if a.cfg.Dev {
		s.Auth = a.auth
	}
	if s.CSRF == "" {
		s.CSRF = randomToken(32)
	}
	defer func() {
		if recover() != nil {
			log.Print("Request failed unexpectedly")
			a.fail(w, r, &s, 500, "Something went wrong. Try again.")
		}
	}()
	if r.Method != "GET" && r.Method != "HEAD" && r.Method != "POST" {
		w.WriteHeader(405)
		return
	}
	if r.Method == "POST" {
		r.Body = http.MaxBytesReader(w, r.Body, 17<<20)
		var e error
		if strings.HasPrefix(r.Header.Get("Content-Type"), "multipart/form-data") {
			a.uploadMu.Lock()
			defer a.uploadMu.Unlock()
			defer debug.FreeOSMemory()
			e = r.ParseMultipartForm(500 << 10)
			if r.MultipartForm != nil {
				defer r.MultipartForm.RemoveAll()
				parts := 0
				for _, v := range r.MultipartForm.Value {
					parts += len(v)
				}
				for _, v := range r.MultipartForm.File {
					parts += len(v)
				}
				if parts > 30 {
					e = errors.New("too many parts")
				}
			}
		} else {
			e = r.ParseForm()
		}
		if e != nil {
			var tooBig *http.MaxBytesError
			if errors.As(e, &tooBig) {
				a.fail(w, r, &s, 413, "Upload up to two covers, 8 MB each. Go back and choose smaller files.")
			} else {
				a.fail(w, r, &s, 400, "Could not read this form. Reload and try again.")
			}
			return
		}
		if !equal(r.PostForm.Get("csrf"), s.CSRF) {
			a.fail(w, r, &s, 400, "This page expired. Reload it and try again.")
			return
		}
		origin := r.Header.Get("Origin")
		if origin != "" && origin != a.cfg.PublicURL && !(origin == "null" && r.Header.Get("Sec-Fetch-Site") == "same-origin") {
			a.fail(w, r, &s, 403, "The request came from a different site.")
			return
		}
	}
	path := r.URL.Path
	if r.Method != "POST" && path == "/healthz" {
		w.Header().Set("Content-Type", "application/json")
		io.WriteString(w, "{\"status\":\"ok\"}\n")
		return
	}
	if a.cfg.Dev && strings.HasPrefix(path, "/__dev__/") {
		a.devAsset(w, r)
		return
	}
	if r.Method != "POST" && strings.HasPrefix(path, "/static/") {
		if strings.HasPrefix(path, "/static/covers/") || strings.HasPrefix(path, "/static/discs/") || strings.HasPrefix(path, "/static/optimized/") {
			w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
			http.StripPrefix("/static/", http.FileServer(http.Dir(filepath.Join(a.cfg.CollectionDir, "static")))).ServeHTTP(w, r)
			return
		}
		http.StripPrefix("/static/", http.FileServer(http.Dir(filepath.Join(a.cfg.Root, "static")))).ServeHTTP(w, r)
		return
	}
	if path == "/login" {
		a.login(w, r, &s)
		return
	}
	if path == "/logout" && r.Method == "POST" {
		s = Session{CSRF: randomToken(32)}
		a.redirect(w, r, &s, "/login")
		return
	}
	if !equal(s.Auth, a.auth) {
		if wantsJSON(r) {
			writeJSON(w, 401, map[string]string{"error": "Your session expired. Sign in again.", "login_url": "/login?next=/"})
			return
		}
		a.redirect(w, r, &s, "/login?next="+url.QueryEscape(path))
		return
	}
	switch {
	case path == "/" && r.Method != "POST":
		a.shelf(w, r, &s, Page{})
	case path == "/shelf/order" && r.Method == "POST":
		a.saveShelfOrder(w, r, &s)
	case path == "/playback" && r.Method == "GET":
		a.playbackState(w, r)
	case path == "/playback" && r.Method == "POST":
		a.controlPlayback(w, r, &s)
	case path == "/cards" && r.Method == "POST":
		a.add(w, r, &s)
	case path == "/cards.csv" && r.Method != "POST":
		a.export(w, r, &s)
	case path == "/settings":
		a.settings(w, r, &s)
	case strings.HasPrefix(path, "/artwork/") && r.Method != "POST":
		name := strings.TrimPrefix(path, "/artwork/")
		if !uploadAssetPattern.MatchString(name) {
			a.fail(w, r, &s, 404, "Artwork not found.")
			return
		}
		w.Header().Set("Cache-Control", "private, max-age=31536000, immutable")
		http.ServeFile(w, r, filepath.Join(a.cfg.DataDir, "artwork", name))
	case strings.HasPrefix(path, "/cards/") && strings.HasSuffix(path, "/edit"):
		id := strings.TrimSuffix(strings.TrimPrefix(path, "/cards/"), "/edit")
		a.withCard(w, r, &s, id, true)
	case strings.HasPrefix(path, "/c/"):
		id := strings.TrimPrefix(path, "/c/")
		playing := strings.HasSuffix(id, "/play")
		if playing {
			id = strings.TrimSuffix(id, "/play")
		}
		if (playing && r.Method != "POST") || (!playing && r.Method == "POST") {
			w.WriteHeader(405)
			return
		}
		a.withCard(w, r, &s, id, false)
	default:
		a.fail(w, r, &s, 404, "This page is not on your shelf.")
	}
}
func (a *App) login(w http.ResponseWriter, r *http.Request, s *Session) {
	destination := safeNext(r.FormValue("next"))
	if r.Method == "POST" {
		a.loginMu.Lock()
		defer a.loginMu.Unlock()
		defer debug.FreeOSMemory()
		now := time.Now().Unix()
		if _, e := a.store.db.Exec("DELETE FROM login_failures WHERE created < ?", now-900); e != nil {
			panic(e)
		}
		var count int
		if e := a.store.db.QueryRow("SELECT COUNT(*) FROM login_failures").Scan(&count); e != nil {
			panic(e)
		}
		if count >= 30 {
			a.fail(w, r, s, 429, "Too many sign-in attempts. Try again in 15 minutes.")
			return
		}
		if !checkPassword(a.cfg.PasswordHash, r.PostForm.Get("password")) {
			if _, e := a.store.db.Exec("INSERT INTO login_failures VALUES(?)", now); e != nil {
				panic(e)
			}
			a.page(w, r, s, "login", Page{Title: "Sign in · FauxVinyl", Next: destination, LoginError: "That password did not match. Try again."}, 401)
			return
		}
		*s = Session{Auth: a.auth, CSRF: randomToken(32)}
		a.redirect(w, r, s, destination)
		return
	}
	if equal(s.Auth, a.auth) {
		a.redirect(w, r, s, destination)
		return
	}
	a.page(w, r, s, "login", Page{Title: "Sign in · FauxVinyl", Next: destination}, 200)
}
func (a *App) cardArt(c Card, custom map[string]string) map[string]string {
	art := map[string]string{}
	for side, file := range a.art[c.URI] {
		if side == "front" || side == "back" {
			art[side] = "/static/" + file
		}
	}
	for side, file := range custom {
		art[side] = "/artwork/" + file
	}
	return art
}
func (a *App) shelf(w http.ResponseWriter, r *http.Request, s *Session, p Page) {
	order := r.URL.Query().Get("sort")
	if order == "" {
		order = s.Sort
	}
	if _, ok := orders[order]; !ok {
		order = "title"
	}
	s.Sort = order
	cards, e := a.store.shelfCards(order)
	if e != nil {
		panic(e)
	}
	for i := range cards {
		art := a.cardArt(cards[i], cards[i].CustomArtwork)
		cards[i].Front = art["front"]
		cards[i].Back = art["back"]
		frontVariants := a.imageVariants(cards[i].Front)
		_, cards[i].FrontSrcset = variantSet(frontVariants, 0)
		_, cards[i].BackSrcset = variantSet(a.imageVariants(cards[i].Back), 0)
		cards[i].ShelfImage, cards[i].ShelfSrcset = variantSet(frontVariants, 320)
		if cards[i].ShelfImage == "" {
			cards[i].ShelfImage = cards[i].Front
		}
		discs := append([]DiscArtwork(nil), a.discs[cards[i].URI]...)
		for j := range discs {
			_, discs[j].Srcset = variantSet(a.imageVariants(discs[j].Image), 0)
		}
		options, _ := json.Marshal(discs)
		cards[i].Discs = string(options)
		glow, _ := json.Marshal(a.glow[cards[i].URI])
		cards[i].Glow = string(glow)
		cards[i].Tone = i % 5
	}
	q := []rune(r.URL.Query().Get("q"))
	if len(q) > 140 {
		q = q[:140]
	}
	p.Cards, p.Sort, p.Q, p.OrderVersion = cards, order, string(q), orderVersion(cardIDs(cards))
	a.page(w, r, s, "index", p, 200)
}
func (a *App) add(w http.ResponseWriter, r *http.Request, s *Session) {
	title := strings.TrimSpace(r.PostForm.Get("title"))
	if !validTitle(title) {
		a.fail(w, r, s, 400, "Enter a card title of 1–140 characters.")
		return
	}
	uri, e := spotifyURI(r.PostForm.Get("uri"))
	if e != nil {
		s.Notice = e.Error()
		a.redirect(w, r, s, "/")
		return
	}
	slug := strings.Trim(slugPattern.ReplaceAllString(strings.ToLower(title), "-"), "-")
	if len(slug) > 45 {
		slug = slug[:45]
	}
	if slug == "" {
		slug = "card"
	}
	c := Card{ID: slug + "-" + strings.ToLower(rand.Text()), Title: title, URI: uri}
	if e = a.store.create(c); e != nil {
		panic(e)
	}
	a.queueMetadata(c.URI)
	s.Notice = "Card added. Copy its permanent URL to your NFC tag."
	a.redirect(w, r, s, "/cards/"+c.ID+"/edit")
}
func (a *App) withCard(w http.ResponseWriter, r *http.Request, s *Session, id string, edit bool) {
	if !cardIDPattern.MatchString(id) {
		a.fail(w, r, s, 404, "This card is not on your shelf.")
		return
	}
	c, e := a.store.card(id)
	if e == sql.ErrNoRows {
		a.fail(w, r, s, 404, "This card is not on your shelf.")
		return
	}
	if e != nil {
		panic(e)
	}
	if edit {
		c.Metadata, e = a.store.metadata(c.URI)
		if e != nil {
			panic(e)
		}
		c.ReleaseDate, e = a.store.releaseDate(c.URI)
		if e != nil {
			panic(e)
		}
		a.edit(w, r, s, c)
		return
	}
	if r.Method == "POST" {
		a.play(w, r, s, c)
		return
	}
	if wantsJSON(r) {
		a.cookie(w, s)
		writeJSON(w, 200, map[string]string{"card_id": id, "csrf": s.CSRF, "action_token": a.action(id, s.CSRF)})
		return
	}
	a.shelf(w, r, s, Page{Card: c, ActionToken: a.action(id, s.CSRF)})
}
func (a *App) edit(w http.ResponseWriter, r *http.Request, s *Session, c Card) {
	custom, e := a.store.artwork(c.ID)
	if e != nil {
		panic(e)
	}
	art := a.cardArt(c, custom)
	p := Page{Card: c, Title: c.Title + " · FauxVinyl", Art: art, Custom: custom}
	if r.Method != "POST" {
		a.page(w, r, s, "edit", p, 200)
		return
	}
	title := strings.TrimSpace(r.PostForm.Get("title"))
	if !validTitle(title) {
		a.fail(w, r, s, 400, "Enter a card title of 1–140 characters.")
		return
	}
	uri, e := spotifyURI(r.PostForm.Get("uri"))
	if e != nil {
		s.Notice = e.Error()
		a.redirect(w, r, s, "/cards/"+c.ID+"/edit")
		return
	}
	oldURI := c.URI
	if uri == oldURI && strings.HasPrefix(uri, "spotify:album:") && r.PostForm.Has("release_date") {
		date := strings.TrimSpace(r.PostForm.Get("release_date"))
		if !validReleaseDate(date) {
			a.fail(w, r, s, 400, "Enter an original album release date in YYYY-MM-DD format.")
			return
		}
		c.ReleaseDateEdited = date != c.ReleaseDate
		c.ReleaseDate = date
	}
	if uri == oldURI && r.PostForm.Has("search_details") {
		m := SearchMetadata{strings.TrimSpace(r.PostForm.Get("artist")), strings.TrimSpace(r.PostForm.Get("album")), strings.TrimSpace(r.PostForm.Get("songs"))}
		if !m.valid() {
			a.fail(w, r, s, 400, "Search details are too long. Use up to 16 KB for artists, 2 KB for the album name and 64 KB for songs.")
			return
		}
		c.MetadataEdited = m != c.Metadata
		c.Metadata = m
	}
	if uri != oldURI {
		c.Metadata = SearchMetadata{}
	}
	c.Title = title
	c.URI = uri
	p.Card = c
	type cover struct {
		data []byte
		ext  string
	}
	prepared := map[string]cover{}
	resets := []string{}
	for _, side := range []string{"front", "back"} {
		if r.PostForm.Get("reset_"+side) != "" {
			resets = append(resets, side)
			continue
		}
		f, _, e := r.FormFile(side)
		if e == http.ErrMissingFile || e == http.ErrNotMultipart {
			continue
		}
		if e != nil {
			p.Error = "Could not read the cover."
			a.page(w, r, s, "edit", p, 400)
			return
		}
		data, ext, e := prepareCover(f)
		f.Close()
		if e != nil {
			p.Error = e.Error()
			a.page(w, r, s, "edit", p, 400)
			return
		}
		prepared[side] = cover{data, ext}
	}
	replacements := map[string]string{}
	for side, cover := range prepared {
		name, e := saveCover(filepath.Join(a.cfg.DataDir, "artwork"), cover.data, cover.ext)
		if e != nil {
			panic(e)
		}
		replacements[side] = name
	}
	if e = a.store.save(c, replacements, resets); e != nil {
		panic(e)
	}
	a.queueMetadata(c.URI)
	s.Notice = "Saved. Your NFC URL stays the same."
	a.redirect(w, r, s, "/cards/"+c.ID+"/edit")
}
func (a *App) play(w http.ResponseWriter, r *http.Request, s *Session, c Card) {
	action, ok := a.readAction(r.PostForm.Get("action_token"), c.ID, s.CSRF)
	if !ok {
		a.fail(w, r, s, 400, "This play request expired. Open the card again.")
		return
	}
	now := time.Now().Unix()
	if _, e := a.store.db.Exec("DELETE FROM used_actions WHERE expires < ?", now); e != nil {
		panic(e)
	}
	if result, e := a.store.db.Exec("INSERT OR IGNORE INTO used_actions VALUES(?,?)", action.Nonce, now+180); e != nil {
		panic(e)
	} else {
		n, e := result.RowsAffected()
		if e != nil {
			panic(e)
		}
		if n == 0 {
			a.fail(w, r, s, 409, "This tap was already processed. Open the card again to replay it.")
			return
		}
	}
	pref, _ := a.store.setting("device", "auto").(string)
	shuffle, _ := a.store.setting("shuffle", true).(bool)
	device, warning, e := a.player.Play(c.URI, pref, shuffle)
	p := Page{Title: c.Title + " · FauxVinyl", Card: c}
	status := 200
	if e != nil {
		p.Error = e.Error()
		status = 503
	}
	if wantsJSON(r) {
		if e != nil {
			a.fail(w, r, s, status, e.Error())
			return
		}
		writeJSON(w, status, map[string]any{"status": "playing", "card_id": c.ID, "title": c.Title, "device": device, "warning": warning, "preview": a.cfg.Dev})
		return
	}
	if e == nil {
		s.Notice = warning
		a.redirect(w, r, s, "/#record="+url.QueryEscape(c.ID))
		return
	}
	a.page(w, r, s, "result", p, status)
}
func (a *App) settings(w http.ResponseWriter, r *http.Request, s *Session) {
	if r.Method == "POST" {
		device := strings.TrimSpace(r.PostForm.Get("device"))
		if len(device) == 0 || utf8.RuneCountInString(device) > 200 {
			a.fail(w, r, s, 400, "Choose a valid device.")
			return
		}
		priority := strings.TrimSpace(r.PostForm.Get("device_priority"))
		if !validDevicePriority(strings.Split(priority, "\n")) {
			a.fail(w, r, s, 400, "Enter up to 20 preferred device names, at most 200 characters each.")
			return
		}
		if e := a.store.set("device", device); e != nil {
			panic(e)
		}
		if e := a.store.set("shuffle", r.PostForm.Get("shuffle") == "on"); e != nil {
			panic(e)
		}
		if e := a.store.set("device_priority", priority); e != nil {
			panic(e)
		}
		s.Notice = "Playback settings saved."
		a.redirect(w, r, s, "/settings")
		return
	}
	pref, _ := a.store.setting("device", "auto").(string)
	shuffle, _ := a.store.setting("shuffle", true).(bool)
	ds, e := a.player.Devices()
	p := Page{Title: "Settings · FauxVinyl", Preference: pref, Shuffle: shuffle, Devices: ds, Offline: pref != "auto"}
	p.DevicePriority, _ = a.store.setting("device_priority", "").(string)
	for _, d := range ds {
		if d.Name == pref {
			p.Offline = false
		}
	}
	if e != nil {
		p.Error = e.Error()
	}
	a.page(w, r, s, "settings", p, 200)
}
func (a *App) export(w http.ResponseWriter, r *http.Request, s *Session) {
	cards, e := a.store.cards("title")
	if e != nil {
		panic(e)
	}
	w.Header().Set("Content-Type", "text/csv; charset=utf-8")
	w.Header().Set("Content-Disposition", "attachment; filename=fauxvinyl-cards.csv")
	out := csv.NewWriter(w)
	out.UseCRLF = true
	out.Write([]string{"card_id", "title", "spotify_uri", "nfc_url"})
	for _, c := range cards {
		title := c.Title
		if title != "" && strings.ContainsRune("=+-@\t\r", rune(title[0])) {
			title = "'" + title
		}
		out.Write([]string{c.ID, title, c.URI, a.cfg.PublicURL + "/c/" + c.ID})
	}
	out.Flush()
}

// Share a lazily refreshed revision across tabs instead of scanning per request.
func (a *App) assetRevision(now time.Time) string {
	a.devRevisionMu.Lock()
	defer a.devRevisionMu.Unlock()
	if a.devRevision != "" && now.Sub(a.devRevisionChecked) < 3*time.Second {
		return a.devRevision
	}
	h := sha256.New()
	for _, dir := range []string{"views", "static"} {
		filepath.WalkDir(filepath.Join(a.cfg.Root, dir), func(path string, d os.DirEntry, e error) error {
			if e == nil && !d.IsDir() {
				info, e := d.Info()
				if e == nil {
					fmt.Fprint(h, path, info.ModTime().UnixNano(), info.Size())
				}
			}
			return nil
		})
	}
	a.devRevision = fmt.Sprintf("%x", h.Sum(nil))
	a.devRevisionChecked = now
	return a.devRevision
}

func (a *App) devAsset(w http.ResponseWriter, r *http.Request) {
	switch r.URL.Path {
	case "/__dev__/revision":
		w.Header().Set("Content-Type", "text/plain")
		io.WriteString(w, a.assetRevision(time.Now()))
	case "/__dev__/live.js":
		w.Header().Set("Content-Type", "application/javascript")
		io.WriteString(w, `'use strict';
(() => {
  let revision, timer, inFlight = false, stopped = false;
  function schedule() {
    clearTimeout(timer);
    if (!stopped && !document.hidden) timer = setTimeout(poll, 1500);
  }
  async function poll() {
    if (stopped || inFlight || document.hidden) return;
    inFlight = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch('/__dev__/revision', {cache: 'no-store', signal: controller.signal});
      if (!response.ok) throw new Error('Revision unavailable');
      const current = await response.text();
      if (revision && revision !== current) location.reload();
      revision = current;
    } catch { /* A stopped preview should not disrupt the page. */ }
    finally {
      clearTimeout(timeout);
      inFlight = false;
      schedule();
    }
  }
  document.addEventListener('visibilitychange', () => { clearTimeout(timer); if (!document.hidden) poll(); });
  window.addEventListener('pagehide', () => { stopped = true; clearTimeout(timer); });
  window.addEventListener('pageshow', () => { stopped = false; poll(); });
  poll();
})();`)
	case "/__dev__/dev.css":
		w.Header().Set("Content-Type", "text/css")
		io.WriteString(w, `form[action="/logout"]{display:none}`)
	default:
		http.NotFound(w, r)
	}
}
