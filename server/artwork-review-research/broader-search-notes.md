# FauxVinyl broader artwork search — seven-album handoff

Research date: 2026-11-11. Final assigned scope: `glory-sound-prep`, `the-story-of-us-quinn`, `a-letter-to-my-younger-self-quinn`, `the-off-season`, `flume`, `swimming`, and `blonde`, both vinyl and CD. No children were started. No app, catalogue, inventory, curation, or build files were changed.

## Result

**21 verified, downloaded candidates cover 12 of the 14 assigned missing album-format pairs.** Nine pairs have at least one complete-disc image; the other three have useful vinyl labels, packaging, or a nearly complete record photo. Both Quinn CD formats remain unverified. The JSON contains at most three candidates per pair and includes no out-of-scope albums.

| Catalogue album ID | Vinyl result | CD result |
|---|---|---|
| `glory-sound-prep` | 2 complete blue-record photos | 1 complete printed face in clear tray |
| `the-story-of-us-quinn` | 2 complete black-record photos; standard-edition fallback | No verified physical CD artwork |
| `a-letter-to-my-younger-self-quinn` | 2 green-label photos; outer record cropped | No verified physical CD artwork |
| `the-off-season` | 1 near-complete blue-record photo + 1 label; slight outer-edge crop | 1 clean full face scan |
| `flume` | 1 deluxe 2LP product photo + 2 label photos | 2 clean full audio-CD face scans from deluxe set |
| `swimming` | 1 complete blue-record photo + 1 standard black-2LP product photo | 1 clean full blue-face scan |
| `blonde` | Official artist-store image of 2 complete separated records | 1 clean full stock face + 1 physical packaging photograph |

The requested deliverable is [broader-search-candidates.json](broader-search-candidates.json). Original downloads, source metadata, download logs and inspection sheets are under [broader-search-downloads](broader-search-downloads/). Start visual review with [contact-selected.jpg](broader-search-downloads/contact-selected.jpg); each tile is numbered in JSON order.

## Scope calculation and method

I resolved the top-level `static/disc-review/catalogue.json` `approved` IDs back to candidate `kind`, rather than treating any candidate as approved. At the start of this run, 8 albums had both approved formats and 35 were incomplete: 22 lacked one approved format and 13 lacked both, totaling 48 missing pairs. All seven assigned albums were in the no-result group and therefore needed both formats. The follow-up assignment superseded the original 35-album search scope; no further search time was spent outside these seven.

For each assigned album I ran text search, image search, and primary product/gallery checks. Discovery covered artist/label stores, public retail and used-item galleries, Bandcamp/Merchtable where relevant, and Discogs. Search-result image summaries were discovery aids only: the retained files were actually downloaded and visually inspected. Every retained URL returned image bytes, decoded successfully with Pillow, and has a matching `local_file`. The source URLs and downloaded images remain unchanged. Contact sheets are inspection derivatives only; no candidate was cropped, masked, recolored, cleaned, composited, or generated.

**Useful access finding:** public Discogs HTML galleries often returned 403, but unauthenticated `https://api.discogs.com/releases/{id}` and master/version endpoints worked and returned real downloadable `images[].uri` values. Exact artist, album, format, labels and catalogue numbers were checked in the API response before selecting an image. Responses are saved in `broader-search-downloads/pages/`. The API's editorial `status: Accepted` is not a release-authenticity flag. `Official` in the handoff describes the documented label/artist edition; it does not authenticate an individual resale copy or prove image licensing.

## Findings and citations

### Jon Bellion — Glory Sound Prep

