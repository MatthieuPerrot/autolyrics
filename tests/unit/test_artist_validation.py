"""Unit tests for _html_mentions_artist word-boundary matching."""

from lyrics_fetcher.fallback import _html_mentions_artist

from tests.helpers.assertions import assert_true, assert_false


class TestRejectsSubstringFalsePositives:
    """Short artist names must not match inside longer words."""

    def test_ai_not_in_wait(self):
        assert_false(
            _html_mentions_artist("<html>WAIT for it</html>", ["AI"]),
            "'AI' should not match inside 'WAIT'",
        )

    def test_ai_not_in_said(self):
        assert_false(
            _html_mentions_artist("<html>She SAID hello</html>", ["AI"]),
            "'AI' should not match inside 'SAID'",
        )

    def test_ai_not_in_available(self):
        assert_false(
            _html_mentions_artist("<html>available now</html>", ["AI"]),
            "'AI' should not match inside 'available'",
        )

    def test_zard_not_in_wizard(self):
        assert_false(
            _html_mentions_artist("<html>The WIZARD of Oz</html>", ["ZARD"]),
            "'ZARD' should not match inside 'WIZARD'",
        )

    def test_zard_not_in_hazard(self):
        assert_false(
            _html_mentions_artist("<html>HAZARD warning</html>", ["ZARD"]),
            "'ZARD' should not match inside 'HAZARD'",
        )

    def test_do_not_in_done(self):
        assert_false(
            _html_mentions_artist("<html>DONE loading</html>", ["DO"]),
            "'DO' should not match inside 'DONE'",
        )

    def test_do_not_in_document(self):
        assert_false(
            _html_mentions_artist("<html>DOCUMENT ready</html>", ["DO"]),
            "'DO' should not match inside 'DOCUMENT'",
        )


class TestMatchesWholeWordArtistNames:
    """Artist names appearing as whole words must still match."""

    def test_ai_standalone(self):
        assert_true(
            _html_mentions_artist("<html>Song by AI - lyrics</html>", ["AI"]),
            "'AI' as a standalone word should match",
        )

    def test_zard_standalone(self):
        assert_true(
            _html_mentions_artist("<html>ZARD official page</html>", ["ZARD"]),
            "'ZARD' as a standalone word should match",
        )

    def test_two_mix_exact(self):
        assert_true(
            _html_mentions_artist("<html>TWO-MIX discography</html>", ["TWO-MIX"]),
            "'TWO-MIX' should match exactly",
        )

    def test_case_insensitive(self):
        assert_true(
            _html_mentions_artist("<html>zard official</html>", ["ZARD"]),
            "matching should be case-insensitive",
        )


class TestHyphenSpaceNormalization:
    """Hyphens and spaces are interchangeable between artist name and HTML."""

    def test_hyphenated_artist_matches_spaced_html(self):
        assert_true(
            _html_mentions_artist("<html>two mix songs</html>", ["TWO-MIX"]),
            "'TWO-MIX' should match 'two mix' in HTML",
        )

    def test_spaced_artist_matches_hyphenated_html(self):
        assert_true(
            _html_mentions_artist("<html>two-mix songs</html>", ["TWO MIX"]),
            "'TWO MIX' should match 'two-mix' in HTML",
        )


class TestSpecialCharactersInNames:
    """Special regex characters in artist names must be escaped properly."""

    def test_larc_en_ciel(self):
        assert_true(
            _html_mentions_artist(
                "<html>L'Arc~en~Ciel concert</html>", ["L'Arc~en~Ciel"]
            ),
            "L'Arc~en~Ciel with tildes should match",
        )

    def test_tm_revolution(self):
        assert_true(
            _html_mentions_artist(
                "<html>T.M.Revolution new album</html>", ["T.M.Revolution"]
            ),
            "T.M.Revolution with dots should match",
        )

    def test_dots_not_treated_as_wildcards(self):
        assert_false(
            _html_mentions_artist(
                "<html>TXMXRevolution</html>", ["T.M.Revolution"]
            ),
            "dots in artist name must not act as regex wildcards",
        )


