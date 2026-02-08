"""Shared fixtures and path setup for the test suite."""

import os
import sys

import pytest

# Add the script/ directory to sys.path so `lyrics_fetcher` is importable
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_script_dir = os.path.join(_project_root, "script")
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def fixture_path():
    """Return a function that resolves a fixture filename to its full path."""
    def _resolve(filename):
        return os.path.join(FIXTURES_DIR, filename)
    return _resolve


@pytest.fixture
def load_fixture():
    """Return a function that reads a fixture file and returns its content."""
    def _load(filename):
        path = os.path.join(FIXTURES_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return _load
