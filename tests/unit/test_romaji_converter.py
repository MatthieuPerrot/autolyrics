"""Unit tests for the romaji converter module."""

from unittest.mock import patch, MagicMock

from lyrics_fetcher.romaji_converter import japanese_to_romaji
from lyrics_fetcher.quality import is_acceptable

from tests.helpers.assertions import (
    assert_equal,
    assert_is_none,
    assert_is_not_none,
    assert_true,
    assert_false,
    assert_in,
    assert_contains_text,
)


class TestJapaneseToRomaji:

    def test_converts_hiragana(self):
        result = japanese_to_romaji("こんにちは")
        assert_is_not_none(result, "hiragana should be convertible")
        assert_false(
            any(0x3040 <= ord(c) <= 0x309F for c in result),
            f"result should contain no hiragana characters, got: {result!r}",
        )

    def test_converts_katakana(self):
        result = japanese_to_romaji("カタカナ")
        assert_is_not_none(result, "katakana should be convertible")
        assert_false(
            any(0x30A0 <= ord(c) <= 0x30FF for c in result),
            f"result should contain no katakana characters, got: {result!r}",
        )

    def test_converts_kanji(self):
        result = japanese_to_romaji("世界")
        assert_is_not_none(result, "kanji should be convertible")
        assert_true(len(result) > 0, "converted text should not be empty")

    def test_converts_mixed_japanese(self):
        result = japanese_to_romaji("風が吹いている街の中で")
        assert_is_not_none(result, "mixed Japanese text should be convertible")

    def test_preserves_line_structure(self):
        japanese_text = "風が吹いている\n街の中で\n君の声が聞こえる"
        result = japanese_to_romaji(japanese_text)
        assert_is_not_none(result)
        lines = result.strip().split("\n")
        assert_equal(
            len(lines), 3,
            f"should preserve 3 lines, got {len(lines)}: {result!r}",
        )

    def test_returns_none_for_empty_string(self):
        result = japanese_to_romaji("")
        assert_is_none(result, "empty string should return None")

    def test_returns_none_for_whitespace_only(self):
        result = japanese_to_romaji("   \n  \n  ")
        assert_is_none(result, "whitespace-only should return None")

    def test_returns_none_for_non_japanese_text(self):
        result = japanese_to_romaji("This is plain English text with no Japanese")
        assert_is_none(result, "non-Japanese text should return None")

    def test_converted_multiline_lyrics_pass_is_acceptable(self):
        # Realistic multi-line Japanese lyrics
        japanese_lyrics = (
            "風が吹いている街の中で\n"
            "君の声が聞こえるよ\n"
            "あの日の約束はまだ\n"
            "僕の胸にあるから\n"
            "夢の中で会えたなら\n"
        )
        result = japanese_to_romaji(japanese_lyrics)
        assert_is_not_none(result, "multi-line lyrics should be convertible")
        assert_true(
            is_acceptable(result),
            f"converted lyrics should pass is_acceptable, got: {result!r}",
        )

    def test_preserves_blank_lines_between_stanzas(self):
        japanese_text = "風が吹いている\n\n街の中で"
        result = japanese_to_romaji(japanese_text)
        assert_is_not_none(result)
        assert_in(
            "\n\n", result,
            "blank lines between stanzas should be preserved",
        )


class TestCutletUnavailable:

    @patch("lyrics_fetcher.romaji_converter._get_cutlet", return_value=None)
    def test_returns_none_when_cutlet_unavailable(self, mock_get_cutlet):
        result = japanese_to_romaji("こんにちは世界")
        assert_is_none(result, "should return None when cutlet is unavailable")
