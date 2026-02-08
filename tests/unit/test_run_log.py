"""Unit tests for the run_log module: event model, RunLog, summary, JSONL."""

import json
import threading

from lyrics_fetcher.run_log import SearchEvent, FetchEvent, RunLog

from tests.helpers.assertions import (
    assert_equal,
    assert_isinstance,
    assert_true,
    assert_false,
    assert_len,
    assert_greater,
    assert_greater_equal,
    assert_contains_text,
    assert_in,
    assert_not_in,
)


# ---------------------------------------------------------------------------
# SearchEvent
# ---------------------------------------------------------------------------

class TestSearchEvent:

    def test_stores_all_fields(self):
        ev = SearchEvent(
            source_name="lyrical_nonsense",
            duration=1.2,
            num_urls_found=3,
        )
        assert_equal(ev.source_name, "lyrical_nonsense")
        assert_equal(ev.duration, 1.2)
        assert_equal(ev.num_urls_found, 3)
        assert_equal(ev.error, None)

    def test_stores_error(self):
        ev = SearchEvent(
            source_name="animelyrics",
            duration=0.0,
            num_urls_found=0,
            error="ConnectionTimeout",
        )
        assert_equal(ev.error, "ConnectionTimeout")

    def test_is_frozen(self):
        ev = SearchEvent(source_name="a", duration=0.1, num_urls_found=1)
        try:
            ev.source_name = "b"
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# FetchEvent
# ---------------------------------------------------------------------------

class TestFetchEvent:

    def test_stores_all_fields(self):
        ev = FetchEvent(
            source_name="lyrical_nonsense",
            fetcher_type="requests",
            url="http://example.com",
            phase=1,
            duration=0.8,
            http_status=200,
            fetch_ok=True,
            parse_ok=True,
            lyrics_length=342,
        )
        assert_equal(ev.source_name, "lyrical_nonsense")
        assert_equal(ev.fetcher_type, "requests")
        assert_equal(ev.url, "http://example.com")
        assert_equal(ev.phase, 1)
        assert_equal(ev.duration, 0.8)
        assert_equal(ev.http_status, 200)
        assert_true(ev.fetch_ok)
        assert_true(ev.parse_ok)
        assert_equal(ev.lyrics_length, 342)
        assert_equal(ev.error, None)
        assert_false(ev.converted)

    def test_converted_defaults_to_false(self):
        ev = FetchEvent(
            source_name="src", fetcher_type="requests", url="http://x",
            phase=1, duration=0.1, http_status=200,
            fetch_ok=True, parse_ok=True, lyrics_length=100,
        )
        assert_false(ev.converted)

    def test_converted_can_be_set_true(self):
        ev = FetchEvent(
            source_name="j_lyric", fetcher_type="requests", url="http://x",
            phase=1, duration=1.4, http_status=200,
            fetch_ok=True, parse_ok=True, lyrics_length=1689,
            converted=True,
        )
        assert_true(ev.converted)

    def test_stores_error(self):
        ev = FetchEvent(
            source_name="animelyrics",
            fetcher_type="selenium",
            url="http://example.com",
            phase=2,
            duration=5.3,
            http_status=0,
            fetch_ok=False,
            parse_ok=False,
            lyrics_length=0,
            error="TimeoutError",
        )
        assert_equal(ev.error, "TimeoutError")

    def test_is_frozen(self):
        ev = FetchEvent(
            source_name="a", fetcher_type="requests", url="http://x",
            phase=1, duration=0.1, http_status=200,
            fetch_ok=True, parse_ok=True, lyrics_length=10,
        )
        try:
            ev.phase = 2
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# RunLog core
# ---------------------------------------------------------------------------

