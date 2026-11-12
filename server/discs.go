package main

import (
	"errors"
	"net/http"
)

var errPlaybackChanged = errors.New("Playback changed on your device. Refresh the playback state and try again.")

type playbackController interface{ SetPlaying(string, bool) error }

func (a *App) controlPlayback(w http.ResponseWriter, r *http.Request, s *Session) {
	c, err := a.store.card(r.PostForm.Get("card_id"))
	if err != nil || c.ID == "" {
		a.fail(w, r, s, 404, "This record is not on your shelf.")
		return
	}
	action := r.PostForm.Get("action")
	if action != "pause" && action != "resume" {
		a.fail(w, r, s, 400, "Choose pause or resume.")
		return
	}
	if !a.cfg.Dev {
		controller, ok := a.player.(playbackController)
		if !ok {
			a.fail(w, r, s, 503, "Playback controls unavailable.")
			return
		}
		if err := controller.SetPlaying(c.URI, action == "resume"); err != nil {
			status := 503
			if errors.Is(err, errPlaybackChanged) {
				status = 409
			}
			a.fail(w, r, s, status, err.Error())
			return
		}
	}
	writeJSON(w, 200, map[string]any{"card_id": c.ID, "is_playing": action == "resume", "context_uri": c.URI, "preview": a.cfg.Dev})
}

// Approved variants are bundled by album URI, independent of shelf title/order.
type DiscArtwork struct {
	ID     string `json:"id"`
	Kind   string `json:"kind"`
	Label  string `json:"label"`
	Image  string `json:"image"`
	Srcset string `json:"srcset,omitempty"`
}

type PlaybackState struct {
	Playing    bool   `json:"is_playing"`
	ContextURI string `json:"context_uri"`
	AlbumURI   string `json:"album_uri"`
	ItemURI    string `json:"item_uri"`
}

type playbackReader interface {
	PlaybackState() (PlaybackState, error)
}

func (a *App) playbackState(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	if a.cfg.Dev {
		writeJSON(w, 200, PlaybackState{})
		return
	}
	reader, ok := a.player.(playbackReader)
	if !ok {
		writeJSON(w, 503, map[string]string{"error": "Playback state unavailable."})
		return
	}
	state, err := reader.PlaybackState()
	if err != nil {
		writeJSON(w, 503, map[string]string{"error": "Playback state unavailable."})
		return
	}
	writeJSON(w, 200, state)
}
