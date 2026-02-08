"""Expanded fingerprint diffing via bot.sannysoft.com (task #6)

1. Patch chromedriver binary to remove $cdc_ signature
2. Collect bot detection results from real Chrome (Remote Debugging) and Selenium
3. Diff the two
"""

import json
import os
import re
import shutil
import sys
import time

from bs4 import BeautifulSoup


def patch_chromedriver(driver_path):
    """Patch chromedriver binary to rename $cdc_ variable."""
    patched_path = driver_path + ".patched"

    if os.path.exists(patched_path):
        print(f"  Using existing patched binary: {patched_path}")
        return patched_path

    print(f"  Patching: {driver_path}")
    shutil.copy2(driver_path, patched_path)

    with open(patched_path, "r+b") as f:
        data = f.read()
        # Replace $cdc_ with $abc_ (same length)
        count = data.count(b"$cdc_")
        if count > 0:
            data = data.replace(b"$cdc_", b"$abc_")
            f.seek(0)
            f.write(data)
            f.truncate()
            print(f"  Patched {count} occurrence(s) of $cdc_")
        else:
            print(f"  No $cdc_ found in binary (already clean or different version)")

    os.chmod(patched_path, 0o755)
    return patched_path


def collect_sannysoft(driver, label):
    """Navigate to bot.sannysoft.com and collect all test results."""
    print(f"\n--- Collecting bot.sannysoft.com [{label}] ---")
    driver.get("https://bot.sannysoft.com/")
    time.sleep(5)  # Wait for all tests to run

    # Extract results from the page
    results = driver.execute_script("""
        var results = {};
        var tables = document.querySelectorAll('table');
        tables.forEach(function(table) {
            var rows = table.querySelectorAll('tr');
            rows.forEach(function(row) {
                var cells = row.querySelectorAll('td');
                if (cells.length >= 2) {
                    var key = cells[0].textContent.trim();
                    var value = cells[1].textContent.trim();
                    var failed = cells[1].classList.contains('failed') ||
                                 cells[1].style.backgroundColor === 'red' ||
                                 cells[1].style.backgroundColor === '#ff0000';
                    results[key] = {value: value, failed: failed};
                }
            });
        });
        return results;
    """)

    print(f"  Collected {len(results)} properties")
    return results


def diff_results(real, selenium):
    """Diff bot.sannysoft.com results between real Chrome and Selenium."""
    all_keys = sorted(set(list(real.keys()) + list(selenium.keys())))
    diffs = []

    for key in all_keys:
        r = real.get(key, {})
        s = selenium.get(key, {})
        rv = r.get("value", "<missing>")
        sv = s.get("value", "<missing>")
        rf = r.get("failed", None)
        sf = s.get("failed", None)

        if rv != sv or rf != sf:
            status = "CRITICAL" if sf and not rf else "DIFF"
            diffs.append({
                "property": key,
                "status": status,
                "real": {"value": rv, "failed": rf},
                "selenium": {"value": sv, "failed": sf},
            })
            marker = "!!!" if status == "CRITICAL" else "   "
            print(f"  {marker} {status}  {key}")
            print(f"           Real:     {rv} (failed={rf})")
            print(f"           Selenium: {sv} (failed={sf})")
        else:
            print(f"       OK   {key}: {rv}")

    return diffs


def main():
    print("Task #6: Expanded fingerprint diffing via bot.sannysoft.com\n")

    # ===== Phase 1: Real Chrome via Remote Debugging =====
    print("=== Phase 1: Real Chrome (Remote Debugging) ===")
    print("Connecting to Chrome on port 9222...")

    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium import webdriver

    opts = ChromeOptions()
    opts.debugger_address = "127.0.0.1:9222"

    try:
        driver_real = webdriver.Chrome(options=opts)
        print("Connected!")
    except Exception as e:
        print(f"ERROR: Is Chrome running with --remote-debugging-port=9222 ?")
        print(f"  {e}")
        return

    real_results = collect_sannysoft(driver_real, "Real Chrome")
    # Don't quit the user's browser

    with open("sandbox/sannysoft_real_chrome.json", "w") as f:
        json.dump(real_results, f, indent=2, default=str)
    print("  Saved to sandbox/sannysoft_real_chrome.json")

    # ===== Phase 2: Patched Selenium =====
    print("\n=== Phase 2: Patched Selenium (Xvfb) ===")

    from pyvirtualdisplay import Display
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    # Get and patch chromedriver
    driver_path = ChromeDriverManager().install()
    patched_path = patch_chromedriver(driver_path)

    # Load real fingerprint for JS patches
    with open("sandbox/fingerprint_real_chrome.json") as f:
        real_fp = json.load(f)

    # Virtual display matching real screen
    screen_w = real_fp.get("screen.width", 1920)
    screen_h = real_fp.get("screen.height", 1200)
    display = Display(visible=False, size=(screen_w, screen_h))
    display.start()
    print(f"  Virtual display: {screen_w}x{screen_h}")

    chrome_options = ChromeOptions()
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
    driver_sel = webdriver.Chrome(service=service, options=chrome_options)

    # Apply JS patches from real fingerprint
    langs = json.dumps(real_fp.get("navigator.languages", []))
    plugins_len = real_fp.get("navigator.plugins.length", 0)
    hw = real_fp.get("navigator.hardwareConcurrency", 4)
    mem = real_fp.get("navigator.deviceMemory", 8)
    real_vendor = json.dumps(real_fp.get("webgl_vendor", ""))
    real_renderer = json.dumps(real_fp.get("webgl_renderer", ""))

    patches_js = f"""
        Object.defineProperty(navigator, 'webdriver', {{get: () => false}});
        Object.defineProperty(navigator, 'languages', {{get: () => {langs}}});
        Object.defineProperty(navigator, 'plugins', {{get: () => [{",".join(["{}"] * plugins_len)}]}});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {hw}}});
        Object.defineProperty(navigator, 'deviceMemory', {{get: () => {mem}}});
        window.chrome = {{runtime: undefined}};
        (function() {{
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {{
                if (param === 37445) return {real_vendor};
                if (param === 37446) return {real_renderer};
                return getParameter.call(this, param);
            }};
        }})();
        const origQuery = navigator.permissions.query.bind(navigator.permissions);
        navigator.permissions.query = (params) =>
            params.name === 'notifications'
            ? Promise.resolve({{state: 'prompt', onchange: null}})
            : origQuery(params);
    """
    driver_sel.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": patches_js
    })

    try:
        sel_results = collect_sannysoft(driver_sel, "Patched Selenium")
        with open("sandbox/sannysoft_selenium.json", "w") as f:
            json.dump(sel_results, f, indent=2, default=str)
        print("  Saved to sandbox/sannysoft_selenium.json")

    finally:
        driver_sel.quit()
        display.stop()

    # ===== Phase 3: Diff =====
    print("\n\n=== Phase 3: DIFF ===\n")
    diffs = diff_results(real_results, sel_results)

    with open("sandbox/sannysoft_diff.json", "w") as f:
        json.dump(diffs, f, indent=2, default=str)

    critical = [d for d in diffs if d["status"] == "CRITICAL"]
    print(f"\n--- {len(diffs)} difference(s), {len(critical)} CRITICAL ---")
    print("Diff saved to sandbox/sannysoft_diff.json")

    if critical:
        print("\nCRITICAL differences (Selenium detected as bot):")
        for d in critical:
            print(f"  - {d['property']}: {d['selenium']['value']}")


if __name__ == "__main__":
    main()
