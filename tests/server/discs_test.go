package main

import (
	"encoding/json"
	"html"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
	"time"
)

func TestApprovedDiscCatalogue(t *testing.T) {
	a := testApp(t)
	count := 0
	seen := map[string]bool{}
	for uri, options := range a.discs {
		if !strings.HasPrefix(uri, "spotify:album:") {
			t.Fatal("disc artwork must be keyed by album URI", uri)
		}
		for _, o := range options {
			count++
			if seen[o.ID] || (o.Kind != "cd" && o.Kind != "vinyl") || o.Label == "" || !strings.HasPrefix(o.Image, "/static/discs/") {
				t.Fatal("invalid or duplicate approved artwork", o)
			}
			seen[o.ID] = true
			if _, err := os.Stat(filepath.Join(a.cfg.CollectionDir, strings.TrimPrefix(o.Image, "/"))); err != nil {
				t.Fatal("approved asset missing", o.Image, err)
			}
		}
	}
	if count != 11 || len(a.discs) != 5 {
		t.Fatal("expected all approved choices", count, len(a.discs))
	}
	b := &browser{a: a}
	signIn(t, b)
	w := b.request("GET", "/", nil, nil)
	if w.Code != 200 || strings.Contains(w.Body.String(), "disc-prototype.js") {
		t.Fatal("main app must load the integrated artwork")
	}
	attrs := regexp.MustCompile(`data-disc-options="([^"]+)"`).FindAllStringSubmatch(w.Body.String(), -1)
	if len(attrs) != 7 {
		t.Fatal("missing per-album options", len(attrs))
	}
	for _, attr := range attrs {
		var options []DiscArtwork
		if err := json.Unmarshal([]byte(html.UnescapeString(attr[1])), &options); err != nil {
			t.Fatal("invalid escaped artwork JSON", err)
		}
	}
}

func TestSpotifyPlaybackState(t *testing.T) {
	for _, tc := range []struct {
		name, body string
		status     int
		want       PlaybackState
	}{
		{"playing", `{"is_playing":true,"context":{"uri":"spotify:playlist:mix"},"item":{"album":{"uri":"spotify:album:one"}}}`, 200, PlaybackState{Playing: true, ContextURI: "spotify:playlist:mix", AlbumURI: "spotify:album:one"}},
		{"paused", `{"is_playing":false,"context":{"uri":"spotify:album:one"},"item":{"album":{"uri":"spotify:album:one"}}}`, 200, PlaybackState{ContextURI: "spotify:album:one", AlbumURI: "spotify:album:one"}},
		{"track", `{"is_playing":true,"context":null,"item":{"uri":"spotify:track:one","album":{"uri":"spotify:album:one"}}}`, 200, PlaybackState{Playing: true, AlbumURI: "spotify:album:one", ItemURI: "spotify:track:one"}},
		{"idle", "", 204, PlaybackState{}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path != "/me/player" || r.Method != "GET" || r.Header.Get("Authorization") != "Bearer token" {
					t.Error("unexpected playback read", r.URL.Path, r.Method)
				}
				w.WriteHeader(tc.status)
				w.Write([]byte(tc.body))
			}))
			defer server.Close()
			s := &Spotify{api: server.URL, http: server.Client(), token: "token", expires: time.Now().Add(time.Hour)}
			got, err := s.PlaybackState()
			if err != nil || got != tc.want {
				t.Fatal(got, err)
			}
		})
	}
}

func TestPlaybackStateRequiresSignIn(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	if w := b.request("GET", "/playback", nil, map[string]string{"Accept": "application/json"}); w.Code != 401 {
		t.Fatal("playback state must require authentication", w.Code)
	}
	signIn(t, b)
	// The preview player has no real playback reader and must fail quietly.
	w := b.request("GET", "/playback", nil, map[string]string{"Accept": "application/json"})
	if w.Code != 503 || w.Header().Get("Cache-Control") != "no-store" {
		t.Fatal(w.Code, w.Header())
	}
	a.cfg.Dev = true
	w = b.request("GET", "/playback", nil, map[string]string{"Accept": "application/json"})
	if w.Code != 200 || strings.Contains(w.Body.String(), `"is_playing":true`) {
		t.Fatal("development mode must not claim real music is playing", w.Code)
	}
}
