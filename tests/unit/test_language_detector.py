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

    def test_pure_english_with_ambiguous_words(self):
        """English text containing 'to' or 'no' (also romaji particles)
        should still be detected as English when no strong romaji is present.
        """
        text = (
            "As if throwing off the sadness and pain,\n"
            "I flap my wings,\n"
            "And in my heart, I spread wide\n"
            "The wings of courage that you've given to me.\n"
            "I want to feel the beat of this irreplaceable love\n"
            "So much, it's heart-wrenching and maddening.\n"
        )
        assert_true(
            is_likely_english(text),
            "pure English containing 'to' should still be detected as English",
        )

    def test_english_with_te_ending_words(self):
        """English words ending in 'te' (white, write) should not be
        confused with Japanese verb endings.
        """
        text = (
            "I'm feelin' like my last name Yuy, First name Heero\n"
            "Gundam on my mind as I write this on my Evo\n"
            "I'm jammin' White Reflection as I write my reflections\n"
            "Eliminate 'em all, that's my mission protocol\n"
        )
        assert_true(
            is_likely_english(text),
            "English text with 'write'/'white' should be detected as English",
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

    def test_pure_english_with_ambiguous_words_rejected(self):
        """English text with 'to'/'no' should be rejected as romaji."""
        text = (
            "As if throwing off the sadness and pain,\n"
            "I flap my wings,\n"
            "And in my heart, I spread wide\n"
            "The wings of courage that you've given to me.\n"
            "I want to feel the beat of this irreplaceable love\n"
            "So much, it's heart-wrenching and maddening.\n"
        )
        assert_false(
            is_likely_romaji(text),
            "pure English with 'to' should be rejected as romaji",
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
