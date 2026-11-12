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
	"strings"
	"testing"
)

func TestResponsiveImagesExistAndPreserveDiscTransparency(t *testing.T) {
	a := testApp(t)
	if len(a.variants) < 200 {
		t.Fatal("responsive catalogue incomplete", len(a.variants))
	}
	for original, variants := range a.variants {
		last := 0
		for _, variant := range variants {
			f, err := os.Open(filepath.Join(a.cfg.Root, strings.TrimPrefix(variant.URL, "/")))
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
