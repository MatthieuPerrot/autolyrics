# Cloudflare Bypass Strategies for animelyrics.com

## Context

animelyrics.com uses advanced Cloudflare protection ("Bot Fight Mode" or higher) that blocks automated scraping. This prevents our scraper from fetching romaji lyrics from one of the best sources for Japanese song lyrics.

### What has been tested and failed
- `requests` with custom User-Agent: **403 Forbidden**
- `cloudscraper`: **403 Forbidden**
- Selenium headless (standard): **Blocked** (Cloudflare JS challenge not resolved)
- Selenium headless + anti-detection (navigator.webdriver override, excludeSwitches, etc.): **Blocked**
- Selenium non-headless + Xvfb: **Blocked** (Cloudflare detects Selenium beyond headless flag)
- Direct `.txt` URLs: **403 Forbidden** (same Cloudflare protection as `.htm`)

### What works
- Manual browser access: the page loads fine after Cloudflare JS challenge auto-resolves (~5-10s, no captcha)
- The HTML structure is well-suited for scraping (clear `class="romaji"` and `class="translation"` separation)

---

## Approach 1: Direct `.txt` URLs

animelyrics.com exposes lyrics in plain text via predictable URLs:
- HTML: `https://www.animelyrics.com/jpop/twomix/whitereflection.htm`
- TXT: `https://www.animelyrics.com/jpop/twomix/whitereflection.txt`

**Hypothesis**: The `.txt` endpoint might have lighter or no Cloudflare protection since it serves plain text rather than HTML.

**Test plan**:
1. Try fetching the `.txt` URL with cloudscraper
2. If it works, parse the plain text format
3. Adapt the scraper to prefer `.txt` URLs when available

**Pros**: Simplest approach, no extra dependencies
**Cons**: May still be blocked; text format may differ from HTML structure

---

## Approach 2: Reuse browser Cloudflare cookies

When a user accesses animelyrics.com in their browser, Cloudflare sets a `cf_clearance` cookie after the JS challenge is resolved. This cookie could be extracted and reused in automated requests.

**Test plan**:
1. Extract `cf_clearance` cookie from user's browser (Firefox/Chrome)
2. Pass it to cloudscraper/requests along with the matching User-Agent
3. Verify the cookie grants access to the page

**Pros**: No extra infrastructure, uses existing browser session
**Cons**: Cookie expires (typically 30min-2h); requires user to have visited the site recently; browser-specific extraction

---

## Approach 3: Selenium non-headless mode

Cloudflare sometimes blocks headless browsers specifically. Running Selenium in visible (non-headless) mode may allow the JS challenge to resolve naturally.

**Test plan**:
1. Launch Selenium without `--headless` flag
2. Navigate to animelyrics URL
3. Wait for Cloudflare challenge to resolve
4. Scrape the page content

**Pros**: Higher chance of bypassing Cloudflare; no external services
**Cons**: Requires a display (X11/Wayland); not suitable for headless servers; slower; user sees browser window

---

## Approach 4: Observe real browser behavior

Have the user describe or screenshot what happens when accessing the site:
- Does Cloudflare show a JS challenge that auto-resolves?
- Is there a CAPTCHA?
- How long does the challenge take?

This information would help design a more targeted Selenium strategy (e.g., specific wait conditions, cookie handling, etc.).

**Pros**: Better understanding leads to better solutions
**Cons**: Requires user involvement; may not lead to a programmatic solution

---

## Approach 5: Chrome Remote Debugging

Connect Selenium to an existing real Chrome instance instead of launching a new one. The browser is the user's real Chrome, so Cloudflare sees a genuine fingerprint.

**How it works**:
1. User launches Chrome once with `google-chrome --remote-debugging-port=9222`
2. Selenium connects to this instance via `debugger_address` option
3. Cloudflare sees a real Chrome (not Selenium-launched), JS challenge auto-resolves
4. Scraper accesses page content through the real browser

**Test plan**:
1. Launch Chrome with remote debugging
2. Connect Selenium via `debugger_address`
3. Navigate to animelyrics and wait for Cloudflare to resolve
4. Verify romaji blocks are accessible

**Pros**: Cloudflare sees real Chrome; no fingerprint patching needed; challenge auto-resolves
**Cons**: Requires Chrome running in background; ties scraper to a running browser instance

---

## Approach 6: Fingerprint diffing strategy

Systematically identify and patch all differences between a real Chrome and Selenium to make them indistinguishable.

**Strategy**:
1. **Compare**: Open a bot-detection site (e.g. `bot.sannysoft.com`) in real Chrome AND in Selenium, diff the results
2. **Identify**: Find all properties that differ (known suspects: `navigator.webdriver`, `window.cdc_*`, `navigator.plugins`, CDP traces, stack traces, WebGL/Canvas fingerprint)
3. **Patch**: Fix each difference via `execute_cdp_cmd` or by modifying the ChromeDriver binary
4. **Validate**: Test on animelyrics

**Note**: This is what `undetected-chromedriver` does automatically. We have it installed but had a version mismatch (ChromeDriver 145 vs Chrome 135). Fixing the version could be the simplest path.

**Pros**: Permanent solution once fingerprint is matched; works headless
**Cons**: Needs initial research; may break on Cloudflare updates (rare)

---

## Decision criteria

| Criterion              | 1: .txt URLs | 2: Cookies | 3: Non-headless | 4: Observe | 5: Remote Debug | 6: Fingerprint |
|------------------------|:---:|:---:|:---:|:---:|:---:|:---:|
| Ease of implementation | High | Medium | Medium | Low | Medium | Low |
| Reliability            | N/A (failed) | Low (expiry) | N/A (failed) | N/A | High | High |
| No extra dependencies  | Yes | Yes | Xvfb | No | Chrome instance | Research |
| Works headless         | Yes | Yes | N/A (failed) | N/A | No (needs Chrome) | Yes |
| Sustainable long-term  | N/A | No | N/A | N/A | Yes | Yes |
| **Status**             | **KO** | Untested | **KO** | Done | **Untested** | **Untested** |
