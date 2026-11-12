"""Prepare verified broader-search finds for the disposable approval board only."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
IMAGES = ROOT / 'static/disc-review/images'
QUALITIES = {'full', 'mockup', 'packaging', 'label', 'partial'}


def run():
    catalogue = json.loads((ROOT / 'static/disc-review/catalogue.json').read_text())
    albums = {a['id']: a for a in catalogue['albums']}
    approved = set(catalogue.get('approved', []))
    overrides_path = OUT / 'broader-review-overrides.json'
    overrides = json.loads(overrides_path.read_text()) if overrides_path.exists() else {}
    formats = {a['id']: {c['kind'] for c in a['candidates'] if c['id'] in approved}
               for a in albums.values()}
    candidates, seen = [], set()
    for path in sorted(OUT.glob('broader-search*-candidates.json')):
        for item in json.loads(path.read_text()):
            item = {**item, **overrides.get(item['image_url'], {})}
            album_id, kind = item['album_id'], item['kind']
            if album_id not in albums or kind in formats[album_id]:
                continue
            if kind not in {'vinyl', 'cd'} or item['quality'] not in QUALITIES:
                raise ValueError(f'Invalid format/quality in {path.name}: {item}')
            local = Path(item['local_file'])
            raw = local.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            signature = (album_id, kind, digest)
            if signature in seen:
                continue
            seen.add(signature)
            image_id = 'external-' + kind + '-' + digest[:20]
            with Image.open(local) as image:
                extension = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp', 'GIF': 'gif'}.get(image.format)
                if not extension:
                    raise ValueError(f'Unsupported image format: {local}')
                original_name = image_id + '.' + extension
                (IMAGES / original_name).write_bytes(raw)
                preview_name = image_id + '-preview.webp'
                preview = ImageOps.exif_transpose(image).convert('RGBA')
                preview.thumbnail((500, 500), Image.Resampling.LANCZOS)
                preview.save(IMAGES / preview_name, 'WEBP', quality=88, method=6)
            candidates.append({
                'id': album_id + ':' + image_id,
                'image_id': image_id,
                'album_id': album_id,
                'release_id': '',
                'kind': kind,
                'label': item['title'],
                'note': item['note'],
                'quality': item['quality'],
                'edition': item['title'],
                'status': item.get('status', 'Unknown'),
                'preview': 'images/' + preview_name,
                'inspect': 'images/' + original_name,
                'original': item['image_url'],
                'source': item['source'],
                'user_reference': False,
                'broader_search': True,
                'sha256': digest,
            })
    (OUT / 'broader-review-candidates.json').write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False) + '\n')
    print(f'Prepared {len(candidates)} broader-search options for approval; no shelf assets changed.')


if __name__ == '__main__':
    run()
