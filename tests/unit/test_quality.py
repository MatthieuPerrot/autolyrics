"""Unit tests for lyrics quality gate (is_acceptable, assess_quality)."""

from lyrics_fetcher.quality import is_acceptable, assess_quality, QualityResult

from tests.helpers.assertions import (
    assert_true,
    assert_false,
    assert_equal,
    assert_is_none,
    assert_is_not_none,
    assert_isinstance,
)


# Sample romaji lyrics that should be accepted (realistic song fragment)
_VALID_ROMAJI = (
    "Kaze ga fuiteiru machi no naka de\n"
    "Kimi no koe ga kikoeru yo\n"
    "Ano hi no yakusoku wa mada\n"
    "Boku no mune ni aru kara\n"
    "Zutto zutto wasurenai\n"
)

_ENGLISH_TEXT = (
    "The wind is blowing through the city\n"
    "I can hear your voice calling\n"
    "The promise from that day still\n"
    "Lives on inside my heart\n"
    "I will never forget you\n"
)

_JAPANESE_TEXT = (
    "風が吹いている街の中で\n"
    "君の声が聞こえるよ\n"
    "あの日の約束はまだ\n"
    "僕の胸にあるから\n"
    "ずっとずっと忘れない\n"
)


class TestIsAcceptable:
    """Tests for the is_acceptable quality gate."""

    def test_accepts_valid_romaji_lyrics(self):
        assert_true(
            is_acceptable(_VALID_ROMAJI),
            "valid romaji lyrics should be accepted",
        )

    def test_rejects_too_short(self):
        assert_false(
            is_acceptable("Kaze ga fuku"),
            "text shorter than minimum length should be rejected",
        )

    def test_rejects_too_few_lines(self):
        # Long enough in characters but only 2 lines
        long_two_lines = (
            "Kaze ga fuiteiru machi no naka de kimi no koe ga\n"
            "Boku no mune ni aru kara zutto zutto wasurenai yo"
        )
        assert_false(
            is_acceptable(long_two_lines),
            "text with fewer than 4 lines should be rejected",
        )

    def test_rejects_incomplete_marker(self):
        text = (
            "Kaze ga fuiteiru machi no naka de\n"
            "Kimi no koe ga kikoeru yo\n"
            "Ano hi no yakusoku wa mada\n"
            "Boku no mune ni aru kara\n"
            "Lyrics not available\n"
        )
        assert_false(
            is_acceptable(text),
            "text containing an incomplete marker should be rejected",
        )

    def test_rejects_english_text(self):
        assert_false(
            is_acceptable(_ENGLISH_TEXT),
            "English text should be rejected",
        )

    def test_rejects_japanese_text(self):
        assert_false(
            is_acceptable(_JAPANESE_TEXT),
            "Japanese text should be rejected",
        )

    def test_accepts_minimum_threshold(self):
        # Exactly at the boundary: 4 lines and >= 50 chars of romaji
        boundary = (
            "Kaze ga fuiteiru machi no naka de\n"
            "Kimi no koe ga kikoeru yo\n"
            "Ano hi no yakusoku wa\n"
            "Boku no mune ni aru kara"
        )
        assert_true(
            is_acceptable(boundary),
            "text at exactly the minimum threshold should be accepted",
        )

    def test_rejects_empty_string(self):
        assert_false(
            is_acceptable(""),
            "empty string should be rejected",
        )

    def test_rejects_whitespace_only(self):
        assert_false(
            is_acceptable("   \n\n  \n  "),
            "whitespace-only string should be rejected",
        )

    def test_rejects_to_be_transcribed_marker(self):
        text = (
            "To be transcribed\n"
            "Kimi no koe ga kikoeru yo\n"
            "Ano hi no yakusoku wa mada\n"
            "Boku no mune ni aru kara\n"
        )
        assert_false(
            is_acceptable(text),
            "text with 'to be transcribed' marker should be rejected",
        )

    def test_marker_detection_is_case_insensitive(self):
        text = (
            "Kaze ga fuiteiru machi no naka de\n"
            "WE DON'T HAVE THIS LYRICS\n"
            "Ano hi no yakusoku wa mada\n"
            "Boku no mune ni aru kara\n"
        )
        assert_false(
            is_acceptable(text),
            "incomplete marker detection should be case-insensitive",
        )


# ---------------------------------------------------------------------------
# assess_quality
# ---------------------------------------------------------------------------

class TestAssessQuality:
    """Tests for the assess_quality function and QualityResult dataclass."""

    def test_returns_quality_result(self):
        result = assess_quality(_VALID_ROMAJI)
        assert_isinstance(result, QualityResult)

    def test_accepts_valid_romaji(self):
        result = assess_quality(_VALID_ROMAJI)
        assert_true(result.is_acceptable, "valid romaji should be acceptable")
        assert_equal(result.detected_language, "romaji")
        assert_is_none(result.rejection_reason)

    def test_rejects_too_short(self):
        result = assess_quality("Kaze ga fuku")
        assert_false(result.is_acceptable)
        assert_equal(result.rejection_reason, "too_short")

    def test_rejects_too_few_lines(self):
        long_two_lines = (
            "Kaze ga fuiteiru machi no naka de kimi no koe ga\n"
            "Boku no mune ni aru kara zutto zutto wasurenai yo"
        )
        result = assess_quality(long_two_lines)
        assert_false(result.is_acceptable)
        assert_equal(result.rejection_reason, "too_few_lines")

    def test_rejects_incomplete_marker(self):
        text = (
            "Kaze ga fuiteiru machi no naka de\n"
            "Kimi no koe ga kikoeru yo\n"
            "Ano hi no yakusoku wa mada\n"
            "Boku no mune ni aru kara\n"
            "Lyrics not available\n"
        )
        result = assess_quality(text)
        assert_false(result.is_acceptable)
        assert_equal(result.rejection_reason, "incomplete_marker")

    def test_rejects_english_text(self):
        result = assess_quality(_ENGLISH_TEXT)
        assert_false(result.is_acceptable)
        assert_equal(result.detected_language, "english")
        assert_equal(result.rejection_reason, "wrong_language")

    def test_rejects_japanese_text(self):
        result = assess_quality(_JAPANESE_TEXT)
        assert_false(result.is_acceptable)
        assert_equal(result.detected_language, "japanese")
        assert_equal(result.rejection_reason, "wrong_language")

    def test_rejects_empty_string(self):
        result = assess_quality("")
        assert_false(result.is_acceptable)
        assert_equal(result.rejection_reason, "too_short")

    def test_consistent_with_is_acceptable(self):
        """assess_quality().is_acceptable must match is_acceptable() for all cases."""
        samples = [
            _VALID_ROMAJI,
            _ENGLISH_TEXT,
            _JAPANESE_TEXT,
            "Kaze ga fuku",
            "",
            "   \n\n  \n  ",
        ]
        for text in samples:
            assert_equal(
                assess_quality(text).is_acceptable,
                is_acceptable(text),
                f"assess_quality and is_acceptable disagree on: {text[:30]!r}",
            )
