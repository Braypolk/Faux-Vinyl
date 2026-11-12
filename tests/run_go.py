"""Compile centralized Go tests in the server package through a temporary overlay."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'server'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['test', 'vet'])
    parser.add_argument('flags', nargs=argparse.REMAINDER, help='Additional Go flags, such as -race or -run TestLogin')
    args = parser.parse_args()
    tests = sorted((ROOT / 'tests/server').glob('*_test.go'))
    if not tests:
        parser.error('No Go tests found in tests/server')
    replacements = {}
    for test in tests:
        destination = SERVER / test.name
        if destination.exists():
            parser.error('Go test also exists in server: ' + test.name)
        replacements[str(destination)] = str(test)
    # Files stay in tests/. The compiler sees them beside the app, retaining
    # private-function access and the server working directory for its assets.
    with tempfile.TemporaryDirectory(prefix='fauxvinyl-go-tests-') as directory:
        overlay = Path(directory) / 'overlay.json'
        overlay.write_text(json.dumps({'Replace': replacements}))
        result = subprocess.run(['go', args.command, '-overlay', str(overlay), *args.flags, './...'], cwd=SERVER)
        return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
