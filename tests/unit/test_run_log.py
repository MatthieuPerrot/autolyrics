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

    def test_empty_log_produces_header_only(self):
        log = RunLog("T", ["A"])
        jsonl = log.to_jsonl()
        lines = jsonl.strip().split("\n")
        assert_len(lines, 1)
        header = json.loads(lines[0])
        assert_equal(header["type"], "run_header")
