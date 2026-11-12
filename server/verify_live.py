"""Verify deployed login, card links, and Spotify access without starting music."""
import argparse
import csv
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.parse

parser = argparse.ArgumentParser()
parser.add_argument('--password-file', type=Path, required=True)
parser.add_argument('--resolve', help='Optional published edge IP while local DNS cache expires')
args = parser.parse_args()
base = 'https://vinyl.bray.dev'

with tempfile.TemporaryDirectory(prefix='fauxvinyl-verify-') as temporary:
    folder = Path(temporary)
    cookies = folder / 'cookies'

    def request(path, data=None):
        destination = folder / 'response'
        command = ['curl', '--silent', '--show-error', '--fail-with-body', '--location', '--max-time', '40',
            '--cookie', str(cookies), '--cookie-jar', str(cookies), '--output', str(destination),
            '--write-out', '%{http_code} %{url_effective}']
        if args.resolve:
            command += ['--resolve', 'vinyl.bray.dev:443:' + args.resolve]
        if data is not None:
            command += ['--header', 'Origin: ' + base, '--data-binary', '@-']
        command += [base + path]
        result = subprocess.run(command, input=urllib.parse.urlencode(data).encode() if data is not None else None,
            capture_output=True, check=False)
        status, _, url = result.stdout.decode().partition(' ')
        if result.returncode:
            raise RuntimeError('Live verification failed for ' + path + ': HTTP ' + status)
        return destination.read_text(), url

    health, _ = request('/healthz')
    assert json.loads(health)['status'] == 'ok'
    login, _ = request('/login')
    csrf = re.search(r'name="csrf" value="([^"]+)"', login).group(1)
    home, landed = request('/login', {'csrf': csrf, 'password': args.password_file.read_text().strip(), 'next': '/'})
    assert landed == base + '/', 'Login did not reach the shelf'
    print('Public HTTPS and shelf sign-in verified.')
    exported, _ = request('/cards.csv')
    cards = list(csv.DictReader(io.StringIO(exported)))
    assert len(cards) >= 48
    assert all(card['nfc_url'].startswith(base + '/c/') for card in cards)
    print(str(len(cards)) + ' cards and permanent domain URLs verified.')
    settings, _ = request('/settings')
    status = re.search(r'Spotify connected[^<]*', settings)
    spotify_error = None
    if not status:
        errors = re.findall(r'role="alert">([^<]+)', settings)
        spotify_error = 'Spotify check failed: ' + ' '.join(errors)
        print(spotify_error)
    else:
        print(status.group(0))
    card, _ = request(urllib.parse.urlsplit(cards[0]['nfc_url']).path)
    assert 'action_token' in card and '/play' in card
    print('Card play form verified. No playback was triggered.')
    if spotify_error:
        raise SystemExit(2)
