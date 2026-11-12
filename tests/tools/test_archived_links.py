"""The generic archive helper accepts inputs without retaining personal URLs."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'archived_links', Path(__file__).resolve().parents[2] / 'archive/esp32/format_link.py')
links = importlib.util.module_from_spec(spec)
spec.loader.exec_module(links)


def test_share_parameters_are_removed():
    assert links.format_link('https://open.spotify.com/album/' + '0' * 22 + '?si=example') == (
        '?item=album&id=' + '0' * 22)


@pytest.mark.parametrize('value', [
    'https://other.example/album/' + '0' * 22,
    'https://open.spotify.com/album/missing',
    'https://open.spotify.com/track/' + '0' * 22,
])
def test_unsupported_links_are_rejected(value):
    with pytest.raises(ValueError):
        links.format_link(value)
