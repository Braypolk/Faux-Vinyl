# Historical implementation

The current application lives in [`../server/`](../server/) and runs on Go.

[`esp32/`](esp32/) retains a generic version of the original Arduino sketch, Spotify CA certificate and URL formatting helper. The sketch folder is named `fauxvinyl` so Arduino can open `fauxvinyl.ino`. It uses DHCP and selects an active Spotify device, an optional preferred device, or a sole available device.

Copy `fauxvinyl/env.example.h` to private, ignored `fauxvinyl/env.h` and fill in Wi-Fi/Spotify credentials, an optional device name, and album or playlist URIs for the random route. Installation-specific network settings, receiver automation and original card lists stay local. The link helper accepts Spotify links as command-line inputs and removes share parameters:

```sh
python3 archive/esp32/format_link.py https://open.spotify.com/album/0000000000000000000000
```

Nothing here is needed to build or deploy the Go server. This is historical source, not a production rollback package: use private deployment backups and matching data snapshots for rollback. The superseded Flask app and original print-cover duplicates have been removed. Current collection artwork is external installation data.

Do not add credentials, database copies, session keys or private deployment backups to this archive. The root ignore rules apply here too.
