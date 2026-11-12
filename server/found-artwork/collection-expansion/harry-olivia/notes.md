# Harry Styles / Olivia Rodrigo disc assets

Four originals prepared using PhotoCraft: blue Harry vinyl, silver Harry CD, white Hope Like Snow Olivia vinyl, and floral Olivia CD. No generated image was used in any final.

All four were individually inspected. Validation: 648×648 RGBA WebP; 640px circular rim at bbox [4,4,644,644]; transparent exterior and centered hole (16px vinyl / 80px CD); opaque annulus. Source spindle geometry was measured, normalized, and mapped to the center before the circular mask. See prepare.py, per-image commands/logs, validation.json, and contact-qa.jpg.

Harry vinyl source: https://coverartarchive.org/release/40c1cead-0993-4d0e-b8c4-30c92c224bc5/44668922556-1200.jpg

Harry CD: Discogs release 36690721, image index 2. Full native scan obtained using browser User-Agent and Discogs Referer; signed URL retained in downloaded API JSON. Complete original scan supersedes an attempted missing-sector reconstruction from official packshot. That image_gen attempt was rejected (request f84d4b16-0ea3-416a-8095-b31cc9f0f308); no output from it was consumed. Its prompt is retained solely as process history.

Olivia vinyl source: https://cdn.shopify.com/s/files/1/0622/4576/5282/files/lFB397621LABEL.jpg?v=1794436580

Olivia CD source: https://cdn.shopify.com/s/files/1/0496/9781/6733/files/YSPSFGSILStoreExclusiveCD.png?v=1777491964

Olivia CD is a genuine official product mockup, with a lower native resolution than the other three. Its floral artwork and pink lettering are retained exactly rather than invented. A matching dark matte makes partial source alpha near the perimeter opaque before the final circular cutout.
