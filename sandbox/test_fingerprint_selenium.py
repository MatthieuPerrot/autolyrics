"""Collect Selenium fingerprint, diff with real Chrome, and test patching (task #6)

Reads sandbox/fingerprint_real_chrome.json to dynamically generate anti-detection patches.
"""

import json
import sys

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


FINGERPRINT_JS = """
return {
    'navigator.webdriver': navigator.webdriver,
    'navigator.userAgent': navigator.userAgent,
    'navigator.platform': navigator.platform,
    'navigator.languages': navigator.languages,
    'navigator.plugins.length': navigator.plugins.length,
    'navigator.hardwareConcurrency': navigator.hardwareConcurrency,
    'navigator.deviceMemory': navigator.deviceMemory,
    'navigator.maxTouchPoints': navigator.maxTouchPoints,

    'window.chrome': !!window.chrome,
    'window.chrome.runtime': !!(window.chrome && window.chrome.runtime),
    'window.chrome.runtime.id': !!(window.chrome && window.chrome.runtime && window.chrome.runtime.id),

    'document.__selenium_unwrapped': !!document.__selenium_unwrapped,
    'document.__webdriver_evaluate': !!document.__webdriver_evaluate,
    'document.__driver_evaluate': !!document.__driver_evaluate,

    'window.outerWidth': window.outerWidth,
    'window.outerHeight': window.outerHeight,
    'window.innerWidth': window.innerWidth,
    'window.innerHeight': window.innerHeight,
    'screen.width': screen.width,
    'screen.height': screen.height,

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

    'permissions_query': await navigator.permissions.query({name: 'notifications'}).then(r => r.state).catch(() => 'error'),

    'has_cdc': (function() {
        for (var key in document) {
            if (key.match(/^cdc_|\\$cdc_|\\$chrome_/)) return key;
        }
        return false;
    })(),
}
"""


def load_real_fingerprint():
    """Load the real Chrome fingerprint collected via Remote Debugging."""
    path = "sandbox/fingerprint_real_chrome.json"
    with open(path) as f:
        return json.load(f)


def build_patches_js(real_fp):
    """Generate JavaScript patches from the real Chrome fingerprint."""
    patches = []

    # navigator.webdriver
    if real_fp.get("navigator.webdriver") is False:
        patches.append(
            "Object.defineProperty(navigator, 'webdriver', {get: () => false});"
        )

    # navigator.languages
    langs = real_fp.get("navigator.languages")
    if langs:
        patches.append(
            f"Object.defineProperty(navigator, 'languages', "
            f"{{get: () => {json.dumps(langs)}}});"
        )

    # navigator.plugins.length
    plugins_len = real_fp.get("navigator.plugins.length", 0)
    if plugins_len > 0:
        fake_plugins = ", ".join(["{}"] * plugins_len)
        patches.append(
            f"Object.defineProperty(navigator, 'plugins', "
            f"{{get: () => [{fake_plugins}]}});"
        )

    # navigator.hardwareConcurrency
    hw = real_fp.get("navigator.hardwareConcurrency")
    if hw:
        patches.append(
            f"Object.defineProperty(navigator, 'hardwareConcurrency', "
            f"{{get: () => {hw}}});"
        )

    # navigator.deviceMemory
    mem = real_fp.get("navigator.deviceMemory")
    if mem:
        patches.append(
            f"Object.defineProperty(navigator, 'deviceMemory', "
            f"{{get: () => {mem}}});"
        )

    # window.chrome
    if real_fp.get("window.chrome"):
        patches.append("window.chrome = {runtime: {}};")

    # permissions
    if real_fp.get("permissions_query") == "prompt":
        patches.append(
            "const origQuery = navigator.permissions.query.bind(navigator.permissions);"
            "navigator.permissions.query = (params) => "
            "params.name === 'notifications' "
            "? Promise.resolve({state: 'prompt', onchange: null}) "
            ": origQuery(params);"
        )

    return "\n".join(patches)


def collect_fingerprint(driver):
    """Collect fingerprint from a running driver."""
    return driver.execute_async_script(
        "var callback = arguments[arguments.length - 1];"
        f"(async () => {{ {FINGERPRINT_JS} }})().then(callback);"
    )


def diff_fingerprints(real, selenium):
    """Compare two fingerprints and return differences."""
    all_keys = sorted(set(list(real.keys()) + list(selenium.keys())))
    diffs = []
    for key in all_keys:
        r = real.get(key, "<missing>")
        s = selenium.get(key, "<missing>")
        if str(r) != str(s):
            diffs.append((key, r, s))
            print(f"  DIFF  {key}")
            print(f"        Real:     {r}")
            print(f"        Selenium: {s}")
            print()
        else:
            print(f"  OK    {key}: {r}")
    return diffs


def main():
    print("Task #6: Fingerprint diffing\n")

    # Load real fingerprint
    real_fp = load_real_fingerprint()
    print(f"Loaded real Chrome fingerprint ({len(real_fp)} properties)")

    # Generate patches from real fingerprint
    patches_js = build_patches_js(real_fp)
    print(f"\nGenerated patches:\n{patches_js}\n")

    # Launch Selenium with Xvfb
    display = Display(visible=False, size=(1920, 1080))
    display.start()

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        f"--user-agent={real_fp.get('navigator.userAgent', '')}"
    )
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Apply dynamic patches from real fingerprint
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": patches_js
    })

    try:
        # Step 1: Collect Selenium fingerprint
        print("--- Step 1: Collect patched Selenium fingerprint ---")
        driver.get("about:blank")
        sel_fp = collect_fingerprint(driver)

        with open("sandbox/fingerprint_selenium.json", "w") as f:
            json.dump(sel_fp, f, indent=2, default=str)

        # Step 2: Diff
        print("\n--- Step 2: Diff ---\n")
        diffs = diff_fingerprints(real_fp, sel_fp)
        print(f"\n{len(diffs)} difference(s) out of {len(real_fp)} properties")

        # Save diff
        with open("sandbox/fingerprint_diff.json", "w") as f:
            json.dump({
                "differences": [
                    {"property": k, "real": r, "selenium": s}
                    for k, r, s in diffs
                ],
                "matching": [
                    k for k in real_fp
                    if str(real_fp.get(k)) == str(sel_fp.get(k))
                ]
            }, f, indent=2, default=str)

        print("Diff saved to sandbox/fingerprint_diff.json")

    finally:
        driver.quit()
        display.stop()

    return len(diffs)


if __name__ == "__main__":
    remaining = main()
    sys.exit(0 if remaining == 0 else 1)
