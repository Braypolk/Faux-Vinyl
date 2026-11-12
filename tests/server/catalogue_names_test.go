package main

import (
	"reflect"
	"testing"
)

func TestCatalogueNameCorrectionsPreserveSavedIdentityAndEdits(t *testing.T) {
	s, err := openStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	defer s.db.Close()
	catalogue := testCatalogue(t)
	if err = s.set("seed_imported", true); err != nil {
		t.Fatal(err)
	}
	cards := []Card{
		{ID: "demo-album", Title: "demo album", URI: "spotify:album:1111111111111111111111"},
		{ID: "new-album", Title: "My personal name", URI: "spotify:album:2222222222222222222222"},
		{ID: "search-album", Title: "another album", URI: "spotify:album:1111111111111111111111"},
	}
	for _, card := range cards {
		if err = s.save(card, nil, nil); err != nil {
			t.Fatal(err)
		}
	}
	before, _ := s.cards("custom")
	if err = s.seedCatalogue(catalogue); err != nil {
		t.Fatal(err)
	}
	after, _ := s.cards("custom")
	if !reflect.DeepEqual(cardIDs(before), cardIDs(after)) {
		t.Fatal("Name cleanup changed shelf order")
	}
	for i, card := range after {
		if card.URI != before[i].URI || card.Created != before[i].Created {
			t.Fatal("Name cleanup changed record identity")
		}
		want := before[i].Title
		if card.ID == "demo-album" {
			want = "Demo Album"
		}
		if card.Title != want {
			t.Fatal("Unexpected title change", card)
		}
	}
	card, _ := s.card("demo-album")
	card.Title = "demo album"
	if err = s.save(card, nil, nil); err != nil {
		t.Fatal(err)
	}
	if err = s.seedCatalogue(catalogue); err != nil {
		t.Fatal(err)
	}
	got, _ := s.card(card.ID)
	if got.Title != card.Title {
		t.Fatal("Completed migration ran twice")
	}
}