The strongest vinyl results are two physical photographs of a complete blue LP, sides A and B, from Capitol release 13113965. They retain textured background, perspective and reflections. The release metadata identifies blue vinyl and Capitol; the images show the correct title, JB emblem, and tracklists. [Discogs release API](https://api.discogs.com/releases/13113965).

Release 33035751 supplies a real CD-face photograph: blue with yellow lettering and the JB emblem, held in a clear jewel-case tray. This is a 2018 CD, not a new edition inferred from the high database ID. The tray and center retainer remain visible. [Discogs CD API](https://api.discogs.com/releases/33035751). The label's own store independently identifies the correct physical CD, but its product image exposes only part of a generic reflective disc; that mockup is weaker and was not added to the final candidate list. [uDiscover product page](https://shop.udiscovermusic.com/products/jon-bellion-glory-sound-prep-cd).

Rejected leads: the four-image eBay CD gallery contains front/back packaging and seller graphics, not a printed CD face; a separately advertised “disc-only” listing also uses the album cover as its image. These were inspected rather than accepted from their titles. [First seller listing](https://www.ebay.com/itm/266263044275), [disc-only listing](https://www.ebay.com/itm/277837866375).

### Quinn XCII — The Story of Us

Record Selector supplies two complete black-vinyl photographs with yellow side-A and red side-B labels. The artist/album name and tracklists are visible. Its page describes these as stock images for the listed LP, so they should not be presented as fresh photographs of the seller's current copy. [Primary retailer gallery](https://recordselectorlv.com/products/the-story-of-us).

**Edition limit:** the photos show the standard 2017 11-track LP. FauxVinyl's catalogue names the 15-track Deluxe digital edition. This is a correct-album physical-edition fallback, not verified Deluxe vinyl. The complete Discogs master version list returned two versions: the standard vinyl and the Deluxe files; it did not document a CD. [Exact-album master versions API](https://api.discogs.com/masters/3242554/versions?per_page=100).

Targeted text/image searches for physical CD, compact disc, disc face, and retailer/collector listings did not yield a verified CD gallery. Sony's album announcement establishes artist and album identity but does not establish a CD pressing. **CD remains unresolved, not declared nonexistent.** [Sony Music release announcement](https://www.sonymusic.ca/press_release/quinn-xcii-announces-debut-album-the-story-of-us-available-september-15).

### Quinn XCII — A Letter to My Younger Self

Discogs release 15988301 is the correct Columbia 2020 black LP, catalogue 19439777331. Its API gallery has useful green side-A/B label photos with legible album and track information, but neither includes the outer record edge. Both are classified `label`, not full-disc artwork. [Release API with format and image URLs](https://api.discogs.com/releases/15988301).

GOOD TASTE documents the corresponding official black LP/UPC 194397773316. The checked Newbury, Walmart and Discrepancy galleries provided covers or sleeve photographs rather than a clean complete record. [GOOD TASTE physical-LP listing](https://goodtasterecords.com/collections/all-products/products/quinn-xcii-a-letter-to-my-younger-self-vinyl-lp), [Discrepancy used-LP gallery](https://www.discrepancy-records.com.au/quinn-xcii-a-letter-to-my-younger-self-vinyl-lp).

No verified CD-face or physical-CD product source emerged from the targeted CD search. Generic digital-store “CD cover” printables were not treated as evidence that a manufactured CD exists. Sony's first-party announcement confirms the album, not that format. **CD remains unresolved.** [Sony Music album announcement](https://www.sonymusic.ca/press_release/quinn-xcii-unveils-third-album-a-letter-to-my-younger-self-today).

### J. Cole — The Off-Season

A clean complete CD-face scan is available for US CD release 19435372, B0034080-02: flaming hoop on the left and black face with Dreamville/Roc Nation branding on the right. The corresponding physical format is also sold by the label. [Discogs exact-CD API](https://api.discogs.com/releases/19435372), [Interscope CD product page](https://interscope.com/products/the-off-season-cd).

The blue-vinyl release 22026808 supplies a nearly complete physical record photograph and a detailed side-A label photograph. **The outer right edge of the wide record image is slightly cropped**, so it is conservatively classified `partial`. Similar-looking central artwork on vinyl is not the CD. [Blue-vinyl release API](https://api.discogs.com/releases/22026808). The additional black-LP gallery checked during this pass contains close label crops rather than a better full outer edge. [Black-LP API](https://api.discogs.com/releases/20023891).

### Flume — Flume / Deluxe Edition

The best CD results are the actual **two audio discs** from the four-disc FCL85 deluxe set: “The Debut Album” and “The Deluxe,” black faces with pink FLUME text on white backgrounds. Both are complete, clean face images. The gallery also contains “The Infinity Prism Tour” and “The Producer Disc”; those are DVD-Video and DVD-Data and were explicitly excluded from CD candidates. [Exact deluxe-set API and complete media specification](https://api.discogs.com/releases/5722780).

The matching deluxe vinyl is FCL85LP, a 2LP mixtape/remixes companion to the debut. Its labels are readable but the close photographs omit the record edge. Turntable Lab also supplies a good product photograph with the jacket and overlapping records; it is classified `packaging`, not a scan. This LP does not reproduce every track of the expanded digital album; the retailer describes the original album as a download. [Deluxe-vinyl API](https://api.discogs.com/releases/5598583), [Turntable Lab deluxe 2LP gallery](https://www.turntablelab.com/products/flume-flume-deluxe-edition-vinyl-2lp).

A pink concentric-ring CD photograph discovered at Retro Unit is the standard debut CD and was not retained after the exact deluxe-set audio discs were found. [Primary used-CD product gallery](https://retrounit.com.au/products/flume-flume-cd-2012).

### Mac Miller — Swimming

Lampala's physical CD product gallery contains a complete 600×596 scan of the blue printed CD face. The hub repeats “SWIMMING BY MAC MILLER”; Warner text is visible along the rim. This is distinct from the circular-looking tracklist on the back cover, which appeared frequently in image searches and was not mistaken for a disc. [Retail CD gallery](https://lampala.com.ua/mac-miller-swimming).

The transparent-blue Urban Outfitters reissue has a complete record photograph, but the archival protector's arrows/text and reflections show through the disc. A standard black-2LP studio product photograph provides a cleaner packaging alternative with overlapping records. Both are correct physical editions of this album. [Blue-vinyl release API](https://api.discogs.com/releases/15158127), [Turntable Lab standard 2LP gallery](https://www.turntablelab.com/products/mac-miller-swimming-vinyl-2lp). Mac Miller's artist store independently identifies standard Swimming vinyl, although the current main image is mainly the cover. [Official artist-store product](https://shop.macmillerswebsite.com/products/swimming-vinyl).

### Frank Ocean — Blonde

The strongest vinyl result comes directly from Blonded: a 2500×1932 studio product image of two separated, complete black records with pale-yellow labels, sides 1-B and 2-C, on white. This is the official reissue presentation. It is not labeled as a scan or as the 2016 black-cover pressing. [Official artist-store gallery](https://blonded.co/products/blonde).

For CD, a primary seller's Black Friday listing contains a clean 600×600 **stock image** of the complete grayscale printed disc face. I cross-checked its design against the physical CD photograph in the correct 2016-11-25 release 9496113, Boys Don't Cry / XL 862160000302; that opened-package photograph is retained as the second candidate. Thus a seller's “sealed” claim is not being used to claim the stock face is a photograph of that individual copy. [Black Friday seller gallery](https://www.ebay.com/itm/363437984401), [exact physical-CD release API](https://api.discogs.com/releases/9496113).

Cheap custom jewel-case CDs also appeared in search, but they were unnecessary once official-edition artwork was verified and are not included. The handoff does not repeat sellers' incorrect generic claims that Blonde never had an official CD.

## Remaining gaps and review priorities

1. **Both Quinn CDs:** no verified candidate. Keep unresolved pending a source that proves the physical album/format and supplies a real image.
2. **Quinn Story LP edition:** standard LP only; approve as an explicit same-album fallback if acceptable for the Deluxe catalogue entry.
3. **Quinn Letter LP:** useful correct labels, but no full outer record found.
4. **Off-Season LP:** very good near-complete blue-record image, with a real small right-edge crop; not an ideal full scan.
5. **Flume LP:** accurate deluxe labels and retail product photo, with the mixtape/remixes edition distinction retained.
6. CD/record product art can be clean without being a physical scan. JSON notes identify stock artwork, studio product photographs, tray photographs and physical scans individually; `quality: full` means the complete disc face/record is visible, not that the file is a scan.

Network limitations are recorded in `fetch-results*.json`: many Shopify `.js` product endpoints returned 429; a few retired product pages returned 404 or redirect loops. Public CDN image requests and the Discogs API worked. No login, paywall, token, or account was used. The earlier MusicBrainz raw image cache was not re-curated or integrated.
