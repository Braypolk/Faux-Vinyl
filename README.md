# FauxVinyl

FauxVinyl turns NFC album cards into a personal Spotify shelf. The current application is a Go web server with SQLite, server-rendered HTML and plain JavaScript. It can run on any Docker host.

Browse front/back sleeves and vinyl/CD artwork, search artists, albums and songs, arrange the shelf, and play, pause or resume music. Each card has a permanent NFC URL; editing its Spotify mapping keeps that URL intact.

## Work locally

Install Go 1.27.3+ and a C compiler (SQLite uses CGO), then run:

```sh
make dev
```

Open **http://127.0.0.1:18787**. Local development signs in automatically, simulates playback and uses a separate ignored `server/.dev-data/` database. It does not load production `.env` credentials. Templates and static files reload during development; restart after changing Go code.

```sh
make test
make build
make secrets  # requires Gitleaks
```

See [`tests/README.md`](tests/README.md) for all test commands and [`server/README.md`](server/README.md) for app usage, additional checks, artwork tooling, deployment and backups.

## Project layout

| Path | Purpose |
| --- | --- |
| [`server/`](server/) | Current Go app, runtime data and Docker setup |
| `server/views/`, `server/static/` | Go templates and browser code |
| [`tests/`](tests/README.md) | All Go, browser, artwork and configuration tests and fixtures |
| [`tools/`](tools/README.md) | Configuration, artwork maintenance and secret checks |
| [`archive/`](archive/) | Original ESP32 firmware |

Your optional collection and artwork live in ignored `server/collection/`; device defaults live in ignored `server/preferences.json`, and saved playback preferences stay in SQLite. A clean checkout starts with an empty shelf. Synthetic collection fixtures live in `tests/fixtures/collection/`. Obsolete print artwork, its preparation pipeline, artwork reviews and the retired Flask app have been removed. Local credentials, runtime data, binaries and rollback backups stay ignored; local rollback files live under `.local/deployment-backups/`.

## Before committing

Install [Gitleaks](https://github.com/gitleaks/gitleaks#installing) (`brew install gitleaks` on macOS), then run `make secrets`. It scans tracked changes and eligible new files, excludes ignored local data, redacts findings, and rejects ignored files that were force-added. Use `GITLEAKS=/path/to/gitleaks` if needed.

To enable the same protection for staged changes on every commit:

```sh
git config core.hooksPath .githooks
```

Credentials belong in ignored `.env` files or private secret files. Database copies, session keys, tunnel tokens, installation-specific deployment tools and private backups must stay out of commits. Local deployment tools, their tests and generated NFC exports are ignored. Ignore rules apply inside `archive/` too; only blank credential examples are versioned. Docker builds include only the current runtime and final assets. Secret scanning is an additional check, not a guarantee; review the staged diff before committing.

This project continues the history of [Braypolk/Faux-Vinyl](https://github.com/Braypolk/Faux-Vinyl).