class TestMultipleArtists:
    """When multiple artists are given, any match is sufficient."""

    def test_first_artist_matches(self):
        assert_true(
            _html_mentions_artist(
                "<html>ZARD best hits</html>", ["ZARD", "B'z"]
            ),
            "should match when first artist is present",
        )

    def test_second_artist_matches(self):
        assert_true(
            _html_mentions_artist(
                "<html>B'z greatest</html>", ["ZARD", "B'z"]
            ),
            "should match when second artist is present",
        )

    def test_none_matches(self):
        assert_false(
            _html_mentions_artist(
                "<html>Ayumi Hamasaki page</html>", ["ZARD", "B'z"]
            ),
            "should not match when no artist is present",
        )


class TestEdgeCases:
    """Edge cases: empty list, single-char names, boundary positions."""

    def test_empty_artist_list(self):
        assert_false(
            _html_mentions_artist("<html>anything</html>", []),
            "empty artist list should never match",
        )

    def test_single_char_artist_exact(self):
        assert_true(
            _html_mentions_artist("<html>Artist: X - Song</html>", ["X"]),
            "single-char artist 'X' as standalone word should match",
        )

    def test_single_char_artist_not_in_word(self):
        assert_false(
            _html_mentions_artist("<html>EXTRA lyrics</html>", ["X"]),
            "single-char artist 'X' should not match inside 'EXTRA'",
        )

    def test_artist_at_start_of_html(self):
        assert_true(
            _html_mentions_artist("ZARD lyrics page", ["ZARD"]),
            "artist at the very start of HTML should match",
        )

    def test_artist_at_end_of_html(self):
        assert_true(
            _html_mentions_artist("Lyrics by ZARD", ["ZARD"]),
            "artist at the very end of HTML should match",
        )


class TestUnicodeNormalization:
    """Unicode variants of punctuation must match their ASCII equivalents."""

    def test_wave_dash_matches_hyphen(self):
        assert_true(
            _html_mentions_artist(
                "<html>l'arc\u301Cen\u301Cciel</html>", ["L'Arc-en-Ciel"]
            ),
            "wave dash U+301C in HTML should match hyphen in artist name",
        )

    def test_curly_right_quote_matches_apostrophe(self):
        assert_true(
            _html_mentions_artist("<html>B\u2019z rocks</html>", ["B'z"]),
            "right curly quote U+2019 should match straight apostrophe",
        )

    def test_curly_left_quote_matches_apostrophe(self):
        assert_true(
            _html_mentions_artist("<html>B\u2018z rocks</html>", ["B'z"]),
            "left curly quote U+2018 should match straight apostrophe",
        )

    def test_fullwidth_ascii_matches_regular(self):
        assert_true(
            _html_mentions_artist(
                "<html>\uff34\uff37\uff2f\uff0d\uff2d\uff29\uff38</html>",
                ["TWO-MIX"],
            ),
            "fullwidth ASCII (NFKC) should match regular ASCII",
        )

    def test_em_dash_matches_hyphen(self):
        assert_true(
            _html_mentions_artist("<html>TWO\u2014MIX</html>", ["TWO-MIX"]),
            "em dash U+2014 should match hyphen",
        )

    def test_en_dash_matches_hyphen(self):
        assert_true(
            _html_mentions_artist("<html>TWO\u2013MIX</html>", ["TWO-MIX"]),
            "en dash U+2013 should match hyphen",
        )

    def test_mixed_unicode_variants(self):
        assert_true(
            _html_mentions_artist(
                "<html>L\u2019Arc\u301Cen\u301CCiel</html>",
                ["L'Arc-en-Ciel"],
            ),
            "mixed curly quote + wave dash should match straight quote + hyphen",
        )
