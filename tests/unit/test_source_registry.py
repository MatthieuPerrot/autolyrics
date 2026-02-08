"""Unit tests for the source registry."""

import os

from lyrics_fetcher.source_registry import Fetcher, LyricsSource, build_registry

from tests.helpers.assertions import (
    assert_equal,
    assert_true,
    assert_false,
    assert_is_none,
    assert_is_not_none,
    assert_in,
    assert_greater,
    assert_len,
)

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")


def _load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


EXPECTED_SOURCE_NAMES = {
    "lyrical_nonsense", "animelyrics", "nautiljon",
    "genius", "j_lyric", "mojim",
}


class TestBuildRegistry:

    def test_returns_all_six_sources(self):
        sources = build_registry()
        assert_len(sources, 6)

    def test_all_expected_sources_present(self):
        sources = build_registry()
        names = {s.name for s in sources}
        assert_equal(names, EXPECTED_SOURCE_NAMES)

    def test_each_source_has_callable_search_and_parse(self):
        sources = build_registry()
        for source in sources:
            assert_true(
                callable(source.search),
                f"{source.name}.search should be callable",
            )
            assert_true(
                callable(source.parse),
                f"{source.name}.parse should be callable",
            )

    def test_each_source_has_at_least_requests_fetcher(self):
        sources = build_registry()
        for source in sources:
            assert_in(
                Fetcher.REQUESTS, source.fetchers,
                f"{source.name} should support at least REQUESTS fetcher",
            )

    def test_quality_ratings_in_valid_range(self):
        sources = build_registry()
        for source in sources:
            assert_greater(
                source.romaji_quality, 0,
                f"{source.name} quality should be > 0",
            )
            assert_true(
                source.romaji_quality <= 5,
                f"{source.name} quality should be <= 5, got {source.romaji_quality}",
            )


class TestFetcherAssignments:

    def test_animelyrics_has_all_three_fetchers(self):
        sources = build_registry()
        animelyrics = next(s for s in sources if s.name == "animelyrics")
        assert_equal(
            animelyrics.fetchers,
            (Fetcher.REQUESTS, Fetcher.SELENIUM, Fetcher.CHROME_FETCHER),
        )

    def test_nautiljon_has_requests_and_selenium(self):
        sources = build_registry()
        nautiljon = next(s for s in sources if s.name == "nautiljon")
        assert_equal(
            nautiljon.fetchers,
            (Fetcher.REQUESTS, Fetcher.SELENIUM),
        )

    def test_requests_only_sources(self):
        sources = build_registry()
        requests_only = {"lyrical_nonsense", "genius", "j_lyric", "mojim"}
        for source in sources:
            if source.name in requests_only:
                assert_equal(
                    source.fetchers, (Fetcher.REQUESTS,),
                    f"{source.name} should only have REQUESTS fetcher",
                )


class TestLyricsSourceDataclass:

    def test_is_frozen(self):
        source = LyricsSource(
            name="test",
            search=lambda t, a: [],
            parse=lambda h: None,
            fetchers=(Fetcher.REQUESTS,),
            romaji_quality=3,
        )
        try:
            source.name = "modified"
            raise AssertionError("LyricsSource should be frozen (immutable)")
        except AttributeError:
            pass  # expected

    def test_raw_parse_defaults_to_none(self):
        source = LyricsSource(
            name="test",
            search=lambda t, a: [],
            parse=lambda h: None,
            fetchers=(Fetcher.REQUESTS,),
            romaji_quality=3,
        )
        assert_is_none(source.raw_parse, "raw_parse should default to None")


class TestRawParseAssignments:

    def test_japanese_sources_have_raw_parse(self):
        sources = build_registry()
        japanese_sources = {"j_lyric", "nautiljon", "mojim"}
        for source in sources:
            if source.name in japanese_sources:
                assert_true(
                    callable(source.raw_parse),
                    f"{source.name} should have a callable raw_parse",
                )

    def test_non_japanese_sources_have_no_raw_parse(self):
        sources = build_registry()
        non_japanese = {"lyrical_nonsense", "animelyrics", "genius"}
        for source in sources:
            if source.name in non_japanese:
                assert_is_none(
                    source.raw_parse,
                    f"{source.name} should have raw_parse=None",
                )

    def test_raw_parse_j_lyric_extracts_japanese_text(self):
        from lyrics_fetcher.j_lyric import raw_parse_j_lyric
        html = _load_fixture("j_lyric_japanese.html")
        result = raw_parse_j_lyric(html)
        assert_is_not_none(result, "raw_parse_j_lyric should extract text")
        assert_in("風が吹いている", result)

    def test_raw_parse_nautiljon_extracts_japanese_text(self):
        from lyrics_fetcher.nautiljon import raw_parse_nautiljon
        html = _load_fixture("nautiljon_japanese.html")
        result = raw_parse_nautiljon(html)
        assert_is_not_none(result, "raw_parse_nautiljon should extract text")
        assert_in("風が吹いている", result)

    def test_raw_parse_mojim_extracts_japanese_text(self):
        from lyrics_fetcher.mojim import raw_parse_mojim
        html = _load_fixture("mojim_japanese.html")
        result = raw_parse_mojim(html)
        assert_is_not_none(result, "raw_parse_mojim should extract text")
        assert_in("風が吹いている", result)

    def test_raw_parse_mojim_trims_chinese_footer(self):
        from lyrics_fetcher.mojim import raw_parse_mojim
        html = _load_fixture("mojim_japanese.html")
        result = raw_parse_mojim(html)
        assert_is_not_none(result)
        assert_false(
            "更多更詳盡歌詞" in result,
            "Chinese footer should be trimmed from raw_parse output",
        )

    def test_raw_parse_j_lyric_returns_none_for_missing_element(self):
        from lyrics_fetcher.j_lyric import raw_parse_j_lyric
        html = _load_fixture("j_lyric_no_lyric.html")
        result = raw_parse_j_lyric(html)
        assert_is_none(result, "should return None when <p id='Lyric'> is absent")

    def test_raw_parse_nautiljon_returns_none_for_missing_element(self):
        from lyrics_fetcher.nautiljon import raw_parse_nautiljon
        html = _load_fixture("nautiljon_no_lyrics.html")
        result = raw_parse_nautiljon(html)
        assert_is_none(result, "should return None when lyrics span is absent")

    def test_raw_parse_mojim_returns_none_for_missing_element(self):
        from lyrics_fetcher.mojim import raw_parse_mojim
        html = _load_fixture("mojim_no_fsZx3.html")
        result = raw_parse_mojim(html)
        assert_is_none(result, "should return None when <dd id='fsZx3'> is absent")
