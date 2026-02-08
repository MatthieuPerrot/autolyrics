from bs4 import BeautifulSoup

from .chrome_fetcher import fetch_with_chrome_fallback
from .utils import search
from .language_detector import is_likely_romaji


def search_lyrical_nonsense(title: str, artists: list) -> list:
    """Return candidate URLs from lyrical-nonsense.com for the given title/artists."""
    artists_str = ' '.join([f'"{artist}"' for artist in artists])
    query = f'site:lyrical-nonsense.com "romaji lyrics" {artists_str} "{title}"'
    print(f"🔍 Recherche Lyrical Nonsense : {query}")

    urls = []
    for url in search(query, num_results=5):
        if "lyrical-nonsense.com" in url:
            urls.append(url)
    return urls


def parse_lyrical_nonsense(html: str) -> str:
    """Extract romaji lyrics from Lyrical Nonsense HTML. Pure function: no fetching."""
    try:
        soup = BeautifulSoup(html, "html.parser")

        romaji_section = soup.find("div", class_="romaji")
        if not romaji_section:
            return None

        paragraphs = romaji_section.find_all("p")
        lines = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
        full_lyrics = "\n".join(lines).strip()

        if not is_likely_romaji(full_lyrics):
            print(f"⚠️  Skipping non-romaji lyrics from Lyrical Nonsense (English or Japanese)")
            return None

        return full_lyrics

    except Exception as e:
        print(f"❌ Erreur scraping Lyrical Nonsense : {e}")
        return None


def find_lyrics_lyrical_nonsense(title: str, artists: list, chrome_fetcher=None) -> str:
    """Backward-compatible wrapper: search + fetch + parse."""
    for url in search_lyrical_nonsense(title, artists):
        print(f"✅ URL trouvée (Lyrical Nonsense): {url}")
        html = fetch_with_chrome_fallback(url, chrome_fetcher)
        if html:
            lyrics = parse_lyrical_nonsense(html)
            if lyrics:
                return lyrics
    return None
