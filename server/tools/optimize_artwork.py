"""Build static responsive WebP derivatives; originals and catalogue paths stay intact."""
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'static/optimized'
DEST.mkdir(parents=True, exist_ok=True)
sources = set()
for art in json.loads((ROOT / 'artwork.json').read_text()).values():
    sources.update('/static/' + art[side] for side in ('front', 'back') if art.get(side))
for options in json.loads((ROOT / 'disc-artwork.json').read_text()).values():
    sources.update(option['image'] for option in options)
manifest = {}
for url in sorted(sources):
    path = ROOT / url.lstrip('/')
    raw = path.read_bytes()
    fingerprint = hashlib.sha256(raw + b'responsive-v1-q82').hexdigest()[:16]
    with Image.open(io.BytesIO(raw)) as source:
        image = ImageOps.exif_transpose(source).convert('RGBA' if source.has_transparency_data else 'RGB')
        width, height = image.size
        variants = []
        for target in (64, 128, 160, 320, 640):
            if target >= width:
                continue
            name = f'{fingerprint}-{target}.webp'
            output = DEST / name
            if not output.exists():
                resized = image.resize((target, max(1, round(height * target / width))), Image.Resampling.LANCZOS)
                resized.save(output, 'WEBP', quality=82, method=6, exact=True)
            variants.append({'url': '/static/optimized/' + name, 'width': target})
        variants.append({'url': url, 'width': width})
        manifest[url] = variants
(ROOT / 'image-variants.json').write_text(json.dumps(manifest, separators=(',', ':')) + '\n')
fronts = { '/static/' + art['front'] for art in json.loads((ROOT / 'artwork.json').read_text()).values() if art.get('front') }
before = sum((ROOT / u.lstrip('/')).stat().st_size for u in fronts)
after = sum((ROOT / max((v for v in manifest[u] if v['width'] <= 320), key=lambda v: v['width'])['url'].lstrip('/')).stat().st_size for u in fronts)
print(f'Prepared responsive artwork for {len(sources)} originals. Shelf covers at 320px: {before:,} → {after:,} bytes ({1-after/before:.1%} smaller).')
