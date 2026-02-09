"""Lightweight Selenium fetcher using headless ChromeDriver (no Xvfb needed)."""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


class SeleniumFetcher:
    """Context manager for headless ChromeDriver sessions.

    Lighter than ChromeFetcher: uses standard ChromeDriver in headless mode,
    suitable for sites that need JS rendering but don't have aggressive
    Cloudflare protection.

    Usage::

        with SeleniumFetcher() as sf:
            html = sf.fetch("https://example.com")
    """

    def __init__(self):
        self._driver = None
        self._started = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

    def start(self):
        """Launch headless ChromeDriver. Called lazily on first fetch()."""
        if self._started:
            return

        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1200")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        self._driver = webdriver.Chrome(options=opts)
        self._started = True
        print("🌐 SeleniumFetcher started (headless ChromeDriver)")

    def stop(self):
        """Shut down the ChromeDriver session."""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
        self._started = False

    def fetch(self, url, timeout=15):
        """Navigate to *url* and return page source.

        Lazily starts ChromeDriver on the first call.  Returns None if stop()
        is called from another thread while fetching.

        Returns:
            Page HTML as string, or None on failure.
        """
        if not self._started:
            self.start()

        try:
            driver = self._driver
            if driver is None:
                return None
            driver.set_page_load_timeout(timeout)
            driver.get(url)
            driver = self._driver
            if driver is None:
                return None
            return driver.page_source
        except Exception as e:
            print(f"❌ SeleniumFetcher error on {url}: {e}")
            return None
