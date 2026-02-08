# Sandbox - Cloudflare Bypass Experiments

Scripts and data for testing and comparing browser fingerprints to bypass Cloudflare bot detection on animelyrics.com.

## Scripts

| Script | Description |
|--------|-------------|
| `test_remote_debug_animelyrics.py` | Chrome Remote Debugging fingerprint extraction: captures browser properties (webdriver, WebGL, plugins) and saves to JSON |
| `test_fingerprint_selenium.py` | Generates anti-detection JS patches from real Chrome fingerprint, tests fingerprint matching real vs Selenium |
| `test_patched_selenium.py` | Patches chromedriver binary (`$cdc_` variable), applies CDP overrides, tests animelyrics bypass |
| `test_sannysoft_diff.py` | Compares real Chrome vs patched Selenium on bot.sannysoft.com, identifies critical detection failures |
| `test_xvfb_animelyrics.py` | Non-headless Selenium on Xvfb with basic navigator patches |
| `test_xvfb_remote_debug.py` | Chrome subprocess + Xvfb + Selenium remote debugging (no ChromeDriver at launch) — basis for `chrome_fetcher.py` |

## Data

| File | Description |
|------|-------------|
| `fingerprint_real_chrome.json` | Fingerprint captured from real Chrome session |
| `fingerprint_selenium.json` | Fingerprint from patched Selenium |
| `fingerprint_diff.json` | Diff of the two fingerprints — 8 differences, 16 matches |
| `sannysoft_real_chrome.json` | bot.sannysoft.com results from real Chrome (all pass) |
| `sannysoft_selenium.json` | bot.sannysoft.com results from patched Selenium (2 critical failures) |
| `sannysoft_diff.json` | Diff of sannysoft results |

## Key Findings

From `fingerprint_diff.json` — differences between real Chrome and Xvfb/Selenium Chrome:

| Property | Real Chrome | Xvfb/Selenium |
|----------|-------------|---------------|
| `webgl_renderer` | AMD Radeon (OpenGL 4.6) | SwiftShader (software) |
| `webgl_vendor` | Google Inc. (AMD) | Google Inc. (Google) |
| `window.chrome.runtime` | `false` | `true` |
| `window.innerWidth` | 1920 | 945 |
| `window.innerHeight` | 1081 | 973 |
| `window.outerWidth` | 1920 | 945 |
| `window.outerHeight` | 1168 | 1060 |
| `screen.height` | 1200 | 1080 |

From `sannysoft_diff.json` — 2 critical failures:

- **PluginArray**: `navigator.plugins` is serialized as an array `[{},...]` instead of a PluginArray object `{"0":{...},...}`
- **WebDriver (New)**: `navigator.webdriver` is `present` (should be `missing`)
