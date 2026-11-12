# FauxVinyl web server

The current app is a Go `net/http` server with SQLite and plain JavaScript. It runs on port 8787 in a single Docker container, with browser assets served from `static/`, optional collection artwork served from a separate runtime directory, and HTML embedded from `views/`. Python maintenance tools live in [`../tools/`](../tools/README.md). The original ESP32 firmware lives in [`../archive/`](../archive/).

## Use the shelf

1. Open your configured `PUBLIC_URL` and sign in with the shelf password.
2. Choose a Spotify playback device in **Settings**. Open Spotify on it first if it is missing.
3. Add or edit a record using a Spotify album, playlist or track link.
4. Copy its permanent `/c/<card-id>` NFC URL, or use **Export NFC URLs** for the full CSV. Write URLs as URL/URI records with your NFC app.
5. Tap a tag to select the record and start playback. Editing its title, artwork or Spotify mapping preserves its NFC URL.

Everyone with the shelf password can play music, edit cards and change playback settings. Sign-in is remembered for 90 days.

Hover, touch, swipe or use the arrow controls to browse. Flip a sleeve to see its back and enlarge it for reading. Search matches artists, albums and songs; playing a search result still starts its record. Sorting supports custom order, A–Z, Z–A and original release dates. **Custom → Arrange** saves a shared order with drag, touch or keyboard controls; conflicting changes from another tab require a reload.

**Play** becomes **Pause** or **Resume** for the playing record. Resume keeps the queue and track position. NFC taps start the scanned record once; refreshing the resulting shelf URL does not repeat playback. A lost playback response is reported as unconfirmed and is not retried automatically. The header's spinning record returns to the currently playing album. Production follows Spotify playback state; local development simulates it. There is no user-facing test-mode toggle.

Disc-choice buttons change artwork only and remember choices in the browser. Collections can include hidden glow editions, revealed by pressing their normal disc choice five times consecutively; they reset on reload. Reduced-motion preferences disable rotation and automatic title scrolling.

Upload front/back artwork independently through **Edit** (JPEG, PNG or WebP, up to 8 MB and 12 megapixels each). Uploads are validated, oriented, resized and re-encoded without metadata; **Use original** restores the bundled side. Uploaded covers persist in the data directory, and replaced files are currently retained.

Spotify playback requires Premium and valid playback scopes. Automatic selection uses the active device, then the priority list saved in Settings, then a sole available device. With multiple idle devices and no matching priority, choose a device in Settings. Explicit device choices, priority order and shuffle are installation settings stored in SQLite. If Spotify reports that the developer app owner needs Premium, check the account that owns the developer app; refreshing a token alone does not confirm playback access.

## Local development and checks

Use Go 1.27.3+ and a C compiler for SQLite. From here, or the repository root:

```sh
make dev
make test
make build
```

The preview binds to **http://127.0.0.1:18787**, signs in automatically, simulates devices/playback and uses `server/.dev-data/`. It does not load production `.env` credentials. Templates and static files reload; revision checks pause in hidden tabs and share a three-second cache across tabs. Restart after Go edits. `DEV_ADDR=127.0.0.1:18788 make dev` changes the preview port. The binary is written to `.local/bin/fauxvinyl` under this directory.

All regression tests live in the repository's [`tests/`](../tests/README.md) directory. `make test` runs the Go suite and vet through a temporary file overlay, preserving access to private server functions without moving test files into the application. Use the Make targets or `tests/run_go.py`; plain `go test ./...` does not discover the centralized tests. From the repository root, `make test-race`, `make test-tools` and `make test-ui` run the other checks; see the [test guide](../tests/README.md) for dependencies, browser checks and focused runs.

The Go suite covers authentication, session validation, CSRF, card persistence, artwork uploads, search, release dates, custom order and Spotify transport behavior using local test servers. The Python suite checks artwork generation and private credential setup. Browser tests cover shelf interactions, layout and responsive image loading with playback simulated.

