"""Test Chrome Remote Debugging on animelyrics.com

Prerequisites: launch Chrome with remote debugging enabled:
    google-chrome --remote-debugging-port=9222
"""

import json
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

sys.path.insert(0, "script")


# Fingerprint properties to extract for later diffing (task #6)
FINGERPRINT_JS = """
return {
    // Navigator properties
    'navigator.webdriver': navigator.webdriver,
    'navigator.userAgent': navigator.userAgent,
    'navigator.platform': navigator.platform,
    'navigator.languages': navigator.languages,
    'navigator.plugins.length': navigator.plugins.length,
    'navigator.hardwareConcurrency': navigator.hardwareConcurrency,
    'navigator.deviceMemory': navigator.deviceMemory,
    'navigator.maxTouchPoints': navigator.maxTouchPoints,

    // Chrome-specific
    'window.chrome': !!window.chrome,
    'window.chrome.runtime': !!(window.chrome && window.chrome.runtime),
    'window.chrome.runtime.id': !!(window.chrome && window.chrome.runtime && window.chrome.runtime.id),

    // Automation detection
    'navigator.webdriver': navigator.webdriver,
    'document.__selenium_unwrapped': !!document.__selenium_unwrapped,
    'document.__webdriver_evaluate': !!document.__webdriver_evaluate,
    'document.__driver_evaluate': !!document.__driver_evaluate,

    // Window properties
    'window.outerWidth': window.outerWidth,
    'window.outerHeight': window.outerHeight,
    'window.innerWidth': window.innerWidth,
    'window.innerHeight': window.innerHeight,
    'screen.width': screen.width,
    'screen.height': screen.height,

    // WebGL
    'webgl_vendor': (function() {
        try {
            var c = document.createElement('canvas');
            var gl = c.getContext('webgl');
            var ext = gl.getExtension('WEBGL_debug_renderer_info');
            return gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
        } catch(e) { return 'error'; }
    })(),
    'webgl_renderer': (function() {
        try {
            var c = document.createElement('canvas');
            var gl = c.getContext('webgl');
            var ext = gl.getExtension('WEBGL_debug_renderer_info');
            return gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
        } catch(e) { return 'error'; }
    })(),

    // Permissions API
    'permissions_query': await navigator.permissions.query({name: 'notifications'}).then(r => r.state).catch(() => 'error'),

    // CDP detection
    'has_cdc': (function() {
        for (var key in document) {
            if (key.match(/^cdc_|\\$cdc_|\\$chrome_/)) return key;
        }
        return false;
    })(),
}
"""


def step1_test_animelyrics(driver):
    """Test if animelyrics loads through Cloudflare."""
    url = "https://www.animelyrics.com/anime/gundamw/gwwr.htm"
    print(f"\n--- Step 1: Test animelyrics ---")
    print(f"URL: {url}")

    driver.get(url)
    print("Waiting for Cloudflare (15s)...")
    time.sleep(15)

    page_source = driver.page_source

    if "Just a moment" in page_source or "challenge-platform" in page_source:
        print("BLOCKED by Cloudflare")
        return False

    if "White Reflection" in page_source:
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
        return True

    title = BeautifulSoup(page_source, "html.parser").find("title")
    print(f"Unexpected page. Title: {title.text if title else 'none'}")
    return False


def step2_extract_fingerprint(driver):
    """Extract browser fingerprint for later diffing."""
    print(f"\n--- Step 2: Extract fingerprint ---")

    # Use async wrapper for the await in permissions query
    js = f"return (async () => {{ {FINGERPRINT_JS} }})()"
    fingerprint = driver.execute_async_script(
        "var callback = arguments[arguments.length - 1];"
        f"(async () => {{ {FINGERPRINT_JS} }})().then(callback);"
    )

    output_path = "sandbox/fingerprint_real_chrome.json"
    with open(output_path, "w") as f:
        json.dump(fingerprint, f, indent=2, default=str)

    print(f"Fingerprint saved to {output_path}")
    for key, value in fingerprint.items():
        print(f"  {key}: {value}")

    return fingerprint


def main():
    print("Task #5: Chrome Remote Debugging test\n")

    chrome_options = Options()
    chrome_options.debugger_address = "127.0.0.1:9222"

    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("Connected to Chrome remote debugging!")
    except Exception as e:
        print(f"Failed to connect. Is Chrome running with --remote-debugging-port=9222 ?")
        print(f"  Launch it with: google-chrome --remote-debugging-port=9222")
        print(f"  Error: {e}")
        return

    try:
        success = step1_test_animelyrics(driver)

        if success:
            step2_extract_fingerprint(driver)
            print("\n=== SUCCESS ===")
            print("Remote Debugging works! Fingerprint saved for task #6.")
        else:
            print("\n=== FAILED ===")
            print("Remote Debugging did not bypass Cloudflare.")

    finally:
        # Don't quit - it's the user's browser!
        print("\n(Browser left open - it's your real Chrome)")


if __name__ == "__main__":
    main()
