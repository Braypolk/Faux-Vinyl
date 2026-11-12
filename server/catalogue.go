package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"strings"
	"time"
)

// Catalogue is an optional installation collection. URI references keep
// NFC identities and legacy corrections independent of the shared item details.
type Catalogue struct {
	Version               int                      `json:"version"`
	Items                 map[string]CatalogueItem `json:"items"`
	StarterCards          []CatalogueCard          `json:"starter_cards"`
	LegacyNameCorrections struct {
		Checked string                    `json:"checked"`
		Basis   string                    `json:"basis"`
		Entries []CatalogueNameCorrection `json:"entries"`
	} `json:"legacy_name_corrections"`
}

type GlowEffect struct {
	Variants map[string]string `json:"variants"`
	Words    []string          `json:"words,omitempty"`
}

type CatalogueItem struct {
	Glow          *GlowEffect       `json:"glow,omitempty"`
	Title         string            `json:"title"`
	Artist        string            `json:"artist"`
	Songs         string            `json:"songs"`
	Source        string            `json:"source"`
	SearchArtists *string           `json:"search_artists,omitempty"`
	SearchTitle   *string           `json:"search_title,omitempty"`
	Release       *CatalogueRelease `json:"release,omitempty"`
	Artwork       map[string]string `json:"artwork,omitempty"`
	Discs         []DiscArtwork     `json:"discs,omitempty"`
}

type CatalogueRelease struct {
	Date   string `json:"date"`
	Source string `json:"source"`
	Title  string `json:"title,omitempty"`
}

type CatalogueCard struct {
	ID  string `json:"id"`
	URI string `json:"uri"`
}

type CatalogueNameCorrection struct {
	CatalogueCard
	PreviousTitle string `json:"previous_title"`
}

func (item CatalogueItem) metadata(uri string) SearchMetadata {
	m := SearchMetadata{Artist: item.Artist, Album: item.Title, Songs: item.Songs}
	if strings.HasPrefix(uri, "spotify:track:") {
		m.Album = ""
	}
	if item.SearchArtists != nil {
		m.Artist = *item.SearchArtists
	}
	if item.SearchTitle != nil {
		m.Album = *item.SearchTitle
	}
	return m
}

func loadCatalogue(dir string) (*Catalogue, error) {
	raw, err := os.ReadFile(filepath.Join(dir, "catalogue.json"))
	if os.IsNotExist(err) {
		return &Catalogue{Version: 1, Items: map[string]CatalogueItem{}}, nil
	}
	if err != nil {
		return nil, err
	}
	return decodeCatalogue(raw)
}

func decodeCatalogue(raw []byte) (*Catalogue, error) {
	var catalogue Catalogue
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&catalogue); err != nil {
		return nil, fmt.Errorf("invalid catalogue: %w", err)
	}
	if err := decoder.Decode(new(any)); err != io.EOF {
		return nil, errors.New("invalid catalogue: expected one JSON object")
	}
	if err := catalogue.validate(); err != nil {
		return nil, err
	}
	return &catalogue, nil
}

func (c *Catalogue) validate() error {
	if c.Version != 1 || c.Items == nil {
		return errors.New("invalid catalogue version or missing items")
	}
	validSource := func(source string) bool {
		u, err := url.Parse(source)
		return err == nil && u.Scheme == "https" && u.Host != "" && u.User == nil
	}
	validImage := func(image, directory string) bool {
		return image == directory+path.Base(image) && path.Ext(image) == ".webp"
	}
	discIDs := map[string]bool{}
	for uri, item := range c.Items {
		checked, err := spotifyURI(uri)
		if err != nil || checked != uri || !validTitle(item.Title) || !item.metadata(uri).valid() || !validSource(item.Source) {
			return fmt.Errorf("invalid catalogue item %q", uri)
		}
		if item.Release != nil {
			r := item.Release
			if !strings.HasPrefix(uri, "spotify:album:") || r.Date == "" || !validReleaseDate(r.Date) || !validSource(r.Source) || (r.Title != "" && !validTitle(r.Title)) {
				return fmt.Errorf("invalid original release for %q", uri)
			}
		}
		for side, image := range item.Artwork {
			if (side != "front" && side != "back") || !validImage(image, "covers/") {
				return fmt.Errorf("invalid sleeve artwork for %q", uri)
			}
		}
		for _, disc := range item.Discs {
			if !strings.HasPrefix(uri, "spotify:album:") || disc.ID == "" || discIDs[disc.ID] || (disc.Kind != "cd" && disc.Kind != "vinyl") || disc.Label == "" || disc.Srcset != "" || !validImage(disc.Image, "/static/discs/") {
				return fmt.Errorf("invalid disc artwork for %q", uri)
			}
			discIDs[disc.ID] = true
		}
		if err := item.validateGlow(); err != nil {
			return fmt.Errorf("invalid glow effect for %q: %w", uri, err)
		}
	}
	checkReferences := func(refs []CatalogueCard) error {
		seen := map[string]bool{}
		for _, ref := range refs {
			if _, exists := c.Items[ref.URI]; !exists || !cardIDPattern.MatchString(ref.ID) || seen[ref.ID] {
				return fmt.Errorf("invalid catalogue card reference %q", ref.ID)
			}
			seen[ref.ID] = true
		}
		return nil
	}
	if err := checkReferences(c.StarterCards); err != nil {
		return err
	}
	legacy := make([]CatalogueCard, 0, len(c.LegacyNameCorrections.Entries))
	for _, entry := range c.LegacyNameCorrections.Entries {
		if !validTitle(entry.PreviousTitle) {
			return fmt.Errorf("invalid previous title for %q", entry.ID)
		}
		legacy = append(legacy, entry.CatalogueCard)
	}
	return checkReferences(legacy)
}

