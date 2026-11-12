package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"
)

// Public catalogue details are cached by Spotify URI, independently of a card's
// display name. Changing its link cannot retain an unrelated artist or song list.
type SearchMetadata struct {
	Artist string `json:"artist"`
	Album  string `json:"album"`
	Songs  string `json:"songs"`
}

func (m SearchMetadata) valid() bool {
	return utf8.ValidString(m.Artist+m.Album+m.Songs) && len(m.Artist) <= 16000 && len(m.Album) <= 2000 && len(m.Songs) <= 64000
}

func (s *Store) metadata(uri string) (SearchMetadata, error) {
	var m SearchMetadata
	e := s.db.QueryRow("SELECT artist,album,songs FROM search_metadata WHERE uri=?", uri).Scan(&m.Artist, &m.Album, &m.Songs)
	if e == sql.ErrNoRows {
		e = nil
	}
	return m, e
}

func (s *Store) cacheMetadata(uri string, m SearchMetadata, success bool) error {
	if !success {
		_, e := s.db.Exec(`INSERT INTO search_metadata(uri,artist,album,songs,checked_at) VALUES(?,'','','',?)
 ON CONFLICT(uri) DO UPDATE SET checked_at=excluded.checked_at WHERE custom=0`, uri, time.Now().Unix())
		return e
	}
	_, e := s.db.Exec(`INSERT INTO search_metadata(uri,artist,album,songs,checked_at) VALUES(?,?,?,?,?)
 ON CONFLICT(uri) DO UPDATE SET artist=excluded.artist,album=excluded.album,songs=excluded.songs,checked_at=excluded.checked_at WHERE custom=0`, uri, m.Artist, m.Album, m.Songs, time.Now().Unix())
	return e
}

func (s *Store) metadataDue(uri string) bool {
	var custom, checked int64
	var artist, album, songs string
	e := s.db.QueryRow("SELECT custom,checked_at,artist,album,songs FROM search_metadata WHERE uri=?", uri).Scan(&custom, &checked, &artist, &album, &songs)
	if e == sql.ErrNoRows {
		return true
	}
	if e != nil || custom != 0 {
		return false
	}
	complete := artist != "" && songs != "" && (album != "" || strings.HasPrefix(uri, "spotify:track:"))
	if complete && !strings.HasPrefix(uri, "spotify:playlist:") {
		return false
	}
	age := 24 * time.Hour
	if complete {
		age = 7 * 24 * time.Hour
	}
	return time.Since(time.Unix(checked, 0)) >= age
}

var embedData = regexp.MustCompile(`(?s)<script\b[^>]*\bid=["']__NEXT_DATA__["'][^>]*>(.*?)</script>`)

func parseSearchMetadata(raw []byte, uri string) (SearchMetadata, error) {
	var m SearchMetadata
	match := embedData.FindSubmatch(raw)
	if len(match) != 2 {
		return m, errors.New("No public track listing available")
	}
	var data struct {
		Props struct {
			PageProps struct {
				State struct {
					Data struct {
						Entity struct {
							URI, Type, Title, Subtitle string
							TrackList                  []struct{ Title, Subtitle string }
						}
					}
				}
			}
		}
	}
	if e := json.Unmarshal(match[1], &data); e != nil {
		return m, e
	}
	entity := data.Props.PageProps.State.Data.Entity
	if entity.URI != uri || entity.Title == "" {
		return m, errors.New("Public listing did not match this record")
	}
	artists, songs := []string{}, []string{}
	seenArtists, seenSongs := map[string]bool{}, map[string]bool{}
	add := func(value string, seen map[string]bool, list *[]string) {
		value = strings.TrimSpace(value)
		if value != "" && !seen[value] {
			seen[value] = true
			*list = append(*list, value)
		}
	}
	if entity.Type != "playlist" {
		add(entity.Subtitle, seenArtists, &artists)
	}
	for _, song := range entity.TrackList {
		add(song.Title, seenSongs, &songs)
		add(song.Subtitle, seenArtists, &artists)
	}
	if entity.Type == "track" {
		add(entity.Title, seenSongs, &songs)
	} else {
		m.Album = entity.Title
	}
	m.Artist, m.Songs = strings.Join(artists, "\n"), strings.Join(songs, "\n")
	if !m.valid() || (m.Artist == "" && m.Songs == "") {
		return SearchMetadata{}, errors.New("Incomplete public track listing")
	}
	return m, nil
}

func fetchSearchMetadata(ctx context.Context, client *http.Client, base, uri string) (SearchMetadata, error) {
	checked, e := spotifyURI(uri)
	if e != nil || checked != uri {
		return SearchMetadata{}, errors.New("Invalid Spotify URI")
	}
	path := strings.ReplaceAll(strings.TrimPrefix(uri, "spotify:"), ":", "/")
	req, e := http.NewRequestWithContext(ctx, "GET", base+"/embed/"+path, nil)
	if e != nil {
		return SearchMetadata{}, e
	}
	res, e := client.Do(req)
	if e != nil {
		return SearchMetadata{}, e
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		return SearchMetadata{}, errors.New("Public Spotify listing is unavailable")
	}
	raw, e := io.ReadAll(io.LimitReader(res.Body, (2<<20)+1))
	if e != nil || len(raw) > 2<<20 {
		return SearchMetadata{}, errors.New("Could not read public Spotify listing")
	}
	return parseSearchMetadata(raw, uri)
}

func (a *App) queueMetadata(uri string) {
	select {
	case a.metadataQueue <- uri:
	default:
	}
}

// One bounded worker avoids slowing down page loads or retaining a web client
// per card. It needs no playback credentials and never makes playback requests.
func (a *App) startMetadata(ctx context.Context) {
	go func() {
		client := &http.Client{Timeout: 10 * time.Second}
		defer client.CloseIdleConnections()
		refresh := func(uri string) {
			if !a.store.metadataDue(uri) || ctx.Err() != nil {
				return
			}
			m, e := fetchSearchMetadata(ctx, client, "https://open.spotify.com", uri)
			if ctx.Err() != nil {
				return
			}
			if e = a.store.cacheMetadata(uri, m, e == nil); e != nil {
				log.Print("Could not save search details")
			}
		}
		cards, e := a.store.cards("custom")
		if e == nil {
			for _, card := range cards {
				refresh(card.URI)
			}
		}
		for {
			select {
			case <-ctx.Done():
				return
			case uri := <-a.metadataQueue:
				refresh(uri)
			}
		}
	}()
}
