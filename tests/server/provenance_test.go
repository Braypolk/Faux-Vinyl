package main

import (
	"database/sql"
	"path/filepath"
	"testing"
)

func TestUpdatedCatalogueDefaultsPreserveManualMetadataAndDates(t *testing.T) {
	s, err := openStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	defer s.db.Close()
	c := testCatalogue(t)
	if err = s.seedCatalogue(c); err != nil {
		t.Fatal(err)
	}
	uri := "spotify:album:1111111111111111111111"
	item := c.Items[uri]
	item.Artist = "Corrected Artist"
	item.Release.Date = "1984-01-11"
	c.Items[uri] = item
	if err = s.seedCatalogue(c); err != nil {
		t.Fatal(err)
	}
	if got, _ := s.metadata(uri); got.Artist != "Corrected Artist" {
		t.Fatal("Default correction lost", got)
	}
	if got, _ := s.releaseDate(uri); got != "1984-01-11" {
		t.Fatal("Default date correction lost", got)
	}
	card, _ := s.card("demo-album")
	card.MetadataEdited = true
	card.Metadata = SearchMetadata{Artist: "Manual Artist", Album: "Manual Album", Songs: "Manual Song"}
	card.ReleaseDateEdited = true
	card.ReleaseDate = ""
	if err = s.save(card, nil, nil); err != nil {
		t.Fatal(err)
	}
	item.Artist = "Another Correction"
	item.Release.Date = "1984-01-12"
	c.Items[uri] = item
	if err = s.seedCatalogue(c); err != nil {
		t.Fatal(err)
	}
	if got, _ := s.metadata(uri); got != card.Metadata {
		t.Fatal("Manual metadata overwritten", got)
	}
	if got, _ := s.releaseDate(uri); got != "" {
		t.Fatal("Manual blank date overwritten", got)
	}
}

func TestLegacyReleaseProvenancePreservesAmbiguousCorrections(t *testing.T) {
	dir := t.TempDir()
	db, err := sql.Open("sqlite3", filepath.Join(dir, "fauxvinyl.sqlite3"))
	if err != nil {
		t.Fatal(err)
	}
	_, err = db.Exec(`CREATE TABLE album_releases(uri TEXT PRIMARY KEY,release_date TEXT NOT NULL);
 INSERT INTO album_releases VALUES('spotify:album:1111111111111111111111','1984-01-09'),('spotify:album:2222222222222222222222','2001-01-01'),('spotify:album:3333333333333333333333','')`)
	db.Close()
	if err != nil {
		t.Fatal(err)
	}
	s, err := openStore(dir)
	if err != nil {
		t.Fatal(err)
	}
	defer s.db.Close()
	c := testCatalogue(t)
	if err = s.seedCatalogue(c); err != nil {
		t.Fatal(err)
	}
	c.Items["spotify:album:1111111111111111111111"].Release.Date = "1984-01-11"
	c.Items["spotify:album:2222222222222222222222"].Release.Date = "2026-03-07"
	c.Items["spotify:album:3333333333333333333333"].Release.Date = "2012-10-23"
	if err = s.seedCatalogue(c); err != nil {
		t.Fatal(err)
	}
	for uri, want := range map[string]string{"spotify:album:1111111111111111111111": "1984-01-11", "spotify:album:2222222222222222222222": "2001-01-01", "spotify:album:3333333333333333333333": ""} {
		if got, _ := s.releaseDate(uri); got != want {
			t.Fatal(uri, got, want)
		}
	}
}
