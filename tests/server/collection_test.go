package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestOptionalCollectionDoesNotConsumeImportOrMigrationFlags(t *testing.T) {
	dir := t.TempDir()
	empty, err := loadCatalogue(filepath.Join(dir, "missing"))
	if err != nil || len(empty.Items) != 0 {
		t.Fatal(empty, err)
	}
	s, err := openStore(dir)
	if err != nil {
		t.Fatal(err)
	}
	defer s.db.Close()
	if err = s.seedCatalogue(empty); err != nil {
		t.Fatal(err)
	}
	for _, key := range []string{"seed_imported", "catalogue_names_corrected_v1"} {
		if s.setting(key, false) == true {
			t.Fatal("Absent collection consumed migration", key)
		}
	}
	if err = s.save(Card{ID: "existing", Title: "Existing record", URI: "spotify:album:9999999999999999999999"}, nil, nil); err != nil {
		t.Fatal(err)
	}
	if err = s.seedCatalogue(empty); err != nil {
		t.Fatal(err)
	}
	if card, _ := s.card("existing"); card.Title != "Existing record" {
		t.Fatal("Optional collection changed existing data")
	}
	if err = s.seedCatalogue(testCatalogue(t)); err != nil {
		t.Fatal(err)
	}
	cards, _ := s.cards("custom")
	if len(cards) != 8 {
		t.Fatal("Later collection import missing", len(cards))
	}
}

func TestFreshInstallStartsWithEmptyShelfAndCanAddRecords(t *testing.T) {
	dir := t.TempDir()
	a, err := newApp(Config{DataDir: dir, PublicURL: testOrigin, PasswordHash: "test", Root: ".", CollectionDir: filepath.Join(dir, "absent"), PreferencesFile: filepath.Join(dir, "absent.json")}, PreviewPlayer{})
	if err != nil {
		t.Fatal(err)
	}
	defer a.store.db.Close()
	cards, _ := a.store.cards("custom")
	if len(cards) != 0 || len(a.art) != 0 || len(a.discs) != 0 {
		t.Fatal("Fresh install loaded personal data")
	}
	if err = a.store.save(Card{ID: "first", Title: "First record", URI: "spotify:album:1111111111111111111111"}, nil, nil); err != nil {
		t.Fatal(err)
	}
	if card, _ := a.store.card("first"); card.Title != "First record" {
		t.Fatal("Empty install cannot save a record")
	}
}

func TestExternalCollectionErrorsAndArtworkRouting(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "catalogue.json"), []byte(`{"version":2}`), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := loadCatalogue(dir); err == nil {
		t.Fatal("Invalid existing collection silently ignored")
	}
	a := testApp(t)
	b := &browser{a: a}
	signIn(t, b)
	for _, url := range []string{"/static/covers/front.webp", "/static/discs/disc.webp", "/static/optimized/covers-front-w160.webp"} {
		w := b.request("GET", url, nil, nil)
		if w.Code != 200 || len(w.Body.Bytes()) == 0 {
			t.Fatal("External artwork unavailable", url, w.Code)
		}
	}
	if w := b.request("GET", "/static/catalogue.json", nil, nil); w.Code != 404 {
		t.Fatal("Collection metadata exposed", w.Code)
	}
}
