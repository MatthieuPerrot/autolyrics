"""Unit tests for MP3 language tag extraction and Japanese language detection."""

from unittest.mock import patch, MagicMock

from lyrics_fetcher_cli import extract_metadata, is_japanese_language

from tests.helpers.assertions import (
    assert_equal,
    assert_true,
    assert_false,
    assert_is_none,
)


# ---------------------------------------------------------------------------
# _is_japanese_language
# ---------------------------------------------------------------------------

class TestIsJapaneseLanguage:

    def test_ja_code(self):
        assert_true(
            is_japanese_language("ja"),
            "'ja' should be recognized as Japanese",
        )

    def test_jpn_code(self):
        assert_true(
            is_japanese_language("jpn"),
            "'jpn' should be recognized as Japanese",
        )

    def test_japanese_word(self):
        assert_true(
            is_japanese_language("japanese"),
            "'japanese' should be recognized as Japanese",
        )

    def test_case_insensitive(self):
        assert_true(
            is_japanese_language("JPN"),
            "Japanese detection should be case-insensitive",
        )

    def test_with_whitespace(self):
        assert_true(
            is_japanese_language("  ja  "),
            "should strip whitespace before checking",
        )

    def test_english_code(self):
        assert_false(
            is_japanese_language("en"),
            "'en' should not be recognized as Japanese",
        )

    def test_french_code(self):
        assert_false(
            is_japanese_language("fr"),
            "'fr' should not be recognized as Japanese",
        )

    def test_empty_string(self):
        assert_false(
            is_japanese_language(""),
            "empty string should not be recognized as Japanese",
        )


# ---------------------------------------------------------------------------
# extract_metadata — language field
# ---------------------------------------------------------------------------

class TestExtractMetadataLanguage:

    @patch("lyrics_fetcher_cli.EasyID3")
    def test_returns_language_when_present(self, mock_easyid3):
        mock_audio = MagicMock()
        mock_audio.get.side_effect = lambda key, default=None: {
            "title": ["WHITE REFLECTION"],
            "artist": ["TWO-MIX"],
            "language": ["jpn"],
        }.get(key, default)
        mock_easyid3.return_value = mock_audio

        title, artists, language = extract_metadata("dummy.mp3")

        assert_equal(title, "WHITE REFLECTION")
        assert_equal(artists, ["TWO-MIX"])
        assert_equal(language, "jpn")

    @patch("lyrics_fetcher_cli.EasyID3")
    def test_returns_none_when_language_absent(self, mock_easyid3):
        mock_audio = MagicMock()
        mock_audio.get.side_effect = lambda key, default=None: {
            "title": ["WHITE REFLECTION"],
            "artist": ["TWO-MIX"],
        }.get(key, default)
        mock_easyid3.return_value = mock_audio

        title, artists, language = extract_metadata("dummy.mp3")

        assert_equal(title, "WHITE REFLECTION")
        assert_is_none(language)
