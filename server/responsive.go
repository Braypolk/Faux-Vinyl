package main

import (
	"bytes"
	"fmt"
	"image"
	"image/jpeg"
	"image/png"
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/image/draw"
)

type ImageVariant struct {
	URL   string `json:"url"`
	Width int    `json:"width"`
}

func variantSet(variants []ImageVariant, limit int) (string, string) {
	var candidates []string
	var fallback string
	for _, v := range variants {
		if limit > 0 && v.Width > limit {
			continue
		}
		candidates = append(candidates, fmt.Sprintf("%s %dw", v.URL, v.Width))
		fallback = v.URL
	}
	return fallback, strings.Join(candidates, ", ")
}

func (a *App) imageVariants(url string) []ImageVariant {
	if variants := a.variants[url]; len(variants) > 0 {
		return variants
	}
	if !strings.HasPrefix(url, "/artwork/") {
		return nil
	}
	name := strings.TrimPrefix(url, "/artwork/")
	if !uploadPattern.MatchString(name) {
		return nil
	}
	var variants []ImageVariant
	for _, width := range []int{160, 320, 640} {
		file := uploadVariantName(name, width)
		if _, err := os.Stat(filepath.Join(a.cfg.DataDir, "artwork", file)); err == nil {
			variants = append(variants, ImageVariant{"/artwork/" + file, width})
		}
	}
	f, err := os.Open(filepath.Join(a.cfg.DataDir, "artwork", name))
	if err == nil {
		cfg, _, err := image.DecodeConfig(f)
		f.Close()
		if err == nil {
			variants = append(variants, ImageVariant{url, cfg.Width})
		}
	}
	return variants
}

func uploadVariantName(name string, width int) string {
	ext := filepath.Ext(name)
	return strings.TrimSuffix(name, ext) + fmt.Sprintf("-w%d", width) + ext
}

// Uploads are resized once when saved (or once on upgrade), never on image GETs.
func prepareUploadVariants(dir, name string) error {
	f, err := os.Open(filepath.Join(dir, name))
	if err != nil {
		return err
	}
	defer f.Close()
	cfg, _, err := image.DecodeConfig(f)
	if err != nil || cfg.Width < 1 || cfg.Height < 1 || int64(cfg.Width)*int64(cfg.Height) > 12000000 {
		return fmt.Errorf("invalid cover")
	}
	var source image.Image
	for _, width := range []int{160, 320, 640} {
		if width >= cfg.Width {
			continue
		}
		file := filepath.Join(dir, uploadVariantName(name, width))
		if _, err := os.Stat(file); err == nil {
			continue
		}
		if source == nil {
			f.Seek(0, 0)
			source, _, err = image.Decode(f)
			if err != nil {
				return err
			}
		}
		dst := image.NewNRGBA(image.Rect(0, 0, width, max(1, cfg.Height*width/cfg.Width)))
		draw.CatmullRom.Scale(dst, dst.Bounds(), source, source.Bounds(), draw.Src, nil)
		var out bytes.Buffer
		if filepath.Ext(name) == ".png" {
			err = png.Encode(&out, dst)
		} else {
			err = jpeg.Encode(&out, dst, &jpeg.Options{Quality: 82})
		}
		if err != nil {
			return err
		}
		tmp, err := os.CreateTemp(dir, ".variant-*")
		if err != nil {
			return err
		}
		tmpName := tmp.Name()
		_, err = tmp.Write(out.Bytes())
		closeErr := tmp.Close()
		if err == nil {
			err = closeErr
		}
		if err == nil {
			err = os.Rename(tmpName, file)
		}
		os.Remove(tmpName)
		if err != nil {
			return err
		}
	}
	return nil
}
