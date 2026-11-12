# reconstruct-a

Assigned zero-based rows: 1, 6, 7, 9, 12. Four completed finals; row 6 blocked.

Completed: Glory Sound Prep CD, beerbongs & bentleys CD, Tuesday Night Music Club blue vinyl, and The E.N.D. emerald vinyl. Built-in image_gen used separately for every assigned row. Exact prompts and successful intermediate PNGs are retained here. PhotoCraft alone performed normalization and conversion; Pillow/NumPy only read and measured images.

All four finals are 648×648 RGBA WebP, alpha bounds (4,4,644,644), with transparent outside and centered holes. CD holes are 80px; blue vinyl 16px; emerald vinyl 18px (2.8% of 640px, slightly enlarged to clear the generated opening cleanly). Each final was opened and visually inspected. See validation.json and photocraft-processing.json. Fine lettering is reconstructed and can differ; each material limitation is recorded in report.json.

Blocked row 6: exact Michael Jackson white-vinyl source was rejected twice by built-in image_gen input moderation, HTTP 400 / moderation_blocked / public-figure, including a product-only extraction retry. Exact request IDs and error messages are in tool-errors.json. No placeholder final or unauthorized fallback was created. Its report output is null.

Original approvals and references were retained, and SHA-256 hashes for all five source references still match approved-new.json. No app, manifest, original asset, or other batch was edited.

Root completion: row 6 is now a PhotoCraft-only manual white-vinyl reconstruction retaining the actual original photographed label. No generation fallback. See finish_white_vinyl.py and report.json. All five rows now have final assets.
