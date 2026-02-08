from bs4 import BeautifulSoup

from .chrome_fetcher import fetch_with_chrome_fallback
from .utils import search
from .language_detector import is_likely_romaji


def search_genius(title: str, artists: list) -> list:
    """Return candidate URLs from genius.com for the given title/artists."""
    artists_str = ' '.join([f'"{artist}"' for artist in artists])
    query = f'site:genius.com "romanized" {artists_str} "{title}"'
    print(f"🔍 [Fallback] Recherche Genius : {query}")

    urls = []
    for url in search(query, num_results=5):
        if "genius.com" in url:
            urls.append(url)
    return urls


def parse_genius(html: str) -> str:
    """Extract romaji lyrics from Genius HTML. Pure function: no fetching."""
    try:
        soup = BeautifulSoup(html, "html.parser")

        containers = soup.find_all("div", {"data-lyrics-container": "true"})
        if not containers:
            return None

        lines = [div.get_text(separator="\n", strip=True) for div in containers]
        full_lyrics = "\n".join(lines).strip()

        if "to be transcribed" in full_lyrics.lower():
            return None

        if not is_likely_romaji(full_lyrics):
            print(f"⚠️  Skipping non-romaji lyrics from Genius (English or Japanese)")
            return None

        return full_lyrics

    except Exception as e:
        print(f"❌ Erreur scraping Genius : {e}")
        return None


def find_lyrics_genius(title: str, artists: list, chrome_fetcher=None) -> str:
    """Backward-compatible wrapper: search + fetch + parse."""
    for url in search_genius(title, artists):
        print(f"✅ URL trouvée (Genius): {url}")
        html = fetch_with_chrome_fallback(url, chrome_fetcher)
        if html:
            lyrics = parse_genius(html)
            if lyrics:
                return lyrics
    return None
