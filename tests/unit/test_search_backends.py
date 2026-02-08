"""Unit tests for search backend timeouts and retry logic."""

from unittest.mock import patch, MagicMock, call

from lyrics_fetcher.search_backends import DuckDuckGoBackend, GoogleScraperBackend

from tests.helpers.assertions import (
    assert_equal,
    assert_true,
    assert_len,
)


# ---------------------------------------------------------------------------
# DuckDuckGoBackend — timeout
# ---------------------------------------------------------------------------

class TestDuckDuckGoTimeout:

    @patch("lyrics_fetcher.search_backends.DDGS")
    def test_ddgs_created_with_timeout(self, mock_ddgs_cls):
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.text.return_value = [{"href": "http://example.com"}]
        mock_ddgs_cls.return_value = mock_instance

        backend = DuckDuckGoBackend()
        backend.search("test query")

        mock_ddgs_cls.assert_called_once_with(timeout=10)


# ---------------------------------------------------------------------------
# GoogleScraperBackend — timeout
# ---------------------------------------------------------------------------

class TestGoogleScraperTimeout:

    @patch("lyrics_fetcher.search_backends.google_search")
    def test_google_scraper_passes_timeout(self, mock_gsearch):
        mock_gsearch.return_value = iter(["http://example.com"])

        backend = GoogleScraperBackend()
        backend.search("test query")

        call_kwargs = mock_gsearch.call_args[1]
        assert_equal(call_kwargs["timeout"], 10)


# ---------------------------------------------------------------------------
# Retry logic in utils.search()
# ---------------------------------------------------------------------------

class TestSearchRetry:

    def _make_backend(self, name, search_side_effect):
        """Create a mock backend with the given name and search behavior."""
        backend = MagicMock()
        backend.name.return_value = name
        backend.search.side_effect = search_side_effect
        return backend

    @patch("lyrics_fetcher.utils.time")
    def test_retries_ddg_once_before_fallback(self, mock_time):
        """DDG fails twice, then Google Scraper succeeds."""
        ddg = self._make_backend("DDG", Exception("DDGSException"))
        gscraper = self._make_backend(
            "GoogleScraper", [["http://google-result.com"]]
        )
        cse = self._make_backend("CSE", [[]])

        with patch("lyrics_fetcher.utils._build_backends", return_value=[ddg, gscraper, cse]):
            from lyrics_fetcher.utils import search
            results = list(search("test query"))

        # DDG should have been called twice (initial + 1 retry)
        assert_equal(ddg.search.call_count, 2)
        # Sleep should have been called once (between retry attempts)
        mock_time.sleep.assert_called_once_with(2)
        # Results should come from Google Scraper
        assert_len(results, 1)
        assert_equal(results[0], "http://google-result.com")

    @patch("lyrics_fetcher.utils.time")
    def test_ddg_succeeds_on_retry(self, mock_time):
        """DDG fails first, succeeds on retry."""
        ddg = self._make_backend("DDG", [
            Exception("DDGSException"),
            ["http://ddg-result.com"],
        ])
        gscraper = self._make_backend("GoogleScraper", [[]])
        cse = self._make_backend("CSE", [[]])

        with patch("lyrics_fetcher.utils._build_backends", return_value=[ddg, gscraper, cse]):
            from lyrics_fetcher.utils import search
            results = list(search("test query"))

        assert_equal(ddg.search.call_count, 2)
        assert_len(results, 1)
        assert_equal(results[0], "http://ddg-result.com")
        # Google Scraper should not have been called
        assert_equal(gscraper.search.call_count, 0)

    def test_no_retry_on_non_first_backend(self):
        """Google Scraper (second backend) should not be retried."""
        ddg = self._make_backend("DDG", [[]])  # returns empty
        gscraper = self._make_backend("GoogleScraper", Exception("HTTPError"))
        cse = self._make_backend("CSE", [[]])

        with patch("lyrics_fetcher.utils._build_backends", return_value=[ddg, gscraper, cse]):
            from lyrics_fetcher.utils import search
            list(search("test query"))

        # Google Scraper should have been called exactly once (no retry)
        assert_equal(gscraper.search.call_count, 1)
