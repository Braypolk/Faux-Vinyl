# Cleanup A

Completed assigned ordered rows: 0, 2, 3, 4, 5, 8, 10, 11, 15, 17, 20, 21, 23, 25.

- 14 final lossless RGBA WebP files, each 648×648; circular 640px disc, 4px transparent margin and centered 16px transparent vinyl spindle hole.
- 11 PhotoCraft cutouts preserve source printing and surface pixels. Each outer ellipse and spindle was measured individually and rectified projectively. Swimming additionally uses a fitted rotated ellipse.
- Rows 0, 3 and 15 use built-in image_gen to reconstruct surfaces with camera/person/hand reflections removed. Their complete printed center labels are original source pixels composited back through PhotoCraft at their measured physical proportion. Generated near-opaque alpha was backed by a matching vinyl color before the final circular mask.
- Multi-disc sources: After Hours selects the unobscured foreground left side-A record; Swimming selects the unobscured foreground right record; Blonde selects the left 1-B record. No extra variants were produced.
- Clear/milky vinyl keeps its photographed pale appearance. Only the exterior and spindle are transparent. Source texture, small surface marks, tiny-print resolution and ordinary lighting reflections remain where cut out faithfully.
- All 14 finals were inspected individually at 648px. `validation.json` records format, full circular alpha bounds, centered clear spindle, transparent 4px exterior and opaque interior annulus. `finals-contact.jpg` provides a checkerboard QA overview.

`report.json` has one entry per source with full candidate ID and absolute output/reference paths. `assigned.json` retains complete assigned source metadata without modifying approvals or references. `prompts.json` and row prompt files retain the exact generation prompts; all six generated PNGs and prepared label/surface intermediates remain here. Command JSON files and PhotoCraft logs record reproducible processing. No app files, manifests, original assets or other batches were edited.

Reproduce with `/Users/bray.polkinghorne/.pyenv/versions/3.13.5/bin/python3 process_batch.py` from this directory or by absolute path. Image mutations and conversion use PhotoCraft; Pillow/NumPy only read, measure, validate and build QA contact sheets.
