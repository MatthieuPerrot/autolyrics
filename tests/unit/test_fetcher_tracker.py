"""Unit tests for _FetcherTracker — thread-safe registry of active fetcher instances."""

import threading
from unittest.mock import MagicMock

from lyrics_fetcher.fallback import _FetcherTracker

from tests.helpers.assertions import (
    assert_equal,
    assert_len,
    assert_true,
)


class TestRegister:
    """register() adds fetcher instances to the internal list."""

    def test_register_single_fetcher(self):
        tracker = _FetcherTracker()
        fetcher = MagicMock()

        tracker.register(fetcher)

        tracker.stop_all()
        fetcher.stop.assert_called_once()

    def test_register_multiple_fetchers(self):
        tracker = _FetcherTracker()
        fetchers = [MagicMock() for _ in range(3)]

        for f in fetchers:
            tracker.register(f)

        tracker.stop_all()
        for f in fetchers:
            f.stop.assert_called_once()


class TestStopAll:
    """stop_all() calls stop on all registered fetchers and clears the list."""

    def test_calls_stop_on_all_registered(self):
        tracker = _FetcherTracker()
        fetchers = [MagicMock() for _ in range(4)]
        for f in fetchers:
            tracker.register(f)

        tracker.stop_all()

        for f in fetchers:
            f.stop.assert_called_once()

    def test_clears_list_after_stop_all(self):
        tracker = _FetcherTracker()
        fetcher = MagicMock()
        tracker.register(fetcher)

        tracker.stop_all()
        fetcher.stop.reset_mock()

        # Second stop_all should not call stop again (list was cleared)
        tracker.stop_all()
        fetcher.stop.assert_not_called()

    def test_idempotent_double_stop_all(self):
        tracker = _FetcherTracker()
        fetcher = MagicMock()
        tracker.register(fetcher)

        tracker.stop_all()
        tracker.stop_all()

        # stop() called exactly once (second stop_all is a noop)
        fetcher.stop.assert_called_once()


class TestStopAllIgnoresErrors:
    """stop() raising an exception should not prevent other fetchers from being stopped."""

    def test_error_in_stop_does_not_block_others(self):
        tracker = _FetcherTracker()

        failing_fetcher = MagicMock()
        failing_fetcher.stop.side_effect = RuntimeError("driver crash")

        healthy_fetcher = MagicMock()

        tracker.register(failing_fetcher)
        tracker.register(healthy_fetcher)

        # Should not raise
        tracker.stop_all()

        failing_fetcher.stop.assert_called_once()
        healthy_fetcher.stop.assert_called_once()


class TestThreadSafety:
    """Concurrent register + stop_all must not raise or lose fetchers."""

    def test_concurrent_register_and_stop_all(self):
        tracker = _FetcherTracker()
        stop_calls = []
        lock = threading.Lock()

        def counting_stop():
            with lock:
                stop_calls.append(1)

        def register_many():
            for _ in range(100):
                f = MagicMock()
                f.stop.side_effect = counting_stop
                tracker.register(f)

        threads = [threading.Thread(target=register_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        tracker.stop_all()

        # All 400 fetchers should have been stopped
        assert_equal(len(stop_calls), 400, "all registered fetchers should be stopped")
