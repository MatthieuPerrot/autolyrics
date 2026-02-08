"""Integration tests for the per-source concurrent pipeline orchestrator.

All network calls are mocked. Tests exercise the full orchestrator logic:
search -> per-source pipelines (REQUESTS fast attempt, then escalation fetchers in parallel).
"""

import os
import sys
import time
import threading
from unittest.mock import patch, MagicMock

import pytest

from lyrics_fetcher.source_registry import Fetcher, LyricsSource, build_registry
from lyrics_fetcher.fallback import get_romaji_lyrics, _fetch_requests, _STATUS_403
from lyrics_fetcher.run_log import RunLog, SearchEvent, FetchEvent

from tests.helpers.assertions import (
    assert_contains_text,
    assert_equal,
    assert_false,
    assert_greater,
    assert_greater_equal,
    assert_in,
    assert_isinstance,
    assert_is_not_none,
    assert_len,
    assert_less,
    assert_not_in,
    assert_true,
)

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")

# Mock HTML that includes common test artist names so artist validation passes.
_MOCK_HTML = "<html><body>TWO-MIX ARTIST lyrics page</body></html>"


def _load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def _romaji_lyrics(source_name):
    """Generate acceptable romaji lyrics tagged with a source name marker."""
    return (
        f"lyrics_from_{source_name}\n"
        "Kaze ga fuiteiru machi no naka de\n"
        "Kimi no koe ga kikoeru yo\n"
        "Ano hi no yakusoku wa mada\n"
        "Boku no mune ni aru kara\n"
    )


# Minimal two-source registry for testing: one REQUESTS-only, one with escalation
def _build_test_registry(html_by_source=None, blocked_sources=None):
    """Build a small registry with controllable search/parse for testing.

    Args:
        html_by_source: dict of source_name -> HTML to return from parse
        blocked_sources: set of source_names that should return 403 on REQUESTS
    """
    html_by_source = html_by_source or {}
    blocked_sources = blocked_sources or set()

    def _make_search(name, urls):
        def search_fn(title, artists):
            return urls
        return search_fn

    def _make_parse(name, html_fixture):
        def parse_fn(html):
            if html == "BLOCKED":
                return None
            return _romaji_lyrics(name)
        return parse_fn

    sources = [
        LyricsSource(
            name="fast_source",
            search=_make_search("fast_source", ["http://fast.example.com/lyrics"]),
            parse=_make_parse("fast_source", None),
            fetchers=(Fetcher.REQUESTS,),
            romaji_quality=2,
        ),
        LyricsSource(
            name="quality_source",
            search=_make_search("quality_source", ["http://quality.example.com/lyrics"]),
            parse=_make_parse("quality_source", None),
            fetchers=(Fetcher.REQUESTS, Fetcher.SELENIUM, Fetcher.CHROME_FETCHER),
            romaji_quality=5,
        ),
    ]
    return sources


class TestPhase1Success:
    """REQUESTS succeeds for at least one source — no escalation needed."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    def test_returns_acceptable_lyrics_from_any_source(
        self, mock_fetch, mock_registry
    ):
        mock_registry.return_value = _build_test_registry()

        def fetch_side_effect(url):
            return (_MOCK_HTML, 200)

        mock_fetch.side_effect = fetch_side_effect

        result = get_romaji_lyrics("WHITE REFLECTION", ["TWO-MIX"])

        assert_is_not_none(result)
        # Concurrent: either source may win — both produce acceptable lyrics
        has_quality = "lyrics_from_quality_source" in result
        has_fast = "lyrics_from_fast_source" in result
        assert_true(
            has_quality or has_fast,
            "result should contain lyrics from one of the sources",
        )


class TestPhase1To2Escalation:
    """Phase 1 gets 403 on a source, Phase 2 (SELENIUM) succeeds."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.selenium_fetcher.SeleniumFetcher")
    def test_escalates_to_selenium_on_403(
        self, mock_selenium_cls, mock_fetch, mock_registry
    ):
        mock_registry.return_value = _build_test_registry()

        def fetch_side_effect(url):
            if "quality" in url:
                return (None, 403)
            if "fast" in url:
                return (None, 500)
            return (None, 0)

        mock_fetch.side_effect = fetch_side_effect

        # Selenium fetcher mock
        mock_sf = MagicMock()
        mock_sf.fetch.return_value = _MOCK_HTML
        mock_sf.__enter__ = MagicMock(return_value=mock_sf)
        mock_sf.__exit__ = MagicMock(return_value=False)
        mock_selenium_cls.return_value = mock_sf

        result = get_romaji_lyrics("WHITE REFLECTION", ["TWO-MIX"])

        assert_is_not_none(result)
        assert_contains_text(result, "lyrics_from_quality_source")
        mock_sf.fetch.assert_called()


