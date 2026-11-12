# FauxVinyl web server

FauxVinyl runs as a TrueNAS custom Docker app at **https://vinyl.bray.dev**.
It replaces the ESP32 web server with permanent NFC card URLs and editable Spotify mappings.

Cloudflare restricts this hostname to the configured home/apartment public IPv4 address and local IPv6 subnet. The shelf password is still required. Devices using cellular data, another internet connection, a VPN, or Private Relay may be blocked. Residents sharing an allowed public address may reach the password screen; this arrangement restricts source addresses rather than identifying a particular Wi-Fi network.

## Use it

1. Open `https://vinyl.bray.dev` and sign in with the shelf password chosen during setup.
2. Open **Settings** and choose a Spotify playback device. Open Spotify on that device first if it is missing.
3. Open a card's edit page and copy its NFC URL, such as `https://vinyl.bray.dev/c/discover-weekly`.
4. Write that URL as a URL/URI record using your NFC writing app. Visitors sign in once on their phone; it remembers them for 90 days.
5. Tap the tag and open its notification. Your shelf opens with that record selected and starts playback through your Spotify account. The phone needs internet access, but does not need Tailscale.

The shelf is seeded with 48 entries from the original `item links.txt`. Add more cards from the home page. Edit a card's title or Spotify link whenever you want: its existing NFC URL stays the same. Use **Export CSV** to download all tag URLs. Everyone with the shelf password can play music, edit cards, and change playback settings.

The entire collection fits in a single row on every screen size without an internal scrollbar. Each spine displays a narrow slice from the center of its front cover; missing covers use a neutral spine. Hover over a spine to preview it immediately, or touch a spine, slide a finger across the shelf, or use the arrow keys. Every front cover loads eagerly. Swipe the selected sleeve to move between records; tap it to turn it over. Search filters the shelf; the sort menu offers Custom, A–Z, Z–A, newest release, and oldest release. Sorting preserves the current search and remembers the order in your browser session. Release sorting uses original album dates, including for remasters and deluxe editions, with undated albums and playlists last. Dates are bundled and stored locally; edit a record’s Original release date to correct it or date a new album. Reissues and automatic search updates cannot overwrite these dates. **Enlarge** opens the current side for closer reading. The selected record keeps its Play, Edit, and Copy NFC URL actions together. Long titles stay on one line and loop gently forward with a gap between repeats. Hover pauses the loop; touch or keyboard focus enables manual scrolling. Reduced-motion preferences disable automatic title scrolling. Browsing also works as a regular card grid when JavaScript is unavailable.

`catalogue-names.json` records the 52-entry name review against the saved Spotify catalogue metadata, including artist credits and source links. Album titles preserve official spelling, punctuation, casing and the linked edition, rather than applying blanket title case. The starter collection uses those names. Existing installations receive a one-time correction matching each original record ID, Spotify URI and old title; custom renames and later edits survive. Playback links, artwork, dates and custom shelf positions stay intact. This cleanup performs no online lookup during startup or browsing.

Press **Play** on the shelf to start the selected record without leaving the page. Feedback stays below the controls while you browse other sleeves. Playback errors include a retry or sign-in/device link where appropriate. Each press gets a fresh one-time action; double presses are blocked while a request is pending. A lost response is reported as unconfirmed playback and is never retried automatically. Existing NFC URLs open this same shelf, select the scanned record, and start it once. The browser then uses a shelf URL with the selected record in its fragment, so refreshing does not repeat playback. Live NFC taps use real playback even if a previous shelf session enabled Test mode; local development keeps simulated playback. Without JavaScript, a Play button remains available and successful playback returns to the shelf.

Enable **Test mode** under the playback controls to preview the UI without Spotify or audio. **Play**, **Pause**, and **Resume** update the selected record's playing indicator and disc animation entirely in the browser; playback requests and state polling are skipped. Browsing another sleeve does not start it. The mode is on by default in local development and remembered for the current tab; `/?test=1` also enables it. Uncheck it to restore normal Play behavior.

While a shelf record is playing, its disc spins at the top center of the header, even while browsing another album. Press it to select the playing record and return to its artwork; a search hiding that record is cleared. Entries without disc artwork use a small vinyl symbol. The shortcut hides when playback pauses or stops and respects reduced-motion preferences.

Choose **Custom → Arrange** to set a shared shelf order. Drag spines with a mouse or touch, or select a record and use **← Move / Move →**. Arrow keys select records; Alt+Left/Right moves the focused record, and Escape cancels the draft. **Save order** persists all positions in SQLite; **Cancel** restores the previous layout. Arrange shows the full collection and restores your search afterward. New records append to the end; renaming or editing artwork does not change positions. If another tab changes the order or adds a record, saving asks you to reload rather than overwrite those changes. Alphabetical/date sorting remains available without changing the saved custom order.

