"""Generated images match display roles and can be safely rebuilt."""
import hashlib
import json
import os
from pathlib import Path
import sys

from PIL import Image, ImageDraw
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/artwork'))
from optimize_artwork import build_artwork


@pytest.fixture
def artwork(tmp_path):
    covers = tmp_path / 'static/covers'
    discs = tmp_path / 'static/discs'
    covers.mkdir(parents=True)
    discs.mkdir()
    Image.new('RGB', (800, 400), 'red').save(covers / 'front.webp', 'WEBP')
    Image.new('RGB', (700, 350), 'blue').save(covers / 'back.webp', 'WEBP')
    Image.new('RGB', (120, 60), 'green').save(covers / 'small.webp', 'WEBP')
    disc = Image.new('RGBA', (648, 648))
    draw = ImageDraw.Draw(disc)
    draw.ellipse((16, 16, 632, 632), fill='red')
    draw.ellipse((290, 290, 358, 358), fill=(0, 0, 0, 0))
    disc.save(discs / 'disc.webp', 'WEBP', exact=True)
    (tmp_path / 'catalogue.json').write_text(json.dumps({'version': 1, 'items': {
        'album': {'artwork': {'front': 'covers/front.webp', 'back': 'covers/back.webp'},
                  'discs': [{'image': '/static/discs/disc.webp'}]},
        'small': {'artwork': {'front': 'covers/small.webp', 'back': 'covers/small.webp'}},
    }}))
    return tmp_path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_sizes_fit_display_roles_without_upscaling_or_changing_originals(artwork):
    originals = {path: digest(path) for path in (artwork / 'static').rglob('*.webp')}
    build_artwork(artwork)
    expected = {
        'covers-front-w160.webp': 160,
        'covers-front-w320.webp': 320,
        'covers-front-w640.webp': 640,
        'covers-back-w320.webp': 320,
        'covers-back-w640.webp': 640,
        'discs-disc-w64.webp': 64,
        'discs-disc-w160.webp': 160,
        'discs-disc-w320.webp': 320,
        'discs-disc-w640.webp': 640,
    }
    generated = artwork / 'static/optimized'
    assert {path.name for path in generated.iterdir()} == set(expected)
    for name, width in expected.items():
        with Image.open(generated / name) as image:
            assert image.width == width
            if name.startswith('covers-'):
                assert image.width == image.height * 2
            else:
                assert image.mode == 'RGBA'
                assert image.getpixel((0, 0))[3] == 0
                assert image.getpixel((image.width // 2, image.height // 2))[3] == 0
    assert not (artwork / 'image-variants.json').exists()
    assert all(digest(path) == before for path, before in originals.items())


def test_rebuild_reuses_outputs_and_prunes_removed_artwork(artwork):
    build_artwork(artwork)
    generated = artwork / 'static/optimized'
    before = {path: (digest(path), path.stat().st_mtime_ns) for path in generated.glob('*.webp')}
    stale = generated / 'obsolete-128.webp'
    stale.write_bytes(b'stale derivative')
    build_artwork(artwork)
    assert not stale.exists()
    assert {path: (digest(path), path.stat().st_mtime_ns) for path in generated.glob('*.webp')} == before
    mapping = json.loads((artwork / 'catalogue.json').read_text())
    del mapping['items']['album']['artwork']['back']
    (artwork / 'catalogue.json').write_text(json.dumps(mapping))
    build_artwork(artwork)
    assert not list(generated.glob('covers-back-*.webp'))
    assert (artwork / 'static/covers/back.webp').exists(), 'pruning must preserve originals'


def test_failed_source_read_keeps_the_previous_derivatives(artwork):
    build_artwork(artwork)
    generated = {path: digest(path) for path in (artwork / 'static/optimized').glob('*.webp')}
    (artwork / 'static/covers/front.webp').unlink()
    with pytest.raises(FileNotFoundError):
        build_artwork(artwork)
    assert {path: digest(path) for path in (artwork / 'static/optimized').glob('*.webp')} == generated


@pytest.mark.parametrize('catalogue', [{'version': 2, 'items': {'album': {}}}, {'version': 1, 'items': {}}, {'version': 1, 'items': []}])
def test_invalid_catalogue_cannot_prune_existing_images(artwork, catalogue):
    build_artwork(artwork)
    generated = {path: digest(path) for path in (artwork / 'static/optimized').glob('*.webp')}
    (artwork / 'catalogue.json').write_text(json.dumps(catalogue))
    with pytest.raises(ValueError, match='catalogue'):
        build_artwork(artwork)
    assert {path: digest(path) for path in (artwork / 'static/optimized').glob('*.webp')} == generated


def test_changed_source_refreshes_predictable_outputs(artwork):
    build_artwork(artwork)
    output = artwork / 'static/optimized/covers-front-w320.webp'
    before = digest(output)
    os.utime(output, ns=(1, 1))
    Image.new('RGB', (800, 400), 'blue').save(artwork / 'static/covers/front.webp', 'WEBP')
    build_artwork(artwork)
    assert digest(output) != before


def test_matching_cover_and_disc_names_do_not_collide(artwork):
    cover = artwork / 'static/covers/front.webp'
    disc = artwork / 'static/discs/front.webp'
    disc.write_bytes((artwork / 'static/discs/disc.webp').read_bytes())
    catalogue = json.loads((artwork / 'catalogue.json').read_text())
    catalogue['items']['album']['discs'][0]['image'] = '/static/discs/front.webp'
    (artwork / 'catalogue.json').write_text(json.dumps(catalogue))
    build_artwork(artwork)
    with Image.open(artwork / 'static/optimized/covers-front-w320.webp') as front:
        assert front.size == (320, 160)
    with Image.open(artwork / 'static/optimized/discs-front-w320.webp') as front:
        assert front.size == (320, 320)
    assert cover.exists()
