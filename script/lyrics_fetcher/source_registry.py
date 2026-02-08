"""Registry of lyrics sources with their fetcher capabilities and quality ratings."""

from enum import Enum
from dataclasses import dataclass
from typing import Callable, Optional


class Fetcher(Enum):
    REQUESTS = "requests"              # ~2s, plain HTTP
    SELENIUM = "selenium"              # ~5-10s, headless ChromeDriver
    CHROME_FETCHER = "chrome_fetcher"  # ~45-60s, Xvfb + Chrome + remote debug


@dataclass(frozen=True)
class LyricsSource:
    name: str
    search: Callable      # (title, artists) -> list[str]  (URLs)
    parse: Callable       # (html) -> str|None  (lyrics)
    fetchers: tuple       # ordered tuple of Fetcher values to try
    romaji_quality: int   # 1-5, higher = better romaji output
    raw_parse: object = None  # (html) -> str|None — extract text without romaji check


def build_registry() -> list[LyricsSource]:
    """Build the source registry with lazy imports to avoid circular dependencies."""
    from .lyrical_nonsense import search_lyrical_nonsense, parse_lyrical_nonsense
    from .animelyrics import search_animelyrics, parse_animelyrics
    from .nautiljon import search_nautiljon, parse_nautiljon, raw_parse_nautiljon
    from .genius import search_genius, parse_genius
    from .j_lyric import search_j_lyric, parse_j_lyric, raw_parse_j_lyric
    from .mojim import search_mojim, parse_mojim, raw_parse_mojim

    return [
        LyricsSource(
            name="lyrical_nonsense",
            search=search_lyrical_nonsense,
            parse=parse_lyrical_nonsense,
            fetchers=(Fetcher.REQUESTS,),
            romaji_quality=5,
        ),
        LyricsSource(
            name="animelyrics",
            search=search_animelyrics,
            parse=parse_animelyrics,
            fetchers=(Fetcher.REQUESTS, Fetcher.SELENIUM, Fetcher.CHROME_FETCHER),
            romaji_quality=5,
        ),
        LyricsSource(
            name="nautiljon",
            search=search_nautiljon,
            parse=parse_nautiljon,
            fetchers=(Fetcher.REQUESTS, Fetcher.SELENIUM),
            romaji_quality=3,
            raw_parse=raw_parse_nautiljon,
        ),
        LyricsSource(
            name="genius",
            search=search_genius,
            parse=parse_genius,
            fetchers=(Fetcher.REQUESTS,),
            romaji_quality=2,
        ),
        LyricsSource(
            name="j_lyric",
            search=search_j_lyric,
            parse=parse_j_lyric,
            fetchers=(Fetcher.REQUESTS,),
            romaji_quality=1,
            raw_parse=raw_parse_j_lyric,
        ),
        LyricsSource(
            name="mojim",
            search=search_mojim,
            parse=parse_mojim,
            fetchers=(Fetcher.REQUESTS,),
            romaji_quality=1,
            raw_parse=raw_parse_mojim,
        ),
    ]