The shelf displays 45 local front covers and 37 matching back covers/tracklists from `covers/` and `covers/done/`, with record placeholders for `maad city`, `Party hits`, and `Other`. Covers are matched by Spotify URI, so renaming a card preserves its artwork, and changing the Spotify item does not leave an unrelated cover behind. Images are bundled with the app and require no Spotify API access. Missing fronts use a vinyl placeholder; missing backs use a labeled sleeve. One file named as a Sheryl Crow tracklist actually depicts a different album, so it is excluded. The original artwork is unchanged; the web copies are WebP images up to 640 pixels on the front and 1280 on the back, with hashed filenames and browser caching. The viewer respects reduced-motion preferences.

Use **Edit** on a selected record to upload front and back artwork independently. Choose JPEG, PNG, or WebP images up to 8 MB and 12 megapixels each. Preview the selected files, then save. Files are validated, oriented, resized to at most 1280 pixels, and re-encoded with metadata removed. Opaque uploads use JPEG and transparent uploads use PNG; existing WebP covers remain supported. Both uploads must be valid before any changes are saved. Custom artwork belongs to that record, takes precedence over bundled covers, and persists across title/link edits, restarts, and deployments. **Use original** removes that side's custom override and restores the bundled cover or placeholder. The permanent NFC URL stays unchanged. Uploaded files require sign-in and are stored in the persistent data directory, not the application image. Replaced files are retained for now; no automatic file cleanup runs.

For bundled artwork preparation, update `cover-sources.json`, install `requirements-artwork.txt` in the build environment, and run `.venv/bin/python prepare_artwork.py --source-dir ../covers`. Rebuild/deploy afterward. `artwork.json` and `static/covers/` are used at runtime. The generated `static/shelf-colors.css` is retained for the earlier gradient design and is no longer loaded by the shelf.

**Existing tags containing `192.168.0.218` still point to that numeric address.** A domain cannot redirect those requests automatically. They need to be rewritten once to use the domain, or a separate LAN routing solution is needed. Domain-based tags then survive future server/IP changes.

Spotify Premium and valid playback scopes are required. Automatic device selection uses the active device, then Living Room TV / Living Room, then a sole available device. Set an explicit device in Settings to avoid following an unrelated active device. The old hardcoded Yamaha power/input requests are not used; wake the receiver or open Spotify if it is offline.

If Settings reports that the **developer app owner** needs Premium, check the account that owns the app in the Spotify developer dashboard. Spotify requires that owner to have an active Premium subscription for development-mode API access, even when a different playback account has Premium. Subscription changes may take a few hours to apply. A successful token refresh alone does not confirm API access. Refresh Settings after the account issue is resolved; another server deployment is unnecessary.

## Deployed architecture

Search matches record names, artists, album names and songs, ignoring case, accents and punctuation. Multiple words can match across those fields. A song match finds the album or playlist containing it; Play still starts that record. Details are cached in SQLite by Spotify URI, and the initial 52 records have a bundled index in `search-metadata.json`. A single bounded worker reads public Spotify embed listings for new links, retries unavailable listings after a day and refreshes cached playlists after a week when the app starts or a record is saved. Page loads and typing never contact Spotify, and indexing needs no playback authorization. Public playlist embeds expose up to 100 songs; private or unavailable listings may need manual details. Use **Edit → Search details** to correct artist, album or song names. Manual corrections survive automatic refreshes and upgrades. Changing a record's Spotify link uses the new item's metadata. `search.go` handles this cache and the public-listing parser; it fails safely if Spotify changes its embed format.

