"""Configure FauxVinyl's route while preserving any shared tunnel routes."""
import argparse
import json
import os
from pathlib import Path
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent


def private_write(path, value):
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as out:
        out.write(value)


class Cloudflare:
    def __init__(self, token_file):
        self.token = Path(token_file).read_text().strip()

    def call(self, method, path, data=None):
        request = urllib.request.Request('https://api.cloudflare.com/client/v4' + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'}, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError('Cloudflare request failed: HTTP ' + str(error.code)) from None
        if not result.get('success'):
            raise RuntimeError('Cloudflare rejected the request.')
        return result['result']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token-file', required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    cf = Cloudflare(args.token_file)
    zones = cf.call('GET', '/zones?name=bray.dev')
    if len(zones) != 1:
        raise RuntimeError('Expected exactly one bray.dev zone.')
    zone = zones[0]
    account_id = zone['account']['id']
    base = '/accounts/' + account_id + '/cfd_tunnel'
    state_path = ROOT / 'deployment-state.json'
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state['account_id'] != account_id or state['zone_id'] != zone['id']:
            raise RuntimeError('Deployment account changed; inspect state before continuing.')
    else:
        matches = cf.call('GET', base + '?name=fauxvinyl&is_deleted=false')
        if matches:
            raise RuntimeError('A FauxVinyl tunnel already exists without local deployment state. Inspect it before reuse.')
        tunnel = cf.call('POST', base, {'name': 'fauxvinyl', 'config_src': 'cloudflare'})
        state = {'account_id': account_id, 'zone_id': zone['id'], 'tunnel_id': tunnel['id'], 'hostname': 'vinyl.bray.dev'}
        private_write(state_path, json.dumps(state, indent=2) + '\n')
        private_write(ROOT / 'tunnel-token', tunnel.get('token') or cf.call('GET', base + '/' + tunnel['id'] + '/token'))
    tunnel_path = base + '/' + state['tunnel_id']
    if state.get('tunnel_mode') == 'shared':
        configuration = cf.call('GET', tunnel_path + '/configurations')['config']
        ingress = configuration['ingress']
        matches = [rule for rule in ingress if rule.get('hostname') == state['hostname']]
        origin = 'http://127.0.0.1:8787'
        if len(matches) > 1 or (matches and matches[0]['service'] != origin):
            raise RuntimeError('An unexpected route already exists for FauxVinyl; inspect it before changing it.')
        if not matches:
            if not ingress or ingress[-1].get('hostname') or ingress[-1].get('path'):
                raise RuntimeError('Shared tunnel catch-all is missing; inspect its ingress rules.')
            ingress.insert(len(ingress) - 1, {'hostname': state['hostname'], 'service': origin, 'originRequest': {}})
            cf.call('PUT', tunnel_path + '/configurations', {'config': configuration})
        print('FauxVinyl uses the existing shared tunnel. Other routes are preserved.')
    else:
        cf.call('PUT', tunnel_path + '/configurations', {'config': {'ingress': [
            {'hostname': state['hostname'], 'service': 'http://fauxvinyl:8787', 'originRequest': {}},
            {'service': 'http_status:404'}]}})
        print('Dedicated FauxVinyl tunnel configured. Token saved privately.')
    if args.publish:
        records_path = '/zones/' + zone['id'] + '/dns_records'
        records = cf.call('GET', records_path + '?name=' + state['hostname'])
        target = state['tunnel_id'] + '.cfargotunnel.com'
        if records:
            if len(records) != 1 or records[0]['type'] != 'CNAME' or records[0]['content'] != target or not records[0]['proxied']:
                raise RuntimeError('An unrelated DNS record exists; it has not been changed.')
        else:
            cf.call('POST', records_path, {'type': 'CNAME', 'name': state['hostname'], 'content': target,
                'proxied': True, 'ttl': 1, 'comment': 'FauxVinyl on TrueNAS via its dedicated Cloudflare Tunnel'})
        print('Published https://' + state['hostname'])
    tunnel = cf.call('GET', tunnel_path)
    print('Tunnel status: ' + tunnel.get('status', 'unknown'))


if __name__ == '__main__':
    main()
