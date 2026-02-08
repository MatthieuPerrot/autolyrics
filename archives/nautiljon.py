from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from googlesearch import search
import time

def find_lyrics_nautiljon(title: str, artist: str) -> str:
    query = f'site:https://www.nautiljon.com/paroles \"{artist}\" \"{title}\"'
    print(f"🔍 Recherche Nautiljon : {query}")

    for url in search(query, num_results=5):
        if "nautiljon.com/paroles" in url:
            print(f"✅ URL trouvée (Nautiljon): {url}")
            lyrics = scrape_nautiljon_selenium(url)
            if lyrics:
                return lyrics
    return None

def scrape_nautiljon_selenium(url: str) -> str:
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url)
        time.sleep(2)  # laisser le JS charger

        from bs4 import BeautifulSoup
        page_source = driver.page_source
        print(page_source, type(page_source))
        soup = BeautifulSoup(page_source, 'html.parser')
        lyrics_section = soup.find('span', {'itemprop': 'lyrics'})
        if lyrics_section:
            print("!!!!!!!!!!!!!!!!")
            print(lyrics_section.get_text())
            print("!!!!!!!!!!!!!!!!")
        else:
            print("Paroles non trouvées.")

        # ✅ Nouvelle cible correcte
        lyrics_element = driver.find_element(By.CSS_SELECTOR, '[itemprop="text"]')
        text = lyrics_element.text.strip()

        driver.quit()

        if len(text.splitlines()) < 3:
            return None

        return text

    except Exception as e:
        print(f"❌ Erreur Selenium/Nautiljon : {e}")
        return None
