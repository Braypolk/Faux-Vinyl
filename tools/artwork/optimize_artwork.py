"""Build responsive WebP sizes by display role and prune stale generated files."""
import argparse
import json
import os
from pathlib import Path
import tempfile

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2] / "server/collection"

# Fronts appear on the shelf as well as in the sleeve viewer. Backs only appear
# in the viewer; discs also appear in 30px choices and the 52px playing icon.
WIDTHS = {
    'front': (160, 320, 640),
    'back': (320, 640),
    'disc': (64, 160, 320, 640),
}


def artwork_sources(root):
    catalogue = json.loads((root / 'catalogue.json').read_text())
    if catalogue.get('version') != 1 or not isinstance(catalogue.get('items'), dict) or not catalogue['items']:
        raise ValueError('Expected a version 1 catalogue with items')
    sources = {}
    for item in catalogue['items'].values():
        sides = item.get('artwork', {})
        for side in ('front', 'back'):
            if sides.get(side):
                sources.setdefault('/static/' + sides[side], set()).update(WIDTHS[side])
        for option in item.get('discs', []):
            sources.setdefault(option['image'], set()).update(WIDTHS['disc'])
    return sources


def build_artwork(root=ROOT):
    sources = artwork_sources(root)
    destination = root / 'static/optimized'
    destination.mkdir(parents=True, exist_ok=True)
    generated = set()
    created = 0
    for url, widths in sorted(sources.items()):
        path = root / url.lstrip('/')
        with Image.open(path) as source:
            width, height = source.size
            if source.getexif().get(274, 1) in (5, 6, 7, 8):
                width, height = height, width
            image = None
            for target in sorted(widths):
                if target >= width:
                    continue
                name = f'{path.parent.name}-{path.stem}-w{target}.webp'
                output = destination / name
                if output.is_symlink():
                    raise ValueError('Generated artwork must not be a symlink: ' + name)
                if not output.exists() or output.stat().st_mtime_ns < path.stat().st_mtime_ns:
                    # Cached derivatives need only the source header, not a full decode.
                    if image is None:
                        image = ImageOps.exif_transpose(source).convert('RGBA' if source.has_transparency_data else 'RGB')
                    resized = image.resize((target, max(1, round(height * target / width))), Image.Resampling.LANCZOS)
                    fd, temporary = tempfile.mkstemp(prefix='.variant-', dir=destination)
                    try:
                        with os.fdopen(fd, 'wb') as out:
                            os.fchmod(out.fileno(), 0o644)
                            resized.save(out, 'WEBP', quality=82, method=6, exact=True)
                        os.replace(temporary, output)
                    finally:
                        if os.path.exists(temporary):
                            os.unlink(temporary)
                    created += 1
                generated.add(name)

    # Only prune after every source has been read and its sizes are ready.
    removed = 0
    for path in destination.glob('*.webp'):
        if path.name not in generated:
            path.unlink()
            removed += 1
    print(f'{len(sources)} originals, {len(generated)} responsive images; created {created}, removed {removed}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection", nargs="?", type=Path, default=ROOT, help="Collection directory containing catalogue.json and static artwork")
    build_artwork(parser.parse_args().collection)
