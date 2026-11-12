"""Install/update FauxVinyl over Tailscale, preserving its tunnel mode."""
import argparse
import ast
import io
import json
import os
from pathlib import Path
import urllib.request
import tarfile
import requests
import yaml
from truenas_rpc import TrueNAS

ROOT = Path(__file__).resolve().parent


def source_archive():
    files = []
    for name in ['main.go', 'shelf.go', 'search.go', 'releases.go', 'store.go', 'auth.go', 'covers.go', 'discs.go', 'spotify.go', 'responsive.go', 'image-variants.json', 'go.mod', 'go.sum', 'seed-cards.json', 'artwork.json', 'disc-artwork.json', 'search-metadata.json', 'catalogue-names.json', 'release-dates.json']:
        files.append(ROOT / name)
    for directory in ['static', 'views']:
        for path in sorted((ROOT / directory).rglob('*')):
            relative = path.relative_to(ROOT)
            if any(part in {'disc-review', 'disc-prototype'} for part in relative.parts) or path.name in {'disc-prototype.js', 'disc-prototype.css'}:
                continue
            if path.is_file():
                files.append(path)
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as archive:
        for path in files:
            content = path.read_bytes()
            entry = tarfile.TarInfo(str(path.relative_to(ROOT)))
            entry.size = len(content)
            entry.mode = 0o644
            archive.addfile(entry, io.BytesIO(content))
    return output.getvalue()


def upload_source(nas, host, username, password_file, data_path):
    entries = nas.call('filesystem.listdir', [data_path])
    if not any(entry['name'] == 'build' for entry in entries):
        nas.call('filesystem.mkdir', [{'path': data_path + '/build', 'options': {'mode': '755'}}])
    archive = source_archive()
    # Use TrueNAS's file-upload endpoint for binary assets instead of putting
    # multi-megabyte images into a WebSocket configuration message.
    response = requests.post('http://' + host + '/_upload/',
        auth=(username, Path(password_file).read_text().strip()),
        files=[('data', (None, json.dumps({'method': 'filesystem.put',
            'params': [data_path + '/build/go-source-bundle.tar.gz', {'mode': 0o644}]}))),
            ('file', ('go-source-bundle.tar.gz', archive, 'application/gzip'))], timeout=120)
    response.raise_for_status()
    nas.wait_job(response.json()['job_id'])
    print('Uploaded source and artwork (' + str(round(len(archive) / 1024)) + ' KiB). No secrets in archive.', flush=True)


def compose_config(data_path, cloudflared_version=None, shared_tunnel=False):
    inline = (ROOT / 'Dockerfile').read_text().replace('COPY . /src', 'COPY go-source-bundle.tar.gz /tmp/source.tar.gz\nRUN tar -xzf /tmp/source.tar.gz -C /src && rm /tmp/source.tar.gz')
    environment = {}
    for line in (ROOT / '.env').read_text().splitlines():
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            environment[key] = ast.literal_eval(value).replace('$', '$$')
    environment['DATA_DIR'] = '/data'
    environment['GOMEMLIMIT'] = '96MiB'
    environment['GOGC'] = '50'
    restrictions = {'restart': 'unless-stopped', 'read_only': True,
        'cap_drop': ['ALL'], 'security_opt': ['no-new-privileges:true'],
        'logging': {'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '3'}}}
    config = {'services': {
        'fauxvinyl': {**restrictions, 'image': 'fauxvinyl-go:search-20261111', 'build': {'context': data_path + '/build', 'dockerfile_inline': inline}, 'pull_policy': 'build',
            'environment': environment, 'volumes': [data_path + ':/data'],
            'tmpfs': ['/tmp:rw,noexec,nosuid,size=64m'],
            'mem_limit': '256m', 'cpus': 1.0},
    }}
    if shared_tunnel:
        config['services']['fauxvinyl']['ports'] = ['127.0.0.1:8787:8787']
    else:
        config['services']['tunnel'] = {**restrictions, 'image': 'cloudflare/cloudflared:' + cloudflared_version,
            'command': ['tunnel', '--no-autoupdate', 'run'],
            'environment': {'TUNNEL_TOKEN': (ROOT / 'tunnel-token').read_text().strip()},
            'depends_on': {'fauxvinyl': {'condition': 'service_healthy'}},
            'mem_limit': '256m', 'cpus': 1.0}
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='100.111.217.103')
    parser.add_argument('--username', default='admin')
    parser.add_argument('--password-file', required=True)
    parser.add_argument('--update', action='store_true')
    args = parser.parse_args()
    nas = TrueNAS(args.host, args.password_file, args.username)
    dataset_name = 'main/fauxvinyl'
    data_path = '/mnt/' + dataset_name
    existing = nas.call('pool.dataset.query', [[['id', '=', dataset_name]], {'select': ['id']}])
    if not existing:
        nas.call('pool.dataset.create', [{'name': dataset_name, 'type': 'FILESYSTEM', 'acltype': 'POSIX'}])
        nas.wait_job(nas.call('filesystem.setperm', [{'path': data_path, 'uid': 1000, 'gid': 1000,
            'mode': '0700', 'options': {'recursive': False, 'traverse': False, 'stripacl': True}}], timeout=60))
        print('Created private persistent dataset ' + dataset_name, flush=True)
    else:
        print('Preserving existing dataset and its permissions.', flush=True)
    upload_source(nas, args.host, args.username, args.password_file, data_path)
    state_path = ROOT / 'deployment-state.json'
    state = json.loads(state_path.read_text())
    shared = state.get('tunnel_mode') == 'shared'
    version = state.get('cloudflared_version')
    if not shared:
        with urllib.request.urlopen('https://api.github.com/repos/cloudflare/cloudflared/releases/latest', timeout=30) as response:
            version = json.load(response)['tag_name']
    config = compose_config(data_path, version, shared_tunnel=shared)
    state.update({'truenas_host': args.host, 'app_name': 'fauxvinyl', 'dataset': dataset_name,
        'cloudflared_version': version, 'backend': 'go'})
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    # Contains runtime secrets. This is excluded from source packages and images.
    path = ROOT / 'truenas-compose.yaml'
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as out:
        yaml.safe_dump(config, out, sort_keys=False)
    apps = nas.call('app.query', [[['id', '=', 'fauxvinyl']], {'select': ['id', 'state']}])
    if apps and not args.update:
        raise RuntimeError('FauxVinyl already exists; explicitly use --update to apply source changes.')
    mode = 'the existing shared tunnel' if shared else 'cloudflared ' + version
    print('Deploying app with ' + mode + '. Secrets are not logged.', flush=True)
    if apps:
        result = nas.call('app.update', ['fauxvinyl', {'custom_compose_config': config}], timeout=900)
    else:
        result = nas.call('app.create', [{'app_name': 'fauxvinyl', 'custom_app': True, 'custom_compose_config': config}], timeout=900)
    result = nas.wait_job(result)
    print(json.dumps({'app': result.get('id'), 'state': result.get('state')}), flush=True)
    nas.close()


if __name__ == '__main__':
    main()
