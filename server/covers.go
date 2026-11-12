package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"golang.org/x/image/draw"
	_ "golang.org/x/image/webp"
	"image"
	"image/color"
	"image/jpeg"
	"image/png"
	"io"
	"os"
	"path/filepath"
)

const coverLimit = 8 * 1024 * 1024

func prepareCover(r io.Reader) ([]byte, string, error) {
	raw, e := io.ReadAll(io.LimitReader(r, coverLimit+1))
	if e != nil || len(raw) > coverLimit {
		return nil, "", fmt.Errorf("Choose covers smaller than 8 MB each.")
	}
	cfg, format, e := image.DecodeConfig(bytes.NewReader(raw))
	if e != nil || (format != "jpeg" && format != "png" && format != "webp") {
		return nil, "", fmt.Errorf("Choose a JPEG, PNG or WebP image.")
	}
	if cfg.Width < 1 || cfg.Height < 1 || int64(cfg.Width)*int64(cfg.Height) > 12000000 {
		return nil, "", fmt.Errorf("Choose covers up to 12 megapixels.")
	}
	orientation, animated := imageMetadata(raw, format)
	if animated {
		return nil, "", fmt.Errorf("Choose a still image for the cover.")
	}
	img, _, e := image.Decode(bytes.NewReader(raw))
	if e != nil {
		return nil, "", fmt.Errorf("Could not read this image.")
	}
	view := orientedImage{img, orientation}
	bounds := view.Bounds()
	w, h := bounds.Dx(), bounds.Dy()
	if w > 1280 || h > 1280 {
		if w >= h {
			h = h * 1280 / w
			w = 1280
		} else {
			w = w * 1280 / h
			h = 1280
		}
	}
	w = max(w, 1)
	h = max(h, 1)
	dst := image.NewNRGBA(image.Rect(0, 0, w, h))
	draw.CatmullRom.Scale(dst, dst.Bounds(), view, bounds, draw.Src, nil)
	var out bytes.Buffer
	ext := "jpg"
	if dst.Opaque() {
		e = jpeg.Encode(&out, dst, &jpeg.Options{Quality: 88})
	} else {
		ext = "png"
		e = png.Encode(&out, dst)
	}
	if e != nil {
		return nil, "", fmt.Errorf("Could not prepare this cover.")
	}
	return out.Bytes(), ext, nil
}
func saveCover(dir string, content []byte, ext string) (string, error) {
	name := fmt.Sprintf("%x.%s", sha256.Sum256(content), ext)
	f, e := os.CreateTemp(dir, ".cover-*")
	if e != nil {
		return "", e
	}
	tmp := f.Name()
	defer os.Remove(tmp)
	if _, e = f.Write(content); e != nil {
		f.Close()
		return "", e
	}
	if e = f.Close(); e != nil {
		return "", e
	}
	if e = os.Rename(tmp, filepath.Join(dir, name)); e != nil {
		return "", e
	}
	if e = prepareUploadVariants(dir, name); e != nil {
		return "", e
	}
	return name, nil
}

// Orient through a view while resizing; avoid another full-sized decoded image.
type orientedImage struct {
	image.Image
	orientation int
}

func (o orientedImage) Bounds() image.Rectangle {
	b := o.Image.Bounds()
	if o.orientation >= 5 && o.orientation <= 8 {
		return image.Rect(0, 0, b.Dy(), b.Dx())
	}
	return image.Rect(0, 0, b.Dx(), b.Dy())
}
func (o orientedImage) At(x, y int) color.Color {
	b := o.Image.Bounds()
	w, h := b.Dx(), b.Dy()
	switch o.orientation {
	case 2:
		x = w - 1 - x
	case 3:
		x, y = w-1-x, h-1-y
	case 4:
		y = h - 1 - y
	case 5:
		x, y = y, x
	case 6:
		x, y = y, h-1-x
	case 7:
		x, y = w-1-y, h-1-x
	case 8:
		x, y = w-1-y, x
	}
	return o.Image.At(x+b.Min.X, y+b.Min.Y)
}
func exifOrientation(b []byte) int {
	b = bytes.TrimPrefix(b, []byte("Exif\x00\x00"))
	if len(b) < 8 {
		return 1
	}
	var order binary.ByteOrder
	switch string(b[:2]) {
	case "II":
		order = binary.LittleEndian
	case "MM":
		order = binary.BigEndian
	default:
		return 1
	}
	if order.Uint16(b[2:4]) != 42 {
		return 1
	}
	offset := uint64(order.Uint32(b[4:8]))
	if offset+2 > uint64(len(b)) {
		return 1
	}
	count := int(order.Uint16(b[offset : offset+2]))
	for i := 0; i < count; i++ {
		pos := offset + 2 + uint64(i)*12
		if pos+12 > uint64(len(b)) {
			break
		}
		p := b[pos : pos+12]
		if order.Uint16(p[:2]) == 0x112 && order.Uint16(p[2:4]) == 3 && order.Uint32(p[4:8]) == 1 {
			v := int(order.Uint16(p[8:10]))
			if v >= 1 && v <= 8 {
				return v
			}
		}
	}
	return 1
}
func imageMetadata(b []byte, format string) (int, bool) {
	orientation := 1
	animated := false
	switch format {
	case "jpeg":
		for pos := 2; pos+4 <= len(b); {
			if b[pos] != 0xff {
				break
			}
			marker := b[pos+1]
			pos += 2
			if marker == 0xda || marker == 0xd9 {
				break
			}
			if marker == 0xff {
				pos--
				continue
			}
			if marker == 0x01 || (marker >= 0xd0 && marker <= 0xd7) {
				continue
			}
			n := int(binary.BigEndian.Uint16(b[pos : pos+2]))
			if n < 2 || pos+n > len(b) {
				break
			}
			if marker == 0xe1 && bytes.HasPrefix(b[pos+2:pos+n], []byte("Exif\x00\x00")) {
				orientation = exifOrientation(b[pos+2 : pos+n])
			}
			pos += n
		}
	case "png":
		for pos := 8; pos+12 <= len(b); {
			n := uint64(binary.BigEndian.Uint32(b[pos : pos+4]))
			end := uint64(pos) + 12 + n
			if end > uint64(len(b)) {
				break
			}
			kind := string(b[pos+4 : pos+8])
			data := b[pos+8 : int(end)-4]
			if kind == "acTL" {
				animated = true
			}
			if kind == "eXIf" {
				orientation = exifOrientation(data)
			}
			pos = int(end)
		}
	case "webp":
		for pos := 12; pos+8 <= len(b); {
			n := uint64(binary.LittleEndian.Uint32(b[pos+4 : pos+8]))
			end := uint64(pos) + 8 + n
			if end > uint64(len(b)) {
				break
			}
			kind := string(b[pos : pos+4])
			data := b[pos+8 : int(end)]
			if kind == "ANIM" || kind == "ANMF" || (kind == "VP8X" && len(data) > 0 && data[0]&2 != 0) {
				animated = true
			}
			if kind == "EXIF" {
				orientation = exifOrientation(data)
			}
			pos = int(end + n%2)
		}
	}
	return orientation, animated
}