- TrueNAS management: `100.111.217.103` over Tailscale; API username `admin`.
- TrueNAS app: `fauxvinyl`, with one `fauxvinyl` container. The existing TrueNAS `cloudflared` app supplies the shared connector.
- App: one Go binary using net/http and SQLite; port 8787. No Python or nginx process runs in the container.
- Memory: a 512 KiB SQLite page cache, one database connection, GOGC=50, and a 96 MiB Go soft memory limit. The 256 MiB container ceiling allows temporary image-decoding peaks; it does not reserve RAM. TrueNAS reported approximately 12 MiB at idle after loading the shelf and all 82 bundled covers on 2026-11-11. Image uploads can temporarily use more memory.
- Cloudflare Tunnel: shared `truenas-tunnel`, with `vinyl.bray.dev` → `http://127.0.0.1:8787` and the existing `photos.bray.dev` route preserved.
- Public DNS: proxied CNAME to the shared tunnel. FauxVinyl publishes port 8787 bound to NAS loopback (`127.0.0.1`); router forwarding is unnecessary.
- Cloudflare Security → Security rules: the first custom rule, **FauxVinyl - home network only**, blocks requests whose hostname is `vinyl.bray.dev` and whose source is outside the configured IPv4 address and IPv6 subnet. The photos hostname and existing security rules are preserved. The private `deployment-state.json` records the rule ID, expression and current allowed sources; it is configuration documentation, not an automatic IP updater.
- The shared connector already uses host networking. Immich retains its own hostname, origin route and Cloudflare Access protection. The former dedicated FauxVinyl connector has been removed; its inactive tunnel and private credentials are retained for rollback.
- Private persistent dataset: **`main/fauxvinyl`**, mounted from **`/mnt/main/fauxvinyl`** to `/data`, owned by UID/GID 1000 with mode 0700.
- `deployment-state.json` records shared tunnel mode, the active tunnel ID and previous dedicated tunnel ID; it contains no credential values.

`/data/fauxvinyl.sqlite3` stores card mappings, custom shelf order, playback settings, and any rotated Spotify refresh token. `/data/session.key` signs remembered logins. `/data/artwork/` stores uploaded covers referenced by the database. Back up these files and the artwork directory together, or snapshot the dataset while the app is stopped. Treat the backup as private. A CSV export preserves card IDs and links but is not a full restore of credentials or sessions. Keep the same dataset when upgrading or reinstalling the app.

The app requires the shelf password, uses secure HttpOnly cookies, checks CSRF on every POST, and consumes signed playback requests once. GET requests do not themselves call Spotify; opening a signed-in NFC URL renders the shelf, whose JavaScript obtains a one-time action and submits playback in the background. Sign-in failures are rate limited. Spotify credentials and the tunnel token are runtime configuration and are not included in the image. The Cloudflare API token stays on the deployment computer and is not sent to TrueNAS.

## Local development

From `server/`, build and run the Go preview (Go 1.27.3+ and a C compiler for SQLite); the project root also forwards `make dev`, `make build` and `make test`:

```sh
make dev
```

Open **http://127.0.0.1:18787**. Dev mode requires a loopback address, signs you in automatically, uses a separate `.dev-data/` database, and simulates Spotify devices/playback. It does not load `.env` or connect to TrueNAS. Local edits persist without changing the live collection. HTML templates and static assets reload automatically; rebuild and restart after changing Go code. Stop with Ctrl+C. The Python `dev.py` and Flask sources are retained as legacy source, not the production runtime.

## Local verification

```sh
go test -race ./...
go vet ./...
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-deploy.txt pytest
.venv/bin/python -m pytest -q tests
```

Go tests cover custom-order persistence/migration/stale-tab protection, the inline playback API, authentication, migration of existing Flask sessions, CSRF and Origin checks, persisted edits and sorting, CSV export, image validation/resizing/reset/access, concurrent one-time playback, and Spotify token rotation/retry/device sequencing. Spotify runs against a local test server. The Python suite retains legacy behavior checks and verifies the shared-tunnel deployment and private source-archive allowlist.

For DOM interaction tests, run a local Go preview, then:

```sh
npm install --prefix /tmp/fauxvinyl-ui-tests --no-audit --no-fund jsdom
NODE_PATH=/tmp/fauxvinyl-ui-tests/node_modules node --test tests/shelf.test.cjs
```

Set `SHELF_TEST_URL` to use another local preview port. These checks read the real shelf HTML and simulate network responses to verify artwork reuse (including the enlarged viewer), image failure/retry handling, playback, duplicate submission prevention, browsing while pending, retries, custom-order dragging/keyboard controls, save/cancel, and stale-tab errors. They never start real music or change saved records.

For a real layout regression check, set `SHELF_TEST_BROWSER` to a Chrome or `chrome-headless-shell` executable and run `NODE_PATH=/tmp/fauxvinyl-ui-tests/node_modules node --test tests/shelf-layout.test.cjs`. It measures sleeve, title, controls and shelf positions while selecting albums with multiple, single and no disc choices at desktop, tablet and phone widths. Artwork uses local placeholders and playback stays simulated.

## Go migration and rollback

