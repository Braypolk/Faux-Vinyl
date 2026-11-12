# Broader external disc-artwork search — singles A

Research date: 2026-11-11. Scope: only the 11 missing formats explicitly assigned, using `static/disc-review/catalogue.json` for artist, album and Spotify URI and its top-level `approved` collection for existing approvals. No MusicBrainz gallery/cache rescan was performed. No app, approval-site, inventory, curation or manifest files were changed.

## Result

21 downloaded, visually inspected candidates across 11 album/format pairs. Seven pairs have complete-disc photographs: Jon Bellion, both Van Halen albums, Post Malone’s *Hollywood’s Bleeding*, Seal (1994), P!nk, and J. Cole. The ten `full` entries include different sides of the same records; these are not ten different albums.

The other four pairs retain explicitly classified fallbacks. No clean standalone CD photograph was verified for *beerbongs & bentleys*. No complete unobscured standalone LP was verified for *Tuesday Night Music Club* or *The E.N.D.*; the latter’s official photograph exposes most or all of a foreground disc at an oblique angle. No official vinyl edition of *The Essential Michael Jackson* was verified; the photographed white vinyl is an unofficial release.

`quality` describes the supplied image, not a promise of automatic cutout suitability. `full` means the complete record is visible, even when its sleeve is in the background; reflections/perspective may remain. `partial` means the rim/sector is cropped or obscured. `packaging` retains visible disc(s) within a physical product shot/packshot. `mockup` is a stock sleeve-and-disc composition. `status` classifies the release, not whether the photograph is hosted by the artist; the Depop item's authenticity remains `Unknown`.

## Method and verification

Used web search and image search for official artist/label shops, physical-product retailers, collector/release photographs and release-image leads. Successful Shopify product JSON supplied exact CDN image URLs and release metadata; candidate images were downloaded unchanged and visually inspected, including complete rim, readable album/label, disc format, and whether the apparent artwork was just a cover. Direct page/metadata and source evidence are linked below. Raw product JSON, fetched page HTML, download indexes and inspection contact sheets remain in `broader-search-singles-a-downloads/` for audit. Contact sheets are viewing derivatives only; original downloaded candidate files are unchanged. No image generation, disc reconstruction, background removal or retouching was performed.

The output JSON has exact image URLs, source pages, per-image caveats, release status and absolute local file paths. All 21 selected local images passed Pillow decoding/verification. Each assigned pair has 1–3 choices, below the four-option maximum. Cover-only squares were excluded, as were failed/HTML image responses and unrelated search matches.

## Album findings and citations

### Post Malone — beerbongs & bentleys (cd)

Catalogue ID: `beerbongs-and-bentleys` · URI: `spotify:album:6trNtQUgC8cgbWcqoMYkOR`.

