"""Integrate the second approved artwork batch after every prepared asset is ready."""
from collections import Counter
import hashlib
import html
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'found-artwork/approved-discs-v2'
DEST = ROOT / 'static/discs'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def run():
    decisions = read(OUT / 'decisions-export.json')
    approved = {c['id'] for a in decisions['albums'] for c in a['candidates']
                if c['decision'] == 'approved'}
    baseline = read(OUT / 'baseline-disc-artwork.json')
    provenance = read(OUT / 'baseline-disc-artwork-sources.json')
    original_approvals = read(OUT / 'baseline-approved-decisions.json')
    sources = read(OUT / 'approved-new.json')
    source_by_id = {c['id']: c for c in sources}
    reports = [item for path in sorted(OUT.glob('*/report.json')) for item in read(path)]
    by_id = {item['id']: item for item in reports}
    if len(by_id) != len(reports) or set(by_id) != set(source_by_id):
        missing = sorted(set(source_by_id) - set(by_id))
        raise ValueError(f'Prepared batch incomplete or duplicated: {missing}')
    original_ids = {c['id'] for c in original_approvals}
    if approved != original_ids | set(source_by_id):
        raise ValueError('Prepared assets must match the updated positive approvals exactly.')

    # Validate the entire batch before changing any public catalogue or asset.
    for source in sources:
        item = by_id[source['id']]
        if (item['image_id'], item['album_id'], item['kind']) != (
                source['image_id'], source['album_id'], source['kind']):
            raise ValueError(f'Prepared asset identity mismatch: {source["id"]}')
        reference_hash = hashlib.sha256(Path(source['reference_path']).read_bytes()).hexdigest()
        if reference_hash != source['sha256']:
            raise ValueError(f'Approved original changed: {source["id"]}')
        with Image.open(item['output']) as image:
            if image.size != (648, 648) or image.mode != 'RGBA':
                raise ValueError(f'Expected 648px RGBA artwork: {source["id"]}')
            alpha = image.getchannel('A')
            bounds = alpha.getbbox()
            if bounds != (4, 4, 644, 644) or alpha.getpixel((324, 324)) != 0:
                raise ValueError(f'Disc rim/spindle not standardized: {source["id"]}, {bounds}')
            radius = 38 if source['kind'] == 'cd' else 6
            if any(alpha.getpixel((324 + dx, 324 + dy))
                   for dx, dy in [(radius, 0), (-radius, 0), (0, radius), (0, -radius)]):
                raise ValueError(f'Spindle hole not centered: {source["id"]}')

    manifest = {uri: list(options) for uri, options in baseline.items()}
    counts = Counter((uri, o['kind']) for uri, options in manifest.items() for o in options)
    prepared = []
    for source in sources:
        item = by_id[source['id']]
        raw = Path(item['output']).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        filename = source['image_id'] + '.' + digest[:12] + '.webp'
        (DEST / filename).write_bytes(raw)
        uri, kind = source['uri'], source['kind']
        counts[uri, kind] += 1
        number = counts[uri, kind]
        label = 'Vinyl' if kind == 'vinyl' else 'CD'
        if number > 1:
            label += ' ' + str(number)
        option = {'id': source['image_id'], 'kind': kind, 'label': label,
                  'image': '/static/discs/' + filename}
        manifest.setdefault(uri, []).append(option)
        record = {**source, 'output': option['image'], 'output_sha256': digest,
                  'processing': item['processing'], 'method': item['method'],
                  'generated': item['method'] == 'reference-reconstruction',
                  'generation_prompt': item.get('prompt', ''),
                  'preparation_notes': item.get('notes', '')}
        provenance.append(record)
        prepared.append({**record, 'option': option})
    for options in manifest.values():
        options.sort(key=lambda option: option['kind'] != 'vinyl')

    write(ROOT / 'disc-artwork.json', manifest)
    write(ROOT / 'disc-artwork-sources.json', provenance)
    write(ROOT / 'found-artwork/approved-discs/approved-decisions.json',
          original_approvals + sources)
    write(OUT / 'integrated.json', prepared)
    make_review(prepared)
    print(f'Integrated {len(prepared)} new assets; '
          f'{sum(map(len, manifest.values()))} variants for {len(manifest)} albums.')


def make_review(prepared):
    review = ROOT / 'static/disc-review'
    generated = sum(c['generated'] for c in prepared)
    css = '''*{box-sizing:border-box}body{margin:0;background:#f4f0e7;color:#25251f;font:14px system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:28px}h1{font-size:32px;letter-spacing:-1px;margin:14px 0 8px}header p{color:#717167}a{color:inherit;text-underline-offset:3px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;margin-top:28px}article{border:1px solid #d9d4c8;border-radius:6px;overflow:hidden;background:#faf8f2}.images{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:#d9d4c8}figure{margin:0;background:#eeeae1}img{display:block;width:100%;aspect-ratio:1;object-fit:contain;background:repeating-conic-gradient(#e5e1d7 0% 25%,#eeeae1 0% 50%)0 0/18px 18px}figcaption{font-size:10px;padding:7px 10px;color:#717167}.info{padding:12px}h2{font-size:16px;margin:0 0 5px}.artist,.method{font-size:11px;color:#717167;margin:0 0 8px}.links{font-size:11px;display:flex;gap:16px} @media(max-width:500px){main{padding:18px}.grid{grid-template-columns:1fr}}'''
    (review / 'prepared.css').write_text(css)
    escape = html.escape
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1">'
             '<title>Prepared disc artwork · FauxVinyl</title>'
             '<link rel="stylesheet" href="prepared.css"></head><body><main><header>'
             '<a href="/">← Shelf</a><h1>Prepared disc artwork</h1>'
             f'<p>{len(prepared)} new variants · {generated} reference reconstructions · '
             'original printing preserved where possible.</p></header><div class="grid">']
    for c in prepared:
        original = '/static/disc-review/' + c['inspect']
        method = ('Reference reconstruction' if c['generated'] else
                  'Manual reconstruction · original label' if c['method'] == 'manual-reconstruction'
                  else 'Original artwork cutout')
        parts.append(f'<article><div class="images"><figure><a href="{escape(original)}">'
                     f'<img loading="lazy" src="{escape(original)}" alt="Approved source"></a>'
                     '<figcaption>Approved source</figcaption></figure><figure>'
                     f'<a href="{escape(c["output"])}"><img loading="lazy" '
                     f'src="{escape(c["output"])}" alt="Prepared {escape(c["kind"])}">'
                     '</a><figcaption>Prepared</figcaption></figure></div><div class="info">'
                     f'<h2>{escape(c["album"])}</h2><p class="artist">{escape(c["artist"])}'
                     f' · {escape(c["option"]["label"])}</p><p class="method">{method}</p>'
                     f'<div class="links"><a href="{escape(c["source"])}" target="_blank" '
                     'rel="noopener">Source ↗</a><a href="/">Shelf</a></div></div></article>')
    parts.append('</div></main></body></html>')
    (review / 'prepared.html').write_text(''.join(parts))


if __name__ == '__main__':
    run()