The Go server preserves the SQLite tables used by Python and adds a `shelf_order` table for custom positions. It uses the same session key, card IDs, settings, refresh tokens, and uploaded-artwork directory. It accepts existing Flask sign-in cookies and upgrades them to HMAC-SHA256 cookies. A rollback to Python may require signing in again. New Go uploads use JPEG/PNG; rolling back the legacy Python runtime would require allowing those two extensions in its artwork route.

Before the first Go update, the dataset was stopped and snapshotted as `main/fauxvinyl@before-go-20261111`. Private rollback Compose configuration is in the deployment workspace's `go-migration-backup-20261111/`; do not copy or share it. The Go build uses `go-source-bundle.tar.gz` and a separate `fauxvinyl-go` image tag, preserving the original Python source archive and image. Restore the saved Python Compose configuration for a runtime rollback. Only roll back the dataset snapshot if needed, because doing so discards subsequent record/settings edits and uploads. Retain the snapshot until the migration is accepted.

The shelf-feature update also retains `main/fauxvinyl@before-shelf-20261111` and a private `shelf-update-backup-20261111/compose-rollback.json` that pins the previous Go image without rebuilding it.

## Deploy or update

Deployment helpers use file paths for secrets and do not print their values. Never commit `.env`, `tunnel-token`, or `truenas-compose.yaml`; the latter contains runtime secrets. Keep these private when copying project files.

If the ISP changes the home public IPv4 address or IPv6 prefix, access fails closed until **FauxVinyl - home network only** is edited in Cloudflare. Update the allowed sources inside that rule while retaining the hostname condition, `not ip.src in {...}`, Block action, and Active status. IPv6 devices use different addresses, so retain the verified local subnet rather than one device's temporary IPv6 address. The app updater preserves this independently configured edge rule. Private `network-access-backup-*` directories record the previous rule list and applied configuration and must stay out of source copies.

```sh
.venv/bin/pip install -r requirements-deploy.txt
.venv/bin/python configure.py --arduino-env ../env.h --password-file /path/to/shelf-password
.venv/bin/python cloudflare_setup.py --token-file /path/to/cloudflare-api-token
.venv/bin/python deploy_truenas.py --host 100.111.217.103 --username admin --password-file /path/to/truenas-password
.venv/bin/python cloudflare_setup.py --token-file /path/to/cloudflare-api-token --publish
```

`configure.py` creates `.env` only if it is absent and reuses the current Arduino Spotify credentials. The current deployment state uses shared tunnel mode: future updates build only the web app, keep the NAS-loopback port and do not create another connector. `cloudflare_setup.py` preserves all other ingress rules in shared mode and refuses an unexpected conflicting FauxVinyl route. For an installed app, retain the existing `.env`, `tunnel-token`, and `deployment-state.json`; edit source and run `deploy_truenas.py` with `--update`. The updater preserves the dataset. It uploads an allowlisted source-and-artwork archive through the TrueNAS API into `/mnt/main/fauxvinyl/build/`, then builds the image from that directory using a short inline Dockerfile. SSH or a source-code web host is unnecessary. TrueNAS retains the source archive and custom app configuration, allowing it to rebuild or restart the app independently of this computer. Deployment secrets are excluded from the source archive.

The source copy in the original project's `server/` directory excludes deployment secrets. Private deployment files for this installation remain in the separate Codex deployment workspace. TrueNAS also retains its runtime Compose configuration. Keep those private files available for subsequent deployment-helper updates; do not assume a fresh source checkout contains them. Private `shared-tunnel-backup-*`, `go-migration-backup-*`, and `shelf-update-backup-*` directories contain migration rollback configuration and must not be shared or copied into source packages. Switching Spotify developer apps also requires replacing the client ID, client secret, and refresh token together and clearing any old `spotify_refresh_token` entry from the private database so a previously rotated token cannot override the new one.

The deployment helper deliberately targets the `main` pool and the `fauxvinyl` app name. Inspect these values before using it on another NAS. It will not overwrite an unrelated `vinyl.bray.dev` DNS record or adopt an unrecorded tunnel. Cloudflare API permissions: Account / Cloudflare Tunnel / Edit for the correct account; Zone / DNS / Edit and Zone / Zone / Read limited to `bray.dev`.

For a conventional Docker host instead of TrueNAS, `compose.yaml` builds the same app from source and publishes it on host loopback port 8787. Create `data/` owned by UID 1000 first, and use an existing host-network Cloudflare connector with the same ingress and public URL. This Compose file does not start a connector.

### Disc artwork

