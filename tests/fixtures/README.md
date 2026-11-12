# Test collection

`collection/` is a small, synthetic runtime collection for Go and UI regression tests. Artwork is generated from solid colors and geometric shapes. Fictional Spotify IDs keep the general fixtures independent of personal playlists and shelves. The glow fixture retains the public album and edition mappings needed to exercise the Easter egg; its artwork is synthetic too.

Run a local preview against this fixture with `COLLECTION_DIR=../tests/fixtures/collection DATA_DIR=/tmp/fauxvinyl-fixture-data make dev` from the repository root. The server process runs from `server/`, so the collection path is relative to that directory.