class TestPhase1To3Escalation:
    """Phase 1 gets 403, Phase 2 also fails, Phase 3 (CHROME_FETCHER) succeeds."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.selenium_fetcher.SeleniumFetcher")
    @patch("lyrics_fetcher.chrome_fetcher.ChromeFetcher")
    def test_escalates_to_chrome_fetcher(
        self, mock_chrome_cls, mock_selenium_cls, mock_fetch, mock_registry
    ):
        mock_registry.return_value = _build_test_registry()

        def fetch_side_effect(url):
            return (None, 403) if "quality" in url else (None, 500)

        mock_fetch.side_effect = fetch_side_effect

        # Selenium also fails (returns None)
        mock_sf = MagicMock()
        mock_sf.fetch.return_value = None
        mock_sf.__enter__ = MagicMock(return_value=mock_sf)
        mock_sf.__exit__ = MagicMock(return_value=False)
        mock_selenium_cls.return_value = mock_sf

        # ChromeFetcher succeeds
        mock_cf = MagicMock()
        mock_cf.fetch.return_value = _MOCK_HTML
        mock_cf.__enter__ = MagicMock(return_value=mock_cf)
        mock_cf.__exit__ = MagicMock(return_value=False)
        mock_chrome_cls.return_value = mock_cf

        result = get_romaji_lyrics("WHITE REFLECTION", ["TWO-MIX"])

        assert_is_not_none(result)
        assert_contains_text(result, "lyrics_from_quality_source")
        mock_cf.fetch.assert_called()


class TestAllFail:
    """All phases fail — returns 'not found' message."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    def test_returns_not_found_message(self, mock_fetch, mock_registry):
        mock_registry.return_value = _build_test_registry()
        mock_fetch.return_value = (None, 500)

        result = get_romaji_lyrics("NONEXISTENT", ["NOBODY"])

        assert_is_not_none(result)
        assert_contains_text(result, "Paroles non trouvées")


class TestNoSearchResults:
    """No source returns any URLs — returns 'not found' immediately."""

    @patch("lyrics_fetcher.fallback.build_registry")
    def test_returns_not_found_when_no_urls(self, mock_registry):
        sources = [
            LyricsSource(
                name="empty",
                search=lambda t, a: [],
                parse=lambda h: None,
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=3,
            ),
        ]
        mock_registry.return_value = sources

        result = get_romaji_lyrics("MISSING", ["UNKNOWN"])

        assert_contains_text(result, "Paroles non trouvées")


