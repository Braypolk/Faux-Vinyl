package main

import (
	"bytes"
	"html"
	"image"
	"image/color"
	"image/png"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
	"testing"
)

func TestBundledVariantsDiscoverExistingSizesAndCacheAtStartup(t *testing.T) {
	root := t.TempDir()
	write := func(name string, width int) {
		t.Helper()
		file := filepath.Join(root, "static", name)
		if err := os.MkdirAll(filepath.Dir(file), 0755); err != nil {
			t.Fatal(err)
		}
		f, err := os.Create(file)
		if err != nil {
			t.Fatal(err)
		}
		err = png.Encode(f, image.NewNRGBA(image.Rect(0, 0, width, width)))
		f.Close()
		if err != nil {
			t.Fatal(err)
		}
	}
	write("covers/shared.png", 500)
	write("discs/shared.png", 120)
	write("covers/original-only.png", 90)
	write("optimized/covers-shared-w160.png", 160)
	write("optimized/discs-shared-w64.png", 64)
	// Sizes larger than the original are never offered, even if stale files exist.
	write("optimized/discs-shared-w160.png", 160)
	a := &App{
		cfg:   Config{Root: root, CollectionDir: root},
		art:   map[string]map[string]string{"album": {"front": "covers/shared.png", "back": "covers/original-only.png"}},
		discs: map[string][]DiscArtwork{"album": {{Image: "/static/discs/shared.png"}}},
	}
	if err := a.loadBundledVariants(); err != nil {
		t.Fatal(err)
	}
	expected := map[string][]ImageVariant{
		"/static/covers/shared.png":        {{"/static/optimized/covers-shared-w160.png", 160}, {"/static/covers/shared.png", 500}},
		"/static/discs/shared.png":         {{"/static/optimized/discs-shared-w64.png", 64}, {"/static/discs/shared.png", 120}},
		"/static/covers/original-only.png": {{"/static/covers/original-only.png", 90}},
	}
	// Rendering uses the in-memory results without reopening originals or sizes.
	if err := os.RemoveAll(filepath.Join(root, "static")); err != nil {
		t.Fatal(err)
	}
	for url, want := range expected {
		if got := a.imageVariants(url); !slices.Equal(got, want) {
			t.Fatalf("%s: got %v, want %v", url, got, want)
		}
	}
	if err := a.loadBundledVariants(); err == nil {
		t.Fatal("missing originals must be reported at startup")
	}
}

func TestResponsiveImagesExistAndPreserveDiscTransparency(t *testing.T) {
	a := testApp(t)
	allowed := map[string]map[int]bool{}
	add := func(url string, widths ...int) {
		if allowed[url] == nil {
			allowed[url] = map[int]bool{}
		}
		for _, width := range widths {
			allowed[url][width] = true
		}
	}
	for _, sides := range a.art {
		if sides["front"] != "" {
			add("/static/"+sides["front"], 160, 320, 640)
		}
		if sides["back"] != "" {
			add("/static/"+sides["back"], 320, 640)
		}
	}
	for _, options := range a.discs {
		for _, option := range options {
			add(option.Image, 64, 160, 320, 640)
		}
	}
	if len(a.variants) != len(allowed) {
		t.Fatal("responsive catalogue does not match current artwork", len(a.variants), len(allowed))
	}
	generated := map[string]bool{}
	for original, variants := range a.variants {
		if allowed[original] == nil || len(variants) == 0 || variants[len(variants)-1].URL != original {
			t.Fatal("missing original or unexpected artwork", original)
		}
		last := 0
		for _, variant := range variants {
			if variant.URL != original {
				if !allowed[original][variant.Width] {
					t.Fatal("unnecessary image size for display role", original, variant.Width)
				}
				generated[variant.URL] = true
			}
			f, err := os.Open(filepath.Join(a.cfg.CollectionDir, strings.TrimPrefix(variant.URL, "/")))
			if err != nil {
				t.Fatal(err)
			}
			cfg, _, err := image.DecodeConfig(f)
			if err != nil || cfg.Width != variant.Width || variant.Width <= last {
				t.Fatal(original, variant, cfg, err)
			}
			last = variant.Width
			if strings.HasPrefix(original, "/static/discs/") && variant.Width == 320 {
				f.Seek(0, 0)
				img, _, err := image.Decode(f)
				if err != nil {
					t.Fatal(err)
				}
				_, _, _, corner := img.At(0, 0).RGBA()
				_, _, _, center := img.At(160, 160).RGBA()
				// Very small original spindle holes can have a faint resampling edge.
				if corner != 0 || center > 32*257 {
					t.Fatal("disc transparency lost", original)
				}
			}
			f.Close()
		}
	}
	entries, err := os.ReadDir(filepath.Join(a.cfg.CollectionDir, "static", "optimized"))
	if err != nil {
		t.Fatal(err)
	}
	for _, entry := range entries {
		if entry.IsDir() || !generated["/static/optimized/"+entry.Name()] {
			t.Fatal("unreferenced generated artwork", entry.Name())
		}
	}
	entries, err = os.ReadDir(filepath.Join(a.cfg.CollectionDir, "static", "covers"))
	if err != nil {
		t.Fatal(err)
	}
	for _, entry := range entries {
		if entry.IsDir() || allowed["/static/covers/"+entry.Name()] == nil {
			t.Fatal("covers must be flat and referenced", entry.Name())
		}
	}
	b := &browser{a: a}
	signIn(t, b)
	home := b.request("GET", "/", nil, nil).Body.String()
	for _, match := range regexp.MustCompile(`data-(front|back)-candidates="([^"]+)"`).FindAllStringSubmatch(home, -1) {
		candidates := strings.Split(html.UnescapeString(match[2]), ",")
		for _, candidate := range candidates {
			fields := strings.Fields(candidate)
			if len(fields) != 2 || !strings.HasSuffix(fields[1], "w") {
				t.Fatal("invalid image candidate descriptor", candidate)
			}
		}
	}
	if strings.Contains(home, "ZgotmplZ") || !strings.Contains(home, `sizes="(max-width: 560px) 118px, 154px"`) || !strings.Contains(home, `data-front-candidates="/static/optimized/`) {
		t.Fatal("missing responsive markup")
	}
}

func TestUploadedCoverThumbnailsPreserveAspectAndAuthentication(t *testing.T) {
	a := testApp(t)
	img := image.NewNRGBA(image.Rect(0, 0, 800, 400))
	img.Set(400, 200, color.NRGBA{R: 255, A: 255})
	var raw bytes.Buffer
	png.Encode(&raw, img)
	name, err := saveCover(filepath.Join(a.cfg.DataDir, "artwork"), raw.Bytes(), "png")
	if err != nil {
		t.Fatal(err)
	}
	variants := a.imageVariants("/artwork/" + name)
	if len(variants) != 4 {
		t.Fatal(variants)
	}
	b := &browser{a: a}
	signIn(t, b)
	for _, v := range variants {
		w := b.request("GET", v.URL, nil, nil)
		cfg, _, err := image.DecodeConfig(bytes.NewReader(w.Body.Bytes()))
		if w.Code != 200 || err != nil || cfg.Width != v.Width || cfg.Height*2 != cfg.Width {
			t.Fatal(v, w.Code, cfg, err)
		}
		anon := &browser{a: a}
		if anon.request("GET", v.URL, nil, nil).Code != 303 {
			t.Fatal("private thumbnail exposed")
		}
	}
}
