"""Unit tests for the storage module: persistent JSONL log storage."""

from datetime import date
from pathlib import Path

import lyrics_fetcher.storage as storage

from tests.helpers.assertions import (
    assert_equal,
    assert_true,
    assert_contains_text,
    assert_isinstance,
)


class TestEnsureDirs:

    def test_creates_logs_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_BASE_DIR", tmp_path / ".autolyrics")
        storage.ensure_dirs()
        assert_true((tmp_path / ".autolyrics" / "logs").is_dir())

    def test_creates_stats_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_BASE_DIR", tmp_path / ".autolyrics")
        storage.ensure_dirs()
        assert_true((tmp_path / ".autolyrics" / "stats").is_dir())

    def test_creates_cache_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_BASE_DIR", tmp_path / ".autolyrics")
        storage.ensure_dirs()
        assert_true((tmp_path / ".autolyrics" / "cache").is_dir())

    def test_is_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_BASE_DIR", tmp_path / ".autolyrics")
        storage.ensure_dirs()
        storage.ensure_dirs()
        assert_true((tmp_path / ".autolyrics" / "logs").is_dir())


class TestBaseDir:

    def test_returns_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_BASE_DIR", tmp_path / ".autolyrics")
        result = storage.base_dir()
        assert_isinstance(result, Path)
        assert_equal(result, tmp_path / ".autolyrics")


class TestLogDir:

    def test_returns_logs_subdir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_BASE_DIR", tmp_path / ".autolyrics")
        result = storage.log_dir()
        assert_equal(result, tmp_path / ".autolyrics" / "logs")


class TestAppendLog:

    def test_creates_file_with_date(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_BASE_DIR", tmp_path / ".autolyrics")
        log_date = date(2025, 6, 15)
        path = storage.append_log('{"type": "run_header"}\n', log_date=log_date)
        assert_equal(path.name, "2025-06-15.jsonl")
        assert_true(path.exists())

    def test_appends_content(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_BASE_DIR", tmp_path / ".autolyrics")
        log_date = date(2025, 6, 15)
        storage.append_log('{"type": "run_header", "run": 1}\n', log_date=log_date)
        storage.append_log('{"type": "run_header", "run": 2}\n', log_date=log_date)
        content = (tmp_path / ".autolyrics" / "logs" / "2025-06-15.jsonl").read_text()
        assert_contains_text(content, '"run": 1')
        assert_contains_text(content, '"run": 2')

    def test_creates_dirs_automatically(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_BASE_DIR", tmp_path / ".autolyrics")
        # directories don't exist yet
        path = storage.append_log('{"test": true}\n', log_date=date(2025, 1, 1))
        assert_true(path.exists())

    def test_returns_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_BASE_DIR", tmp_path / ".autolyrics")
        path = storage.append_log('{"test": true}\n', log_date=date(2025, 1, 1))
        assert_isinstance(path, Path)

    def test_defaults_to_today(self, tmp_path, monkeypatch):
        monkeypatch.setattr(storage, "_BASE_DIR", tmp_path / ".autolyrics")
        path = storage.append_log('{"test": true}\n')
        today = date.today().isoformat()
        assert_equal(path.name, f"{today}.jsonl")
