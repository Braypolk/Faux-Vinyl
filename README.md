# FauxVinyl

FauxVinyl turns NFC album cards into a personal music shelf. The current app is a Go web server in [`server/`](server/), deployed as a TrueNAS Docker app at **https://vinyl.bray.dev**. This project continues the history of [Braypolk/Faux-Vinyl](https://github.com/Braypolk/Faux-Vinyl).

The shelf includes front/back sleeves, selectable vinyl/CD artwork, playback and pause/resume controls, artist/song/album search, custom shelf order, original release-date sorting, responsive artwork and mobile layouts. NFC URLs stay stable when an album mapping changes.

## Work locally

From this project folder, with Go 1.27.3+ and a C compiler installed:

```sh
make dev
```

Open **http://127.0.0.1:18787**. The preview uses a separate `.dev-data/` database, signs in automatically, and simulates playback. Templates and static files reload during development; restart after Go code changes. The live TrueNAS app uses its own persistent data.

```sh
make test
make build
```

See [`server/README.md`](server/README.md) for browser checks, image preparation, deployment and backups. Production credentials, local runtime state and deployment configuration stay in ignored files. The current local preview state has been carried over into this folder.

## Artwork and NFC workflow

The app's final artwork and responsive sizes are versioned under `server/static/`. Artwork sources, reconstruction prompts, approval data and preparation scripts live under `server/found-artwork/` and `server/artwork-review-research/`. The approval interface is preserved under `server/static/disc-review/`, and the NFC writing lists are in `server/nfc-writing/`.

Large source-photo downloads, generated intermediates and research caches remain available locally and are ignored by Git; the source URLs and preparation scripts are retained. Rebuilding the app uses the final versioned assets directly.

## Original ESP32 firmware

The original Arduino sketch and print-cover files remain at the project root. The sketch uses [spotify-api-arduino](https://github.com/witnessmenow/spotify-api-arduino). Its private `env.h` stays ignored. The web app replaces the ESP32 server for the current setup.
