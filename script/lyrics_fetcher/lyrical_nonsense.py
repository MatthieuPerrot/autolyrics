import requests
from bs4 import BeautifulSoup
from googlesearch import search

def find_lyrics_lyrical_nonsense(title: str, artist: str) -> str:
    query = f'site:lyrical-nonsense.com "romaji lyrics" "{artist}" "{title}"'
    print(f"🔍 Recherche Lyrical Nonsense : {query}")

    for url in search(query, num_results=5):
        if "lyrical-nonsense.com" in url:
            print(f"✅ URL trouvée (Lyrical Nonsense): {url}")
            return scrape_lyrical_nonsense(url)
    return None

def scrape_lyrical_nonsense(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (lyrics-scraper)"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")

        romaji_section = soup.find("div", class_="romaji")
        if not romaji_section:
            return None

        paragraphs = romaji_section.find_all("p")
        lines = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
        return "\n".join(lines).strip()

    except Exception as e:
        print(f"❌ Erreur scraping Lyrical Nonsense : {e}")
        return None
