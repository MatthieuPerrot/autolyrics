# Placeholders pour l'instant. Futur : détection de langue, conversion romaji, logs, etc.

import time


def is_romaji(text: str) -> bool:
    return all(ord(c) < 128 for c in text)


def detect_script(text: str) -> str:
    # Très simplifié
    if any('\u3040' <= c <= '\u30ff' for c in text):
        return 'japanese'
    elif any('\u1100' <= c <= '\u11FF' or '\uAC00' <= c <= '\uD7AF' for c in text):
        return 'korean'
    return 'latin'


def _build_backends():
    """Build the list of search backends in priority order."""
    from .search_backends import (
        DuckDuckGoBackend,
        GoogleScraperBackend,
        GoogleCSEBackend,
    )

    return [
        DuckDuckGoBackend(),
        GoogleScraperBackend(),
        GoogleCSEBackend(
            api_key="AIzaSyD5TjrWP30FSRBGZOieAozKV3C5QYr7mYA",
            cx="84f6b21ca8e964f6a"
        ),
    ]


# Retry only the first backend (DDG) — subsequent backends are already fallbacks.
_FIRST_BACKEND_RETRIES = 1
_RETRY_DELAY = 2


def search(query: str, num_results: int = 5):
    """
    Search with automatic fallback across multiple backends.
    Yields URLs one by one.

    Backends are tried in order:
    1. DuckDuckGo (most reliable, no API key) — retried once on failure
    2. Google Scraper (can be rate limited)
    3. Google CSE (has IP restrictions in this case)
    """
    backends = _build_backends()

    for i, backend in enumerate(backends):
        retries = _FIRST_BACKEND_RETRIES if i == 0 else 0
        for attempt in range(retries + 1):
            try:
                results = backend.search(query, num_results)
                if results:
                    print(f"✅ Using search backend: {backend.name()}")
                    for url in results:
                        yield url
                    return
                else:
                    print(f"⚠️ {backend.name()} returned no results")
                    break  # Empty results are not transient, skip retry
            except Exception as e:
                if attempt < retries:
                    time.sleep(_RETRY_DELAY)
                    continue
                print(f"⚠️ {backend.name()} failed: {type(e).__name__}")
                break

    # All backends failed
    print("❌ All search backends failed")
