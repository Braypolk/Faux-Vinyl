# Regression tests

Run these commands from the repository root. All regression suites and fixtures live here:

| Directory | Coverage |
| --- | --- |
| `server/` | Go app, authentication, persistence, catalogue, playback and artwork |
| `ui/` | Shelf interactions, browser layout and responsive image loading |
| `artwork/` | Artwork generation, cached sizes and safe pruning |
| `tools/` | Private credential setup and configuration preservation |

## Go

Install Go 1.27.3+, a C compiler for SQLite, and Python 3 for the runner:

```sh
make test
make test-race
python3 tests/run_go.py test -run TestLogin
```

`make test` runs the Go suite and vet. `tests/run_go.py` creates a temporary Go file overlay so the tests compile in the server package with access to private functions and server-relative asset paths. The files stay in `tests/server/`; the overlay is removed afterward. Use the runner or Make targets; plain `go test ./...` from `server/` does not discover these tests. Additional Go flags can follow `test` or `vet`.

## Python tools

```sh
python3.13 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
make test-tools PYTHON=.venv/bin/python
```

For one suite, run `.venv/bin/python -m pytest -q tests/artwork` or replace `artwork` with `tools`. Fixtures use temporary directories.

## Browser UI

Start a local preview with the synthetic test collection in another terminal. Use a new temporary data directory so tests do not depend on a saved personal shelf:

```sh
COLLECTION_DIR=../tests/fixtures/collection DATA_DIR="$(mktemp -d)" make dev
```

The collection path is relative to the server working directory used by `make dev`. The tests require a loopback URL and keep playback simulated.

```sh
npm install --prefix /tmp/fauxvinyl-ui-tests --no-audit --no-fund jsdom
NODE_PATH=/tmp/fauxvinyl-ui-tests/node_modules make test-ui
```

Set `SHELF_TEST_URL` when using a different loopback port. The layout check is skipped unless `SHELF_TEST_BROWSER` names a Chrome or `chrome-headless-shell` executable:

```sh
NODE_PATH=/tmp/fauxvinyl-ui-tests/node_modules \
SHELF_TEST_BROWSER=/path/to/chrome-headless-shell make test-ui
```

`ui/responsive-browser.cjs` additionally checks real image loading in Playwright/WebKit at desktop, tablet and phone sizes. With Playwright and its WebKit runtime installed, run:

```sh
NODE_PATH=/path/to/playwright/node_modules node tests/ui/responsive-browser.cjs
```
