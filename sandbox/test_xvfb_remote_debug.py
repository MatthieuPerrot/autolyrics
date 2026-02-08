"""Test: Autonomous Cloudflare bypass via Xvfb + Chrome subprocess + Remote Debugging

No ChromeDriver involved in launching Chrome.
"""

import json
import subprocess
import sys
import time

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

sys.path.insert(0, "script")


def wait_for_chrome(port=9222, timeout=10):
    """Wait until Chrome's remote debugging port is ready."""
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=1)
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


def main():
    print("Autonomous Cloudflare bypass: Xvfb + Chrome subprocess\n")

    with open("sandbox/fingerprint_real_chrome.json") as f:
        real_fp = json.load(f)

    screen_w = real_fp.get("screen.width", 1920)
    screen_h = real_fp.get("screen.height", 1200)

    # Step 1: Virtual display
    display = Display(visible=False, size=(screen_w, screen_h))
    display.start()
    print(f"Virtual display: {screen_w}x{screen_h}")

    # Step 2: Launch Chrome directly (no ChromeDriver)
    chrome_cmd = [
        "google-chrome",
        "--remote-debugging-port=9222",
        "--no-first-run",
        "--no-default-browser-check",
        f"--window-size={screen_w},{screen_h}",
        "about:blank",
    ]
    print(f"Launching Chrome...")
    chrome_proc = subprocess.Popen(
        chrome_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if not wait_for_chrome(9222):
        print("ERROR: Chrome did not start in time")
        chrome_proc.terminate()
        display.stop()
        return False

    print("Chrome ready on port 9222")

    # Step 3: Connect via Remote Debugging
    opts = Options()
    opts.debugger_address = "127.0.0.1:9222"

    try:
        driver = webdriver.Chrome(options=opts)
        print("Selenium connected!")
    except Exception as e:
        print(f"Failed to connect: {e}")
        chrome_proc.terminate()
        display.stop()
        return False

    try:
        # Step 4: Quick sanity check
        print("\n--- Fingerprint check ---")
        checks = driver.execute_script("""
            return {
                'webdriver': navigator.webdriver,
                'plugins_type': navigator.plugins instanceof PluginArray,
                'plugins_len': navigator.plugins.length,
                'platform': navigator.platform,
            };
        """)
        for k, v in checks.items():
            print(f"  {k}: {v}")

        # Step 5: Test animelyrics
        print("\n--- Test animelyrics ---")
        url = "https://www.animelyrics.com/anime/gundamw/gwwr.htm"
        print(f"URL: {url}")

        driver.get(url)
        print("Waiting for Cloudflare (15s)...")
        time.sleep(15)

        page_source = driver.page_source

        if "Just a moment" in page_source or "challenge-platform" in page_source:
            print("\nBLOCKED by Cloudflare")
            return False

        if "White Reflection" in page_source:
            print("\nCloudflare BYPASSED!")

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

            return True

        title = BeautifulSoup(page_source, "html.parser").find("title")
        print(f"Unexpected. Title: {title.text if title else 'none'}")
        return False

    finally:
        driver.quit()
        chrome_proc.terminate()
        chrome_proc.wait()
        display.stop()
        print("\nChrome + display closed.")


if __name__ == "__main__":
    success = main()
    if success:
        print("\n=== SUCCESS! Fully autonomous Cloudflare bypass! ===")
    else:
        print("\n=== FAILED ===")
    sys.exit(0 if success else 1)
