package main

import (
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	_ "github.com/mattn/go-sqlite3"
	"net/url"
	"path/filepath"
	"strings"
)

type Card struct {
	ID                                               string `json:"id"`
	Title                                            string `json:"title"`
	URI                                              string `json:"uri"`
	Created                                          string
	Front, Back                                      string
	FrontSrcset, BackSrcset, ShelfImage, ShelfSrcset string
	Discs, Glow                                      string
	Tone                                             int
	Metadata                                         SearchMetadata
	CustomArtwork                                    map[string]string `json:"-"`
	MetadataEdited                                   bool
	ReleaseDate                                      string
	ReleaseDateEdited                                bool
}
type Store struct{ db *sql.DB }

var orders = map[string]string{"title": "title COLLATE NOCASE,id", "title-desc": "title COLLATE NOCASE DESC,id", "newest": "release", "oldest": "release", "custom": "custom"}

func openStore(dir string) (*Store, error) {
	dsn := "file:" + filepath.ToSlash(filepath.Join(dir, "fauxvinyl.sqlite3")) + "?" + url.Values{"_busy_timeout": {"15000"}, "_cache_size": {"-512"}, "_journal_mode": {"DELETE"}}.Encode()
	db, e := sql.Open("sqlite3", dsn)
	if e != nil {
		return nil, e
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	s := &Store{db}
	_, e = db.Exec(`CREATE TABLE IF NOT EXISTS cards(id TEXT PRIMARY KEY,title TEXT NOT NULL,uri TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
 CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS card_artwork(card_id TEXT NOT NULL,side TEXT NOT NULL,filename TEXT NOT NULL,PRIMARY KEY(card_id,side));
 CREATE TABLE IF NOT EXISTS album_releases(uri TEXT PRIMARY KEY,release_date TEXT NOT NULL,custom INTEGER NOT NULL DEFAULT 0);
 CREATE TABLE IF NOT EXISTS shelf_order(card_id TEXT PRIMARY KEY,position INTEGER NOT NULL);
 INSERT OR IGNORE INTO shelf_order(card_id,position)
 SELECT id,COALESCE((SELECT MAX(position)+1 FROM shelf_order),0)+ROW_NUMBER() OVER(ORDER BY title COLLATE NOCASE,id)-1
 FROM cards WHERE id NOT IN (SELECT card_id FROM shelf_order);
 CREATE TABLE IF NOT EXISTS used_actions(nonce TEXT PRIMARY KEY,expires INTEGER NOT NULL);
 CREATE TABLE IF NOT EXISTS login_failures(created REAL NOT NULL); PRAGMA mmap_size=0;`)
	if e != nil {
		db.Close()
		return nil, e
	}
	if _, e = db.Exec(`CREATE TABLE IF NOT EXISTS search_metadata(uri TEXT PRIMARY KEY,artist TEXT NOT NULL,album TEXT NOT NULL,songs TEXT NOT NULL,custom INTEGER NOT NULL DEFAULT 0,checked_at INTEGER NOT NULL)`); e != nil {
		db.Close()
		return nil, e
	}
	// Older releases have no provenance. Leave them unclassified until their
	// collection is available; matching defaults can then be recognized safely.
	rows, e := db.Query("PRAGMA table_info(album_releases)")
	if e != nil {
		db.Close()
		return nil, e
	}
	hasCustom := false
	for rows.Next() {
		var cid, required, primary int
		var name, kind string
		var fallback any
		if e = rows.Scan(&cid, &name, &kind, &required, &fallback, &primary); e != nil {
			break
		}
		hasCustom = hasCustom || name == "custom"
	}
	if e == nil {
		e = rows.Err()
	}
	rows.Close()
	if e == nil && !hasCustom {
		_, e = db.Exec("ALTER TABLE album_releases ADD COLUMN custom INTEGER")
	}
	if e != nil {
		db.Close()
		return nil, e
	}
	return s, nil
}
func (s *Store) setting(k string, fallback any) any {
	var raw string
	if s.db.QueryRow("SELECT value FROM settings WHERE key=?", k).Scan(&raw) != nil {
		return fallback
	}
	var out any
	if json.Unmarshal([]byte(raw), &out) != nil {
		return fallback
	}
	return out
}
func (s *Store) set(k string, v any) error {
	b, e := json.Marshal(v)
	if e != nil {
		return e
	}
	_, e = s.db.Exec("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", k, string(b))
	return e
}
func (s *Store) cards(order string) ([]Card, error) {
	o, ok := orders[order]
	if !ok {
		o = orders["title"]
	}
	query := "SELECT id,title,uri,created_at FROM cards ORDER BY " + o
	if order == "custom" {
		query = customCardsSQL
	} else if order == "newest" || order == "oldest" {
		direction := "ASC"
		if order == "newest" {
			direction = "DESC"
		}
		query = `SELECT c.id,c.title,c.uri,c.created_at FROM cards c
 LEFT JOIN album_releases d ON d.uri=c.uri
 ORDER BY COALESCE(d.release_date,'')='',d.release_date ` + direction + `,c.title COLLATE NOCASE,c.id`
	}
	rows, e := s.db.Query(query)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	out := []Card{}
	for rows.Next() {
		var c Card
		if e = rows.Scan(&c.ID, &c.Title, &c.URI, &c.Created); e != nil {
			return nil, e
		}
		out = append(out, c)
	}
	return out, rows.Err()
}
func (s *Store) card(id string) (Card, error) {
	var c Card
	e := s.db.QueryRow("SELECT id,title,uri,created_at FROM cards WHERE id=?", id).Scan(&c.ID, &c.Title, &c.URI, &c.Created)
	return c, e
}

// Load shelf details in one bulk read, preserving the ordering used by cards.
func (s *Store) shelfCards(order string) ([]Card, error) {
	cards, err := s.cards(order)
	if err != nil || len(cards) == 0 {
		return cards, err
	}
	byID := make(map[string]*Card, len(cards))
	for i := range cards {
		byID[cards[i].ID] = &cards[i]
	}
	rows, err := s.db.Query(`SELECT c.id,COALESCE(m.artist,''),COALESCE(m.album,''),COALESCE(m.songs,''),
 COALESCE(f.filename,''),COALESCE(b.filename,'') FROM cards c
 LEFT JOIN search_metadata m ON m.uri=c.uri
 LEFT JOIN card_artwork f ON f.card_id=c.id AND f.side='front'
 LEFT JOIN card_artwork b ON b.card_id=c.id AND b.side='back'`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var id, front, back string
		var metadata SearchMetadata
		if err := rows.Scan(&id, &metadata.Artist, &metadata.Album, &metadata.Songs, &front, &back); err != nil {
			return nil, err
		}
		if card := byID[id]; card != nil {
			card.Metadata = metadata
			card.CustomArtwork = map[string]string{}
			if front != "" {
				card.CustomArtwork["front"] = front
			}
			if back != "" {
				card.CustomArtwork["back"] = back
			}
		}
	}
	return cards, rows.Err()
}

func (s *Store) artwork(id string) (map[string]string, error) {
	rows, e := s.db.Query("SELECT side,filename FROM card_artwork WHERE card_id=?", id)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	out := map[string]string{}
	for rows.Next() {
		var a, b string
		if e = rows.Scan(&a, &b); e != nil {
			return nil, e
		}
		out[a] = b
	}
	return out, rows.Err()
}

// Creation must never replace an existing card or its permanent NFC mapping.
func (s *Store) create(c Card) error {
	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	if _, err = tx.Exec("INSERT INTO cards(id,title,uri) VALUES(?,?,?)", c.ID, c.Title, c.URI); err != nil {
		return err
	}
	if _, err = tx.Exec("INSERT INTO shelf_order(card_id,position) SELECT ?,COALESCE(MAX(position)+1,0) FROM shelf_order", c.ID); err != nil {
		return err
	}
	return tx.Commit()
}

func (s *Store) save(c Card, art map[string]string, resets []string) error {
	tx, e := s.db.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	_, e = tx.Exec("INSERT INTO cards(id,title,uri) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,uri=excluded.uri", c.ID, c.Title, c.URI)
	if e != nil {
		return e
	}
	if _, e = tx.Exec("INSERT OR IGNORE INTO shelf_order(card_id,position) SELECT ?,COALESCE(MAX(position)+1,0) FROM shelf_order", c.ID); e != nil {
		return e
	}
	for _, side := range resets {
		if _, e = tx.Exec("DELETE FROM card_artwork WHERE card_id=? AND side=?", c.ID, side); e != nil {
			return e
		}
	}
	for side, file := range art {
		if _, e = tx.Exec("INSERT INTO card_artwork(card_id,side,filename) VALUES(?,?,?) ON CONFLICT(card_id,side) DO UPDATE SET filename=excluded.filename", c.ID, side, file); e != nil {
			return e
		}
	}
	if c.MetadataEdited {
		if _, e = tx.Exec(`INSERT INTO search_metadata(uri,artist,album,songs,custom,checked_at) VALUES(?,?,?,?,1,0)
 ON CONFLICT(uri) DO UPDATE SET artist=excluded.artist,album=excluded.album,songs=excluded.songs,custom=1`, c.URI, c.Metadata.Artist, c.Metadata.Album, c.Metadata.Songs); e != nil {
			return e
		}
	}
	if c.ReleaseDateEdited {
		if !validReleaseDate(c.ReleaseDate) || !strings.HasPrefix(c.URI, "spotify:album:") {
			return errors.New("Enter an original album release date in YYYY-MM-DD format")
		}
		if _, e = tx.Exec(`INSERT INTO album_releases(uri,release_date,custom) VALUES(?,?,1)
 ON CONFLICT(uri) DO UPDATE SET release_date=excluded.release_date,custom=1`, c.URI, c.ReleaseDate); e != nil {
			return e
		}
	}
	return tx.Commit()
}

const customCardsSQL = `SELECT c.id,c.title,c.uri,c.created_at FROM cards c LEFT JOIN shelf_order o ON o.card_id=c.id ORDER BY o.position IS NULL,o.position,c.created_at,c.rowid`

var errOrderConflict = errors.New("The shelf changed in another tab. Reload before arranging it again.")
var errInvalidOrder = errors.New("Include every record once when saving the shelf order.")

func orderVersion(ids []string) string {
	sum := sha256.Sum256([]byte(strings.Join(ids, "\x00")))
	return hex.EncodeToString(sum[:])
}
func cardIDs(cards []Card) []string {
	ids := make([]string, len(cards))
	for i, c := range cards {
		ids[i] = c.ID
	}
	return ids
}

// Compare and replace inside one transaction: stale tabs cannot hide newly added records.
func (s *Store) saveOrder(ids []string, version string) error {
	tx, e := s.db.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	rows, e := tx.Query(customCardsSQL)
	if e != nil {
		return e
	}
	current := []string{}
	for rows.Next() {
		var c Card
		if e = rows.Scan(&c.ID, &c.Title, &c.URI, &c.Created); e != nil {
			rows.Close()
			return e
		}
		current = append(current, c.ID)
	}
	e = rows.Err()
	rows.Close()
	if e != nil {
		return e
	}
	if !equal(version, orderVersion(current)) {
		return errOrderConflict
	}
	if len(ids) != len(current) {
		return errInvalidOrder
	}
	remaining := map[string]bool{}
	for _, id := range current {
		remaining[id] = true
	}
	for _, id := range ids {
		if !remaining[id] {
			return errInvalidOrder
		}
		delete(remaining, id)
	}
	if _, e = tx.Exec("DELETE FROM shelf_order"); e != nil {
		return e
	}
	for i, id := range ids {
		if _, e = tx.Exec("INSERT INTO shelf_order(card_id,position) VALUES(?,?)", id, i); e != nil {
			return e
		}
	}
	return tx.Commit()
}
