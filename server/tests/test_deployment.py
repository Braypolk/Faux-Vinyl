"""Shared-tunnel updates must never replace another application's routes."""
import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cloudflare_setup
import deploy_truenas


def test_shared_deployment_does_not_create_or_read_a_tunnel_token(tmp_path, monkeypatch):
    (tmp_path / '.env').write_text("PUBLIC_URL='https://vinyl.bray.dev'\nAPP_PASSWORD_HASH='test'\n")
    (tmp_path / 'Dockerfile').write_text((deploy_truenas.ROOT / 'Dockerfile').read_text())
    monkeypatch.setattr(deploy_truenas, 'ROOT', tmp_path)
    config = deploy_truenas.compose_config('/mnt/main/fauxvinyl', shared_tunnel=True)
    assert set(config['services']) == {'fauxvinyl'}
    assert config['services']['fauxvinyl']['image'].startswith('fauxvinyl-go:')
    assert config['services']['fauxvinyl']['environment']['GOMEMLIMIT'] == '96MiB'
    assert 'go-source-bundle.tar.gz' in config['services']['fauxvinyl']['build']['dockerfile_inline']
    assert 'python' not in config['services']['fauxvinyl']['build']['dockerfile_inline']
    assert config['services']['fauxvinyl']['ports'] == ['127.0.0.1:8787:8787']
    assert config['services']['fauxvinyl']['volumes'] == ['/mnt/main/fauxvinyl:/data']


@pytest.mark.parametrize('existing', ['missing', 'matching', 'conflicting'])
def test_shared_route_updates_preserve_immich_and_refuse_conflicts(tmp_path, monkeypatch, existing):
    photos = {'hostname': 'photos.bray.dev', 'service': 'http://localhost:30041',
              'originRequest': {'connectTimeout': 15}}
    rules = [copy.deepcopy(photos)]
    if existing != 'missing':
        rules.append({'hostname': 'vinyl.bray.dev',
                      'service': 'http://127.0.0.1:8787' if existing == 'matching' else 'http://unexpected:8080',
                      'originRequest': {}})
    rules.append({'service': 'http_status:404'})
    original = {'ingress': rules, 'warp-routing': {'enabled': False}}
    state = {'account_id': 'account', 'zone_id': 'zone', 'tunnel_id': 'shared',
             'hostname': 'vinyl.bray.dev', 'tunnel_mode': 'shared'}
    (tmp_path / 'deployment-state.json').write_text(json.dumps(state))

    class FakeCloudflare:
        def __init__(self):
            self.saved = None

        def call(self, method, path, data=None):
            if path == '/zones?name=bray.dev':
                assert method == 'GET'
                return [{'id': 'zone', 'account': {'id': 'account'}}]
            if path.endswith('/configurations'):
                if method == 'GET':
                    return {'config': copy.deepcopy(original)}
                assert method == 'PUT'
                self.saved = copy.deepcopy(data['config'])
                return {}
            assert method == 'GET' and path.endswith('/cfd_tunnel/shared')
            return {'status': 'healthy'}

    cf = FakeCloudflare()
    monkeypatch.setattr(cloudflare_setup, 'ROOT', tmp_path)
    monkeypatch.setattr(cloudflare_setup, 'Cloudflare', lambda token_file: cf)
    monkeypatch.setattr(sys, 'argv', ['cloudflare_setup.py', '--token-file', 'unused'])
    if existing == 'conflicting':
        with pytest.raises(RuntimeError, match='unexpected route'):
            cloudflare_setup.main()
        assert cf.saved is None
    else:
        cloudflare_setup.main()
        if existing == 'matching':
            assert cf.saved is None
        else:
            assert cf.saved['ingress'][0] == photos
            assert cf.saved['ingress'][-1] == {'service': 'http_status:404'}
            assert cf.saved['warp-routing'] == original['warp-routing']
            assert cf.saved['ingress'][1]['service'] == 'http://127.0.0.1:8787'


def test_go_archive_contains_no_secrets_or_legacy_runtime():
    import io
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(deploy_truenas.source_archive()), mode='r:gz') as archive:
        names = set(archive.getnames())
    assert {'main.go', 'shelf.go', 'store.go', 'releases.go', 'release-dates.json', 'responsive.go', 'image-variants.json', 'auth.go', 'covers.go', 'spotify.go', 'go.mod', 'go.sum', 'views/base.html'} <= names
    assert not any(name.endswith('.py') or name.startswith('.') or 'backup' in name or 'test' in name for name in names)
    assert 'static/covers/harry-2026.front.99112a958bd2.webp' in names
    assert 'static/covers/olivia-2026.front.747b0a306618.webp' in names
