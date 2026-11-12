"""Prepare deployment secrets without displaying or embedding them in source."""
import argparse
import ast
import getpass
import os
from pathlib import Path
import re
from werkzeug.security import generate_password_hash

parser = argparse.ArgumentParser()
parser.add_argument('--arduino-env', type=Path, required=True)
parser.add_argument('--password-file', type=Path, help='Read one password supplied through the secure input card')
parser.add_argument('--output', type=Path, default=Path('.env'))
args = parser.parse_args()
source = args.arduino_env.read_text()
def value(name):
    match = re.search(r'\b' + name + r'\[\]\s*=\s*("(?:[^"\\]|\\.)*")', source)
    if not match:
        raise SystemExit('Missing Arduino setting: ' + name)
    return ast.literal_eval(match.group(1))
password = args.password_file.read_text().strip() if args.password_file else getpass.getpass('Choose a shelf password (at least 14 characters): ')
if len(password) < 14:
    raise SystemExit('Choose a password with at least 14 characters.')
# PBKDF2 is supported by both the local system Python and the container.
settings = {
    'PUBLIC_URL': 'https://vinyl.bray.dev',
    'APP_PASSWORD_HASH': generate_password_hash(password, method='pbkdf2:sha256:1000000'),
    'SPOTIFY_CLIENT_ID': value('clientId'),
    'SPOTIFY_CLIENT_SECRET': value('clientSecret'),
    'SPOTIFY_REFRESH_TOKEN': value('SPOTIFY_REFRESH_TOKEN'),
}
# Single quotes prevent Compose from interpolating dollar signs in the hash.
for val in settings.values():
    if any(c in val for c in ["'", '\n', '\r']):
        raise SystemExit('A credential contains unsupported dotenv characters.')
fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as out:
    for key, val in settings.items():
        out.write(f"{key}='{val}'\n")
print('Deployment credentials written privately. No secret values were displayed.')
