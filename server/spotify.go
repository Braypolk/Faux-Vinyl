package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

type Device struct {
	ID         string `json:"id"`
	Name       string `json:"name"`
	Active     bool   `json:"is_active"`
	Restricted bool   `json:"is_restricted"`
}
type Player interface {
	Devices() ([]Device, error)
	Play(string, string, bool) (string, string, error)
}
type PreviewPlayer struct{}

func (PreviewPlayer) Devices() ([]Device, error) {
	return []Device{{ID: "preview", Name: "Local preview", Active: true}}, nil
}
func (PreviewPlayer) Play(string, string, bool) (string, string, error) {
	return "Local preview", "Preview only — no music was started.", nil
}

type Spotify struct {
	store                                         *Store
	clientID, clientSecret, initialRefresh, token string
	expires                                       time.Time
	http                                          *http.Client
	api, accounts                                 string
	mu                                            sync.Mutex
	playMu                                        sync.Mutex
}

func (s *Spotify) accessToken(force bool) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if !force && s.token != "" && time.Now().Before(s.expires) {
		return s.token, nil
	}
	refresh, _ := s.store.setting("spotify_refresh_token", s.initialRefresh).(string)
	if s.clientID == "" || s.clientSecret == "" || refresh == "" {
		return "", errors.New("Spotify credentials are missing from the app configuration.")
	}
	values := url.Values{"grant_type": {"refresh_token"}, "refresh_token": {refresh}}
	req, _ := http.NewRequest("POST", s.accounts+"/api/token", strings.NewReader(values.Encode()))
	req.SetBasicAuth(s.clientID, s.clientSecret)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	res, e := s.http.Do(req)
	if e != nil {
		return "", errors.New("Could not reach Spotify. Try again in a moment.")
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		if res.StatusCode == 400 || res.StatusCode == 401 {
			return "", errors.New("Spotify authorization needs attention. Renew the refresh token or check the client credentials.")
		}
		return "", errors.New("Spotify token service is unavailable. Try again shortly.")
	}
	var result struct {
		Access  string `json:"access_token"`
		Refresh string `json:"refresh_token"`
		Expires int    `json:"expires_in"`
	}
	if json.NewDecoder(io.LimitReader(res.Body, 1<<20)).Decode(&result) != nil || result.Access == "" {
		return "", errors.New("Spotify returned an unexpected token response.")
	}
	if result.Refresh != "" {
		if e = s.store.set("spotify_refresh_token", result.Refresh); e != nil {
			return "", errors.New("Could not save Spotify authorization. Try again.")
		}
	}
	if result.Expires == 0 {
		result.Expires = 3600
	}
	s.token = result.Access
	s.expires = time.Now().Add(time.Duration(max(0, result.Expires-60)) * time.Second)
	return s.token, nil
}
func (s *Spotify) request(method, path string, body any, out any) error {
	for attempt := 0; attempt < 2; attempt++ {
		token, e := s.accessToken(attempt > 0)
		if e != nil {
			return e
		}
		var data []byte
		if body != nil {
			data, e = json.Marshal(body)
			if e != nil {
				return e
			}
		}
		req, _ := http.NewRequest(method, s.api+"/"+path, bytes.NewReader(data))
		req.Header.Set("Authorization", "Bearer "+token)
		if body != nil {
			req.Header.Set("Content-Type", "application/json")
		}
		res, e := s.http.Do(req)
		if e != nil {
			return errors.New("Could not reach Spotify. Try again in a moment.")
		}
		raw, e := io.ReadAll(io.LimitReader(res.Body, 1<<20))
		res.Body.Close()
		if e != nil {
			return errors.New("Could not read Spotify's response.")
		}
		if res.StatusCode == 401 && attempt == 0 {
			continue
		}
		switch {
		case res.StatusCode == 429:
			return errors.New("Spotify is rate limiting requests. Wait a moment before trying again.")
		case res.StatusCode == 403:
			if bytes.Contains(raw, []byte("Active premium subscription required for the owner of the app")) {
				return errors.New("Spotify requires active Premium on the account that owns this developer app. Check that owner account’s subscription; changes can take a few hours to apply.")
			}
			return errors.New("Spotify denied playback. Check Premium membership, playback permissions, and app access.")
		case res.StatusCode >= 400:
			return errors.New("Spotify could not complete the request. Open Spotify on the speaker or device and try again.")
		}
		if out != nil && len(raw) > 0 && json.Unmarshal(raw, out) != nil {
			return errors.New("Spotify returned an unexpected response.")
		}
		return nil
	}
	return errors.New("Spotify authorization could not be refreshed.")
}
func (s *Spotify) Devices() ([]Device, error) {
	var result struct {
		Devices []Device `json:"devices"`
	}
	if e := s.request("GET", "me/player/devices", nil, &result); e != nil {
		return nil, e
	}
	out := []Device{}
	for _, d := range result.Devices {
		if d.ID != "" && !d.Restricted {
			out = append(out, d)
		}
	}
	return out, nil
}

