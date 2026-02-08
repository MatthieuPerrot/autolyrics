"""Quality gate for fetched lyrics.

Decides whether a parse result is good enough to accept immediately
or whether the orchestrator should keep trying other sources.
"""

from dataclasses import dataclass
from typing import Optional

from .language_detector import detect_lyrics_language

_MIN_LENGTH = 50   # characters — shorter than ~1 couplet is suspicious
_MIN_LINES = 4     # a real song has at least a few lines

_INCOMPLETE_MARKERS = [
    "to be transcribed",
    "lyrics not available",
    "paroles non disponibles",
    "we don't have this lyrics",
]


@dataclass(frozen=True)
class QualityResult:
    is_acceptable: bool
    detected_language: str
    rejection_reason: Optional[str]  # "too_short", "too_few_lines", "incomplete_marker", "wrong_language", None


def assess_quality(lyrics: str) -> QualityResult:
    """Assess lyrics quality and detect language.

    Returns a QualityResult with acceptance decision, detected language,
    and rejection reason (if any).
    """
    stripped = lyrics.strip()
    if len(stripped) < _MIN_LENGTH:
        return QualityResult(False, "unknown", "too_short")
    if stripped.count("\n") + 1 < _MIN_LINES:
        return QualityResult(False, "unknown", "too_few_lines")
    if any(marker in lyrics.lower() for marker in _INCOMPLETE_MARKERS):
        return QualityResult(False, "unknown", "incomplete_marker")
    detected = detect_lyrics_language(lyrics)
    if detected != "romaji":
        return QualityResult(False, detected, "wrong_language")
    return QualityResult(True, "romaji", None)


def is_acceptable(lyrics: str) -> bool:
    """Return True if lyrics meet minimum quality criteria."""
    return assess_quality(lyrics).is_acceptable
