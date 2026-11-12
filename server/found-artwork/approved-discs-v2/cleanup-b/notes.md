# cleanup-b artwork preparation

Completed all 15 exclusive zero-based rows: 14, 19, 24, 26, 27, 29, 30, 32, 35, 36, 37, 38, 39, 41, 42.

- 13 PhotoCraft cutouts preserve the approved artwork pixels, printing, side, and color.
- Rows 36 (Curtain Call) and 37 (Death of a Bachelor) use built-in image_gen reference reconstruction for reflected/clipped unprinted vinyl. PhotoCraft composites the original photographed printed labels back over the reconstructed material. A narrow reconstructed black label border remains. Original label detail is limited by source resolution.
- Every final is a lossless 648×648 RGBA WebP with a 640px circular disc, 4px transparent margins, and a centered transparent spindle: 16px for vinyl or 80px for CD. CD hub rings remain visible.
- Each outer ellipse and spindle was measured separately. A circle-preserving projective correction aligns the source spindle with the output center after the ellipse is straightened.
- The Father Figure mockup retains its existing clear-vinyl partial alpha. Its source has a small preexisting rectangular edge trim; the individually inset circular mask removes that trim and the surrounding shadow.
- Photographed scanner texture, slight surface marks, and lighting remain on direct cutouts. The Life of Pablo option retains its approved unofficial status and warm amber tone. Product renders remain product renders.

`report.json` is the delivery manifest, including absolute final paths, full candidate IDs, processing, exact generation prompts, source paths, and per-item limitations. `validation.json` records geometry/alpha checks and SHA-256 hashes; every original reference hash matches its approval. Approvals, references, application code, and other batches were not modified.

Original generated PNGs, exact prompts (`prompts.json`), label patches, reconstructed bases, PhotoCraft command log, and reproducible preparation/validation scripts are retained here. No CLI/API image-generation fallback was used.

Visual QA: `qa-finals-1.jpg`, `qa-finals-2.jpg`, `qa-finals-3.jpg` show every final on checkerboards. Each final was inspected, including its full rim and center. `finals-contact.jpg` is a compact index.
