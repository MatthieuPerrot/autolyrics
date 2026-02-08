from bs4 import BeautifulSoup

from .chrome_fetcher import fetch_with_chrome_fallback
from .utils import search
from .language_detector import is_likely_romaji


def search_j_lyric(title: str, artists: list) -> list:
    """Return candidate URLs from j-lyric.net for the given title/artists."""
    artists_str = ' '.join([f'"{artist}"' for artist in artists])
    query = f'site:j-lyric.net {artists_str} "{title}"'
    print(f"🔍 Recherche J-Lyric : {query}")

    urls = []
    for url in search(query, num_results=5):
        if "j-lyric.net" in url and "/artist/" in url:
            urls.append(url)
    return urls


def parse_j_lyric(html: str) -> str:
    """Extract romaji lyrics from J-Lyric HTML. Pure function: no fetching."""
    try:
        soup = BeautifulSoup(html, "html.parser")

        lyric_div = soup.find("p", id="Lyric")
        if not lyric_div:
            return None

        text = lyric_div.get_text("\n", strip=True)

        if not is_likely_romaji(text):
            print(f"⚠️  Skipping non-romaji lyrics from J-Lyric (English or Japanese)")
            return None

        return text

    except Exception as e:
        print(f"❌ Erreur scraping J-Lyric : {e}")
        return None


def raw_parse_j_lyric(html: str) -> str | None:
    """Extract lyrics text from J-Lyric HTML without romaji validation."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        lyric_div = soup.find("p", id="Lyric")
        if not lyric_div:
            return None
        return lyric_div.get_text("\n", strip=True)
    except Exception:
        return None


def find_lyrics_j_lyric(title: str, artists: list, chrome_fetcher=None) -> str:
    """Backward-compatible wrapper: search + fetch + parse."""
    for url in search_j_lyric(title, artists):
        print(f"✅ URL trouvée (J-Lyric): {url}")
        html = fetch_with_chrome_fallback(url, chrome_fetcher)
        if html:
            lyrics = parse_j_lyric(html)
            if lyrics:
                return lyrics
    return None
