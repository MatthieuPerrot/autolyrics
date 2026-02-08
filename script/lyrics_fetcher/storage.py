"""Persistent storage for autolyrics run logs and future caches.

All data is stored under ~/.autolyrics/ with subdirectories:
  - logs/   — JSONL run logs (one file per day)
  - stats/  — future: aggregated statistics
  - cache/  — future: cached search results
"""

from datetime import date
from pathlib import Path

_BASE_DIR = Path.home() / ".autolyrics"


def base_dir() -> Path:
    return _BASE_DIR


def ensure_dirs() -> None:
    """Create the storage directory tree (idempotent)."""
    for sub in ("logs", "stats", "cache"):
        (_BASE_DIR / sub).mkdir(parents=True, exist_ok=True)


def log_dir() -> Path:
    return _BASE_DIR / "logs"


def append_log(jsonl_content: str, log_date: date = None) -> Path:
    """Append JSONL content to the daily log file.

    Args:
        jsonl_content: JSONL string to append (should end with newline).
        log_date: Date for the log filename (default: today).

    Returns:
        Path to the log file written to.
    """
    if log_date is None:
        log_date = date.today()

    ensure_dirs()
    path = log_dir() / f"{log_date.isoformat()}.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(jsonl_content)
        if not jsonl_content.endswith("\n"):
            f.write("\n")
    return path
