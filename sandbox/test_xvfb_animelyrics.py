"""Test Selenium non-headless + Xvfb on animelyrics.com"""

import sys
import time

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Add script/ to path for language_detector
sys.path.insert(0, "script")


def main():
    print("Testing Selenium non-headless + Xvfb...\n")

    # Virtual display (Chrome thinks it has a real screen)
    display = Display(visible=False, size=(1920, 1080))
    display.start()
    print("Virtual display started")

    chrome_options = Options()
    # NO --headless flag!
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    )
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.navigator.chrome = {runtime: {}};
        """
    })

    url = "https://www.animelyrics.com/anime/gundamw/gwwr.htm"
    print(f"URL: {url}")

    try:
        driver.get(url)
        print("Waiting for Cloudflare (15s)...")
        time.sleep(15)

        page_source = driver.page_source

        if "Just a moment" in page_source or "challenge-platform" in page_source:
            print("BLOCKED by Cloudflare")
        elif "White Reflection" in page_source:
            print("Cloudflare bypassed!")

            soup = BeautifulSoup(page_source, "html.parser")
            romaji = soup.find_all("td", class_="romaji")
            print(f"  Found {len(romaji)} romaji blocks")

            if romaji:
                from lyrics_fetcher.language_detector import is_likely_romaji

                dt = romaji[0].find("dt")
                if dt and "Lyrics from" in dt.text:
                    dt.decompose()
                sample = romaji[0].get_text("\n", strip=True)
                print(f"  is_likely_romaji: {is_likely_romaji(sample)}")
                print(f"  Sample: {sample[:150]}...")
        else:
            title = BeautifulSoup(page_source, "html.parser").find("title")
            print(f"Unexpected page. Title: {title.text if title else 'none'}")

    finally:
        driver.quit()
        display.stop()
        print("\nBrowser + display closed.")


if __name__ == "__main__":
    main()
