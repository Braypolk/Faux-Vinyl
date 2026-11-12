package main

import (
	"encoding/json"
	"image"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestRequestedCollectionHasCoversBothDiscFormatsAndOriginalDates(t *testing.T) {
	a := testApp(t)
	raw, _ := resources.ReadFile("search-metadata.json")
	var metadata map[string]SearchMetadata
	if e := json.Unmarshal(raw, &metadata); e != nil {
		t.Fatal(e)
	}
	raw, _ = resources.ReadFile("release-dates.json")
	var dates map[string]struct {
		Date string `json:"date"`
	}
	if e := json.Unmarshal(raw, &dates); e != nil {
		t.Fatal(e)
	}
	requested := []struct{ artist, album, year string }{
		{"Noah Kahan", "The Great Divide", "2026"},
		{"Noah Kahan", "Stick Season", "2022"},
		{"Taylor Swift", "1989", "2014"},
		{"Taylor Swift", "folklore", "2020"},
		{"Ariana Grande", "thank u, next", "2019"},
		{"Rihanna", "ANTI", "2016"},
		{"Tame Impala", "The Slow Rush", "2020"},
		{"Rainbow Kitten Surprise", "How To: Friend, Love, Freefall", "2018"},
		{"Beyoncé", "BEYONCÉ", "2013"},
		{"Harry Styles", "Kiss All The Time. Disco, Occasionally.", "2026"},
		{"Olivia Rodrigo", "you seem pretty sad for a girl so in love", "2026"},
	}
	for _, want := range requested {
		var uri string
		for key, m := range metadata {
			if strings.Contains(strings.ToLower(m.Artist), strings.ToLower(want.artist)) && strings.HasPrefix(strings.ToLower(m.Album), strings.ToLower(want.album)) {
				if uri != "" {
					t.Fatal("Ambiguous requested album", want.album)
				}
				uri = key
			}
		}
		if uri == "" {
			t.Fatal("Missing requested album", want.artist, want.album)
		}
		if !strings.HasPrefix(dates[uri].Date, want.year+"-") {
			t.Fatal("Wrong original release year", want.album, dates[uri].Date)
		}
		if want.album == "1989" && strings.Contains(metadata[uri].Album, "Taylor’s Version") {
			t.Fatal("Original 1989 recording required")
		}
		if want.artist == "Rainbow Kitten Surprise" && !strings.Contains(metadata[uri].Songs, "Fever Pitch") {
			t.Fatal("Album containing Fever Pitch required")
		}
		for _, side := range []string{"front", "back"} {
			if a.art[uri][side] == "" {
				t.Fatal("Missing sleeve side", want.album, side)
			}
			if _, e := os.Stat(filepath.Join(a.cfg.Root, "static", a.art[uri][side])); e != nil {
				t.Fatal(e)
			}
		}
		formats := map[string]bool{}
		for _, option := range a.discs[uri] {
			formats[option.Kind] = true
			f, e := os.Open(filepath.Join(a.cfg.Root, strings.TrimPrefix(option.Image, "/")))
			if e != nil {
				t.Fatal(e)
			}
			im, _, e := image.Decode(f)
			f.Close()
			if e != nil {
				t.Fatal(e)
			}
			if im.Bounds().Dx() != 648 || im.Bounds().Dy() != 648 {
				t.Fatal("Wrong normalized disc size", want.album, option.Kind)
			}
			for _, point := range [][2]int{{0, 0}, {647, 647}, {324, 324}} {
				_, _, _, alpha := im.At(point[0], point[1]).RGBA()
				if alpha != 0 {
					t.Fatal("Disc exterior/hole must be transparent", want.album, option.Kind, point)
				}
			}
			_, _, _, alpha := im.At(324, 20).RGBA()
			if alpha < 60000 {
				t.Fatal("Incomplete disc rim", want.album, option.Kind)
			}
		}
		if !formats["vinyl"] || !formats["cd"] {
			t.Fatal("Both vinyl and CD required", want.album)
		}
	}
}
