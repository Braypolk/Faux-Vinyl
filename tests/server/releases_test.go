package main

import (
	"net/url"
	"reflect"
	"strings"
	"testing"
)

func TestReleaseSortUsesOriginalDatesAndUndatedLast(t *testing.T) {
	dir := t.TempDir()
	s, e := openStore(dir)
	if e != nil {
		t.Fatal(e)
	}
	defer s.db.Close()
	cards := []Card{
		{ID: "new", Title: "New album", URI: "spotify:album:2222222222222222222222", ReleaseDate: "2026-03-06", ReleaseDateEdited: true},
		{ID: "old", Title: "1984 (Remastered)", URI: "spotify:album:1111111111111111111111", ReleaseDate: "1984-01-09", ReleaseDateEdited: true},
		{ID: "tie", Title: "Another album", URI: "spotify:album:3WZZF72ihlKPZBS4zSsNHl", ReleaseDate: "2026-03-06", ReleaseDateEdited: true},
		{ID: "unknown", Title: "Undated album", URI: "spotify:album:6s84u2TUpR3wdUv4NgKA2j"},
		{ID: "playlist", Title: "Playlist", URI: "spotify:playlist:37i9dQZEVXcEhQ4vCW9RIF"},
	}
	for _, c := range cards {
		if e = s.save(c, nil, nil); e != nil {
			t.Fatal(e)
		}
	}
	// Deliberately make the oldest album the newest addition.
	if _, e = s.db.Exec("UPDATE cards SET created_at='2099-01-01' WHERE id='old'"); e != nil {
		t.Fatal(e)
	}
	before, _ := s.cards("custom")
	for order, want := range map[string][]string{
		"newest": {"tie", "new", "old", "playlist", "unknown"},
		"oldest": {"old", "tie", "new", "playlist", "unknown"},
	} {
		got, e := s.cards(order)
		if e != nil || !reflect.DeepEqual(cardIDs(got), want) {
			t.Fatal(order, cardIDs(got), e)
		}
	}
	after, _ := s.cards("custom")
	if !reflect.DeepEqual(before, after) {
		t.Fatal("Release sorting changed custom order")
	}
	other, e := openStore(dir)
	if e != nil {
		t.Fatal(e)
	}
	defer other.db.Close()
	if d, e := other.releaseDate(cards[1].URI); e != nil || d != "1984-01-09" {
		t.Fatal("Date did not survive reopening", d, e)
	}
}

func TestReleaseDateEditorPreservesCorrectionsAndFollowsURI(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	csrf := signIn(t, b)
	c, _ := a.store.card("demo-album")
	path := "/cards/demo-album/edit"
	if page := b.request("GET", path, nil, nil).Body.String(); !strings.Contains(page, `name="release_date" value="1984-01-09"`) {
		t.Fatal("Original remaster date missing")
	}
	values := url.Values{"csrf": {csrf}, "title": {c.Title}, "uri": {c.URI}, "release_date": {"1984-01-10"}}
	if w := b.request("POST", path, values, nil); w.Code != 303 {
		t.Fatal(w.Code, w.Body.String())
	}
	seed := testCatalogue(t)
	if e := a.store.seedCatalogue(seed); e != nil {
		t.Fatal(e)
	}
	if d, _ := a.store.releaseDate(c.URI); d != "1984-01-10" {
		t.Fatal("Bundled dates overwrote correction", d)
	}
	values.Set("release_date", "2026-02-30")
	if w := b.request("POST", path, values, nil); w.Code != 400 {
		t.Fatal("Invalid date accepted", w.Code)
	}
	values.Set("release_date", "")
	if w := b.request("POST", path, values, nil); w.Code != 303 {
		t.Fatal(w.Code)
	}
	a.store.seedCatalogue(seed)
	if d, _ := a.store.releaseDate(c.URI); d != "" {
		t.Fatal("Intentional blank date overwritten", d)
	}
	values.Set("uri", "spotify:album:2222222222222222222222")
	values.Set("release_date", "1984-01-09") // Old form value must not follow a changed link.
	if w := b.request("POST", path, values, nil); w.Code != 303 {
		t.Fatal(w.Code)
	}
	if d, _ := a.store.releaseDate(values.Get("uri")); d != "2026-03-06" {
		t.Fatal("Unrelated date followed URI edit", d)
	}
}

func TestBundledReleaseDatesCoverEveryAlbum(t *testing.T) {
	a := testApp(t)
	catalogue := testCatalogue(t)
	count := 0
	for uri := range catalogue.Items {
		date, e := a.store.releaseDate(uri)
		if e != nil {
			t.Fatal(e)
		}
		if strings.HasPrefix(uri, "spotify:album:") {
			count++
			if date == "" || !validReleaseDate(date) {
				t.Fatal("Missing original date", uri, date)
			}
		} else if date != "" {
			t.Fatal("Playlist has an album date", uri)
		}
	}
	if count != 6 {
		t.Fatal("Expected every fixture album to have a date", count)
	}
	for _, date := range []string{"2026-2-01", "2026-02-29", "0000-01-01", "2026-01-01T00:00:00Z"} {
		if validReleaseDate(date) {
			t.Fatal("Invalid date accepted", date)
		}
	}
}
