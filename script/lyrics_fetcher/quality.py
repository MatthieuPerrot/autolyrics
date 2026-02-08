"""Quality gate for fetched lyrics.

Decides whether a parse result is good enough to accept immediately
or whether the orchestrator should keep trying other sources.
"""

from .language_detector import is_likely_romaji

_MIN_LENGTH = 50   # characters — shorter than ~1 couplet is suspicious
_MIN_LINES = 4     # a real song has at least a few lines

_INCOMPLETE_MARKERS = [
    "to be transcribed",
    "lyrics not available",
    "paroles non disponibles",
    "we don't have this lyrics",
]


def is_acceptable(lyrics: str) -> bool:
    """Return True if lyrics meet minimum quality criteria."""
    stripped = lyrics.strip()
    if len(stripped) < _MIN_LENGTH:
        return False
    if stripped.count("\n") + 1 < _MIN_LINES:
        return False
    if any(marker in lyrics.lower() for marker in _INCOMPLETE_MARKERS):
        return False
    if not is_likely_romaji(lyrics):
        return False
    return True
