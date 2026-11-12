# Disc artwork experiment — two albums only

Local dev: http://127.0.0.1:18787/?disc=maad-city or /?disc=billie.
Use the Disc preview buttons under the shelf to switch samples and preview/pause the spin.
The local simulated Play button also starts the animation. No music or real pause requests are sent.

## Sources

- Kendrick Lamar, good kid, m.A.A.d city (deluxe), Disc 1 CD:
  https://musicbrainz.org/release/e1d99364-1ad9-4f4d-9505-2242eff10a44/cover-art
  https://coverartarchive.org/release/e1d99364-1ad9-4f4d-9505-2242eff10a44/30544560749-1200.jpg
- Billie Eilish, WHEN WE ALL FALL ASLEEP, WHERE DO WE GO?, CD:
  https://musicbrainz.org/release/6789dd53-0ec6-410c-9c71-c4a75c12d214/cover-art
  https://coverartarchive.org/release/6789dd53-0ec6-410c-9c71-c4a75c12d214/30664206604-1200.jpg

Downloaded 2026-11-11. Both delivered scans are 600×600 even at the 1200 URL.
Original printing and plastic hubs retained. Outside and center hole removed with PhotoCraft CLI elliptical selections and a layer mask. No generated or reconstructed artwork.

PhotoCraft sequence: layer.new.layerFromBackground(ifPresent=true), select.rect(ellipse=true), select.rect(ellipse=true,mode=subtract), layer.layerMask.revealSelection, select.deselect, image.crop, export PNG.
Coordinates in the 600×600 sources:
- maad city outer x=5,y=5,width=590,height=590; hole x=267,y=265,width=66,height=69.
- Billie outer x=7,y=7,width=586,height=587; hole x=266,y=266,width=68,height=68.
- Both cropped x=3,y=3,width=594,height=594 to preserve a small transparent rim.

Final transparent PNGs copied to static/disc-prototype/.

## Scope and follow-up

The template loads disc-prototype.js/css only in dev mode. Only the two selected album titles have disc art. No persistent metadata, production deployment, or original project sync was performed.
Spin is a visual preview, not actual playback polling. Before general rollout, integrate actual playback/pause/track-end state, stable artwork metadata and upload support. CSS honors reduced-motion settings and animates in the browser (no server frames/polling).

Discarded candidates: HIT ME HARD AND SOFT MusicBrainz release 720b16c1-6669-4aeb-bdc1-4ec33c67fd04 has center-label close-ups rather than a complete vinyl face. The official Interscope anniversary product packshot hides part of the record behind the sleeve. Neither was reconstructed or used in the preview.
