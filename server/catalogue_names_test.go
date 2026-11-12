package main

import (
	"encoding/json"
	"reflect"
	"testing"
)

func TestCatalogueNameCorrections(t *testing.T) {
	s, err := openStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	defer s.db.Close()
	data, err := resources.ReadFile("catalogue-names.json")
	if err != nil {
		t.Fatal(err)
	}
	cards := []Card{
		{ID: "4-your-eyes-only", Title: "4 your eyes only", URI: "spotify:album:3CCnGldVQ90c26aFATC1PW"},
		{ID: "maad-city", Title: "My personal name", URI: "spotify:album:3DGQ1iZ9XKUQxAUWjfC34w"},
		{ID: "seal", Title: "seal", URI: "spotify:album:3CCnGldVQ90c26aFATC1PW"},
		{ID: "custom-record", Title: "my record", URI: "spotify:album:0JGOiO34nwfUdDrD612dOp"},
	}
	for _, card := range cards {
		if err = s.save(card, nil, nil); err != nil {
			t.Fatal(err)
		}
	}
	before, _ := s.cards("custom")
	if err = s.correctCatalogueNames(data); err != nil {
		t.Fatal(err)
	}
	after, _ := s.cards("custom")
	if !reflect.DeepEqual(cardIDs(before), cardIDs(after)) {
		t.Fatal("Name cleanup changed shelf order")
	}
	for i, card := range after {
		if card.URI != before[i].URI || card.Created != before[i].Created {
			t.Fatal("Name cleanup changed record identity or date")
		}
		want := before[i].Title
		if card.ID == "4-your-eyes-only" {
			want = "4 Your Eyez Only"
		}
		if card.Title != want {
			t.Fatal("Unexpected name change", card.ID, card.Title, want)
		}
	}
	// An intentional later edit, even back to an old name, survives restart.
	card, _ := s.card("4-your-eyes-only")
	card.Title = "4 your eyes only"
	if err = s.save(card, nil, nil); err != nil {
		t.Fatal(err)
	}
	if err = s.correctCatalogueNames(data); err != nil {
		t.Fatal(err)
	}
	got, _ := s.card(card.ID)
	if got.Title != card.Title {
		t.Fatal("Cleanup ran again after its completed migration")
	}
}

func TestReviewedNamesAndStarterCatalogueAgree(t *testing.T) {
	var manifest struct {
		Entries []struct{ ID, URI, Title, Artist string }
	}
	data, _ := resources.ReadFile("catalogue-names.json")
	if err := json.Unmarshal(data, &manifest); err != nil {
		t.Fatal(err)
	}
	if len(manifest.Entries) != 63 {
		t.Fatal("Expected the entire reviewed collection")
	}
	byID := map[string]string{}
	for _, entry := range manifest.Entries {
		byID[entry.ID] = entry.Title
		if entry.ID == "funhouse" && entry.Artist != "P!nk" {
			t.Fatal("Artist styling lost")
		}
	}
	seed, _ := resources.ReadFile("seed-cards.json")
	var cards []Card
	json.Unmarshal(seed, &cards)
	for _, card := range cards {
		if card.Title != byID[card.ID] {
			t.Fatal("Starter name differs from reviewed name", card.ID)
		}
	}
	if byID["beerbongs-and-bentleys"] != "beerbongs & bentleys" || byID["kids"] != "K.I.D.S." || byID["forest-hill-drive"] != "2014 Forest Hills Drive" {
		t.Fatal("Canonical spelling/styling lost")
	}
}