class TestRunLogAddEvents:

    def test_starts_empty(self):
        log = RunLog("TITLE", ["ARTIST"])
        assert_len(log.search_events, 0)
        assert_len(log.fetch_events, 0)

    def test_stores_title_and_artists(self):
        log = RunLog("WHITE REFLECTION", ["TWO-MIX"])
        assert_equal(log.title, "WHITE REFLECTION")
        assert_equal(log.artists, ["TWO-MIX"])

    def test_add_search_event(self):
        log = RunLog("T", ["A"])
        ev = SearchEvent(source_name="src", duration=1.0, num_urls_found=2)
        log.add_search_event(ev)
        assert_len(log.search_events, 1)
        assert_equal(log.search_events[0], ev)

    def test_add_fetch_event(self):
        log = RunLog("T", ["A"])
        ev = FetchEvent(
            source_name="src", fetcher_type="requests", url="http://x",
            phase=1, duration=0.5, http_status=200,
            fetch_ok=True, parse_ok=True, lyrics_length=100,
        )
        log.add_fetch_event(ev)
        assert_len(log.fetch_events, 1)
        assert_equal(log.fetch_events[0], ev)

    def test_returns_copies_not_references(self):
        log = RunLog("T", ["A"])
        ev = SearchEvent(source_name="src", duration=1.0, num_urls_found=2)
        log.add_search_event(ev)
        # Mutating the returned list should not affect internal state
        log.search_events.append("junk")
        assert_len(log.search_events, 1)

    def test_total_duration(self):
        log = RunLog("T", ["A"])
        log.add_search_event(SearchEvent("a", duration=1.0, num_urls_found=0))
        log.add_search_event(SearchEvent("b", duration=2.0, num_urls_found=0))
        log.add_fetch_event(FetchEvent(
            source_name="a", fetcher_type="requests", url="http://x",
            phase=1, duration=0.5, http_status=200,
            fetch_ok=True, parse_ok=True, lyrics_length=10,
        ))
        assert_greater_equal(log.total_duration, 3.5)

    def test_thread_safety(self):
        log = RunLog("T", ["A"])
        errors = []

        def add_events(n):
            try:
                for i in range(n):
                    log.add_search_event(
                        SearchEvent(f"src_{i}", duration=0.01, num_urls_found=1)
                    )
                    log.add_fetch_event(
                        FetchEvent(
                            source_name=f"src_{i}", fetcher_type="requests",
                            url="http://x", phase=1, duration=0.01,
                            http_status=200, fetch_ok=True, parse_ok=True,
                            lyrics_length=10,
                        )
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_events, args=(50,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert_len(errors, 0, "concurrent add should not raise errors")
        assert_len(log.search_events, 200)
        assert_len(log.fetch_events, 200)


# ---------------------------------------------------------------------------
# F1: format_summary
# ---------------------------------------------------------------------------

class TestRunLogFormatSummary:

    def _make_populated_log(self):
        log = RunLog("WHITE REFLECTION", ["TWO-MIX"])
        log.add_search_event(SearchEvent("lyrical_nonsense", 1.2, 3))
        log.add_search_event(SearchEvent("animelyrics", 0.0, 0, error="ConnectionTimeout"))
        log.add_fetch_event(FetchEvent(
            source_name="lyrical_nonsense", fetcher_type="requests",
            url="http://lyrical.example.com/lyrics", phase=1,
            duration=0.8, http_status=200, fetch_ok=True, parse_ok=True,
            lyrics_length=342,
        ))
        log.add_fetch_event(FetchEvent(
            source_name="animelyrics", fetcher_type="selenium",
            url="http://anime.example.com/lyrics", phase=2,
            duration=5.3, http_status=0, fetch_ok=False, parse_ok=False,
            lyrics_length=0,
        ))
        return log

    def test_contains_run_header(self):
        log = self._make_populated_log()
        summary = log.format_summary()
        assert_contains_text(summary, "WHITE REFLECTION")
        assert_contains_text(summary, "TWO-MIX")

    def test_contains_search_section(self):
        log = self._make_populated_log()
        summary = log.format_summary()
        assert_contains_text(summary, "lyrical_nonsense")
        assert_contains_text(summary, "ConnectionTimeout")

    def test_contains_fetch_section(self):
        log = self._make_populated_log()
        summary = log.format_summary()
        assert_contains_text(summary, "parse_ok")
        assert_contains_text(summary, "fetch_fail")

    def test_contains_total_duration(self):
        log = self._make_populated_log()
        summary = log.format_summary()
        assert_contains_text(summary, "Total:")

    def test_fetch_status_mapping_parse_fail(self):
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="src", fetcher_type="requests",
            url="http://x", phase=1, duration=0.1,
            http_status=200, fetch_ok=True, parse_ok=False, lyrics_length=0,
        ))
        summary = log.format_summary()
        assert_contains_text(summary, "parse_fail")

    def test_empty_log_does_not_crash(self):
        log = RunLog("T", ["A"])
        summary = log.format_summary()
        assert_isinstance(summary, str)

    def test_converted_result_shows_in_result_line(self):
        log = RunLog("unravel", ["Ado"])
        log.add_fetch_event(FetchEvent(
            source_name="j_lyric", fetcher_type="requests",
            url="http://j-lyric.net/song", phase=1,
            duration=1.4, http_status=200, fetch_ok=True, parse_ok=True,
            lyrics_length=1689, converted=True,
        ))
        summary = log.format_summary()
        assert_contains_text(summary, "1689 chars, converted")

    def test_converted_shows_in_fetch_section(self):
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="j_lyric", fetcher_type="requests",
            url="http://j-lyric.net/song", phase=1,
            duration=1.4, http_status=200, fetch_ok=True, parse_ok=True,
            lyrics_length=1689, converted=True,
        ))
        summary = log.format_summary()
        # In the fetch section, status should be "converted" not "parse_ok"
        assert_contains_text(summary, "converted")

    def test_native_result_does_not_show_converted(self):
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="animelyrics", fetcher_type="requests",
            url="http://animelyrics.com/song", phase=1,
            duration=0.8, http_status=200, fetch_ok=True, parse_ok=True,
            lyrics_length=500,
        ))
        summary = log.format_summary()
        assert_not_in("converted", summary)


