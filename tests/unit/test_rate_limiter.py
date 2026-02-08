"""Unit tests for the rate_limiter module.

Tests cover: domain extraction, user-agent rotation, per-domain rate limiting,
HTTP status cooldowns, JSONL history loading, thread safety, and public accessors.
"""

import json
import os
import threading
import time
from pathlib import Path
from unittest.mock import patch

from lyrics_fetcher.rate_limiter import (
    DEFAULT_MIN_INTERVAL,
    COOLDOWN_429,
    COOLDOWN_403,
    HISTORY_WINDOW_HOURS,
    DomainPolicy,
    RateLimiter,
    extract_domain,
    load_recent_fetch_history,
    random_user_agent,
)

from tests.helpers.assertions import (
    assert_equal,
    assert_greater,
    assert_greater_equal,
    assert_in,
    assert_is_none,
    assert_is_not_none,
    assert_isinstance,
    assert_less,
    assert_true,
    assert_false,
    assert_len,
)


# ---------------------------------------------------------------------------
# extract_domain
# ---------------------------------------------------------------------------

class TestExtractDomain:

    def test_https_url(self):
        result = extract_domain("https://www.example.com/path")
        assert_equal(result, "www.example.com")

    def test_http_url(self):
        result = extract_domain("http://lyrics.example.org/page")
        assert_equal(result, "lyrics.example.org")

    def test_lowercases_domain(self):
        result = extract_domain("https://WWW.EXAMPLE.COM/Path")
        assert_equal(result, "www.example.com")

    def test_empty_string(self):
        result = extract_domain("")
        assert_equal(result, "")


# ---------------------------------------------------------------------------
# random_user_agent
# ---------------------------------------------------------------------------

class TestRandomUserAgent:

    def test_returns_string(self):
        ua = random_user_agent()
        assert_isinstance(ua, str)
        assert_greater(len(ua), 10, "user agent should be a realistic browser string")

    def test_varies_across_calls(self):
        """Multiple calls should eventually produce different UAs."""
        agents = {random_user_agent() for _ in range(50)}
        assert_greater(len(agents), 1, "user agent pool should have variety")


# ---------------------------------------------------------------------------
# RateLimiter.wait_for_domain
# ---------------------------------------------------------------------------

class TestWaitForDomain:

    def test_first_request_no_wait(self):
        limiter = RateLimiter()
        t0 = time.time()
        waited = limiter.wait_for_domain("https://example.com/page1")
        elapsed = time.time() - t0
        assert_less(elapsed, 0.5, "first request should not wait")
        assert_less(waited, 0.1)

    def test_same_domain_waits(self):
        limiter = RateLimiter(policy=DomainPolicy(min_interval=1.0))
        limiter.wait_for_domain("https://example.com/page1")
        t0 = time.time()
        waited = limiter.wait_for_domain("https://example.com/page2")
        elapsed = time.time() - t0
        assert_greater_equal(elapsed, 0.5, "second request to same domain should wait")
        assert_greater_equal(waited, 0.5)

    def test_different_domains_no_interference(self):
        limiter = RateLimiter(policy=DomainPolicy(min_interval=2.0))
        limiter.wait_for_domain("https://alpha.example.com/page")
        t0 = time.time()
        waited = limiter.wait_for_domain("https://beta.example.com/page")
        elapsed = time.time() - t0
        assert_less(elapsed, 0.5, "different domains should not interfere")
        assert_less(waited, 0.1)


# ---------------------------------------------------------------------------
# RateLimiter.record_response
# ---------------------------------------------------------------------------

class TestRecordResponse:

    def test_429_triggers_cooldown(self):
        limiter = RateLimiter()
        limiter.record_response("https://example.com/page", 429)
        remaining = limiter.cooldown_remaining("https://example.com/any")
        assert_greater(remaining, 0.0, "429 should trigger cooldown")
        assert_greater(remaining, COOLDOWN_403,
                       "429 cooldown should be longer than 403 cooldown")

    def test_403_triggers_cooldown(self):
        limiter = RateLimiter()
        limiter.record_response("https://example.com/page", 403)
        remaining = limiter.cooldown_remaining("https://example.com/any")
        assert_greater(remaining, 0.0, "403 should trigger cooldown")

    def test_200_no_cooldown(self):
        limiter = RateLimiter()
        limiter.record_response("https://example.com/page", 200)
        remaining = limiter.cooldown_remaining("https://example.com/any")
        assert_less(remaining, 0.1, "200 should not trigger cooldown")

    def test_429_cooldown_longer_than_403(self):
        assert_greater(COOLDOWN_429, COOLDOWN_403,
                       "429 cooldown constant should exceed 403 cooldown constant")


# ---------------------------------------------------------------------------
# load_recent_fetch_history
# ---------------------------------------------------------------------------

