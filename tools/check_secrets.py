"""Scan commit-eligible files without copying ignored local credentials."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def git(root, *args, **kwargs):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          stdout=subprocess.PIPE, **kwargs).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged', action='store_true', help='Check the exact staged changes')
    args = parser.parse_args()
    root = Path(git(Path.cwd(), 'rev-parse', '--show-toplevel').decode().strip())
    scanner = shutil.which(os.environ.get('GITLEAKS', 'gitleaks'))
    if not scanner:
        parser.exit(2, 'Install Gitleaks (brew install gitleaks), or set GITLEAKS to its executable.\n')
    if args.staged:
        names = git(root, 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z')
    else:
        names = git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z')
    # Git permits force-adding ignored files. Refuse those even if the scanner
    # does not recognize their credential format (SQLite and session keys, etc.).
    ignored = subprocess.run(
        ['git', '-C', str(root), 'check-ignore', '--no-index', '--stdin', '-z'],
        input=names, stdout=subprocess.PIPE, check=False)
    if ignored.returncode not in (0, 1):
        raise SystemExit(ignored.returncode)
    if ignored.stdout:
        print('Ignored/private paths must be removed from the index:')
        for name in ignored.stdout.split(b'\0'):
            if name:
                print('  ' + os.fsdecode(name))
        raise SystemExit(1)
    options = ['--redact', '--no-banner']
    if args.staged:
        raise SystemExit(subprocess.run(
            [scanner, 'git', '--pre-commit', '--staged', *options, str(root)], cwd=root).returncode)
    # A private temporary snapshot includes tracked modifications and eligible
    # new files, excludes deleted paths, and leaves local data untouched.
    with tempfile.TemporaryDirectory(prefix='fauxvinyl-secret-scan-') as directory:
        snapshot = Path(directory)
        for name in sorted(set(names.split(b'\0')) - {b''}):
            relative = Path(os.fsdecode(name))
            source = root / relative
            if source.is_symlink():
                parser.exit(1, 'Refusing to copy a symlink into the secret scan: ' + str(relative) + '\n')
            if not source.is_file():
                continue
            destination = snapshot / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        raise SystemExit(subprocess.run([scanner, 'dir', *options, str(snapshot)], cwd=root).returncode)


if __name__ == '__main__':
    main()
