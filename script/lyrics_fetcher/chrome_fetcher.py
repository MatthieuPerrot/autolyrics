"""Cloudflare bypass via Xvfb + Chrome subprocess + Selenium Remote Debugging.

Chrome is launched as a regular subprocess (no ChromeDriver involvement at launch),
which makes it indistinguishable from a real user browser. Selenium connects
afterwards via the remote debugging protocol for page interaction.
"""

import socket
import subprocess
import tempfile
import time

import requests
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def _find_free_port():
    """Find a random available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port, timeout=10):
    """Wait until a TCP port is accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


class ChromeFetcher:
    """Context manager that lazily starts a real Chrome browser for Cloudflare bypass.

    Chrome is only launched on the first call to fetch(), so if no scraper
    needs it the overhead is zero.

    Usage::

        with ChromeFetcher() as cf:
            html = cf.fetch("https://example.com")
    """

    def __init__(self):
        self._display = None
        self._chrome_proc = None
        self._driver = None
        self._port = None
        self._user_data_dir = None
        self._started = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

    def start(self):
        """Launch Xvfb display and Chrome subprocess, then connect Selenium."""
        if self._started:
            return

        self._port = _find_free_port()

        # Virtual display
        self._display = Display(visible=False, size=(1920, 1200))
        self._display.start()

        # Separate user-data-dir so Chrome starts a new instance even if
        # another Chrome is already running.
        self._user_data_dir = tempfile.mkdtemp(prefix="chrome_fetcher_")

        # Launch Chrome directly (no ChromeDriver)
        chrome_cmd = [
            "google-chrome",
            f"--remote-debugging-port={self._port}",
            f"--user-data-dir={self._user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1920,1200",
            "about:blank",
        ]
        self._chrome_proc = subprocess.Popen(
            chrome_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if not _wait_for_port(self._port):
            self.stop()
            raise RuntimeError("Chrome did not start in time")

        # Connect Selenium via remote debugging (no ChromeDriver launch)
        opts = Options()
        opts.debugger_address = f"127.0.0.1:{self._port}"
        self._driver = webdriver.Chrome(options=opts)

        self._started = True
        print(f"🌐 ChromeFetcher started (port {self._port})")

    def stop(self):
        """Shut down driver, Chrome process, and virtual display."""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

        if self._chrome_proc:
            try:
                self._chrome_proc.terminate()
                self._chrome_proc.wait(timeout=5)
            except Exception:
                pass
            self._chrome_proc = None

        if self._display:
            try:
                self._display.stop()
            except Exception:
                pass
            self._display = None

        if self._user_data_dir:
            import shutil
            try:
                shutil.rmtree(self._user_data_dir)
            except Exception:
                pass
            self._user_data_dir = None

        self._started = False

    def _is_cloudflare_challenge(self, page_source):
        """Check if the page is a Cloudflare challenge/waiting page."""
        return "Just a moment" in page_source or "challenge-platform" in page_source

    def fetch(self, url, timeout=60, poll_interval=5):
        """Navigate to *url*, poll until Cloudflare resolves or timeout.

        Lazily starts Chrome on the first call.  Returns None if stop() is
        called from another thread while fetching.
        """
        if not self._started:
            self.start()

        try:
            driver = self._driver
            if driver is None:
                return None
            driver.get(url)

            deadline = time.time() + timeout
            while time.time() < deadline:
                driver = self._driver
                if driver is None:
                    return None
                page_source = driver.page_source
                if not self._is_cloudflare_challenge(page_source):
                    return page_source
                time.sleep(poll_interval)
        except Exception as e:
            print(f"⚠️  ChromeFetcher error on {url}: {e}")
            return None

        print(f"⚠️  ChromeFetcher: Cloudflare still blocking after {timeout}s")
        return None


def fetch_with_chrome_fallback(url, chrome_fetcher=None, headers=None):
    """Fetch a URL with requests, falling back to ChromeFetcher on HTTP 403.

    Returns the HTML content as a string, or None on failure.
    """
    try:
        if headers is None:
            headers = {"User-Agent": "Mozilla/5.0 (lyrics-scraper)"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 403 and chrome_fetcher is not None:
            print(f"⚠️  HTTP 403 on {url}, retrying with ChromeFetcher...")
            return chrome_fetcher.fetch(url)
        resp.raise_for_status()
        return resp.text
    except requests.exceptions.HTTPError:
        if chrome_fetcher is not None:
            print(f"⚠️  HTTP error on {url}, retrying with ChromeFetcher...")
            return chrome_fetcher.fetch(url)
        return None
    except Exception as e:
        print(f"❌ fetch_with_chrome_fallback error: {e}")
        return None