class TestAllSourcesTried:
    """All sources with search results are tried (concurrent, no ordering guarantee)."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_all_sources_with_urls_are_fetched(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        fetched_sources = []
        lock = threading.Lock()

        def make_search(name):
            def search_fn(title, artists):
                return [f"http://{name}.example.com"]
            return search_fn

        def make_parse(name):
            def parse_fn(html):
                with lock:
                    fetched_sources.append(name)
                return None
            return parse_fn

        sources = [
            LyricsSource(
                name="low", search=make_search("low"), parse=make_parse("low"),
                fetchers=(Fetcher.REQUESTS,), romaji_quality=1,
            ),
            LyricsSource(
                name="high", search=make_search("high"), parse=make_parse("high"),
                fetchers=(Fetcher.REQUESTS,), romaji_quality=5,
            ),
            LyricsSource(
                name="mid", search=make_search("mid"), parse=make_parse("mid"),
                fetchers=(Fetcher.REQUESTS,), romaji_quality=3,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (_MOCK_HTML, 200)

        get_romaji_lyrics("TEST", ["ARTIST"])

        # All sources should have been tried (order is non-deterministic)
        assert_equal(
            sorted(fetched_sources), ["high", "low", "mid"],
            "all sources should be tried in concurrent mode",
        )


# ---------------------------------------------------------------------------
# RunLog integration
# ---------------------------------------------------------------------------

class TestRunLogIntegration:
    """Orchestrator creates a RunLog and records events into it."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_finalize_run_receives_populated_run_log(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        mock_registry.return_value = _build_test_registry()
        mock_fetch.return_value = (_MOCK_HTML, 200)

        get_romaji_lyrics("WHITE REFLECTION", ["TWO-MIX"])

        mock_finalize.assert_called_once()
        run_log = mock_finalize.call_args[0][0]
        assert_isinstance(run_log, RunLog)
        assert_equal(run_log.title, "WHITE REFLECTION")
        assert_equal(run_log.artists, ["TWO-MIX"])

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_run_log_contains_search_events(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        mock_registry.return_value = _build_test_registry()
        mock_fetch.return_value = (_MOCK_HTML, 200)

        get_romaji_lyrics("TITLE", ["ARTIST"])

        run_log = mock_finalize.call_args[0][0]
        search_names = [e.source_name for e in run_log.search_events]
        # Both sources from _build_test_registry should have search events
        assert_in("fast_source", search_names)
        assert_in("quality_source", search_names)

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_run_log_contains_fetch_events(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        mock_registry.return_value = _build_test_registry()
        mock_fetch.return_value = (_MOCK_HTML, 200)

        get_romaji_lyrics("TITLE", ["ARTIST"])

        run_log = mock_finalize.call_args[0][0]
        # At least one fetch event (quality_source succeeds in phase 1)
        assert_greater_equal(len(run_log.fetch_events), 1)
        fetch_ev = run_log.fetch_events[0]
        assert_isinstance(fetch_ev, FetchEvent)
        assert_equal(fetch_ev.phase, 1)

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_run_log_records_search_errors(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        def error_search(title, artists):
            raise ConnectionError("test error")

        sources = [
            LyricsSource(
                name="error_source",
                search=error_search,
                parse=lambda h: None,
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=3,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (None, 500)

        get_romaji_lyrics("TITLE", ["ARTIST"])

        run_log = mock_finalize.call_args[0][0]
        error_evts = [e for e in run_log.search_events if e.error is not None]
        assert_greater_equal(len(error_evts), 1)
        assert_contains_text(error_evts[0].error, "test error")

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_finalize_called_even_when_no_urls(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        sources = [
            LyricsSource(
                name="empty",
                search=lambda t, a: [],
                parse=lambda h: None,
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=3,
            ),
        ]
        mock_registry.return_value = sources

        get_romaji_lyrics("MISSING", ["UNKNOWN"])

        mock_finalize.assert_called_once()


# ---------------------------------------------------------------------------
# Parallel search
# ---------------------------------------------------------------------------

class TestParallelSearch:
    """Search across sources runs in parallel, not sequentially."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_search_runs_concurrently(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """Multiple slow searches should complete in ~1 wall-clock second, not N."""
        search_delay = 0.5  # seconds per search

        def slow_search(title, artists):
            time.sleep(search_delay)
            return [f"http://example.com/{title}"]

        sources = [
            LyricsSource(
                name=f"source_{i}",
                search=slow_search,
                parse=lambda h, i=i: _romaji_lyrics(f"source_{i}"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5 - i,
            )
            for i in range(4)
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (_MOCK_HTML, 200)

        t0 = time.time()
        get_romaji_lyrics("TEST", ["ARTIST"])
        wall_time = time.time() - t0

        # 4 sources * 0.5s = 2.0s sequential. Parallel should be ~0.5s.
        # Allow generous margin but must be faster than sequential.
        sequential_time = len(sources) * search_delay
        assert_greater(
            sequential_time, wall_time,
            f"parallel search should be faster than {sequential_time:.1f}s sequential"
        )

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_search_results_collected_for_all_sources(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        mock_registry.return_value = _build_test_registry()
        mock_fetch.return_value = (None, 500)  # all fetch fail

        get_romaji_lyrics("TITLE", ["ARTIST"])

        run_log = mock_finalize.call_args[0][0]
        search_names = {e.source_name for e in run_log.search_events}
        assert_in("fast_source", search_names)
        assert_in("quality_source", search_names)

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_search_error_does_not_block_other_sources(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        def error_search(title, artists):
            raise ConnectionError("boom")

        sources = [
            LyricsSource(
                name="broken",
                search=error_search,
                parse=lambda h: None,
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
            LyricsSource(
                name="working",
                search=lambda t, a: ["http://working.example.com"],
                parse=lambda h: _romaji_lyrics("working"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=3,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (_MOCK_HTML, 200)

        result = get_romaji_lyrics("TITLE", ["ARTIST"])

        assert_contains_text(result, "lyrics_from_working")


# ---------------------------------------------------------------------------
# Quality early-exit
# ---------------------------------------------------------------------------

class TestQualityEarlyExit:
    """Orchestrator uses is_acceptable to decide whether to keep trying."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_prefers_acceptable_over_unacceptable(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """quality_source returns a 1-word snippet; fast_source returns full lyrics.

        The orchestrator should return the acceptable result from fast_source,
        not the unacceptable one.
        """
        sources = [
            LyricsSource(
                name="quality_source",
                search=lambda t, a: ["http://quality.example.com"],
                parse=lambda h: "just one word",
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
            LyricsSource(
                name="fast_source",
                search=lambda t, a: ["http://fast.example.com"],
                parse=lambda h: _romaji_lyrics("fast_source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=2,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (_MOCK_HTML, 200)

        result = get_romaji_lyrics("TITLE", ["ARTIST"])

        assert_contains_text(result, "lyrics_from_fast_source")

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_returns_not_found_when_only_unacceptable(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """All sources return short lyrics (unacceptable) — result should be
        'Paroles non trouvées', not the unacceptable snippets.
        """
        sources = [
            LyricsSource(
                name="source_a",
                search=lambda t, a: ["http://a.example.com"],
                parse=lambda h: "kaze ga fuku",
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
            LyricsSource(
                name="source_b",
                search=lambda t, a: ["http://b.example.com"],
                parse=lambda h: "yume no naka de",
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=2,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (_MOCK_HTML, 200)

        result = get_romaji_lyrics("TITLE", ["ARTIST"])

        assert_contains_text(result, "Paroles non trouvées")

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_early_exits_on_acceptable_result(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """A fast source returns acceptable lyrics — slow source should
        be cancelled by early-exit. Wall time proves it.
        """
        def fetch_side_effect(url):
            if "quality" in url:
                return (_MOCK_HTML, 200)
            # Slow source: 2s delay
            time.sleep(2.0)
            return (_MOCK_HTML, 200)

        sources = [
            LyricsSource(
                name="quality_source",
                search=lambda t, a: ["http://quality.example.com"],
                parse=lambda h: _romaji_lyrics("quality_source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
            LyricsSource(
                name="slow_source",
                search=lambda t, a: ["http://slow.example.com"],
                parse=lambda h: _romaji_lyrics("slow_source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=2,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.side_effect = fetch_side_effect

        t0 = time.time()
        result = get_romaji_lyrics("TITLE", ["ARTIST"])
        wall_time = time.time() - t0

        assert_is_not_none(result)
        # Result should contain acceptable lyrics
        assert_not_in("Paroles non trouvées", result)
        # Should finish well before 2s (early-exit cancels slow source)
        assert_less(wall_time, 1.5, f"early-exit should cancel slow source ({wall_time:.2f}s)")


# ---------------------------------------------------------------------------
# Domain-level 403 early-break
# ---------------------------------------------------------------------------

class TestDomainLevelBlock:
    """A 403 on the first URL of a source breaks the URL loop immediately.

    All URLs for a single source share the same domain, so a 403 on
    the first URL means the entire domain is blocked.
    """

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_stops_trying_urls_after_first_403(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """Source with 3 URLs, first returns 403 — _fetch_requests called once."""
        sources = [
            LyricsSource(
                name="blocked_source",
                search=lambda t, a: [
                    "http://blocked.example.com/page1",
                    "http://blocked.example.com/page2",
                    "http://blocked.example.com/page3",
                ],
                parse=lambda h: _romaji_lyrics("blocked_source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (None, 403)

        get_romaji_lyrics("TITLE", ["ARTIST"])

        # Only the first URL should have been attempted
        assert_equal(
            mock_fetch.call_count, 1,
            "should stop after first 403 — remaining URLs share the same domain",
        )

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.selenium_fetcher.SeleniumFetcher")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_keeps_first_url_for_escalation(
        self, mock_finalize, mock_selenium_cls, mock_fetch, mock_registry
    ):
        """Source with 3 URLs, first returns 403 — Phase 2 receives only first URL."""
        sources = [
            LyricsSource(
                name="blocked_source",
                search=lambda t, a: [
                    "http://blocked.example.com/page1",
                    "http://blocked.example.com/page2",
                    "http://blocked.example.com/page3",
                ],
                parse=lambda h: _romaji_lyrics("blocked_source"),
                fetchers=(Fetcher.REQUESTS, Fetcher.SELENIUM),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (None, 403)

        # Selenium fetcher mock
        mock_sf = MagicMock()
        mock_sf.fetch.return_value = _MOCK_HTML
        mock_sf.__enter__ = MagicMock(return_value=mock_sf)
        mock_sf.__exit__ = MagicMock(return_value=False)
        mock_selenium_cls.return_value = mock_sf

        result = get_romaji_lyrics("TITLE", ["ARTIST"])

        # Phase 2 should only try the first URL (the one that was 403'd)
        assert_equal(
            mock_sf.fetch.call_count, 1,
            "Phase 2 should only receive the first blocked URL",
        )
        mock_sf.fetch.assert_called_with("http://blocked.example.com/page1")
        assert_contains_text(result, "lyrics_from_blocked_source")


# ---------------------------------------------------------------------------
# Concurrent pipeline
# ---------------------------------------------------------------------------

class TestConcurrentPipeline:
    """Sources run in parallel, not sequentially."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_sources_run_in_parallel(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """Two sources with 0.5s fetch delays — wall time should be < 2x sequential."""
        fetch_delay = 0.5

        def slow_fetch(url):
            time.sleep(fetch_delay)
            return (_MOCK_HTML, 200)

        sources = [
            LyricsSource(
                name=f"source_{i}",
                search=lambda t, a, i=i: [f"http://source_{i}.example.com"],
                parse=lambda h, i=i: _romaji_lyrics(f"source_{i}"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=3,
            )
            for i in range(4)
        ]
        mock_registry.return_value = sources
        mock_fetch.side_effect = slow_fetch

        t0 = time.time()
        get_romaji_lyrics("TEST", ["ARTIST"])
        wall_time = time.time() - t0

        sequential_time = len(sources) * fetch_delay
        assert_greater(
            sequential_time, wall_time,
            f"sources should run in parallel ({wall_time:.2f}s vs {sequential_time:.1f}s sequential)",
        )

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_early_exit_cancels_other_sources(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """Fast source returns immediately; slow source has a 2s delay.
        Wall time should be << 2s because early-exit cancels the slow source.
        """
        def fetch_side_effect(url):
            if "fast" in url:
                return (_MOCK_HTML, 200)
            # Slow source: simulate long fetch
            time.sleep(2.0)
            return (_MOCK_HTML, 200)

        sources = [
            LyricsSource(
                name="fast_source",
                search=lambda t, a: ["http://fast.example.com"],
                parse=lambda h: _romaji_lyrics("fast_source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=3,
            ),
            LyricsSource(
                name="slow_source",
                search=lambda t, a: ["http://slow.example.com"],
                parse=lambda h: _romaji_lyrics("slow_source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=3,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.side_effect = fetch_side_effect

        t0 = time.time()
        result = get_romaji_lyrics("TEST", ["ARTIST"])
        wall_time = time.time() - t0

        assert_is_not_none(result)
        # Should complete well before 2s (early-exit cancels slow_source)
        assert_less(wall_time, 1.5, f"early-exit should cancel slow source ({wall_time:.2f}s)")

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_returns_not_found_when_only_unacceptable_sources(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """Two sources both return unacceptable lyrics — result should be
        'Paroles non trouvées', not any of the unacceptable snippets.
        """
        sources = [
            LyricsSource(
                name="low_q",
                search=lambda t, a: ["http://low.example.com"],
                parse=lambda h: "yume no naka de",
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=1,
            ),
            LyricsSource(
                name="high_q",
                search=lambda t, a: ["http://high.example.com"],
                parse=lambda h: "kaze ga fuku",
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (_MOCK_HTML, 200)

        result = get_romaji_lyrics("TITLE", ["ARTIST"])

        assert_contains_text(result, "Paroles non trouvées")


# ---------------------------------------------------------------------------
# Parallel escalation (intra-source)
# ---------------------------------------------------------------------------

class TestParallelEscalation:
    """Within a source, escalation fetchers run in parallel after a 403."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.selenium_fetcher.SeleniumFetcher")
    @patch("lyrics_fetcher.chrome_fetcher.ChromeFetcher")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_escalation_fetchers_run_in_parallel(
        self, mock_finalize, mock_chrome_cls, mock_selenium_cls,
        mock_fetch, mock_registry
    ):
        """Source gets 403 on REQUESTS. Selenium and Chrome each take 0.5s.
        Parallel escalation should complete in ~0.5s, not ~1.0s.
        """
        escalation_delay = 0.5

        sources = [
            LyricsSource(
                name="blocked_source",
                search=lambda t, a: ["http://blocked.example.com/page1"],
                parse=lambda h: _romaji_lyrics("blocked_source"),
                fetchers=(Fetcher.REQUESTS, Fetcher.SELENIUM, Fetcher.CHROME_FETCHER),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (None, 403)

        def make_slow_fetcher():
            mock_f = MagicMock()
            def slow_fetch(url):
                time.sleep(escalation_delay)
                return _MOCK_HTML
            mock_f.fetch.side_effect = slow_fetch
            mock_f.__enter__ = MagicMock(return_value=mock_f)
            mock_f.__exit__ = MagicMock(return_value=False)
            return mock_f

        mock_selenium_cls.return_value = make_slow_fetcher()
        mock_chrome_cls.return_value = make_slow_fetcher()

        t0 = time.time()
        result = get_romaji_lyrics("TEST", ["ARTIST"])
        wall_time = time.time() - t0

        assert_is_not_none(result)
        assert_contains_text(result, "lyrics_from_blocked_source")
        # 2 fetchers * 0.5s sequential = 1.0s. Parallel should be ~0.5s.
        assert_less(
            wall_time, 1.0,
            f"escalation should be parallel ({wall_time:.2f}s)",
        )

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.selenium_fetcher.SeleniumFetcher")
    @patch("lyrics_fetcher.chrome_fetcher.ChromeFetcher")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_escalation_first_success_wins(
        self, mock_finalize, mock_chrome_cls, mock_selenium_cls,
        mock_fetch, mock_registry
    ):
        """Source gets 403. Selenium returns fast, Chrome is slow.
        Result should come quickly from Selenium.
        """
        sources = [
            LyricsSource(
                name="esc_source",
                search=lambda t, a: ["http://esc.example.com/page1"],
                parse=lambda h: _romaji_lyrics("esc_source"),
                fetchers=(Fetcher.REQUESTS, Fetcher.SELENIUM, Fetcher.CHROME_FETCHER),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (None, 403)

        # Selenium: fast
        mock_sf = MagicMock()
        mock_sf.fetch.return_value = _MOCK_HTML
        mock_sf.__enter__ = MagicMock(return_value=mock_sf)
        mock_sf.__exit__ = MagicMock(return_value=False)
        mock_selenium_cls.return_value = mock_sf

        # Chrome: slow (2s)
        mock_cf = MagicMock()
        def slow_chrome_fetch(url):
            time.sleep(2.0)
            return _MOCK_HTML
        mock_cf.fetch.side_effect = slow_chrome_fetch
        mock_cf.__enter__ = MagicMock(return_value=mock_cf)
        mock_cf.__exit__ = MagicMock(return_value=False)
        mock_chrome_cls.return_value = mock_cf

        t0 = time.time()
        result = get_romaji_lyrics("TEST", ["ARTIST"])
        wall_time = time.time() - t0

        assert_is_not_none(result)
        assert_contains_text(result, "lyrics_from_esc_source")
        # Should finish well before 2s (Selenium wins, Chrome cancelled by early-exit)
        assert_less(wall_time, 1.5, f"first-success should win ({wall_time:.2f}s)")


# ---------------------------------------------------------------------------
# Fallback grace period
# ---------------------------------------------------------------------------

class TestFallbackGracePeriod:
    """When no acceptable result exists, the orchestrator returns after a grace
    period instead of waiting indefinitely for slow escalation.
    """

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.selenium_fetcher.SeleniumFetcher")
    @patch("lyrics_fetcher.chrome_fetcher.ChromeFetcher")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_does_not_wait_for_slow_escalation_when_fallback_exists(
        self, mock_finalize, mock_chrome_cls, mock_selenium_cls,
        mock_fetch, mock_registry
    ):
        """fast_source returns unacceptable lyrics immediately.
        blocked_source gets 403 and escalates to Chrome (30s).
        Orchestrator should return with fallback well before 30s.
        """
        def fetch_side_effect(url):
            if "fast" in url:
                return (_MOCK_HTML, 200)
            # blocked_source returns 403
            return (None, 403)

        sources = [
            LyricsSource(
                name="fast_source",
                search=lambda t, a: ["http://fast.example.com"],
                parse=lambda h: "short fallback text",  # unacceptable
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=2,
            ),
            LyricsSource(
                name="blocked_source",
                search=lambda t, a: ["http://blocked.example.com"],
                parse=lambda h: _romaji_lyrics("blocked_source"),
                fetchers=(Fetcher.REQUESTS, Fetcher.SELENIUM, Fetcher.CHROME_FETCHER),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.side_effect = fetch_side_effect

        # Selenium: fails
        mock_sf = MagicMock()
        mock_sf.fetch.return_value = None
        mock_sf.__enter__ = MagicMock(return_value=mock_sf)
        mock_sf.__exit__ = MagicMock(return_value=False)
        mock_selenium_cls.return_value = mock_sf

        # Chrome: very slow (30s) — should be cut off by grace period
        mock_cf = MagicMock()
        def very_slow_chrome(url):
            time.sleep(30.0)
            return None  # fails after long wait
        mock_cf.fetch.side_effect = very_slow_chrome
        mock_cf.__enter__ = MagicMock(return_value=mock_cf)
        mock_cf.__exit__ = MagicMock(return_value=False)
        mock_chrome_cls.return_value = mock_cf

        t0 = time.time()
        result = get_romaji_lyrics("TITLE", ["ARTIST"])
        wall_time = time.time() - t0

        assert_is_not_none(result)
        # Grace period still works (wall time < 30s), but unacceptable
        # fallback is not returned — only acceptable results are.
        assert_contains_text(result, "Paroles non trouvées")
        assert_less(
            wall_time, 15.0,
            f"should not wait for slow Chrome when fallback exists ({wall_time:.2f}s)",
        )

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.selenium_fetcher.SeleniumFetcher")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_acceptable_result_during_grace_period_wins(
        self, mock_finalize, mock_selenium_cls, mock_fetch, mock_registry
    ):
        """fast_source returns unacceptable lyrics immediately.
        blocked_source gets 403, escalates to Selenium which returns
        acceptable lyrics within the grace period. The acceptable result
        should win over the fallback.
        """
        def fetch_side_effect(url):
            if "fast" in url:
                return (_MOCK_HTML, 200)
            return (None, 403)

        sources = [
            LyricsSource(
                name="fast_source",
                search=lambda t, a: ["http://fast.example.com"],
                parse=lambda h: "short fallback text",  # unacceptable
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=2,
            ),
            LyricsSource(
                name="blocked_source",
                search=lambda t, a: ["http://blocked.example.com"],
                parse=lambda h: _romaji_lyrics("blocked_source"),
                fetchers=(Fetcher.REQUESTS, Fetcher.SELENIUM),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.side_effect = fetch_side_effect

        # Selenium: returns after 1s with acceptable lyrics
        mock_sf = MagicMock()
        def delayed_selenium(url):
            time.sleep(1.0)
            return _MOCK_HTML
        mock_sf.fetch.side_effect = delayed_selenium
        mock_sf.__enter__ = MagicMock(return_value=mock_sf)
        mock_sf.__exit__ = MagicMock(return_value=False)
        mock_selenium_cls.return_value = mock_sf

        t0 = time.time()
        result = get_romaji_lyrics("TITLE", ["ARTIST"])
        wall_time = time.time() - t0

        # Acceptable result from selenium should win (found_event triggers early-exit)
        assert_contains_text(result, "lyrics_from_blocked_source")
        assert_less(wall_time, 3.0, f"acceptable should win within grace period ({wall_time:.2f}s)")


# ---------------------------------------------------------------------------
# Artist validation
# ---------------------------------------------------------------------------

class TestArtistValidation:
    """HTML pages that don't mention the artist are skipped before parsing."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_skips_page_when_artist_not_in_html(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """Fetch returns HTML for wrong artist — parse should not be called."""
        parse_called = []

        def tracking_parse(html):
            parse_called.append(True)
            return _romaji_lyrics("source")

        sources = [
            LyricsSource(
                name="source",
                search=lambda t, a: ["http://source.example.com"],
                parse=tracking_parse,
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        # HTML mentions "Jack White" but NOT "TWO-MIX"
        mock_fetch.return_value = (
            "<html><body>Jack White - White Room Lyrics</body></html>", 200
        )

        result = get_romaji_lyrics("WHITE REFLECTION", ["TWO-MIX"])

        assert_contains_text(result, "Paroles non trouvées")
        assert_len(
            parse_called, 0,
            "parse should not be called for wrong-artist HTML",
        )

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_accepts_page_when_artist_in_html(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """Fetch returns HTML mentioning the artist — parse should be called."""
        sources = [
            LyricsSource(
                name="source",
                search=lambda t, a: ["http://source.example.com"],
                parse=lambda h: _romaji_lyrics("source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (
            "<html><body>TWO-MIX - White Reflection Lyrics</body></html>", 200
        )

        result = get_romaji_lyrics("WHITE REFLECTION", ["TWO-MIX"])

        assert_contains_text(result, "lyrics_from_source")

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_artist_check_is_case_insensitive(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """Artist name matching should be case-insensitive."""
        sources = [
            LyricsSource(
                name="source",
                search=lambda t, a: ["http://source.example.com"],
                parse=lambda h: _romaji_lyrics("source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (
            "<html><body>two-mix white reflection</body></html>", 200
        )

        result = get_romaji_lyrics("WHITE REFLECTION", ["TWO-MIX"])

        assert_contains_text(result, "lyrics_from_source")


# ---------------------------------------------------------------------------
# Japanese-to-romaji automatic conversion
# ---------------------------------------------------------------------------

# Japanese lyrics that raw_parse would extract (no romaji source available)
_JAPANESE_LYRICS = (
    "風が吹いている街の中で\n"
    "君の声が聞こえるよ\n"
    "あの日の約束はまだ\n"
    "僕の胸にあるから\n"
    "夢の中で会えたなら\n"
)

# Mock HTML containing ARTIST name and Japanese lyrics
_MOCK_JAPANESE_HTML = (
    "<html><body>"
    "<p>ARTIST lyrics page</p>"
    "<p id='Lyric'>"
    "風が吹いている街の中で\n"
    "君の声が聞こえるよ\n"
    "あの日の約束はまだ\n"
    "僕の胸にあるから\n"
    "夢の中で会えたなら\n"
    "</p></body></html>"
)


class TestJapaneseToRomajiConversion:
    """When no native romaji is available, raw_parse + converter produces romaji."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_converts_japanese_lyrics_to_romaji(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """Source returns Japanese lyrics (parse returns None because not romaji),
        but raw_parse extracts them and converter produces acceptable romaji.
        """
        def raw_parse_fn(html):
            return _JAPANESE_LYRICS

        sources = [
            LyricsSource(
                name="japanese_source",
                search=lambda t, a: ["http://japanese.example.com"],
                parse=lambda h: None,  # not romaji
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=1,
                raw_parse=raw_parse_fn,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (_MOCK_JAPANESE_HTML, 200)

        result = get_romaji_lyrics("TITLE", ["ARTIST"])

        assert_is_not_none(result)
        assert_not_in("Paroles non trouvées", result)

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_prefers_native_romaji_over_conversion(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """A source that returns native romaji (via parse) is preferred over
        another source that uses raw_parse + conversion.

        The romaji_source fetches instantly while japanese_source is delayed,
        so romaji_source wins the race and its result is returned.
        """
        def raw_parse_fn(html):
            return _JAPANESE_LYRICS

        def fetch_side_effect(url):
            if "japanese" in url:
                time.sleep(0.5)
            return (_MOCK_JAPANESE_HTML, 200)

        sources = [
            LyricsSource(
                name="romaji_source",
                search=lambda t, a: ["http://romaji.example.com"],
                parse=lambda h: _romaji_lyrics("romaji_source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
            LyricsSource(
                name="japanese_source",
                search=lambda t, a: ["http://japanese.example.com"],
                parse=lambda h: None,
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=1,
                raw_parse=raw_parse_fn,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.side_effect = fetch_side_effect

        result = get_romaji_lyrics("TITLE", ["ARTIST"])

        assert_contains_text(result, "lyrics_from_romaji_source")

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    @patch("lyrics_fetcher.romaji_converter.japanese_to_romaji", return_value=None)
    def test_falls_back_to_not_found_when_conversion_fails(
        self, mock_converter, mock_finalize, mock_fetch, mock_registry
    ):
        """raw_parse extracts text but converter returns None — not found."""
        def raw_parse_fn(html):
            return _JAPANESE_LYRICS

        sources = [
            LyricsSource(
                name="japanese_source",
                search=lambda t, a: ["http://japanese.example.com"],
                parse=lambda h: None,
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=1,
                raw_parse=raw_parse_fn,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (_MOCK_JAPANESE_HTML, 200)

        result = get_romaji_lyrics("TITLE", ["ARTIST"])

        assert_contains_text(result, "Paroles non trouvées")

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_sources_without_raw_parse_skip_conversion(
        self, mock_finalize, mock_fetch, mock_registry
    ):
        """Source with raw_parse=None should not attempt conversion."""
        conversion_attempted = []

        original_japanese_to_romaji = None
        try:
            from lyrics_fetcher import romaji_converter
            original_japanese_to_romaji = romaji_converter.japanese_to_romaji
            def tracking_converter(text):
                conversion_attempted.append(True)
                return original_japanese_to_romaji(text)
            romaji_converter.japanese_to_romaji = tracking_converter

            sources = [
                LyricsSource(
                    name="no_raw_parse_source",
                    search=lambda t, a: ["http://noraw.example.com"],
                    parse=lambda h: None,  # parse fails
                    fetchers=(Fetcher.REQUESTS,),
                    romaji_quality=1,
                    # raw_parse=None (default)
                ),
            ]
            mock_registry.return_value = sources
            mock_fetch.return_value = (_MOCK_JAPANESE_HTML, 200)

            get_romaji_lyrics("TITLE", ["ARTIST"])

            assert_false(
                bool(conversion_attempted),
                "converter should not be called when raw_parse is None",
            )
        finally:
            if original_japanese_to_romaji is not None:
                romaji_converter.japanese_to_romaji = original_japanese_to_romaji