- **packaging / Official** — [Post Malone — beerbongs & bentleys, official CD jewel-case packshot](https://www.republicrecords.com/products/post-malone-beerbongs-bentleys-cd). Official Republic product page verifies the CD. Yellow disc is visible through the jewel case; transparent case artwork and the black tracklist sticker overlap the disc. This is a packaged CD packshot, not a clean standalone disc. Do not assume all barbed-wire graphics are printed on the disc. [Direct image](https://cdn.shopify.com/s/files/1/0280/5537/1810/products/bb_disk_cover_final_label_large_41d35c1c-2580-4b38-b145-6c4ef276a18f_1_copy.png?v=1750364611).
- **packaging / Unknown** — [Post Malone — beerbongs & bentleys CD, resale photograph](https://www.depop.com/products/staycute-post-malone-beerbongs-and-bentleys/). Actual jewel-case photograph on a wooden surface; yellow CD and clear hub visible. Case typography and barbed-wire graphics overlap the disc. No standalone disc photograph found; seller-item authenticity is unverified. [Direct image](https://media-photos.depop.com/b1/1277519/1807307595_290fdd5dc88f4be28808dfe854241106/P0.jpg).

Searches for disc-only, rear/inside jewel-case, and resale CD photographs continued to return jewel cases or cover art. The official packshot is the best verified format source. The barbed-wire and typography may be printed on transparent packaging rather than the disc; these images must not be interpreted as a clean circular disc texture.

### Jon Bellion — The Human Condition (vinyl)

Catalogue ID: `the-human-condition` · URI: `spotify:album:2jJReDZqTuAxr4R0ItimZc`.

- **full / Official** — [Jon Bellion — The Human Condition, clear vinyl portrait-label photograph](https://ca.rarevinyl.com/products/jon-bellion-the-human-condition-clear-vinyl-us-2-lp-vinyl-record-double-b002486501jk02-880401). Complete near-front-on clear record with illustrated portrait label on a white background. Retailer identifies 2016 US Capitol/Visionary clear 2LP, B002486501JK02, barcode 602547858047. Tight but complete outer rim; genuine item photograph rather than a generic clear-disc mockup. [Direct image](https://cdn.shopify.com/s/files/1/0566/5105/5295/files/jon-bellion-the-human-condition-clear-vinyl-us-2-lp-vinyl-record-double-oo2lth880401-880401b.jpg?v=1764695582).

The clear-vinyl retailer photograph is substantially stronger than the Collide Records sleeve mockup, whose mostly blank generic labels do not show the actual portrait artwork. Shuga Records and End of an Ear galleries returned cover/back/sticker images rather than exposed records. The 2016 clear pressing is verified by the product description; the original image shows Capitol/Visionary artwork.

### Van Halen — 1984 (Remastered) (vinyl)

Catalogue ID: `1984` · URI: `spotify:album:3REUXdj5OPKhuDTrTtCBU0`.

- **full / Official** — [Van Halen — 1984, US Warner Bros vinyl side 1](https://yourvinylshop.com/products/van-halen-1984-1984-warner-bros-vg-vg-4). Actual complete black record with white Warner Bros label, photographed on its printed inner sleeve. Product verifies 1984 Warner Bros pressing. Slight perspective, reflections, and background remain; outer rim is visible. [Direct image](https://cdn.shopify.com/s/files/1/0369/2878/2476/files/vintage-vinyl-records-0827.jpg?v=1696953223).
- **full / Official** — [Van Halen — 1984, US Warner Bros vinyl side 2](https://yourvinylshop.com/products/van-halen-1984-1984-warner-bros-vg-vg-4). Opposite side of the same complete physical record; white Warner Bros label. Printed inner sleeve behind the disc, with light reflections and slight perspective. [Direct image](https://cdn.shopify.com/s/files/1/0369/2878/2476/files/vintage-vinyl-records-0828.jpg?v=1696953224).
- **partial / Official** — [Van Halen — 1984, UK white-label vinyl photograph on stand](https://atlasrecords.co.uk/products/van-halen-1984-lp-vinyl-566281). Clean near-front-on actual record photograph with white Warner Bros label, UK K/92-3985-1. A wooden display stand obscures a small section of the bottom rim; Atlas watermark is on the background. Image downloaded successfully, but the product JSON endpoint returned 404; page/release identification was cross-checked through the indexed source. [Direct image](https://atlasrecords.co.uk/cdn/shop/files/Van-Halen-1984-4_1bf7f540-9ce8-4132-9b07-9d4642418e03.jpg?v=1759511013).

Both high-resolution Your Vinyl Shop sides show the complete record. Atlas is an optional cleaner-background alternate, but its small wooden stand hides the bottom rim; therefore it is explicitly partial. The exact Atlas image downloaded successfully while the product JSON endpoint returned 404, so its release identification relies on the indexed source and visible label rather than a successful JSON fetch. Official Van Halen Store stock artwork showed a sleeve/partial record rather than a better full disc.

### Van Halen — Van Halen (Remastered) (vinyl)

Catalogue ID: `van-halen-album` · URI: `spotify:album:7DdEbYFPKTZ8KB4z6L4UnQ`.

- **full / Official** — [Van Halen — Van Halen (1978), Warner Bros palm-tree label side 1](https://yourvinylshop.com/products/van-halen-van-halen-1978-warner-bros-records-vg-ex). Complete black LP with Warner Bros palm-tree center label. Actual retailer photograph on black inner sleeve; some glare and perspective. Source identifies a 1978 US Warner Bros pressing, with promo punch on the cover. [Direct image](https://cdn.shopify.com/s/files/1/0369/2878/2476/files/vintage-vinyl-records-0490_cd5371ae-9952-4bc3-a940-2eeb7d3197ce.jpg?v=1738700718).
- **full / Official** — [Van Halen — Van Halen (1978), Warner Bros palm-tree label side 2](https://yourvinylshop.com/products/van-halen-van-halen-1978-warner-bros-records-vg-ex). Opposite side of the same complete black LP. Actual photograph with the correct album title and Warner Bros palm-tree label; background inner sleeve, reflections and slight perspective remain. [Direct image](https://cdn.shopify.com/s/files/1/0369/2878/2476/files/vintage-vinyl-records-0491_2a0e8693-555b-4166-9868-352cb4a7c1e0.jpg?v=1738700718).

The Your Vinyl Shop pair is preferable to the Record Pusher label-only crop, auction packaging photograph and Atlas partly sleeve-obscured record. Source identifies the 1978 US Warner Bros pressing; the promo punch belongs to the jacket, not a different album. Both center labels use the authentic palm-tree Warner Bros design.

### Michael Jackson — The Essential Michael Jackson (vinyl)

Catalogue ID: `michael-jackson` · URI: `spotify:album:77dNyQA0z8dV33M4so4eRY`.

- **partial / Unofficial** — [Michael Jackson — The Essential Michael Jackson, unofficial white vinyl photograph](https://curatedshop.com.au/product/lot-050-michael-jackson-the-essential-michael-jackson-white-vinyl-2xlp-compilation/). Actual white-vinyl photograph with black Epic-style center label; readable compilation title, side-B tracks and 5204222001 catalogue number. Paper inner sleeve obscures the upper-left disc sector and photograph is oblique. Curated Shop does not disclose unofficial status, but the matching EPC 5204221 / 5204222001 release is explicitly classified as Unofficial by Discrepancy Records. No official vinyl edition verified. [Direct image](https://curatedshop.com.au/wp-content/uploads/2026/02/IMG_9600.jpg).

The Curated Shop page does not disclose unofficial status. The photographed center label gives 5204222001; [Discrepancy Records explicitly labels the matching EPC 5204221 / 5204222001 release “Unofficial Release UK”](https://www.discrepancy-records.com.au/michael-jackson-the-essential-michael-jackson-viny). This catalogue match is the basis for the Unofficial classification. [Cratehound’s indexed vinyl versions](https://www.cratehound.app/albums/michael-jackson/the-essential-michael-jackson-35097) also identify unofficial Epic (2) variants. A [collector Flickr image](https://www.flickr.com/photos/kiekeboetjen_mj/4389790011/) appeared to show white records with the cover, but all attempted image sizes returned 403 and were not retained as candidates. Popsike yielded cover/back images only. No official vinyl edition was verified in this search; do not silently substitute the unofficial artwork for an official release.

### Post Malone — Hollywood's Bleeding (vinyl)

Catalogue ID: `hollywood-s-bleeding` · URI: `spotify:album:4g1ZRSobMefqF6nelkgibi`.

- **full / Official** — [Post Malone — Hollywood’s Bleeding, green 180g vinyl photograph](https://us.rarevinyl.com/products/post-malone-hollywood-s-bleeding-180gm-green-vinyl-uk-2-lp-vinyl-record-double-b0031154-01-849806). Complete green record on white background, near-front-on, black/red Republic label. Source verifies 2020 UK/EU 17-track 180g green 2LP, B0031154-01, barcode 602508305528. Actual used-item photograph with a complete tightly framed rim. [Direct image](https://cdn.shopify.com/s/files/1/0566/5105/5295/files/post-malone-hollywood-s-bleeding-180gm-green-vinyl-uk-2-lp-vinyl-record-double-4qx2lho849806-849806b.jpg?v=1730916424).
- **packaging / Official** — [Post Malone — Hollywood’s Bleeding, pink vinyl with sleeve](https://www.plaidroomrecords.com/products/post-malone-hollywoods-bleeding-15529080). Actual retailer photograph of pink vinyl beside the sleeve. The sleeve covers the left portion of the record. Product identifies a 2020 Republic edition; useful colored-pressing fallback, not a standalone full-disc image. [Direct image](https://www.plaidroomrecords.com/cdn/shop/products/MBL_3511_8632910d-19de-402f-85fe-7cc139d17b35.jpg?v=1675968727).

The RareVinyl green LP is the strongest complete-disc result, verified as 2020 Republic B0031154-01. Plaid Room provides a real pink-pressing product photograph as a visibly partial alternate. Official Post Malone/Mercury store imagery offered sleeve-and-record mockups with obscured discs and did not improve on the full green photograph.

### Sheryl Crow — Tuesday Night Music Club (Deluxe Edition) (vinyl)

Catalogue ID: `sheryl-crow-tuesday-night-music-club` · URI: `spotify:album:11ZOyF9bKgnusVD1rUapwv`.

- **partial / Official** — [Sheryl Crow — Tuesday Night Music Club, official black vinyl photograph](https://interscope.com/products/tuesday-night-music-club-lp). Official Interscope product photograph of black LP and sleeve. Center label is clearly visible, but the bottom outer rim is cut off by the image boundary; no complete standalone disc in this image. This physical original-album edition does not reproduce all bonus material of the catalogue’s digital Deluxe edition. [Direct image](https://cdn.shopify.com/s/files/1/0272/7605/0568/files/SherylCrow_TuesdayNightMusicClub.jpg?v=1756473845).
- **packaging / Official** — [Sheryl Crow — Tuesday Night Music Club, 2018 blue vinyl photograph](https://www.plaidroomrecords.com/products/sheryl-crow-tuesday-night-music-club-12830606). Actual used-item retailer photograph; blue LP partly hidden by sleeve, with A&M picture label visible. Source verifies 2018 A&M Records / UMe pressing and two discs. Different edition from the later black 1LP; not the full digital Deluxe tracklist. Full disc rim unavailable. [Direct image](https://cdn.shopify.com/s/files/1/1487/4550/files/MBL_4585_62ee0f67-dfc8-45ef-8ae1-419bd9fc2885.jpg?v=1712952050).

The official black-vinyl photograph cuts off the bottom edge, while the 2018 blue 2LP photographs hide a large part of each record behind the jacket. A later RareVinyl listing returned only another sleeve-obscured stock image, not a standalone LP. These physical editions also do not represent every bonus track of the catalogue’s 2009 Deluxe digital edition. The 2018 blue edition and later black edition should remain distinguished.

### Seal — Seal (vinyl)

Catalogue ID: `seal` · URI: `spotify:album:1mSECpFqHRW6leG4idqTE1`.

- **full / Official** — [Seal — Seal (1994), 30th anniversary milky-clear vinyl photograph](https://uk.rarevinyl.com/products/seal-seal-milky-clear-vinyl-30th-anniversary-edition-us-2-lp-vinyl-record-double-081227815493-891695). Complete near-front-on milky-clear record with Seal silhouette center label on white. Source verifies 2024 US 30th-anniversary 2LP, originally released in 1994, barcode/catalogue 081227815493, original album plus B-sides/rarities. Correct second Seal album, not the 1991 debut. [Direct image](https://cdn.shopify.com/s/files/1/0566/5105/5295/files/seal-seal-milky-clear-vinyl-30th-anniversary-edition-us-2-lp-vinyl-record-double-sea2lse891695-891695b.jpg?v=1778083938).
- **mockup / Official** — [Seal — Seal (1994), black-vinyl 30th anniversary packaging mockup](https://spindizzyrecords.com/products/seal-seal-30th-anniversary-deluxe-edition). Retailer stock packaging mockup: black vinyl partly behind the 1994 album cover. Printed center label is partially visible. Deluxe 30th-anniversary edition; lower-priority fallback because sleeve obscures about half the record. [Direct image](https://cdn.shopify.com/s/files/1/0588/3455/0945/files/Seal_-_Seal__Deluxe_Edition_-_2LP_Black_Vinyl_-_2024.jpg?v=1713272787).

The milky-clear record is the correct 1994 sophomore album. The [Rhino 30th-anniversary announcement](https://media.rhino.com/press-release/seal-deluxe-edition) corroborates the 2024 expanded 2LP reissue and milky-white Barnes & Noble variant. The Rhino media JPG returned 403, but the RareVinyl product image downloaded and was inspected. A Vinylbazar image lead returned an HTML challenge rather than a decodable image and is excluded. Spindizzy provides a stock black-disc mockup only.

### P!nk — Funhouse (Expanded Edition) (vinyl)

Catalogue ID: `funhouse` · URI: `spotify:album:1LOJfNDxQhbpssKx7oM7at`.

- **full / Official** — [P!nk — Funhouse, 2018 yellow vinyl picture-label photograph](https://uk.rarevinyl.com/products/pink-funhouse-yellow-vinyl-uk-2-lp-vinyl-record-double-88985497941-826160). Complete bright yellow translucent record with Funhouse picture label on gray background. Actual item photograph; source verifies 2018 UK/EU RCA 2LP, catalogue 88985497941, barcode 889854979416. Original physical album edition rather than all digital Expanded-edition bonus content. Retailer description and track-count text disagree, so no track-count claim is made. [Direct image](https://cdn.shopify.com/s/files/1/0566/5105/5295/files/pink-funhouse-yellow-vinyl-uk-2-lp-vinyl-record-double-p-k2lfu826160-826160b.jpg?v=1712463948).
- **mockup / Official** — [P!nk — Funhouse, official Sony black-vinyl packaging mockup](https://store.sonymusic.fr/products/p-nk-funhouse-2lp). Official Sony Music France 2LP stock mockup. Black record protrudes from the sleeve; the label is hidden. Correct album/format but unsuitable for recovering its printed label artwork. Lower-priority format/packaging fallback only. [Direct image](https://cdn.shopify.com/s/files/1/0917/0357/4862/files/s-l1200_61eeefc6-6c3e-4f74-b5ce-d4dac7d209e9.jpg?v=1753977315).

The yellow 2018 RCA 2LP photograph is a real complete record with a P!nk picture label. Its retailer text says 14 tracks while its enumerated tracklist shows 12; no track-count claim is used. It corresponds to the original physical album rather than all bonus material in the Spotify Expanded edition. The Sony stock black-vinyl alternative is included as an official packaging reference, but its center label is hidden and it cannot supply actual label artwork.

### Black Eyed Peas — THE E.N.D. (THE ENERGY NEVER DIES) (vinyl)

Catalogue ID: `the-end-black-eyed-peas` · URI: `spotify:album:3lng6RAtdksQ2q02Fk5jaB`.

- **packaging / Official** — [Black Eyed Peas — The E.N.D., official emerald 2LP photograph](https://interscope.com/products/black-eyed-peas-the-e-n-d-translucent-emerald-2lp). Official Interscope physical-product photograph: two translucent emerald LPs beside sleeve. Foreground record appears complete and its The E.N.D. label is visible, but it is oblique with another record overlapping near its upper-left edge; upper-left disc is cropped at the image boundary. Strong photo fallback rather than a front-on standalone disc. [Direct image](https://cdn.shopify.com/s/files/1/0272/7605/0568/files/VINYL_BF_BLACK-EYED-PEAS_THE-END_197.jpg?v=1746125649).
- **mockup / Official** — [Black Eyed Peas — The E.N.D., official emerald 2LP mockup](https://interscope.com/products/black-eyed-peas-the-e-n-d-translucent-emerald-2lp). Official Interscope stock packaging mockup of translucent emerald 2LP. Sleeve obscures parts of both records. Correct album and edition, lower-priority than the actual product photograph. [Direct image](https://cdn.shopify.com/s/files/1/0272/7605/0568/files/E.N.D.png?v=1746125649).

The official Interscope photo is much better than generic packaging renders: its foreground emerald disc has a visible The E.N.D. label, but the composition is oblique and includes a second partly cropped record and jacket. It remains classified as packaging. Interscope verifies the album and all four sides of the emerald 2LP edition. A separate JG Music image lead returned 404. Other broad matches included unrelated albums called The End and were rejected. No better front-on, unobscured individual disc was verified.

### J. Cole — 4 Your Eyez Only (vinyl)

Catalogue ID: `4-your-eyes-only` · URI: `spotify:album:3CCnGldVQ90c26aFATC1PW`.

- **full / Official** — [J. Cole — 4 Your Eyez Only, physical black vinyl side A](https://www.yoyomedia.art/products/j-cole-4-your-eyez-only). Complete black LP with readable J. Cole / 4 Your Eyez Only center label. Actual retailer photograph on an inner sleeve with reflections and slight perspective. Source identifies Dreamville and lists B0026313-02A; this is the LP, not a CD. Vinyl packaging differs from the catalogue’s digital cover. [Direct image](https://cdn.shopify.com/s/files/1/0661/6875/0310/products/1675112325487.jpg?v=1691334850).
- **full / Official** — [J. Cole — 4 Your Eyez Only, physical black vinyl side B](https://www.yoyomedia.art/products/j-cole-4-your-eyez-only). Opposite side of the same complete LP; actual retailer photograph with matching album label. Full rim visible on inner sleeve; light reflections and mild perspective remain. [Direct image](https://cdn.shopify.com/s/files/1/0661/6875/0310/products/1675112348075.jpg?v=1691334850).

The YoYo Media photographs show the physical Dreamville LP and readable 4 Your Eyez Only labels on both sides, with all of each rim visible. The product’s metadata lists B0026313-02A and 2016 Dreamville; that year is reported as source metadata, not independently treated as the pressing date. The vinyl jacket art differs from the Spotify cover. RareVinyl offered a useful label-only crop, while Joe’s photographs retained sleeve occlusion; neither improves on the two complete YoYo discs.

## Unsuccessful gaps and handling

- **beerbongs & bentleys / CD:** no verified naked-disc image; retain jewel-case packshots as packaging only.
- **Tuesday Night Music Club / vinyl:** no complete unobscured disc; official photo crops the rim, blue pressing is sleeve-obscured.
- **The E.N.D. / vinyl:** official physical photo is the best available fallback; an individual front-on disc remains a gap.
- **The Essential Michael Jackson / vinyl:** no verified official edition; one real unofficial white-vinyl partial photo retained with explicit status.

The download directory also contains rejected/exploratory files, including cover-only images and failed responses. Only entries in `broader-search-singles-a-candidates.json` are proposed candidates. No assertion is made that an unsuccessful search proves an image or official edition does not exist. Sources were public pages; no authenticated account or outreach was used.
