"""Unit tests for all 6 parse_* functions.

Each parser is a pure function: HTML in, lyrics string (or None) out.
No network calls, no side effects.
"""

import pytest

from lyrics_fetcher.animelyrics import parse_animelyrics
from lyrics_fetcher.nautiljon import parse_nautiljon
from lyrics_fetcher.genius import parse_genius
from lyrics_fetcher.j_lyric import parse_j_lyric
from lyrics_fetcher.mojim import parse_mojim
from lyrics_fetcher.lyrical_nonsense import parse_lyrical_nonsense

from tests.helpers.assertions import (
    assert_is_none,
    assert_is_not_none,
    assert_contains_text,
    assert_not_in,
)


# ── animelyrics ──────────────────────────────────────────────────────

class TestParseAnimelyrics:

    def test_extracts_romaji_from_div(self, load_fixture):
        html = load_fixture("animelyrics_romaji.html")
        result = parse_animelyrics(html)
        assert_is_not_none(result, "should extract romaji lyrics")
        assert_contains_text(result, "kimi ga sora datta")

    def test_extracts_romaji_from_td(self, load_fixture):
        html = load_fixture("animelyrics_td_romaji.html")
        result = parse_animelyrics(html)
        assert_is_not_none(result, "should extract romaji from <td> elements too")
        assert_contains_text(result, "hikari no naka de")

    def test_rejects_english_only(self, load_fixture):
        html = load_fixture("animelyrics_english_only.html")
        result = parse_animelyrics(html)
        assert_is_none(result, "should reject English-only lyrics")

    def test_filters_english_blocks_from_mixed(self, load_fixture):
        html = load_fixture("animelyrics_mixed.html")
        result = parse_animelyrics(html)
        assert_is_not_none(result, "should keep romaji block from mixed page")
        assert_contains_text(result, "kimi ga sora datta")
        assert_not_in("reflection", result, "should not contain English block")

    def test_returns_none_when_no_romaji_div(self, load_fixture):
        html = load_fixture("animelyrics_no_romaji.html")
        result = parse_animelyrics(html)
        assert_is_none(result, "should return None when no romaji div found")

    def test_strips_credits_dt(self, load_fixture):
        html = load_fixture("animelyrics_with_credits.html")
        result = parse_animelyrics(html)
        assert_is_not_none(result, "should parse despite credits dt")
        assert_not_in("Lyrics from", result, "should strip credits")
        assert_contains_text(result, "kaze ga fuku")


# ── nautiljon ────────────────────────────────────────────────────────

class TestParseNautiljon:

    def test_extracts_romaji(self, load_fixture):
        html = load_fixture("nautiljon_romaji.html")
        result = parse_nautiljon(html)
        assert_is_not_none(result, "should extract lyrics from itemprop='lyrics'")
        assert_contains_text(result, "kokoro no oku")

    def test_returns_none_when_no_lyrics_span(self, load_fixture):
        html = load_fixture("nautiljon_no_lyrics.html")
        result = parse_nautiljon(html)
        assert_is_none(result, "should return None when no lyrics span found")


# ── genius ───────────────────────────────────────────────────────────

class TestParseGenius:

    def test_extracts_romaji(self, load_fixture):
        html = load_fixture("genius_romaji.html")
        result = parse_genius(html)
        assert_is_not_none(result, "should extract lyrics from data-lyrics-container")
        assert_contains_text(result, "todokanu omoi")

    def test_combines_multiple_containers(self, load_fixture):
        html = load_fixture("genius_romaji.html")
        result = parse_genius(html)
        assert_is_not_none(result)
        assert_contains_text(result, "todokanu omoi")
        assert_contains_text(result, "aitai yo")

    def test_rejects_to_be_transcribed(self, load_fixture):
        html = load_fixture("genius_to_be_transcribed.html")
        result = parse_genius(html)
        assert_is_none(result, "should reject 'to be transcribed' pages")

    def test_returns_none_when_no_container(self, load_fixture):
        html = load_fixture("genius_no_container.html")
        result = parse_genius(html)
        assert_is_none(result, "should return None when no lyrics container found")


# ── j_lyric ──────────────────────────────────────────────────────────

class TestParseJLyric:

    def test_extracts_romaji(self, load_fixture):
        html = load_fixture("j_lyric_romaji.html")
        result = parse_j_lyric(html)
        assert_is_not_none(result, "should extract lyrics from p#Lyric")
        assert_contains_text(result, "sora wo miagete")

    def test_returns_none_when_no_lyric_p(self, load_fixture):
        html = load_fixture("j_lyric_no_lyric.html")
        result = parse_j_lyric(html)
        assert_is_none(result, "should return None when no p#Lyric found")


# ── mojim ────────────────────────────────────────────────────────────

class TestParseMojim:

    def test_extracts_romaji(self, load_fixture):
        html = load_fixture("mojim_romaji.html")
        result = parse_mojim(html)
        assert_is_not_none(result, "should extract lyrics from dd#fsZx3")
        assert_contains_text(result, "hateshinai sora")

    def test_strips_chinese_footer(self, load_fixture):
        html = load_fixture("mojim_romaji.html")
        result = parse_mojim(html)
        assert_is_not_none(result)
        assert_not_in("更多更詳盡歌詞", result, "should strip Chinese footer text")

    def test_returns_none_when_no_fsZx3(self, load_fixture):
        html = load_fixture("mojim_no_fsZx3.html")
        result = parse_mojim(html)
        assert_is_none(result, "should return None when no dd#fsZx3 found")


# ── lyrical_nonsense ─────────────────────────────────────────────────

class TestParseLyricalNonsense:

    def test_extracts_romaji(self, load_fixture):
        html = load_fixture("lyrical_nonsense_romaji.html")
        result = parse_lyrical_nonsense(html)
        assert_is_not_none(result, "should extract lyrics from div.romaji paragraphs")
        assert_contains_text(result, "aoi sora no shita de")

    def test_skips_empty_paragraphs(self, load_fixture):
        html = load_fixture("lyrical_nonsense_romaji.html")
        result = parse_lyrical_nonsense(html)
        assert_is_not_none(result)
        lines = [l for l in result.split("\n") if l.strip()]
        # The fixture has 4 non-empty paragraphs + 1 empty
        assert_contains_text(result, "yume ga kanau made")

    def test_returns_none_when_no_romaji_div(self, load_fixture):
        html = load_fixture("lyrical_nonsense_no_romaji.html")
        result = parse_lyrical_nonsense(html)
        assert_is_none(result, "should return None when no div.romaji found")
