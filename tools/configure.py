"""Create a private .env for the Go server without displaying credentials."""
import argparse
import ast
import getpass
import os
from pathlib import Path
import re

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1] / "server"


def arduino_value(source, name):
    match = re.search(r'\b' + name + r'\[\]\s*=\s*("(?:[^"\\]|\\.)*")', source)
    if not match:
        raise ValueError('Missing Arduino setting: ' + name)
    return ast.literal_eval(match.group(1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arduino-env', type=Path, help='Optional one-time import from an archived env.h')
    parser.add_argument('--password-file', type=Path)
    parser.add_argument('--client-id-file', type=Path)
    parser.add_argument('--client-secret-file', type=Path)
    parser.add_argument('--refresh-token-file', type=Path)
    parser.add_argument('--public-url', required=True, help='Public origin of this installation, such as https://fauxvinyl.example')
    parser.add_argument('--output', type=Path, default=ROOT / '.env')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; keep the current credentials or choose another --output.')
    files = [args.client_id_file, args.client_secret_file, args.refresh_token_file]
    if args.arduino_env and any(files):
        parser.error('Use either --arduino-env or Spotify credential files.')

    def read(path, prompt):
        return path.read_text().strip() if path else getpass.getpass(prompt)

    password = read(args.password_file, 'Choose a shelf password (at least 14 characters): ')
    if len(password) < 14:
        parser.error('Choose a password with at least 14 characters.')
    if args.arduino_env:
        source = args.arduino_env.read_text()
        try:
            credentials = [arduino_value(source, name)
                           for name in ['clientId', 'clientSecret', 'SPOTIFY_REFRESH_TOKEN']]
        except ValueError as error:
            parser.error(str(error))
    else:
        credentials = [read(path, prompt) for path, prompt in zip(files, [
            'Spotify client ID: ', 'Spotify client secret: ', 'Spotify refresh token: '])]
    if not all(credentials):
        parser.error('All three Spotify credentials are required.')
    settings = {
        'PUBLIC_URL': args.public_url,
        'APP_PASSWORD_HASH': generate_password_hash(password, method='pbkdf2:sha256:1000000'),
        **dict(zip(['SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_REFRESH_TOKEN'], credentials)),
    }
    # Single quotes stop Compose from interpolating dollar signs in the hash.
    if any(c in value for value in settings.values() for c in ["'", '\n', '\r']):
        parser.error('A setting contains unsupported dotenv characters.')
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as out:
        for key, value in settings.items():
            out.write(f"{key}='{value}'\n")
    print('Deployment credentials written privately. No secret values were displayed.')


if __name__ == '__main__':
    main()
