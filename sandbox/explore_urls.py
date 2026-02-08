#!/usr/bin/env python3
"""Explore all search URLs for a given song across all sources.

Usage:
    python3 sandbox/explore_urls.py "WHITE REFLECTION" "TWO-MIX"
    python3 sandbox/explore_urls.py "TITLE" "ARTIST1" "ARTIST2"
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "script"))

from lyrics_fetcher.source_registry import build_registry


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} TITLE ARTIST [ARTIST2 ...]")
        sys.exit(1)

    title = sys.argv[1]
    artists = sys.argv[2:]

    print(f"Title:   {title}")
    print(f"Artists: {artists}")
    print()

    sources = build_registry()

    for source in sources:
        print(f"--- {source.name} (quality={source.romaji_quality}) ---")
        try:
            urls = source.search(title, artists)
        except Exception as e:
            print(f"  SEARCH ERROR: {e}")
            continue

        if not urls:
            print("  (no URLs found)")
        else:
            for i, url in enumerate(urls, 1):
                print(f"  {i}. {url}")
        print()


if __name__ == "__main__":
    main()
