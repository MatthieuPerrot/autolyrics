#!/usr/bin/env python3
"""Test script for search backends"""

import sys
from lyrics_fetcher.utils import search


def test_search():
    """Test search function with fallback"""
    query = 'site:animelyrics.com "romaji lyrics" "Yui" "Again"'
    print(f"Testing search with query: {query}\n")

    results = []
    try:
        for i, url in enumerate(search(query, num_results=3), 1):
            print(f"  [{i}] {url}")
            results.append(url)
            if i >= 3:  # Limit to 3 results for testing
                break
    except Exception as e:
        print(f"❌ Search failed completely: {e}")
        return False

    if results:
        print(f"\n✅ Search successful! Found {len(results)} results")
        return True
    else:
        print("\n❌ Search failed - no results")
        return False


def test_individual_backends():
    """Test each backend individually"""
    from lyrics_fetcher.search_backends import (
        DuckDuckGoBackend,
        GoogleScraperBackend,
        GoogleCSEBackend,
    )

    query = 'site:animelyrics.com "Yui" "Again"'

    backends = [
        DuckDuckGoBackend(),
        GoogleScraperBackend(),
        GoogleCSEBackend(
            api_key="AIzaSyD5TjrWP30FSRBGZOieAozKV3C5QYr7mYA",
            cx="84f6b21ca8e964f6a"
        ),
    ]

    print("\n" + "=" * 60)
    print("Testing individual backends:")
    print("=" * 60)

    for backend in backends:
        print(f"\nTesting {backend.name()}...")
        try:
            results = backend.search(query, num_results=2)
            if results:
                print(f"  ✅ Success! Found {len(results)} results")
                for i, url in enumerate(results[:2], 1):
                    print(f"    [{i}] {url}")
            else:
                print(f"  ⚠️ No results found")
        except Exception as e:
            print(f"  ❌ Failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Search Backend Test Suite")
    print("=" * 60)

    # Test main search function with fallback
    success = test_search()

    # Test individual backends
    if "--detailed" in sys.argv:
        test_individual_backends()

    sys.exit(0 if success else 1)
