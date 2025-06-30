from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from googlesearch import search
from bs4 import BeautifulSoup


def find_lyrics_nautiljon(title: str, artists: list) -> str:
    artists_str = ' '.join([f'"{artist}"' for artist in artists])
    query1 = f'site:https://www.nautiljon.com/paroles {artists_str} \"{title}\"'
    query2 = f'site:https://www.nautiljon.com/paroles \"{title}\"'
    
    for query in [query1, query2]:
        print(f"🔍 Recherche Nautiljon : {query}")
        for url in search(query, num_results=2):
            if "nautiljon.com/paroles" in url:
                print(f"✅ URL trouvée (Nautiljon): {url}")
                lyrics = scrape_nautiljon_selenium(url)
                if lyrics:
                    return lyrics
    return None


def scrape_nautiljon_selenium(url: str) -> str:
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # 🆕 mode furtif
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # ✅ On modifie les propriétés JavaScript connues pour trahir Selenium
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            """
        })

        driver.get(url)

        # ⏳ Attente explicite que l'élément lyrics apparaisse
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[itemprop="lyrics"]'))
        )

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        lyrics_section = soup.find('span', {'itemprop': 'lyrics'})

        if lyrics_section:
            text = lyrics_section.get_text()
        else:
            text = None

        driver.quit()
        return text

    except Exception as e:
        print(f"❌ Erreur Selenium/Nautiljon furtif : {e}")
        return None
