from bs4 import BeautifulSoup

from .chrome_fetcher import fetch_with_chrome_fallback
from .utils import search
from .language_detector import is_likely_romaji


def search_nautiljon(title: str, artists: list) -> list:
    """Return candidate URLs from nautiljon.com for the given title/artists."""
    artists_str = ' '.join([f'"{artist}"' for artist in artists])
    query1 = f'site:https://www.nautiljon.com/paroles {artists_str} \"{title}\"'
    query2 = f'site:https://www.nautiljon.com/paroles \"{title}\"'

    urls = []
    for query in [query1, query2]:
        print(f"🔍 Recherche Nautiljon: {query}")
        for url in search(query, num_results=2):
            print(f"🔍 URL (Nautiljon): {url}")
            if "nautiljon.com/paroles" in url:
                urls.append(url)
    return urls


def parse_nautiljon(html: str) -> str:
    """Extract romaji lyrics from Nautiljon HTML. Pure function: no fetching."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        lyrics_section = soup.find("span", {"itemprop": "lyrics"})

        if not lyrics_section:
            return None

        text = lyrics_section.get_text()

        if not is_likely_romaji(text):
            print(f"⚠️  Skipping non-romaji lyrics from Nautiljon (English or Japanese)")
            return None

        return text

    except Exception as e:
        print(f"❌ Erreur scraping Nautiljon : {e}")
        return None


def raw_parse_nautiljon(html: str) -> str | None:
    """Extract lyrics text from Nautiljon HTML without romaji validation."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        lyrics_section = soup.find("span", {"itemprop": "lyrics"})
        if not lyrics_section:
            return None
        return lyrics_section.get_text()
    except Exception:
        return None


def find_lyrics_nautiljon(title: str, artists: list, chrome_fetcher=None) -> str:
    """Backward-compatible wrapper: search + fetch + parse."""
    for url in search_nautiljon(title, artists):
        print(f"✅ URL trouvée (Nautiljon): {url}")
        html = fetch_with_chrome_fallback(url, chrome_fetcher)
        if html:
            lyrics = parse_nautiljon(html)
            if lyrics:
                return lyrics
    return None
