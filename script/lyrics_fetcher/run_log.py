"""Event model and run log for lyrics fetch operations.

Records SearchEvent and FetchEvent instances during a lyrics fetch run,
then produces a human-readable summary (format_summary) or a machine-readable
JSONL export (to_jsonl).  Thread-safe for concurrent search (parallel search).
"""

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class SearchEvent:
    source_name: str
    duration: float           # seconds
    num_urls_found: int
    error: Optional[str] = None


@dataclass(frozen=True)
class FetchEvent:
    source_name: str
    fetcher_type: str         # "requests", "selenium", "chrome_fetcher"
    url: str
    phase: int                # 1, 2, or 3
    duration: float
    http_status: int
    fetch_ok: bool
    parse_ok: bool
    lyrics_length: int
    error: Optional[str] = None
    converted: bool = False
    detected_language: Optional[str] = None


def _fetch_status(ev: FetchEvent) -> str:
    """Map fetch/parse booleans to a human-readable status label."""
    if not ev.fetch_ok:
        return "fetch_fail"
    if not ev.parse_ok:
        return "parse_fail"
    if ev.detected_language and ev.detected_language != "romaji":
        return f"rejected ({ev.detected_language})"
    if ev.converted:
        return "converted"
    return "parse_ok"


class RunLog:
    """Collects events for a single lyrics fetch run."""

    def __init__(self, title: str, artists: list[str]):
        self.title = title
        self.artists = list(artists)
        self._search_events: list[SearchEvent] = []
        self._fetch_events: list[FetchEvent] = []
        self._lock = threading.Lock()

    # -- thread-safe add -------------------------------------------------------

    def add_search_event(self, event: SearchEvent) -> None:
        with self._lock:
            self._search_events.append(event)

    def add_fetch_event(self, event: FetchEvent) -> None:
        with self._lock:
            self._fetch_events.append(event)

    # -- read access (copies) --------------------------------------------------

    @property
    def search_events(self) -> list[SearchEvent]:
        with self._lock:
            return list(self._search_events)

    @property
    def fetch_events(self) -> list[FetchEvent]:
        with self._lock:
            return list(self._fetch_events)

    @property
    def total_duration(self) -> float:
        with self._lock:
            total = sum(e.duration for e in self._search_events)
            total += sum(e.duration for e in self._fetch_events)
            return total

    # -- F1: human-readable summary --------------------------------------------

    def format_summary(self) -> str:
        lines = []
        artists_str = " ".join(self.artists)
        lines.append(f"=== Run Summary: {self.title} - {artists_str} ===")
        lines.append("")

        # Search section
        search_evts = self.search_events
        if search_evts:
            lines.append("Search:")
            lines.append(f"  {'Source':<24} {'Duration':>8}  {'URLs':>4}  Status")
            for ev in search_evts:
                status = f"ERROR: {ev.error}" if ev.error else "ok"
                lines.append(
                    f"  {ev.source_name:<24} {ev.duration:>7.1f}s  {ev.num_urls_found:>4}  {status}"
                )
            lines.append("")

        # Fetch section
        fetch_evts = self.fetch_events
        if fetch_evts:
            lines.append("Fetch:")
            lines.append(
                f"  {'Source':<24} {'Fetcher':<16} {'Phase':>5}  "
                f"{'Duration':>8}  {'Status':<12} URL"
            )
            for ev in fetch_evts:
                status = _fetch_status(ev)
                lines.append(
                    f"  {ev.source_name:<24} {ev.fetcher_type:<16} {ev.phase:>5}  "
                    f"{ev.duration:>7.1f}s  {status:<12} {ev.url}"
                )
            lines.append("")

        # Result line — exclude rejected (wrong-language) events
        def _is_accepted(e):
            if not e.fetch_ok or not e.parse_ok:
                return False
            if e.detected_language and e.detected_language != "romaji":
                return False
            return True

        success = [e for e in fetch_evts if _is_accepted(e)]
        if success:
            best = success[0]
            suffix = ", converted" if best.converted else ""
            result_str = f"{best.source_name} ({best.lyrics_length} chars{suffix})"
        else:
            best_lang = next(
                (e.detected_language for e in fetch_evts if e.detected_language),
                None,
            )
            if best_lang:
                result_str = f"none (best: {best_lang})"
            else:
                result_str = "none"
        lines.append(f"Total: {self.total_duration:.1f}s | Result: {result_str}")

        return "\n".join(lines)

    # -- F2: JSONL export ------------------------------------------------------

    def to_jsonl(self) -> str:
        lines = []

        header = {
            "type": "run_header",
            "title": self.title,
            "artists": self.artists,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_duration": self.total_duration,
        }
        lines.append(json.dumps(header, ensure_ascii=False))

        for ev in self.search_events:
            record = asdict(ev)
            record["type"] = "search"
            lines.append(json.dumps(record, ensure_ascii=False))

        for ev in self.fetch_events:
            record = asdict(ev)
            record["type"] = "fetch"
            lines.append(json.dumps(record, ensure_ascii=False))

        return "\n".join(lines)