// Seed one transaction without overwriting saved collection edits. Keep the
// existing migration keys so upgrades cannot repeat starter/name changes.
func (s *Store) seedCatalogue(c *Catalogue) error {
	seeded := s.setting("seed_imported", false) == true
	corrected := s.setting("catalogue_names_corrected_v1", false) == true
	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	if !seeded && len(c.StarterCards) > 0 {
		for _, ref := range c.StarterCards {
			if _, err = tx.Exec("INSERT OR IGNORE INTO cards(id,title,uri) VALUES(?,?,?)", ref.ID, c.Items[ref.URI].Title, ref.URI); err != nil {
				return err
			}
			if _, err = tx.Exec("INSERT OR IGNORE INTO shelf_order(card_id,position) SELECT ?,COALESCE(MAX(position)+1,0) FROM shelf_order", ref.ID); err != nil {
				return err
			}
		}
		if _, err = tx.Exec("INSERT INTO settings(key,value) VALUES('seed_imported','true') ON CONFLICT(key) DO UPDATE SET value='true'"); err != nil {
			return err
		}
	}
	checked := time.Now().Unix()
	for uri, item := range c.Items {
		m := item.metadata(uri)
		if _, err = tx.Exec(`INSERT INTO search_metadata(uri,artist,album,songs,checked_at) VALUES(?,?,?,?,?)
 ON CONFLICT(uri) DO UPDATE SET artist=excluded.artist,album=excluded.album,songs=excluded.songs,checked_at=excluded.checked_at
 WHERE custom=0 AND (artist<>excluded.artist OR album<>excluded.album OR songs<>excluded.songs)`, uri, m.Artist, m.Album, m.Songs, checked); err != nil {
			return err
		}
		if item.Release != nil {
			if _, err = tx.Exec("UPDATE album_releases SET custom=(release_date<>?) WHERE uri=? AND custom IS NULL", item.Release.Date, uri); err != nil {
				return err
			}
			if _, err = tx.Exec(`INSERT INTO album_releases(uri,release_date,custom) VALUES(?,?,0)
 ON CONFLICT(uri) DO UPDATE SET release_date=excluded.release_date WHERE custom=0`, uri, item.Release.Date); err != nil {
				return err
			}
		}
	}
	if !corrected && len(c.LegacyNameCorrections.Entries) > 0 {
		for _, entry := range c.LegacyNameCorrections.Entries {
			if _, err = tx.Exec("UPDATE cards SET title=? WHERE id=? AND uri=? AND title=?", c.Items[entry.URI].Title, entry.ID, entry.URI, entry.PreviousTitle); err != nil {
				return err
			}
		}
		if _, err = tx.Exec("INSERT INTO settings(key,value) VALUES('catalogue_names_corrected_v1','true') ON CONFLICT(key) DO UPDATE SET value='true'"); err != nil {
			return err
		}
	}
	return tx.Commit()
}

// Glow variants refer only to editions on this item. The normal choice stays
// visible and unlocks its matching hidden edition after five presses.
func (item CatalogueItem) validateGlow() error {
	if item.Glow == nil {
		return nil
	}
	if len(item.Glow.Variants) == 0 || len(item.Glow.Words) > 4 {
		return errors.New("expected reveal variants and up to four words")
	}
	editions := map[string]DiscArtwork{}
	for _, disc := range item.Discs {
		editions[disc.ID] = disc
	}
	hidden := map[string]bool{}
	for normal, secret := range item.Glow.Variants {
		from, fromOK := editions[normal]
		to, toOK := editions[secret]
		if !fromOK || !toOK || normal == secret || from.Kind != to.Kind || hidden[secret] {
			return errors.New("reveal must link distinct matching editions")
		}
		hidden[secret] = true
	}
	for normal := range item.Glow.Variants {
		if hidden[normal] {
			return errors.New("a hidden edition cannot unlock another edition")
		}
	}
	for _, word := range item.Glow.Words {
		if !validTitle(word) {
			return errors.New("invalid reveal word")
		}
	}
	return nil
}
