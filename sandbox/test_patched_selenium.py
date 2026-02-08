"""Test patched Selenium on animelyrics - fixing CRITICAL issues from sannysoft diff

Fixes:
- WebDriver: use CDP to disable webdriver flag at browser level
- PluginArray: don't override navigator.plugins (let Chrome handle it natively)
"""

import json
import sys
import time

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

sys.path.insert(0, "script")


def patch_chromedriver(driver_path):
    """Patch chromedriver binary to rename $cdc_ variable."""
    import os
    import shutil

    patched_path = driver_path + ".patched"
    if os.path.exists(patched_path):
        return patched_path

    shutil.copy2(driver_path, patched_path)
    with open(patched_path, "r+b") as f:
        data = f.read()
        data = data.replace(b"$cdc_", b"$abc_")
        f.seek(0)
        f.write(data)
        f.truncate()
    os.chmod(patched_path, 0o755)
    return patched_path


def main():
    print("Task #6: Patched Selenium - fixing CRITICAL issues\n")

    with open("sandbox/fingerprint_real_chrome.json") as f:
        real_fp = json.load(f)

    screen_w = real_fp.get("screen.width", 1920)
    screen_h = real_fp.get("screen.height", 1200)

    display = Display(visible=False, size=(screen_w, screen_h))
    display.start()
    print(f"Virtual display: {screen_w}x{screen_h}")

    # Patch chromedriver binary
    driver_path = ChromeDriverManager().install()
    patched_path = patch_chromedriver(driver_path)
    print(f"Using patched chromedriver")

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"--window-size={screen_w},{screen_h}")
    chrome_options.add_argument(
        f"--user-agent={real_fp.get('navigator.userAgent', '')}"
    )
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(patched_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # FIX WebDriver: disable at browser level via CDP
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": """
            // Delete the webdriver property entirely so it falls back to
            // the prototype default (undefined/missing), rather than
            // redefining with a getter that returns false
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """}
    )

    # Separate patches for non-plugin properties
    langs = json.dumps(real_fp.get("navigator.languages", []))
    hw = real_fp.get("navigator.hardwareConcurrency", 4)
    mem = real_fp.get("navigator.deviceMemory", 8)
    real_vendor = json.dumps(real_fp.get("webgl_vendor", ""))
    real_renderer = json.dumps(real_fp.get("webgl_renderer", ""))

    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": f"""
            // Languages
            Object.defineProperty(navigator, 'languages', {{get: () => {langs}}});

            // Hardware
            Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {hw}}});
            Object.defineProperty(navigator, 'deviceMemory', {{get: () => {mem}}});

            // FIX: Do NOT override navigator.plugins - let Chrome handle PluginArray natively

            // Chrome object
            window.chrome = {{runtime: undefined}};

            // WebGL
            (function() {{
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(param) {{
                    if (param === 37445) return {real_vendor};
                    if (param === 37446) return {real_renderer};
                    return getParameter.call(this, param);
                }};
            }})();

            // Permissions
            const origQuery = navigator.permissions.query.bind(navigator.permissions);
            navigator.permissions.query = (params) =>
                params.name === 'notifications'
                ? Promise.resolve({{state: 'prompt', onchange: null}})
                : origQuery(params);
        """}
    )

    try:
        # Step 1: Verify fixes on sannysoft
        print("\n--- Step 1: Verify fixes on bot.sannysoft.com ---")
        driver.get("https://bot.sannysoft.com/")
        time.sleep(5)

        checks = driver.execute_script("""
            return {
                'WebDriver': navigator.webdriver,
                'PluginArray type': navigator.plugins instanceof PluginArray,
                'Plugins length': navigator.plugins.length,
                'WebGL renderer': (function() {
                    try {
                        var c = document.createElement('canvas');
                        var gl = c.getContext('webgl');
                        var ext = gl.getExtension('WEBGL_debug_renderer_info');
                        return gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
                    } catch(e) { return 'error'; }
                })()
            };
        """)
        for k, v in checks.items():
            val = str(v)[:80]
            print(f"  {k}: {val}")

        # Step 2: Test animelyrics
        print("\n--- Step 2: Test animelyrics ---")
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
        display.stop()
        print("\nBrowser + display closed.")


if __name__ == "__main__":
    success = main()
    if success:
        print("\n=== SUCCESS! Autonomous Cloudflare bypass! ===")
    else:
        print("\n=== FAILED ===")
    sys.exit(0 if success else 1)
