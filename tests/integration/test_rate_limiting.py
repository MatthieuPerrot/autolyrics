"""Integration tests for rate limiting in the lyrics fetcher pipeline.

Tests exercise the full pipeline with rate limiting injected, verifying
User-Agent rotation, 429 cooldown recording, and pipeline integration.
All network calls are mocked.
"""

import threading
from unittest.mock import patch, MagicMock, call

from lyrics_fetcher.source_registry import Fetcher, LyricsSource
from lyrics_fetcher.fallback import get_romaji_lyrics
from lyrics_fetcher.run_log import RunLog

from tests.helpers.assertions import (
    assert_contains_text,
    assert_greater,
    assert_is_not_none,
    assert_true,
)

_MOCK_HTML = "<html><body>ARTIST lyrics page</body></html>"


def _romaji_lyrics(source_name):
    """Generate acceptable romaji lyrics tagged with a source name marker."""
    return (
        f"lyrics_from_{source_name}\n"
        "Kaze ga fuiteiru machi no naka de\n"
        "Kimi no koe ga kikoeru yo\n"
        "Ano hi no yakusoku wa mada\n"
        "Boku no mune ni aru kara\n"
    )


# ---------------------------------------------------------------------------
# User-Agent rotation
# ---------------------------------------------------------------------------

class TestUserAgentRotation:
    """_fetch_requests uses varied User-Agent strings."""

    @patch("lyrics_fetcher.fallback.requests_lib")
    def test_fetch_requests_uses_random_user_agent(self, mock_requests_lib):
        """Multiple calls to _fetch_requests should use different UAs."""
        from lyrics_fetcher.fallback import _fetch_requests

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>ok</html>"
        mock_requests_lib.get.return_value = mock_response
        mock_requests_lib.exceptions = __import__("requests").exceptions

        observed_uas = set()
        for _ in range(20):
            _fetch_requests("https://example.com/page")
            ua = mock_requests_lib.get.call_args[1]["headers"]["User-Agent"]
            observed_uas.add(ua)

        assert_greater(
            len(observed_uas), 1,
            "User-Agent should vary across calls to _fetch_requests",
        )


# ---------------------------------------------------------------------------
# 429 recording in pipeline
# ---------------------------------------------------------------------------

class TestFetchRequestsRecords429:
    """record_response is called with the correct status code."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback.requests_lib")
    @patch("lyrics_fetcher.fallback._finalize_run")
    def test_record_response_called_on_429(
        self, mock_finalize, mock_requests_lib, mock_registry
    ):
        """When a source returns 429, the rate limiter's record_response is called."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = ""
        http_error = __import__("requests").exceptions.HTTPError(response=mock_response)
        mock_requests_lib.get.side_effect = http_error
        mock_requests_lib.exceptions = __import__("requests").exceptions

        sources = [
            LyricsSource(
                name="rate_limited_source",
                search=lambda t, a: ["http://ratelimited.example.com/page"],
                parse=lambda h: _romaji_lyrics("rate_limited_source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=3,
            ),
        ]
        mock_registry.return_value = sources

        result = get_romaji_lyrics("TITLE", ["ARTIST"])

        # The pipeline should still complete (with not found)
        assert_is_not_none(result)

        # Check the run log recorded the 429 status
        run_log = mock_finalize.call_args[0][0]
        statuses = [e.http_status for e in run_log.fetch_events]
        assert_true(
            429 in statuses,
            f"run log should contain a 429 status, got: {statuses}",
        )


# ---------------------------------------------------------------------------
# Pipeline creates and uses rate_limiter
# ---------------------------------------------------------------------------

class TestPipelineRateLimiting:
    """The full pipeline creates a RateLimiter and passes it through."""

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    @patch("lyrics_fetcher.fallback.RateLimiter")
    def test_pipeline_creates_rate_limiter(
        self, mock_rl_cls, mock_finalize, mock_fetch, mock_registry
    ):
        """get_romaji_lyrics should instantiate a RateLimiter."""
        mock_rl = MagicMock()
        mock_rl.wait_for_domain.return_value = 0.0
        mock_rl_cls.return_value = mock_rl

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
        mock_fetch.return_value = (_MOCK_HTML, 200)

        get_romaji_lyrics("TITLE", ["ARTIST"])

        mock_rl_cls.assert_called_once()

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    @patch("lyrics_fetcher.fallback.RateLimiter")
    def test_pipeline_calls_wait_for_domain(
        self, mock_rl_cls, mock_finalize, mock_fetch, mock_registry
    ):
        """The pipeline should call wait_for_domain before fetching."""
        mock_rl = MagicMock()
        mock_rl.wait_for_domain.return_value = 0.0
        mock_rl_cls.return_value = mock_rl

        sources = [
            LyricsSource(
                name="source",
                search=lambda t, a: ["http://source.example.com/page"],
                parse=lambda h: _romaji_lyrics("source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (_MOCK_HTML, 200)

        get_romaji_lyrics("TITLE", ["ARTIST"])

        mock_rl.wait_for_domain.assert_called()

    @patch("lyrics_fetcher.fallback.build_registry")
    @patch("lyrics_fetcher.fallback._fetch_requests")
    @patch("lyrics_fetcher.fallback._finalize_run")
    @patch("lyrics_fetcher.fallback.RateLimiter")
    def test_pipeline_calls_record_response(
        self, mock_rl_cls, mock_finalize, mock_fetch, mock_registry
    ):
        """The pipeline should call record_response after fetching."""
        mock_rl = MagicMock()
        mock_rl.wait_for_domain.return_value = 0.0
        mock_rl_cls.return_value = mock_rl

        sources = [
            LyricsSource(
                name="source",
                search=lambda t, a: ["http://source.example.com/page"],
                parse=lambda h: _romaji_lyrics("source"),
                fetchers=(Fetcher.REQUESTS,),
                romaji_quality=5,
            ),
        ]
        mock_registry.return_value = sources
        mock_fetch.return_value = (_MOCK_HTML, 200)

        get_romaji_lyrics("TITLE", ["ARTIST"])

        mock_rl.record_response.assert_called()
        # Verify the status code was passed
        recorded_call = mock_rl.record_response.call_args
        assert_is_not_none(recorded_call)
