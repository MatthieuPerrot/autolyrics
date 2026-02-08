"""Unit tests for URL language marker filter (_is_non_romaji_language_url)."""

from lyrics_fetcher.fallback import _is_non_romaji_language_url

from tests.helpers.assertions import assert_true, assert_false


class TestRejectsNonRomajiLanguageUrls:
    """URLs containing parenthesized non-romaji language markers are filtered out."""

    def test_rejects_english_marker(self):
        assert_true(
            _is_non_romaji_language_url(
                "https://www.nautiljon.com/paroles/two-mix/white+reflection+(english).html"
            ),
            "URL with (english) marker should be rejected",
        )

    def test_rejects_french_marker(self):
        assert_true(
            _is_non_romaji_language_url(
                "https://www.nautiljon.com/paroles/song+(français).html"
            ),
            "URL with (français) marker should be rejected",
        )

    def test_rejects_case_insensitive(self):
        assert_true(
            _is_non_romaji_language_url(
                "https://site.com/song+(English).html"
            ),
            "URL with (English) marker should be rejected (case-insensitive)",
        )

    def test_rejects_spanish_marker(self):
        assert_true(
            _is_non_romaji_language_url(
                "https://site.com/song+(español).html"
            ),
            "URL with (español) marker should be rejected",
        )

    def test_rejects_chinese_marker(self):
        assert_true(
            _is_non_romaji_language_url(
                "https://site.com/song+(chinese).html"
            ),
            "URL with (chinese) marker should be rejected",
        )

    def test_rejects_korean_marker(self):
        assert_true(
            _is_non_romaji_language_url(
                "https://site.com/song+(korean).html"
            ),
            "URL with (korean) marker should be rejected",
        )

    def test_rejects_german_marker(self):
        assert_true(
            _is_non_romaji_language_url(
                "https://site.com/song+(deutsch).html"
            ),
            "URL with (deutsch) marker should be rejected",
        )

    def test_rejects_italian_marker(self):
        assert_true(
            _is_non_romaji_language_url(
                "https://site.com/song+(italiano).html"
            ),
            "URL with (italiano) marker should be rejected",
        )


class TestAcceptsValidUrls:
    """URLs without non-romaji language markers pass through the filter."""

    def test_accepts_plain_url(self):
        assert_false(
            _is_non_romaji_language_url(
                "https://www.nautiljon.com/paroles/two-mix/white+reflection.html"
            ),
            "plain URL without language marker should be accepted",
        )

    def test_accepts_romaji_content_url(self):
        assert_false(
            _is_non_romaji_language_url(
                "https://www.animelyrics.com/anime/gundam/whiteref.htm"
            ),
            "URL without parenthesized language marker should be accepted",
        )

    def test_accepts_url_with_unrelated_parens(self):
        assert_false(
            _is_non_romaji_language_url(
                "https://site.com/song+(bonus+track).html"
            ),
            "URL with non-language parenthesized text should be accepted",
        )

    def test_accepts_url_with_romaji_in_path(self):
        assert_false(
            _is_non_romaji_language_url(
                "https://site.com/romaji/song.html"
            ),
            "URL with 'romaji' in path (not as marker) should be accepted",
        )

    def test_accepts_url_with_japanese_in_path(self):
        assert_false(
            _is_non_romaji_language_url(
                "https://site.com/japanese/song.html"
            ),
            "URL with 'japanese' in path (not parenthesized) should be accepted",
        )