Run `make secrets` from the repository root before committing. See the [root README](../README.md#before-committing) for Gitleaks and the optional staged pre-commit hook.

## Runtime data and backups

`DATA_DIR` defaults to `data/` (`.dev-data/` in local development). The supplied Compose setup mounts `server/data/` at `/data`; make the host directory writable by UID/GID 1000 with mode 0700.

- `fauxvinyl.sqlite3`: cards, custom order, playback settings, search metadata and any rotated Spotify refresh token.
- `session.key`: remembered-login signing key.
- `artwork/`: uploaded sleeves and their generated responsive sizes.

Back these up together, or snapshot the persistent volume while the app is stopped. Backups are private. CSV export preserves card IDs and links, but cannot restore credentials, uploads or sessions. Keep the data directory when upgrading.

The Go server uses signed `v1` login cookies. Retired Flask cookies require signing in again; existing Go logins continue to work. The database and session signing key stay in place across upgrades. Use matching private backups and persistent-volume snapshots for rollback.

## Deploy or update

From the repository root, create a private `server/.env` with the shelf password and Spotify credentials:

```sh
python3.13 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/configure.py --public-url https://fauxvinyl.example
```

Replace the example origin with your installation's public HTTPS origin. The setup tool prompts privately, creates a mode-0600 file, and preserves existing credentials. Credential files are also supported; run `tools/configure.py --help` for options. The optional `--arduino-env archive/esp32/fauxvinyl/env.h` imports the original Spotify credentials once.

`PUBLIC_URL` is required in production and determines NFC links and the accepted request origin. Local development derives it from the loopback listen address. The Go binary reads environment variables, including `*_FILE` for credentials; Docker Compose loads `.env`.

From `server/`, create `data/` owned by UID/GID 1000 with mode 0700, then run:

```sh
docker compose up --build -d
```

The supplied Compose setup binds the app to `127.0.0.1:8787`; configure an HTTPS reverse proxy for your public hostname. Hostnames, routing, access restrictions and infrastructure automation belong in local deployment configuration. The container uses a 96 MiB Go soft memory limit and a 256 MiB ceiling to allow image-decoding peaks. Back up the data directory before updates and retain it when rebuilding the container.

## Collection and artwork

The Go binary embeds templates only. An optional runtime collection lives in `collection/` under the server working directory, or in the directory selected by `COLLECTION_DIR`. This directory contains `catalogue.json` and a `static/` directory with `covers/`, `discs/` and `optimized/` subdirectories. `server/collection/` is ignored by Git. A missing catalogue starts an empty shelf, and records can be added through the app. The portable Docker image contains application code and browser assets; Compose mounts `server/collection/` read-only at `/app/collection`.

The catalogue uses version 1 with an `items` object keyed by Spotify URI. Each item can include title, artist, songs, source, original release details, front/back artwork and disc choices. `starter_cards` is an optional ordered list of ID/URI references for a one-time import. Existing card IDs, personal titles, custom order and deleted cards survive restarts. Optional `legacy_name_corrections` supports historical title migrations; the existing migration flags remain compatible. Starting without a collection does not consume those flags, so a collection can be provided later.

Catalogue search metadata and release dates supply defaults. Updated defaults reach existing installations while explicitly edited metadata and release dates, including intentional blank dates, remain saved. For older release-date rows without provenance, dates matching the collection are recognized as defaults; differing values are preserved as personal corrections.

Artwork references retain the `/static/covers/`, `/static/discs/` and `/static/optimized/` URLs, so moving the collection does not change NFC links or image references. At startup the app discovers existing responsive sizes from predictable filenames and caches their URLs and original dimensions. Restart after changing the catalogue or generated sizes; no binary rebuild is required. Use a new content-hashed original filename when replacing artwork to invalidate browser caches.

Optional `glow` metadata on a catalogue item keeps reveal rules with its disc editions. For example, `"glow": {"variants": {"normal-disc-id": "hidden-disc-id"}, "words": ["where", "do", "we", "go"]}` hides the target edition and reveals it after five consecutive presses on the normal choice. Both editions must belong to the item and have the same kind. Omit `glow` to show every edition normally. Reveals reset on reload and do not change saved disc preferences.

The maintained [artwork tool](../tools/README.md#artwork) generates responsive sizes from the current collection. From the repository root:

```sh
.venv/bin/pip install -r tools/artwork/requirements.txt
.venv/bin/python tools/artwork/optimize_artwork.py
# Or select another collection:
.venv/bin/python tools/artwork/optimize_artwork.py /path/to/collection
```

Fronts use 160/320/640 px, backs 320/640 px, and discs 64/160/320/640 px. Original images remain available and are never upscaled or pruned. Uploaded sleeves remain in the data directory and receive their sizes when saved or during an upgrade.


## Local device defaults

Settings stores the selected device, automatic priority order and shuffle in SQLite. An optional `preferences.json` in the server working directory, or the file selected by `PREFERENCES_FILE`, can bootstrap device priorities:

```json
{"device_priority": ["Desk Speaker", "Kitchen Speaker"]}
```

This file is local and ignored at `server/preferences.json`. Priorities import only when the database has no saved priority setting. Later Settings edits, including clearing the list, take precedence. For Docker, an optional preferences file can live in the persistent data directory with `PREFERENCES_FILE=/data/preferences.json` in `.env`.
