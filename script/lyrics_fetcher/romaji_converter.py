"""Convert Japanese text (kanji/kana) to romaji using cutlet.

Lazy-initializes the cutlet instance on first use. If cutlet is not installed,
all conversion calls gracefully return None.
"""

from .language_detector import contains_japanese_characters

_cutlet_instance = None
_cutlet_available = None  # None=unknown, True/False after first check


def _get_cutlet():
    """Lazy-init cutlet.Cutlet, return None if unavailable."""
    global _cutlet_instance, _cutlet_available

    if _cutlet_available is False:
        return None
    if _cutlet_instance is not None:
        return _cutlet_instance

    try:
        import cutlet
        _cutlet_instance = cutlet.Cutlet()
        _cutlet_available = True
        return _cutlet_instance
    except ImportError:
        _cutlet_available = False
        return None


def japanese_to_romaji(text: str) -> str | None:
    """Convert Japanese text to romaji. Returns None if not Japanese or unavailable."""
    if not text or not text.strip():
        return None

    if not contains_japanese_characters(text):
        return None

    converter = _get_cutlet()
    if converter is None:
        return None

    try:
        lines = text.split("\n")
        converted_lines = []
        for line in lines:
            if not line.strip():
                converted_lines.append("")
            else:
                converted_lines.append(converter.romaji(line))
        return "\n".join(converted_lines)
    except Exception:
        return None
