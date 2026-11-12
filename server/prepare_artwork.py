"""Build web-sized covers from the project's existing artwork; never edit originals."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageOps
from artwork_colors import cover_colors, write_shelf_colors

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--source-dir', type=Path, required=True)
args = parser.parse_args()
sources = json.loads((ROOT / 'cover-sources.json').read_text())
cards = {card['id']: card for card in json.loads((ROOT / 'seed-cards.json').read_text())}
destination = ROOT / 'static' / 'covers' / 'v2'
destination.mkdir(parents=True, exist_ok=True)
artwork = {}
total = 0
# The supplied print artwork includes a legitimate 10,000 x 10,000 image.
Image.MAX_IMAGE_PIXELS = 128_000_000
for index, (card_id, sides) in enumerate(sources.items(), 1):
    artwork[cards[card_id]['uri']] = {}
    for side, relative in sides.items():
        with Image.open(args.source_dir / relative) as original:
            image = ImageOps.exif_transpose(original)
            limit = 1280 if side == 'back' else 640
            image.thumbnail((limit, limit), Image.Resampling.LANCZOS)
            if image.mode == 'RGBA' or 'transparency' in image.info:
                rgba = image.convert('RGBA')
                image = Image.new('RGB', rgba.size, '#f4f0e7')
                image.paste(rgba, mask=rgba.getchannel('A'))
            else:
                image = image.convert('RGB')
            content = io.BytesIO()
            image.save(content, format='WEBP', quality=84 if side == 'back' else 80, method=6)
            data = content.getvalue()
        if side == 'front':
            with Image.open(io.BytesIO(data)) as cover:
                first, second = cover_colors(cover)
                artwork[cards[card_id]['uri']].update(color=first, secondary_color=second)
        digest = hashlib.sha256(data).hexdigest()[:12]
        name = card_id + ('.back' if side == 'back' else '') + '.' + digest + '.webp'
        (destination / name).write_bytes(data)
        artwork[cards[card_id]['uri']][side] = 'covers/v2/' + name
        total += len(data)
    if index % 10 == 0:
        print('Prepared ' + str(index) + ' covers', flush=True)
write_shelf_colors(artwork, ROOT / 'static' / 'shelf-colors.css')
(ROOT / 'artwork.json').write_text(json.dumps(artwork, indent=2) + '\n')
print('Prepared ' + str(len(artwork)) + ' fronts and ' + str(sum('back' in sides for sides in artwork.values())) + ' backs (' + str(round(total / 1024)) + ' KiB total). Originals unchanged.')
