package main

import (
	"database/sql"
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
