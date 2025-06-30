import requests
from bs4 import BeautifulSoup
from googlesearch import search

def find_lyrics_genius(title: str, artists: list) -> str:
    artists_str = ' '.join([f'"{artist}"' for artist in artists])
    query = f'site:genius.com "romanized" {artists_str} "{title}"'
    print(f"🔍 [Fallback] Recherche Genius : {query}")

    for url in search(query, num_results=5):
        if "genius.com" in url:
            print(f"✅ URL trouvée (Genius): {url}")
            lyrics = scrape_genius_lyrics(url)
            if lyrics:
                return lyrics
    return None

def scrape_genius_lyrics(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (lyrics-scraper)"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")

        containers = soup.find_all("div", {"data-lyrics-container": "true"})
        if not containers:
            return None

        lines = [div.get_text(separator="\n", strip=True) for div in containers]
        full_lyrics = "\n".join(lines).strip()

        if "to be transcribed" in full_lyrics.lower():
            return None

        return full_lyrics

    except Exception as e:
        print(f"❌ Erreur scraping Genius : {e}")
        return None


