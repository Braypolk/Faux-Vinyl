package main

import (
	"encoding/json"
	"os"
	"reflect"
	"strings"
	"testing"
)

func testCatalogue(t *testing.T) *Catalogue {
	t.Helper()
	c, err := loadCatalogue("../tests/fixtures/collection")
	if err != nil {
		t.Fatal(err)
	}
	return c
}

func TestCatalogueRejectsBrokenReferencesAndMetadata(t *testing.T) {
	for name, change := range map[string]func(*Catalogue){
		"unsupported version": func(c *Catalogue) { c.Version++ },
		"empty items":         func(c *Catalogue) { c.Items = nil },
		"unknown starter URI": func(c *Catalogue) { c.StarterCards[0].URI = "spotify:album:missing" },
		"duplicate card ID":   func(c *Catalogue) { c.StarterCards = append(c.StarterCards, c.StarterCards[0]) },
		"unknown legacy URI": func(c *Catalogue) {
			c.LegacyNameCorrections.Entries[0].URI = "spotify:album:missing"
		},
		"invalid URI": func(c *Catalogue) { c.Items["invalid"] = c.Items[c.StarterCards[0].URI] },
		"invalid release": func(c *Catalogue) {
			c.Items["spotify:album:1111111111111111111111"].Release.Date = "1984-02-30"
		},
		"nested artwork": func(c *Catalogue) {
			c.Items[c.StarterCards[0].URI].Artwork["front"] = "covers/../private.webp"
		},
		"generated disc variants": func(c *Catalogue) {
			for _, item := range c.Items {
				if len(item.Discs) > 0 {
					item.Discs[0].Srcset = "/static/optimized/generated.webp 320w"
					break
				}
			}
		},
	} {
		t.Run(name, func(t *testing.T) {
			c := testCatalogue(t)
			change(c)
			raw, err := json.Marshal(c)
			if err != nil {
				t.Fatal(err)
			}
			if _, err = decodeCatalogue(raw); err == nil {
				t.Fatal("Accepted malformed catalogue")
			}
		})
	}
	raw, err := os.ReadFile("../tests/fixtures/collection/catalogue.json")
	if err != nil {
		t.Fatal(err)
	}
	for name, bad := range map[string][]byte{
		"unknown field": []byte(strings.Replace(string(raw), `"version": 1`, `"version": 1, "typo": true`, 1)),
		"trailing JSON": append(append([]byte{}, raw...), []byte(` {}`)...),
	} {
		t.Run(name, func(t *testing.T) {
			if _, err := decodeCatalogue(bad); err == nil {
				t.Fatal("Accepted malformed JSON")
			}
		})
	}
}

func TestCatalogueSeedPreservesStarterIdentityAndExistingMigrationFlags(t *testing.T) {
	c := testCatalogue(t)
	s, err := openStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	defer s.db.Close()
	if err = s.seedCatalogue(c); err != nil {
		t.Fatal(err)
	}
	cards, err := s.cards("custom")
	if err != nil || len(cards) != len(c.StarterCards) {
		t.Fatal("Starter shelf missing", len(cards), err)
	}
	for i, card := range cards {
		ref := c.StarterCards[i]
		if card.ID != ref.ID || card.URI != ref.URI || card.Title != c.Items[ref.URI].Title {
			t.Fatal("Starter identity or order changed", card.ID)
		}
	}
	for table, want := range map[string]int{"search_metadata": len(c.Items), "album_releases": 6} {
		var count int
		if err = s.db.QueryRow("SELECT COUNT(*) FROM " + table).Scan(&count); err != nil || count != want {
			t.Fatal("Missing bundled details", table, count, err)
		}
	}
	for _, key := range []string{"seed_imported", "catalogue_names_corrected_v1"} {
		if s.setting(key, false) != true {
			t.Fatal("Existing migration key missing", key)
		}
	}
	// An old installation with completed migrations must retain deleted records
	// and later personal titles even when they match the original legacy title.
	removed, edited := cards[0], cards[1]
	if _, err = s.db.Exec("DELETE FROM cards WHERE id=?", removed.ID); err != nil {
		t.Fatal(err)
	}
	edited.Title = "My own title"
	if err = s.save(edited, nil, nil); err != nil {
		t.Fatal(err)
	}
	before, _ := s.cards("custom")
	if err = s.seedCatalogue(c); err != nil {
		t.Fatal(err)
	}
	after, _ := s.cards("custom")
	if !reflect.DeepEqual(before, after) {
		t.Fatal("Completed migration changed the saved shelf")
	}
}

func TestCatalogueSeedRollsBackAllChangesOnFailure(t *testing.T) {
	s, err := openStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	defer s.db.Close()
	if _, err = s.db.Exec(`CREATE TRIGGER reject_metadata BEFORE INSERT ON search_metadata BEGIN SELECT RAISE(ABORT,'test failure'); END`); err != nil {
		t.Fatal(err)
	}
	if err = s.seedCatalogue(testCatalogue(t)); err == nil {
		t.Fatal("Expected seed failure")
	}
	for _, table := range []string{"cards", "shelf_order", "search_metadata", "album_releases", "settings"} {
		var count int
		if err = s.db.QueryRow("SELECT COUNT(*) FROM " + table).Scan(&count); err != nil || count != 0 {
			t.Fatal("Seed left partial changes", table, count, err)
		}
	}
}
