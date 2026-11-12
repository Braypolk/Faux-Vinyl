package main

import (
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"
)

func TestSpotifyPauseResumePreservesQueueAndPosition(t *testing.T) {
	playing := true
	context := "spotify:album:one"
	var writes []string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "GET" {
			io.WriteString(w, `{"device":{"id":"actual TV"},"is_playing":`+map[bool]string{true: "true", false: "false"}[playing]+`,"context":{"uri":"`+context+`"}}`)
			return
		}
		body, _ := io.ReadAll(r.Body)
		if len(body) != 0 || r.URL.Query().Get("device_id") != "actual TV" {
			t.Error("transport must target the actual device and preserve its queue", string(body), r.URL)
		}
		writes = append(writes, r.URL.Path)
		playing = strings.HasSuffix(r.URL.Path, "/play")
		w.WriteHeader(204)
	}))
	defer server.Close()
	s := &Spotify{api: server.URL, http: server.Client(), token: "token", expires: time.Now().Add(time.Hour)}
	if err := s.SetPlaying(context, false); err != nil {
		t.Fatal(err)
	}
	if err := s.SetPlaying(context, false); err != nil {
		t.Fatal(err)
	}
	if err := s.SetPlaying(context, true); err != nil {
		t.Fatal(err)
	}
	if strings.Join(writes, ",") != "/me/player/pause,/me/player/play" {
		t.Fatal(writes)
	}
	context = "spotify:album:another"
	if err := s.SetPlaying("spotify:album:one", false); !errors.Is(err, errPlaybackChanged) || len(writes) != 2 {
		t.Fatal("must not pause unrelated playback", err, writes)
	}
}

type transportPlayer struct {
	controlledPlayer
	calls   []bool
	failure error
}

func (p *transportPlayer) SetPlaying(_ string, playing bool) error {
	p.calls = append(p.calls, playing)
	return p.failure
}

func TestTransportRequiresAuthCSRFAndCurrentRecord(t *testing.T) {
	a := testApp(t)
	p := &transportPlayer{}
	a.player = p
	b := &browser{a: a}
	if w := b.request("POST", "/playback", nil, jsonHeaders); w.Code == 200 {
		t.Fatal("anonymous transport allowed")
	}
	csrf := signIn(t, b)
	cards, _ := a.store.cards("title")
	form := url.Values{"csrf": {csrf}, "card_id": {cards[0].ID}, "action": {"pause"}}
	bad := url.Values{"csrf": {"wrong"}, "card_id": {cards[0].ID}, "action": {"pause"}}
	if w := b.request("POST", "/playback", bad, jsonHeaders); w.Code == 200 || len(p.calls) != 0 {
		t.Fatal("missing CSRF allowed")
	}
	if w := b.request("POST", "/playback", form, map[string]string{"Accept": "application/json", "Origin": "https://other.example"}); w.Code != 403 || len(p.calls) != 0 {
		t.Fatal("foreign origin allowed")
	}
	w := b.request("POST", "/playback", form, jsonHeaders)
	if w.Code != 200 || jsonBody(t, w)["is_playing"] != false || len(p.calls) != 1 || p.calls[0] {
		t.Fatal(w.Code, w.Body.String(), p.calls)
	}
	form.Set("action", "resume")
	w = b.request("POST", "/playback", form, jsonHeaders)
	if w.Code != 200 || jsonBody(t, w)["is_playing"] != true || !p.calls[1] {
		t.Fatal(w.Code, w.Body.String())
	}
	p.failure = errPlaybackChanged
	if w := b.request("POST", "/playback", form, jsonHeaders); w.Code != 409 {
		t.Fatal(w.Code, w.Body.String())
	}
	form.Set("card_id", "missing")
	if w := b.request("POST", "/playback", form, jsonHeaders); w.Code != 404 {
		t.Fatal(w.Code)
	}
}
