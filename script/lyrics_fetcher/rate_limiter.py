"""Per-domain rate limiting and User-Agent rotation for lyrics fetching.

Provides thread-safe rate limiting between HTTP requests to the same domain,
cooldown handling after 429/403 responses, and a pool of realistic browser
User-Agent strings to reduce ban risk.

Persistent state: reads recent JSONL logs to honor cooldowns across runs.
"""

import json
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


DEFAULT_MIN_INTERVAL = 3.0   # seconds between requests to the same domain
COOLDOWN_429 = 60.0          # seconds to wait after a 429 response
COOLDOWN_403 = 30.0          # seconds to wait after a 403 response
JITTER_FACTOR = 0.5          # randomized fraction of base delay
HISTORY_WINDOW_HOURS = 24    # how far back to read JSONL logs

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]


def extract_domain(url: str) -> str:
    """Extract the lowercased domain (netloc) from a URL."""
    if not url:
        return ""
    return urlparse(url).netloc.lower()


def random_user_agent() -> str:
    """Return a random User-Agent string from the pool."""
    return random.choice(_USER_AGENTS)


def load_recent_fetch_history(log_dir, window_hours=HISTORY_WINDOW_HOURS) -> dict:
    """Read recent JSONL logs and extract per-domain fetch history.

    Reads today's and yesterday's log files. Returns a dict of
    {domain: {"last_fetch": float_timestamp, "cooldown_until": float_or_none}}.
    """
    log_dir = Path(log_dir)
    if not log_dir.exists():
        return {}

    today = date.today()
    dates_to_check = [today, today - timedelta(days=1)]
    cutoff = time.time() - (window_hours * 3600)

    history = {}

    for d in dates_to_check:
        path = log_dir / f"{d.isoformat()}.jsonl"
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                current_run_ts = None
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if record.get("type") == "run_header":
                        ts_str = record.get("timestamp", "")
                        try:
                            from datetime import datetime, timezone
                            dt = datetime.fromisoformat(ts_str)
                            current_run_ts = dt.timestamp()
                        except (ValueError, TypeError):
                            current_run_ts = None
                        continue

                    if record.get("type") != "fetch":
                        continue

                    url = record.get("url", "")
                    domain = extract_domain(url)
                    if not domain:
                        continue

                    # Use run timestamp as the fetch time approximation
                    fetch_ts = current_run_ts or time.time()
                    if fetch_ts < cutoff:
                        continue

                    entry = history.get(domain, {})
                    entry["last_fetch"] = max(entry.get("last_fetch", 0), fetch_ts)

                    http_status = record.get("http_status", 0)
                    if http_status == 429:
                        entry["cooldown_until"] = fetch_ts + COOLDOWN_429
                    elif http_status == 403:
                        existing_cd = entry.get("cooldown_until", 0)
                        new_cd = fetch_ts + COOLDOWN_403
                        entry["cooldown_until"] = max(existing_cd, new_cd)

                    history[domain] = entry
        except OSError:
            continue

    return history


@dataclass
class DomainPolicy:
    """Configurable rate-limiting policy per domain."""
    min_interval: float = DEFAULT_MIN_INTERVAL
    cooldown_429: float = COOLDOWN_429
    cooldown_403: float = COOLDOWN_403


class RateLimiter:
    """Thread-safe per-domain rate limiter with cooldown support.

    Reserves time slots under a lock before sleeping, so concurrent threads
    for the same domain serialize correctly without races.
    """

    def __init__(self, policy: Optional[DomainPolicy] = None,
                 log_dir: Optional[Path] = None):
        self._policy = policy or DomainPolicy()
        self._lock = threading.Lock()
        self._last_request: dict[str, float] = {}   # domain -> timestamp
        self._cooldown_until: dict[str, float] = {}  # domain -> timestamp

        # Load persistent state from JSONL logs
        if log_dir is not None:
            try:
                history = load_recent_fetch_history(log_dir)
                for domain, entry in history.items():
                    if "last_fetch" in entry:
                        self._last_request[domain] = entry["last_fetch"]
                    if "cooldown_until" in entry:
                        self._cooldown_until[domain] = entry["cooldown_until"]
            except Exception:
                pass  # graceful degradation

    def wait_for_domain(self, url: str) -> float:
        """Block until it is safe to make a request to this domain.

        Returns the actual wait time in seconds.
        """
        domain = extract_domain(url)
        with self._lock:
            wait = self._compute_wait(domain)
            # Reserve the time slot before releasing the lock
            self._last_request[domain] = time.time() + wait
        if wait > 0:
            time.sleep(wait)
        return wait

    def record_response(self, url: str, status_code: int) -> None:
        """Record a response status and trigger cooldowns for 429/403."""
        domain = extract_domain(url)
        with self._lock:
            if status_code == 429:
                self._cooldown_until[domain] = time.time() + self._policy.cooldown_429
            elif status_code == 403:
                self._cooldown_until[domain] = time.time() + self._policy.cooldown_403

    def get_user_agent(self) -> str:
        """Return a random User-Agent string."""
        return random_user_agent()

    def cooldown_remaining(self, url: str) -> float:
        """Return seconds remaining in cooldown for this domain, or 0."""
        domain = extract_domain(url)
        with self._lock:
            deadline = self._cooldown_until.get(domain, 0)
            remaining = deadline - time.time()
            return max(0.0, remaining)

    def time_since_last_request(self, url: str) -> Optional[float]:
        """Return seconds since last request to this domain, or None if never."""
        domain = extract_domain(url)
        with self._lock:
            last = self._last_request.get(domain)
            if last is None:
                return None
            return time.time() - last

    def _compute_wait(self, domain: str) -> float:
        """Compute how long to wait before the next request to this domain.

        Must be called while holding self._lock.
        """
        now = time.time()
        wait = 0.0

        # Cooldown check
        cooldown_deadline = self._cooldown_until.get(domain, 0)
        if cooldown_deadline > now:
            wait = max(wait, cooldown_deadline - now)

        # Min interval check
        last = self._last_request.get(domain)
        if last is not None:
            elapsed = now - last
            if elapsed < self._policy.min_interval:
                interval_wait = self._policy.min_interval - elapsed
                wait = max(wait, interval_wait)

        # Add jitter
        if wait > 0:
            jitter = random.uniform(0, wait * JITTER_FACTOR)
            wait += jitter

        return wait