func (s *Spotify) PlaybackState() (PlaybackState, error) {
	var result struct {
		Playing bool `json:"is_playing"`
		Context struct {
			URI string `json:"uri"`
		} `json:"context"`
		Item struct {
			URI   string `json:"uri"`
			Album struct {
				URI string `json:"uri"`
			} `json:"album"`
		} `json:"item"`
	}
	if err := s.request("GET", "me/player", nil, &result); err != nil {
		return PlaybackState{}, err
	}
	return PlaybackState{Playing: result.Playing, ContextURI: result.Context.URI, AlbumURI: result.Item.Album.URI, ItemURI: result.Item.URI}, nil
}

// Change transport on the current device without replacing its queue or position.
func (s *Spotify) SetPlaying(uri string, playing bool) error {
	s.playMu.Lock()
	defer s.playMu.Unlock()
	var current struct {
		Playing bool `json:"is_playing"`
		Device  struct {
			ID string `json:"id"`
		} `json:"device"`
		Context struct {
			URI string `json:"uri"`
		} `json:"context"`
		Item struct {
			URI   string `json:"uri"`
			Album struct {
				URI string `json:"uri"`
			} `json:"album"`
		} `json:"item"`
	}
	if err := s.request("GET", "me/player", nil, &current); err != nil {
		return err
	}
	if current.Device.ID == "" || (uri != current.Context.URI && uri != current.Item.Album.URI && uri != current.Item.URI) {
		return errPlaybackChanged
	}
	if current.Playing == playing {
		return nil
	}
	action := "pause"
	if playing {
		action = "play"
	}
	return s.request("PUT", "me/player/"+action+"?"+url.Values{"device_id": {current.Device.ID}}.Encode(), nil, nil)
}
func chooseDevice(ds []Device, pref, priority string) (Device, error) {
	if pref != "auto" {
		for _, d := range ds {
			if d.Name == pref || d.ID == pref {
				return d, nil
			}
		}
		return Device{}, errors.New("Your selected device is offline. Open Spotify on it, or choose another device in Settings.")
	}
	for _, d := range ds {
		if d.Active {
			return d, nil
		}
	}
	for _, name := range strings.Split(priority, "\n") {
		name = strings.TrimSpace(name)
		if name == "" {
			continue
		}
		for _, d := range ds {
			if d.Name == name {
				return d, nil
			}
		}
	}
	if len(ds) == 1 {
		return ds[0], nil
	}
	if len(ds) == 0 {
		return Device{}, errors.New("No Spotify devices are available. Open Spotify on the device you want to use.")
	}
	return Device{}, errors.New("Choose a playback device in Settings, or start Spotify on one device first.")
}
func (s *Spotify) Play(uri, pref string, shuffle bool) (string, string, error) {
	s.playMu.Lock()
	defer s.playMu.Unlock()
	ds, e := s.Devices()
	if e != nil {
		return "", "", e
	}
	priority, _ := s.store.setting("device_priority", "").(string)
	d, e := chooseDevice(ds, pref, priority)
	if e != nil {
		return "", "", e
	}
	if !d.Active {
		if e = s.request("PUT", "me/player", map[string]any{"device_ids": []string{d.ID}, "play": false}, nil); e != nil {
			return "", "", e
		}
	}
	body := map[string]any{"context_uri": uri}
	if strings.HasPrefix(uri, "spotify:track:") {
		body = map[string]any{"uris": []string{uri}}
	}
	q := url.Values{"device_id": {d.ID}}
	if e = s.request("PUT", "me/player/play?"+q.Encode(), body, nil); e != nil {
		return "", "", e
	}
	q.Set("state", fmt.Sprint(shuffle))
	warning := ""
	if s.request("PUT", "me/player/shuffle?"+q.Encode(), nil, nil) != nil {
		warning = "Playback started, but Spotify could not update shuffle."
	}
	return d.Name, warning, nil
}
