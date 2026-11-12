# Maintenance tools

The application lives in `server/`. Run these commands from the repository root. Tools resolve application paths relative to this checkout, so invocation does not depend on the working directory. Explicit input-file paths remain relative to the command's working directory.

## Configuration

```sh
python3.13 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/configure.py --public-url https://fauxvinyl.example
```

Replace the example origin with your installation's public HTTPS origin. `configure.py` creates a private `server/.env` using hidden prompts or credential files. Existing credentials are never overwritten. Run it with `--help` for file inputs and the optional one-time import from the archived firmware. See the [server deployment guide](../server/README.md#deploy-or-update) for the portable Docker setup.

## Artwork

```sh
.venv/bin/pip install -r tools/artwork/requirements.txt
.venv/bin/python tools/artwork/optimize_artwork.py
# Optional: pass a different collection directory as the positional argument.
```

`artwork/optimize_artwork.py` creates responsive WebP sizes from the artwork and disc mappings in the ignored `server/collection/catalogue.json`. Predictable names let the app discover sizes once at startup: `covers/album.<hash>.webp` produces `optimized/covers-album.<hash>-w320.webp`, while disc derivatives use the `discs-` prefix. Sizes follow their display roles: front covers use 160/320/640 px, back covers 320/640 px, and discs 64/160/320/640 px (including the small choice and playing icons). Sizes at or above an original's width are skipped; the original remains available for enlarged viewing. A shared image receives the union of the sizes needed by its roles.

The tool reuses existing derivatives unless their source is newer, writes resized files atomically, then removes unreferenced WebP files from `static/optimized/` after successfully processing every source. This directory contains generated files only; keep originals in the flat `static/covers/` and `static/discs/` directories. Missing or unreadable source images stop the run before pruning. Use a new content-hashed original filename when replacing artwork to invalidate browser caches, update the catalogue reference, and restart the app after regenerating sizes.

Run the artwork regression checks with `.venv/bin/python -m pytest -q tests/artwork`.

The old print-cover import pipeline and artwork review tooling have been removed. Current full-size images live in `server/collection/static/covers/` and `server/collection/static/discs/`; their responsive sizes live in `server/collection/static/optimized/`. Update the current mappings when replacing artwork, then regenerate responsive sizes with the command above.


All regression suites and setup instructions are collected in [`tests/`](../tests/README.md).

## Secret checks

Install Gitleaks and run `make secrets` from the repository root. `check_secrets.py` checks commit-eligible files; `--staged` checks the exact staged changes. Findings are redacted. Ignored files that were force-added are rejected.

The optional `.githooks/pre-commit` hook calls this tool automatically after enabling it with `git config core.hooksPath .githooks`. See the [root README](../README.md#before-committing) for setup.
