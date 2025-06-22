import requests
from bs4 import BeautifulSoup
from googlesearch import search

def find_lyrics_mojim(title: str, artist: str) -> str:
    query = f'site:mojim.com "{artist}" "{title}"'
    print(f"🔍 Recherche Mojim : {query}")

    for url in search(query, num_results=5):
        if "mojim.com" in url and "jpy" in url:  # pour filtrer la section japonaise
            print(f"✅ URL trouvée (Mojim): {url}")
            return scrape_mojim(url)
    return None

def scrape_mojim(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (lyrics-scraper)"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")

        lyric_block = soup.find("dd", id="fsZx3")
        if not lyric_block:
            return None

        text = lyric_block.get_text("\n", strip=True)
        if "更多更詳盡歌詞" in text:
            text = text.split("更多更詳盡歌詞")[0]
        return text.strip()

    except Exception as e:
        print(f"❌ Erreur scraping Mojim : {e}")
        return None
