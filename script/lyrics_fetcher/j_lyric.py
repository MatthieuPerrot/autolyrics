import requests
from bs4 import BeautifulSoup
from googlesearch import search

def find_lyrics_j_lyric(title: str, artists: list) -> str:
    artists_str = ' '.join([f'"{artist}"' for artist in artists])
    query = f'site:j-lyric.net {artists_str} "{title}"'
    print(f"🔍 Recherche J-Lyric : {query}")

    for url in search(query, num_results=5):
        if "j-lyric.net" in url and "/artist/" in url:
            print(f"✅ URL trouvée (J-Lyric): {url}")
            return scrape_j_lyric(url)
    return None

def scrape_j_lyric(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (lyrics-scraper)"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")

        lyric_div = soup.find("p", id="Lyric")
        if not lyric_div:
            return None

        return lyric_div.get_text("\n", strip=True)

    except Exception as e:
        print(f"❌ Erreur scraping J-Lyric : {e}")
        return None