# ---------------------------------------------------------------------------
# F2: to_jsonl
# ---------------------------------------------------------------------------

class TestRunLogToJsonl:

    def test_first_line_is_run_header(self):
        log = RunLog("WHITE REFLECTION", ["TWO-MIX"])
        log.add_search_event(SearchEvent("src", 1.0, 2))
        jsonl = log.to_jsonl()
        lines = jsonl.strip().split("\n")
        header = json.loads(lines[0])
        assert_equal(header["type"], "run_header")
        assert_equal(header["title"], "WHITE REFLECTION")
        assert_equal(header["artists"], ["TWO-MIX"])
        assert_in("timestamp", header)
        assert_in("total_duration", header)

    def test_search_events_serialized(self):
        log = RunLog("T", ["A"])
        log.add_search_event(SearchEvent("src", 1.0, 2))
        jsonl = log.to_jsonl()
        lines = jsonl.strip().split("\n")
        search_lines = [json.loads(l) for l in lines if json.loads(l)["type"] == "search"]
        assert_len(search_lines, 1)
        assert_equal(search_lines[0]["source_name"], "src")

    def test_fetch_events_serialized(self):
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="src", fetcher_type="requests", url="http://x",
            phase=1, duration=0.5, http_status=200,
            fetch_ok=True, parse_ok=True, lyrics_length=100,
        ))
        jsonl = log.to_jsonl()
        lines = jsonl.strip().split("\n")
        fetch_lines = [json.loads(l) for l in lines if json.loads(l)["type"] == "fetch"]
        assert_len(fetch_lines, 1)
        assert_equal(fetch_lines[0]["source_name"], "src")
        assert_equal(fetch_lines[0]["fetcher_type"], "requests")

    def test_each_line_is_valid_json(self):
        log = RunLog("T", ["A"])
        log.add_search_event(SearchEvent("s1", 1.0, 2))
        log.add_fetch_event(FetchEvent(
            source_name="s1", fetcher_type="requests", url="http://x",
            phase=1, duration=0.5, http_status=200,
            fetch_ok=True, parse_ok=True, lyrics_length=100,
        ))
        jsonl = log.to_jsonl()
        for line in jsonl.strip().split("\n"):
            parsed = json.loads(line)
            assert_isinstance(parsed, dict)

    def test_converted_field_serialized_in_jsonl(self):
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="j_lyric", fetcher_type="requests", url="http://x",
            phase=1, duration=1.4, http_status=200,
            fetch_ok=True, parse_ok=True, lyrics_length=1689,
            converted=True,
        ))
        jsonl = log.to_jsonl()
        lines = jsonl.strip().split("\n")
        fetch_lines = [json.loads(l) for l in lines if json.loads(l)["type"] == "fetch"]
        assert_len(fetch_lines, 1)
        assert_true(fetch_lines[0]["converted"])

    def test_empty_log_produces_header_only(self):
        log = RunLog("T", ["A"])
        jsonl = log.to_jsonl()
        lines = jsonl.strip().split("\n")
        assert_len(lines, 1)
        header = json.loads(lines[0])
        assert_equal(header["type"], "run_header")

    def test_detected_language_serialized_in_jsonl(self):
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="nautiljon", fetcher_type="requests", url="http://x",
            phase=1, duration=0.5, http_status=200,
            fetch_ok=True, parse_ok=False, lyrics_length=0,
            detected_language="english",
        ))
        jsonl = log.to_jsonl()
        lines = jsonl.strip().split("\n")
        fetch_lines = [json.loads(l) for l in lines if json.loads(l)["type"] == "fetch"]
        assert_len(fetch_lines, 1)
        assert_equal(fetch_lines[0]["detected_language"], "english")


# ---------------------------------------------------------------------------
# FetchEvent.detected_language
# ---------------------------------------------------------------------------

