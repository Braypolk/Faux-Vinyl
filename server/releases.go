package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"strings"
	"time"
)

// These are original album dates, independently reviewed rather than dates of
// Spotify reissues. They are cached by URI so changing a card's link cannot
// retain another album's date. A stored blank is an intentional manual reset.
func validReleaseDate(date string) bool {
	if date == "" {
		return true
	}
	t, e := time.Parse("2006-01-02", date)
	return e == nil && t.Year() >= 1900 && t.Year() <= 9999 && t.Format("2006-01-02") == date
}

func (s *Store) releaseDate(uri string) (string, error) {
	var date string
	e := s.db.QueryRow("SELECT release_date FROM album_releases WHERE uri=?", uri).Scan(&date)
	if e == sql.ErrNoRows {
		e = nil
	}
	return date, e
}

func (s *Store) seedReleaseDates(raw []byte) error {
	var dates map[string]struct {
		Date string `json:"date"`
	}
	if e := json.Unmarshal(raw, &dates); e != nil {
		return e
	}
	tx, e := s.db.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	for uri, release := range dates {
		checked, err := spotifyURI(uri)
		if err != nil || uri != checked || !strings.HasPrefix(uri, "spotify:album:") || release.Date == "" || !validReleaseDate(release.Date) {
			return errors.New("Invalid bundled original release date")
		}
		if _, e = tx.Exec("INSERT OR IGNORE INTO album_releases(uri,release_date) VALUES(?,?)", uri, release.Date); e != nil {
			return e
		}
	}
	return tx.Commit()
}
