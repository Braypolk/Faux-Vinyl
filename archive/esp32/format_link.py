"""Convert Spotify links into query strings for the historical ESP32 sketch."""
import argparse
import re
from urllib.parse import urlencode, urlsplit


def format_link(value):
    url = urlsplit(value)
    match = re.fullmatch(r"/(album|playlist)/([A-Za-z0-9]{22})/?", url.path)
    if url.scheme != "https" or url.netloc != "open.spotify.com" or not match:
        raise ValueError("Use a Spotify album or playlist link")
    return "?" + urlencode({"item": match[1], "id": match[2]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("links", nargs="+", help="Spotify album or playlist URLs")
    args = parser.parse_args()
    try:
        output = [format_link(link) for link in args.links]
    except ValueError as error:
        parser.error(str(error))
    print("\n".join(output))


if __name__ == "__main__":
    main()
