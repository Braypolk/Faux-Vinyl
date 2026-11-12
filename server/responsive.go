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
	URL   string
	Width int
}

// Bundled images are discovered once at startup. Only existing sizes are used;
// the optimizer can omit sizes that a particular display role does not need.
func (a *App) loadBundledVariants() error {
	sources := map[string]bool{}
	for _, sides := range a.art {
		for _, file := range sides {
			sources["/static/"+file] = true
		}
	}
	for _, options := range a.discs {
		for _, option := range options {
			sources[option.Image] = true
		}
	}
	a.variants = make(map[string][]ImageVariant, len(sources))
	for url := range sources {
		base := "/static/optimized/" + filepath.Base(filepath.Dir(url)) + "-" + filepath.Base(url)
		variants, err := discoverImageVariants(a.cfg.CollectionDir, url, base, []int{64, 160, 320, 640})
		if err != nil {
			return fmt.Errorf("bundled artwork %s: %w", url, err)
		}
		a.variants[url] = variants
	}
	return nil
}

func discoverImageVariants(root, url, base string, widths []int) ([]ImageVariant, error) {
	f, err := os.Open(filepath.Join(root, strings.TrimPrefix(url, "/")))
	if err != nil {
		return nil, err
	}
	cfg, _, err := image.DecodeConfig(f)
	f.Close()
	if err != nil {
		return nil, err
	}
	var variants []ImageVariant
	for _, width := range widths {
		if width >= cfg.Width {
			continue
		}
		candidate := imageVariantName(base, width)
		info, err := os.Stat(filepath.Join(root, strings.TrimPrefix(candidate, "/")))
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return nil, err
		}
		if info.Mode().IsRegular() && info.Size() > 0 {
			variants = append(variants, ImageVariant{candidate, width})
		}
	}
	return append(variants, ImageVariant{url, cfg.Width}), nil
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
	if cached, ok := a.uploadVariants.Load(url); ok {
		return cached.([]ImageVariant)
	}
	variants, err := discoverImageVariants(a.cfg.DataDir, url, url, []int{160, 320, 640})
	if err != nil {
		return nil
	}
	// Upload names are content hashes; dimensions and derivatives are immutable.
	cached, _ := a.uploadVariants.LoadOrStore(url, variants)
	return cached.([]ImageVariant)
}

func imageVariantName(name string, width int) string {
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
		file := filepath.Join(dir, imageVariantName(name, width))
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