class TestFetchEventDetectedLanguage:

    def test_defaults_to_none(self):
        ev = FetchEvent(
            source_name="src", fetcher_type="requests", url="http://x",
            phase=1, duration=0.1, http_status=200,
            fetch_ok=True, parse_ok=False, lyrics_length=0,
        )
        assert_equal(ev.detected_language, None)

    def test_can_be_set(self):
        ev = FetchEvent(
            source_name="src", fetcher_type="requests", url="http://x",
            phase=1, duration=0.1, http_status=200,
            fetch_ok=True, parse_ok=False, lyrics_length=0,
            detected_language="english",
        )
        assert_equal(ev.detected_language, "english")


# ---------------------------------------------------------------------------
# _fetch_status with detected_language
# ---------------------------------------------------------------------------

class TestFetchStatusWithLanguage:

    def test_rejected_english_lyrics(self):
        """Lyrics parsed but wrong language → status should be 'rejected (english)'."""
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="genius", fetcher_type="requests",
            url="http://genius.example.com", phase=1,
            duration=0.5, http_status=200, fetch_ok=True, parse_ok=True,
            lyrics_length=200, detected_language="english",
        ))
        summary = log.format_summary()
        assert_contains_text(
            summary, "rejected (english)",
            "wrong-language lyrics should show 'rejected (language)'",
        )

    def test_rejected_non_romaji_latin(self):
        """French lyrics parsed → status should be 'rejected (non_romaji_latin)'."""
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="nautiljon", fetcher_type="requests",
            url="http://nautiljon.example.com", phase=1,
            duration=0.3, http_status=200, fetch_ok=True, parse_ok=True,
            lyrics_length=300, detected_language="non_romaji_latin",
        ))
        summary = log.format_summary()
        assert_contains_text(summary, "rejected (non_romaji_latin)")

    def test_rejected_japanese_lyrics(self):
        """Japanese lyrics parsed → status should be 'rejected (japanese)'."""
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="j_lyric", fetcher_type="requests",
            url="http://j-lyric.example.com", phase=1,
            duration=0.5, http_status=200, fetch_ok=True, parse_ok=True,
            lyrics_length=400, detected_language="japanese",
        ))
        summary = log.format_summary()
        assert_contains_text(summary, "rejected (japanese)")

    def test_romaji_not_rejected(self):
        """Romaji lyrics should show 'parse_ok', not 'rejected'."""
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="animelyrics", fetcher_type="requests",
            url="http://animelyrics.example.com", phase=1,
            duration=0.5, http_status=200, fetch_ok=True, parse_ok=True,
            lyrics_length=300, detected_language="romaji",
        ))
        summary = log.format_summary()
        assert_not_in("rejected", summary)
        assert_contains_text(summary, "parse_ok")

    def test_parse_fail_without_language(self):
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="src", fetcher_type="requests",
            url="http://x", phase=1,
            duration=0.1, http_status=200, fetch_ok=True, parse_ok=False,
            lyrics_length=0,
        ))
        summary = log.format_summary()
        assert_contains_text(summary, "parse_fail")
        assert_not_in("rejected", summary)


# ---------------------------------------------------------------------------
# format_summary: result line with best rejected language
# ---------------------------------------------------------------------------

class TestSummaryBestRejectedLanguage:

    def test_no_result_shows_best_rejected_language(self):
        """When only wrong-language lyrics found, result line shows best rejected."""
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="src", fetcher_type="requests",
            url="http://x", phase=1,
            duration=0.5, http_status=200, fetch_ok=True, parse_ok=True,
            lyrics_length=200, detected_language="english",
        ))
        summary = log.format_summary()
        assert_contains_text(summary, "none (best: english)")

    def test_no_result_without_language_shows_plain_none(self):
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="src", fetcher_type="requests",
            url="http://x", phase=1,
            duration=0.5, http_status=200, fetch_ok=False, parse_ok=False,
            lyrics_length=0,
        ))
        summary = log.format_summary()
        assert_contains_text(summary, "Result: none")
        assert_not_in("best:", summary)

    def test_rejected_event_not_counted_as_success(self):
        """A rejected (wrong-language) event should not appear in Result line as success."""
        log = RunLog("T", ["A"])
        log.add_fetch_event(FetchEvent(
            source_name="genius", fetcher_type="requests",
            url="http://genius.example.com", phase=1,
            duration=0.5, http_status=200, fetch_ok=True, parse_ok=True,
            lyrics_length=200, detected_language="english",
        ))
        summary = log.format_summary()
        assert_not_in("Result: genius", summary)
        assert_contains_text(summary, "Result: none")
