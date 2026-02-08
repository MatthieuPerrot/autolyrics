"""Unit tests for the language detector module.

Tests cover the three main functions: is_likely_english, contains_japanese_characters,
and is_likely_romaji. Focus on edge cases around mixed English/romaji text, which is
common in J-pop songs.
"""

from lyrics_fetcher.language_detector import (
    is_likely_english,
    is_likely_romaji,
    contains_japanese_characters,
)

from tests.helpers.assertions import assert_true, assert_false


# ---------------------------------------------------------------------------
# is_likely_english
# ---------------------------------------------------------------------------

class TestIsLikelyEnglish:

    def test_pure_english_text(self):
        text = (
            "I feel your love reflection\n"
            "coming through the atmosphere\n"
            "into my heart forever"
        )
        assert_true(is_likely_english(text), "pure English should be detected")

    def test_pure_romaji_text(self):
        text = (
            "kimi ga sora datta\n"
            "sono kokoro ni fureta\n"
            "toki wo koete haruka"
        )
        assert_false(is_likely_english(text), "pure romaji should not be English")

    def test_mixed_english_and_romaji_is_not_english(self):
        """J-pop songs commonly mix English choruses with romaji verses.

        If romaji indicators (particles, verb endings) are present,
        the text should NOT be classified as English.
        """
        text = (
            "I feel your love reflection\n"
            "kizu tsuite mo kizu tsukerarete mo\n"
            "donna koto ga atte mo\n"
            "I can still believe our love\n"
            "kimi no namida wo nuguitai"
        )
        assert_false(
            is_likely_english(text),
            "mixed English/romaji should not be classified as English "
            "when romaji indicators are present",
        )

    def test_english_with_romaji_particles_is_not_english(self):
        """Even a minority of romaji lines is enough to mark it as non-English."""
        text = (
            "White reflection in the sky\n"
            "bokutachi wa mada shiranai\n"
            "The future that awaits us"
        )
        assert_false(
            is_likely_english(text),
            "romaji particles (wa) should override English phrase detection",
        )


# ---------------------------------------------------------------------------
# is_likely_romaji
# ---------------------------------------------------------------------------

class TestIsLikelyRomaji:

    def test_pure_romaji(self):
        text = (
            "kimi ga sora datta\n"
            "sono kokoro ni fureta\n"
            "toki wo koete haruka"
        )
        assert_true(is_likely_romaji(text), "pure romaji should be accepted")

    def test_pure_english_rejected(self):
        text = (
            "I feel your love reflection\n"
            "coming through the atmosphere\n"
            "into my heart forever"
        )
        assert_false(is_likely_romaji(text), "pure English should be rejected")

    def test_mixed_english_and_romaji_accepted(self):
        """Romaji with English phrases mixed in should still be accepted."""
        text = (
            "I feel your love reflection\n"
            "kizu tsuite mo kizu tsukerarete mo\n"
            "donna koto ga atte mo\n"
            "I can still believe our love\n"
            "kimi no namida wo nuguitai"
        )
        assert_true(
            is_likely_romaji(text),
            "mixed English/romaji should be accepted as romaji",
        )

    def test_japanese_characters_rejected(self):
        text = "ここにいるよ kimi no soba ni"
        assert_false(
            is_likely_romaji(text),
            "text with Japanese characters should be rejected",
        )


# ---------------------------------------------------------------------------
# contains_japanese_characters
# ---------------------------------------------------------------------------

class TestContainsJapaneseCharacters:

    def test_hiragana(self):
        assert_true(contains_japanese_characters("あいうえお"))

    def test_katakana(self):
        assert_true(contains_japanese_characters("アイウエオ"))

    def test_kanji(self):
        assert_true(contains_japanese_characters("漢字"))

    def test_romaji_only(self):
        assert_false(contains_japanese_characters("kimi ga sora datta"))

    def test_english_only(self):
        assert_false(contains_japanese_characters("hello world"))
