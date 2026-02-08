from bs4 import BeautifulSoup

from .chrome_fetcher import fetch_with_chrome_fallback
from .utils import search
from .language_detector import is_likely_romaji


def search_mojim(title: str, artists: list) -> list:
    """Return candidate URLs from mojim.com for the given title/artists."""
    artists_str = ' '.join([f'"{artist}"' for artist in artists])
    query = f'site:mojim.com {artists_str} "{title}"'
    print(f"🔍 Recherche Mojim : {query}")

    urls = []
    for url in search(query, num_results=5):
        if "mojim.com" in url and "jpy" in url:
            urls.append(url)
    return urls


def parse_mojim(html: str) -> str:
    """Extract romaji lyrics from Mojim HTML. Pure function: no fetching."""
    try:
        soup = BeautifulSoup(html, "html.parser")

        lyric_block = soup.find("dd", id="fsZx3")
        if not lyric_block:
            return None

        text = lyric_block.get_text("\n", strip=True)
        if "更多更詳盡歌詞" in text:
            text = text.split("更多更詳盡歌詞")[0]
        text = text.strip()

        if not is_likely_romaji(text):
            print(f"⚠️  Skipping non-romaji lyrics from Mojim (English or Japanese)")
            return None

        return text

    except Exception as e:
        print(f"❌ Erreur scraping Mojim : {e}")
        return None


def raw_parse_mojim(html: str) -> str | None:
    """Extract lyrics text from Mojim HTML without romaji validation."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        lyric_block = soup.find("dd", id="fsZx3")
        if not lyric_block:
            return None
        text = lyric_block.get_text("\n", strip=True)
        if "更多更詳盡歌詞" in text:
            text = text.split("更多更詳盡歌詞")[0]
        return text.strip()
    except Exception:
        return None


def find_lyrics_mojim(title: str, artists: list, chrome_fetcher=None) -> str:
    """Backward-compatible wrapper: search + fetch + parse."""
    for url in search_mojim(title, artists):
        print(f"✅ URL trouvée (Mojim): {url}")
        html = fetch_with_chrome_fallback(url, chrome_fetcher)
        if html:
            lyrics = parse_mojim(html)
            if lyrics:
                return lyrics
    return None
