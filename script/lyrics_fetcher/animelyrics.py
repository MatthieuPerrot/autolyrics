import requests
from bs4 import BeautifulSoup
from googlesearch import search

def find_lyrics_animelyrics(title: str, artists: list) -> str:
    artists_str = ' '.join([f'"{artist}"' for artist in artists])
    query = f'site:animelyrics.com "romaji lyrics" {artists_str} "{title}"'
    print(f"🔍 Recherche animelyrics : {query}")

    for url in search(query, num_results=5):
        if "animelyrics.com" in url:
            print(f"✅ URL trouvée (animelyrics): {url}")
            lyrics = scrape_animelyrics(url)
            if lyrics:
                return lyrics
    return None

def scrape_animelyrics(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (lyrics-scraper)"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")
        
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
            lyrics.append(block.get_text("\n", strip=True))
        return "\n".join(lyrics).strip()

    except Exception as e:
        print(f"❌ Erreur scraping animelyrics : {e}")
        return None