class TestLoadHistory:

    def test_reads_fetch_events(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        from datetime import date, datetime, timezone
        today = date.today().isoformat()
        now_iso = datetime.now(timezone.utc).isoformat()
        log_file = log_dir / f"{today}.jsonl"
        records = [
            json.dumps({"type": "run_header", "title": "t", "artists": ["a"],
                         "timestamp": now_iso,
                         "total_duration": 1.0}),
            json.dumps({"type": "fetch", "source_name": "src",
                         "fetcher_type": "requests", "url": "https://example.com/p",
                         "phase": 1, "duration": 0.5, "http_status": 200,
                         "fetch_ok": True, "parse_ok": True, "lyrics_length": 100}),
        ]
        log_file.write_text("\n".join(records) + "\n", encoding="utf-8")

        history = load_recent_fetch_history(log_dir, window_hours=24)
        assert_in("example.com", history)

    def test_records_429_cooldown_from_history(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        from datetime import date, datetime, timezone
        today = date.today().isoformat()
        now_iso = datetime.now(timezone.utc).isoformat()
        log_file = log_dir / f"{today}.jsonl"
        records = [
            json.dumps({"type": "run_header", "title": "t", "artists": ["a"],
                         "timestamp": now_iso,
                         "total_duration": 1.0}),
            json.dumps({"type": "fetch", "source_name": "src",
                         "fetcher_type": "requests", "url": "https://rate-limited.com/p",
                         "phase": 1, "duration": 0.5, "http_status": 429,
                         "fetch_ok": False, "parse_ok": False, "lyrics_length": 0}),
        ]
        log_file.write_text("\n".join(records) + "\n", encoding="utf-8")

        history = load_recent_fetch_history(log_dir, window_hours=24)
        assert_in("rate-limited.com", history)
        entry = history["rate-limited.com"]
        assert_is_not_none(entry.get("cooldown_until"),
                           "429 in history should set cooldown_until")

    def test_ignores_old_runs(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        # Write a log file from 3 days ago
        from datetime import date, timedelta
        old_date = (date.today() - timedelta(days=3)).isoformat()
        log_file = log_dir / f"{old_date}.jsonl"
        records = [
            json.dumps({"type": "fetch", "source_name": "src",
                         "fetcher_type": "requests", "url": "https://old.example.com/p",
                         "phase": 1, "duration": 0.5, "http_status": 200,
                         "fetch_ok": True, "parse_ok": True, "lyrics_length": 100}),
        ]
        log_file.write_text("\n".join(records) + "\n", encoding="utf-8")

        history = load_recent_fetch_history(log_dir, window_hours=24)
        assert_equal(len(history), 0, "old log files should be ignored")

    def test_handles_missing_dir(self, tmp_path):
        log_dir = tmp_path / "nonexistent"
        history = load_recent_fetch_history(log_dir, window_hours=24)
        assert_equal(len(history), 0, "missing dir should return empty dict")


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety:

    def test_concurrent_requests_same_domain(self):
        """5 concurrent threads for the same domain should all complete without error."""
        limiter = RateLimiter(policy=DomainPolicy(min_interval=0.1))
        results = []
        errors = []

        def worker():
            try:
                w = limiter.wait_for_domain("https://example.com/page")
                results.append(w)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert_len(errors, 0, f"no errors expected, got: {errors}")
        assert_len(results, 5, "all 5 threads should complete")


# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------

class TestTimeSinceLastRequest:

    def test_none_when_never_requested(self):
        limiter = RateLimiter()
        result = limiter.time_since_last_request("https://never.example.com/p")
        assert_is_none(result, "should be None for a domain never requested")

    def test_positive_after_request(self):
        limiter = RateLimiter()
        limiter.wait_for_domain("https://example.com/page")
        time.sleep(0.05)
        result = limiter.time_since_last_request("https://example.com/other")
        assert_is_not_none(result)
        assert_greater(result, 0.0, "should be positive after a request")


class TestCooldownRemaining:

    def test_zero_when_no_cooldown(self):
        limiter = RateLimiter()
        remaining = limiter.cooldown_remaining("https://example.com/p")
        assert_less(remaining, 0.1)

    def test_positive_after_429(self):
        limiter = RateLimiter()
        limiter.record_response("https://example.com/p", 429)
        remaining = limiter.cooldown_remaining("https://example.com/any")
        assert_greater(remaining, 0.0)


# ---------------------------------------------------------------------------
# DomainPolicy defaults
# ---------------------------------------------------------------------------

class TestDomainPolicy:

    def test_default_values(self):
        policy = DomainPolicy()
        assert_equal(policy.min_interval, DEFAULT_MIN_INTERVAL)
        assert_equal(policy.cooldown_429, COOLDOWN_429)
        assert_equal(policy.cooldown_403, COOLDOWN_403)

    def test_custom_values(self):
        policy = DomainPolicy(min_interval=5.0, cooldown_429=120.0, cooldown_403=60.0)
        assert_equal(policy.min_interval, 5.0)
        assert_equal(policy.cooldown_429, 120.0)
        assert_equal(policy.cooldown_403, 60.0)
