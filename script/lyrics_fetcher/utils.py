# Placeholders pour l'instant. Futur : détection de langue, conversion romaji, logs, etc.

def is_romaji(text: str) -> bool:
    return all(ord(c) < 128 for c in text)


def detect_script(text: str) -> str:
    # Très simplifié
    if any('\u3040' <= c <= '\u30ff' for c in text):
        return 'japanese'
    elif any('\u1100' <= c <= '\u11FF' or '\uAC00' <= c <= '\uD7AF' for c in text):
        return 'korean'
    return 'latin'


def search(query: str, num_results: int = 5):
    """
    Search with automatic fallback across multiple backends.
    Yields URLs one by one.

    Backends are tried in order:
    1. DuckDuckGo (most reliable, no API key)
    2. Google Scraper (can be rate limited)
    3. Google CSE (has IP restrictions in this case)
    """
    from .search_backends import (
        DuckDuckGoBackend,
        GoogleScraperBackend,
        GoogleCSEBackend,
    )

    # Define backends in priority order
    backends = [
        DuckDuckGoBackend(),
        GoogleScraperBackend(),
        GoogleCSEBackend(
            api_key="AIzaSyD5TjrWP30FSRBGZOieAozKV3C5QYr7mYA",
            cx="84f6b21ca8e964f6a"
        ),
    ]

    for backend in backends:
        try:
            results = backend.search(query, num_results)
            if results:
                print(f"✅ Using search backend: {backend.name()}")
                for url in results:
                    yield url
                return  # Success, don't try other backends
            else:
                print(f"⚠️ {backend.name()} returned no results")
        except Exception as e:
            print(f"⚠️ {backend.name()} failed: {type(e).__name__}")
            # Continue to next backend
            continue

    # All backends failed
    print("❌ All search backends failed")
