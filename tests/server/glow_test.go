package main

import "testing"

func TestGlowMetadataValidation(t *testing.T) {
	item := CatalogueItem{
		Discs: []DiscArtwork{{ID: "normal", Kind: "cd"}, {ID: "secret", Kind: "cd"}, {ID: "vinyl", Kind: "vinyl"}},
		Glow:  &GlowEffect{Variants: map[string]string{"normal": "secret"}, Words: []string{"one", "two", "three", "four"}},
	}
	if err := item.validateGlow(); err != nil {
		t.Fatal(err)
	}
	for name, variants := range map[string]map[string]string{
		"missing edition":       {"normal": "missing"},
		"different kind":        {"normal": "vinyl"},
		"self reveal":           {"normal": "normal"},
		"hidden trigger":        {"normal": "secret", "secret": "normal"},
		"shared hidden edition": {"normal": "secret", "vinyl": "secret"},
		"no variants":           {},
	} {
		t.Run(name, func(t *testing.T) {
			candidate := item
			candidate.Glow = &GlowEffect{Variants: variants}
			if err := candidate.validateGlow(); err == nil {
				t.Fatal("accepted invalid reveal")
			}
		})
	}
	item.Glow.Words = []string{"one", "two", "three", "four", "five"}
	if err := item.validateGlow(); err == nil {
		t.Fatal("accepted more reveal words than presses")
	}
	item.Glow = nil
	if err := item.validateGlow(); err != nil {
		t.Fatal("glow metadata should be optional", err)
	}
}
