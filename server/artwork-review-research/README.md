# Temporary disc artwork review

Open http://127.0.0.1:18787/static/disc-review/ using the existing local FauxVinyl preview.

All 43 albums are represented together. There are 265 curated choices: nine albums have complete vinyl photographs and another 21 have CD fallbacks. Thirteen albums have no usable full-disc scan in the searched sources. Nine playlist entries are listed separately.

Approve or deny individual options, optionally add an album note, then export `fauxvinyl-disc-art-decisions.json`. Decisions are saved in this browser only. Approving does not apply images. Import restores exported decisions. Local preview and inline conversation have separate browser storage; use one for reviewing and export its decisions.

Research follows MusicBrainz release groups through physical releases with artwork. 106 vinyl galleries and 338 CD galleries were attempted, including CD-R/HDCD variants and images typed Other or untyped. Three gallery requests and six nonessential thumbnail downloads remain unavailable; details are in research-report.json. Missing results do not establish that a physical edition or photograph does not exist elsewhere.

Source thumbnails are unedited. Curation excludes label-only vinyl closeups, reverse/data surfaces, packaging and inserts. All included bytes match the recorded download SHA-256. White backgrounds, hands and perspective remain visible for approval. Processing and shelf integration must wait for decisions.

Files:
- inventory.json: shelf inventory, matching release groups, releases, raw candidates and source errors.
- downloads.json: exact fetched URL, local filename, dimensions and SHA-256.
- curation.json: visual screening decisions and reasons.
- ../static/disc-review/catalogue.json: complete curated candidate manifest with source links.
- ../static/disc-review/index.html, review.css, review.js: disposable local approval interface.

No playback, artwork database, original-project source, TrueNAS deployment or production files were changed for this review.
