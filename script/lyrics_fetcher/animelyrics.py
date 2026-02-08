import requests
from bs4 import BeautifulSoup

from .chrome_fetcher import fetch_with_chrome_fallback
from .utils import search
from .language_detector import is_likely_romaji


def search_animelyrics(title: str, artists: list) -> list:
    """Return candidate URLs from animelyrics.com for the given title/artists."""
    artists_str = ' '.join([f'"{artist}"' for artist in artists])
    query = f'site:animelyrics.com "romaji lyrics" {artists_str} "{title}"'
    print(f"🔍 Recherche animelyrics : {query}")

    urls = []
    try:
        for url in search(query, num_results=5):
            if "animelyrics.com" in url:
                urls.append(url)
    except Exception as e:
        print(f"❌ Erreur lors de la recherche animelyrics : {e}")
    return urls


def parse_animelyrics(html: str) -> str:
    """Extract romaji lyrics from animelyrics HTML. Pure function: no fetching."""
    try:
        soup = BeautifulSoup(html, "html.parser")

        blocks = soup.find_all("div", class_="romaji")
        if len(blocks) == 0:
            blocks = soup.find_all("td", class_="romaji")
        if not blocks:
            return None

        lyrics = []
        for block in blocks:
            dt = block.find("dt")
            if dt and "Lyrics from" in dt.text:
                dt.decompose()

            text = block.get_text("\n", strip=True)

            if is_likely_romaji(text):
                lyrics.append(text)
            else:
                print(f"⚠️  Skipping non-romaji block (English or Japanese)")

        if not lyrics:
            print(f"❌ No romaji lyrics found (only English translations)")
            return None

        return "\n".join(lyrics).strip()

    except Exception as e:
        print(f"❌ Erreur scraping animelyrics : {e}")
        return None


def find_lyrics_animelyrics(title: str, artists: list, chrome_fetcher=None) -> str:
    """Backward-compatible wrapper: search + fetch + parse."""
    for url in search_animelyrics(title, artists):
        print(f"✅ URL trouvée (animelyrics): {url}")
        html = _fetch_animelyrics(url, chrome_fetcher)
        if html:
            lyrics = parse_animelyrics(html)
            if lyrics:
                return lyrics
    return None


def _fetch_animelyrics(url: str, chrome_fetcher=None) -> str:
    """Fetch animelyrics URL with Cloudflare detection and ChromeFetcher fallback."""
    try:
        html = None
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 403 and chrome_fetcher is not None:
                print(f"⚠️  HTTP 403 on animelyrics, retrying with ChromeFetcher...")
                html = chrome_fetcher.fetch(url)
            else:
                html = resp.text
        except Exception:
            if chrome_fetcher is not None:
                html = chrome_fetcher.fetch(url)

        if not html:
            return None

        # Cloudflare challenge page detection
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and "Just a moment" in soup.title.text:
            if chrome_fetcher is not None:
                print(f"⚠️  Cloudflare challenge detected, retrying with ChromeFetcher...")
                html = chrome_fetcher.fetch(url)
            else:
                return None

        return html

    except Exception as e:
        print(f"❌ Erreur fetch animelyrics : {e}")
        return None