The shelf keeps loaded and in-flight cover images, disc images and disc-choice thumbnails for the lifetime of the page. Revisiting an album or switching back to a disc variant reuses the existing image elements without assigning their URLs again. The enlarged viewer caches its own images. Back covers and discs load as albums are visited; failed cover or disc loads can retry on a later visit. This uses some browser memory to avoid repeated image setup while browsing. Hashed artwork URLs retain the existing one-year HTTP cache policy between page visits; replacement artwork uses a new URL.

The shelf includes the 84 disc images for 42 albums, with transparent backgrounds and spindle holes. Albums with several approved variants show small artwork buttons beside the title. The sleeve layout and choice-row space stay consistent when selecting albums without a disc or variants; long choice rows scroll horizontally. Choices are remembered per album in the current browser, along with the preferred vinyl/CD format for albums without a saved choice. Changing disc artwork changes the visual only.

For **WHEN WE ALL FALL ASLEEP, WHERE DO WE GO?**, CD 2 and Vinyl 2 are hidden glow-in-the-dark editions. Select the album and press **CD 1** or **Vinyl** five times consecutively to reveal that format, darken the listening room and add a soft green glow to the disc and playing shortcut. Each format has its own sequence; changing format or another action breaks an unfinished sequence. Once unlocked, browsing other albums and pausing or resuming preserve glow mode; playing another record or changing the CD/Vinyl choice restores the normal theme. Returning to the album while glow mode is active still shows the revealed edition. Reloading requires unlocking again. The reveal does not change playback or save a hidden edition as a preference. Reduced-motion preferences keep the glow steady.

The glow vinyl uses the black Side A label and ivory phosphorescent pressing photographed by [RareVinyl](https://uk.rarevinyl.com/products/billie-eilish-when-we-all-fall-asleep-where-do-we-go-glow-in-the-dark-vinyl-us-vinyl-lp-album-record-b0031105-01-840658), consistent with the [documented glow release](https://musicbrainz.org/release/9a217c4f-557a-4e90-b7bf-989f166862b6). Built-in imagegen prepared the transparent cutout; CSS adds the green light effect. The original photographs, extraction prompt and processing details are recorded in `disc-artwork-sources.json` and `found-artwork/glow-vinyl/`.

`disc-artwork.json` maps album URIs to the approved assets under `static/discs/`. `disc-artwork-sources.json` records their source releases, approvals, download hashes, preparation methods and exact reconstruction prompts. The second batch adds 44 approved variants: 24 original-image cutouts, 19 AI-assisted reference reconstructions and one manual reconstruction retaining its photographed label. Reconstructed small print and material details may differ from the physical release. Image preparation happens offline; the Go app serves cached WebP files without decoding or processing them. Temporary research and the approval page are excluded from Docker builds and deployment archives.

Outside Test mode, the production animation follows Spotify's playback state, checked every 20 seconds while the page is visible; paused or unrelated playback stops the disc. Failed state checks stop the animation and back off to one minute. Test mode simulates playback and rotation entirely in the browser. Reduced-motion preferences disable rotation.

The collection expansion adds The Great Divide, Stick Season, original 2014 1989, folklore, thank u, next, ANTI, The Slow Rush, How to: Friend, Love, Freefall (including Fever Pitch), and BEYONCÉ. These and the 2026 Harry Styles/Olivia Rodrigo albums each have front/back sleeve art and a choice of vinyl or CD. The 22 new disc options include 18 original-image cutouts and four reconstructed groove surfaces with the original printed label pixels retained (1989, folklore, thank u, next and BEYONCÉ). Artwork is normalized offline with PhotoCraft to 648px transparent WebP, with concentric rims and spindle holes. Sources, exact reconstruction prompts, and validation are retained in `found-artwork/collection-expansion/integrated.json` and `prompts.json`; original album dates remain in `release-dates.json`.
Responsive artwork is generated ahead of deployment with `.venv-preview/bin/python tools/optimize_artwork.py` after adding or replacing bundled artwork. The shelf uses covers up to 320px; sleeve, enlarged artwork, disc choices and the now-playing icon use `srcset`/`sizes` so the browser can select the appropriate resolution. Originals stay available for the enlarged view. Uploaded sleeves get their derivatives once when saved or on upgrade. Image requests serve files directly and do not resize images in memory.

The shelf's Play button follows Spotify playback state and becomes Pause for the playing record, then Resume when paused. Resume continues the current queue and track position. NFC scans continue to start the scanned record as before.

The project now lives at the repository root above `server/`. Local launch builds `.local/bin/fauxvinyl`; credentials, deployment configuration, `.dev-data/` and migration snapshots stay ignored. The complete local artwork research is preserved here, with source-photo downloads and intermediate images ignored while final app/approval assets and provenance stay versioned.
