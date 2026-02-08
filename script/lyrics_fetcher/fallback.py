"""Per-source concurrent pipeline lyrics orchestrator.

Two-level concurrency:
  - Inter-source: each source runs its own pipeline in parallel
  - Intra-source: after REQUESTS returns 403, all remaining fetchers
    for that source launch in parallel (Selenium || Chrome || ...)

Any fetcher from any source that finds acceptable lyrics triggers
immediate early-exit for everything else via a shared threading.Event.
"""

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests as requests_lib
from bs4 import BeautifulSoup

from .quality import is_acceptable
from .run_log import RunLog, SearchEvent, FetchEvent
from .source_registry import Fetcher, build_registry
from .storage import append_log


# HTTP 403 status code indicates Cloudflare or bot-protection blocking
_STATUS_403 = 403

# Parenthesized language markers in URLs that indicate non-romaji content
_NON_ROMAJI_URL_PATTERN = re.compile(
    r'\('
    r'(?:english|eng|français|french|fr|spanish|español|chinese|korean'
    r'|deutsch|german|italian|italiano|portuguese|russian)'
    r'\)',
    re.IGNORECASE,
)


def _is_non_romaji_language_url(url: str) -> bool:
    """Return True if URL contains a language marker indicating non-romaji content."""
    return _NON_ROMAJI_URL_PATTERN.search(url) is not None


class _ResultHolder:
    """Thread-safe container for the best lyrics result (3-tier priority).

    Tiers (highest to lowest priority):
      - native:    from source.parse — triggers immediate early-exit
      - converted: from raw_parse + romaji converter — waits for native
      - fallback:  is_acceptable() returned False — not returned to user
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._native = None       # (lyrics, quality) — from source.parse
        self._converted = None    # (lyrics, quality) — from raw_parse + converter
        self._fallback = None     # (lyrics, quality) — best unacceptable

    def submit(self, lyrics, quality):
        """Store first native acceptable result."""
        with self._lock:
            if self._native is None:
                self._native = (lyrics, quality)

    def submit_converted(self, lyrics, quality):
        """Store first converted acceptable result."""
        with self._lock:
            if self._converted is None:
                self._converted = (lyrics, quality)

    def submit_fallback(self, lyrics, quality):
        """Store highest-quality unacceptable result."""
        with self._lock:
            if self._fallback is None or quality > self._fallback[1]:
                self._fallback = (lyrics, quality)

    @property
    def acceptable(self):
        """Return best result: native > converted > None."""
        with self._lock:
            if self._native:
                return self._native[0]
            if self._converted:
                return self._converted[0]
            return None

    @property
    def has_any_result(self):
        """Return True if any result (native, converted, or fallback) exists."""
        with self._lock:
            return (self._native is not None
                    or self._converted is not None
                    or self._fallback is not None)


def _is_cloudflare_challenge(html: str) -> bool:
    """Detect Cloudflare challenge pages in fetched HTML."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        return soup.title and "Just a moment" in soup.title.text
    except Exception:
        return False


def _fetch_requests(url: str) -> tuple:
    """Fetch a URL with requests. Returns (html, status_code)."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (lyrics-scraper)"}
        resp = requests_lib.get(url, headers=headers, timeout=10)
        if resp.status_code == _STATUS_403:
            return None, _STATUS_403
        resp.raise_for_status()
        html = resp.text
        if _is_cloudflare_challenge(html):
            return None, _STATUS_403
        return html, resp.status_code
    except requests_lib.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        return None, status
    except Exception as e:
        print(f"... requests error on {url}: {e}")
        return None, 0


def _html_mentions_artist(html, artists):
    """Check if any artist name appears in the fetched HTML as a whole word."""
    html_lower = html.lower()
    for artist in artists:
        artist_lower = artist.lower()
        variants = {artist_lower}
        if "-" in artist_lower:
            variants.add(artist_lower.replace("-", " "))
        if " " in artist_lower:
            variants.add(artist_lower.replace(" ", "-"))
        for variant in variants:
            pattern = r'\b' + re.escape(variant) + r'\b'
            if re.search(pattern, html_lower):
                return True
    return False


def _try_source_with_fetcher(source, urls, fetcher_type, fetcher_instance=None,
                             run_log=None, phase=0, cancel_event=None,
                             artists=None):
    """Try all URLs for a source using the given fetcher.

    Args:
        source: LyricsSource from registry
        urls: list of candidate URLs
        fetcher_type: Fetcher enum value
        fetcher_instance: SeleniumFetcher or ChromeFetcher instance (for non-REQUESTS)
        run_log: optional RunLog to record FetchEvents into
        phase: phase number (1 or 2) for event recording
        cancel_event: optional threading.Event — checked before each URL
        artists: optional list of artist names for HTML validation

    Returns:
        (lyrics, blocked_urls, converted) where blocked_urls is a list of
        URLs that got 403 and converted is True when lyrics came from
        raw_parse + romaji converter (not from the native parse path).
    """
    blocked_urls = []

    for url in urls:
        if cancel_event is not None and cancel_event.is_set():
            break

        t0 = time.time()

        if fetcher_type == Fetcher.REQUESTS:
            html, status_code = _fetch_requests(url)
        else:
            html = fetcher_instance.fetch(url)
            status_code = 200 if html else 0

        duration = time.time() - t0

        fetch_ok = html is not None
        parse_ok = False
        lyrics = None
        converted = False
        lyrics_length = 0

        if html:
            if artists and not _html_mentions_artist(html, artists):
                print(
                    f"  ... {source.name} | {fetcher_type.value} | {duration:.1f}s | "
                    f"artist mismatch | {url}"
                )
                if run_log is not None:
                    run_log.add_fetch_event(FetchEvent(
                        source_name=source.name,
                        fetcher_type=fetcher_type.value,
                        url=url,
                        phase=phase,
                        duration=duration,
                        http_status=status_code,
                        fetch_ok=True,
                        parse_ok=False,
                        lyrics_length=0,
                    ))
                continue

            lyrics = source.parse(html)
            if lyrics is None and source.raw_parse is not None:
                raw_text = source.raw_parse(html)
                if raw_text is not None:
                    from .romaji_converter import japanese_to_romaji
                    lyrics = japanese_to_romaji(raw_text)
                    converted = lyrics is not None
            parse_ok = lyrics is not None
            lyrics_length = len(lyrics) if lyrics else 0
            print(
                f"  ... {source.name} | {fetcher_type.value} | {duration:.1f}s | "
                f"{'ok' if parse_ok else 'parse failed'} | {url}"
            )
        else:
            print(
                f"  ... {source.name} | {fetcher_type.value} | {duration:.1f}s | "
                f"fetch failed (status={status_code}) | {url}"
            )

        if run_log is not None:
            run_log.add_fetch_event(FetchEvent(
                source_name=source.name,
                fetcher_type=fetcher_type.value,
                url=url,
                phase=phase,
                duration=duration,
                http_status=status_code,
                fetch_ok=fetch_ok,
                parse_ok=parse_ok,
                lyrics_length=lyrics_length,
            ))

        if lyrics:
            return lyrics, blocked_urls, converted

        # Domain-level block — remaining URLs will also be 403'd
        if fetcher_type == Fetcher.REQUESTS and status_code == _STATUS_403:
            blocked_urls.append(url)
            break

    return None, blocked_urls, False


def _get_fetcher_class(fetcher_type):
    """Lazy-import and return the fetcher class for a given Fetcher enum value."""
    if fetcher_type == Fetcher.SELENIUM:
        from .selenium_fetcher import SeleniumFetcher
        return SeleniumFetcher
    if fetcher_type == Fetcher.CHROME_FETCHER:
        from .chrome_fetcher import ChromeFetcher
        return ChromeFetcher
    raise ValueError(f"No fetcher class for {fetcher_type}")


def _submit_result(lyrics, source, found_event, result_holder, converted=False):
    """Submit lyrics to result_holder. Returns True if native acceptable (triggers early-exit)."""
    if not lyrics:
        return False
    if is_acceptable(lyrics):
        if converted:
            result_holder.submit_converted(lyrics, source.romaji_quality)
            return False
        result_holder.submit(lyrics, source.romaji_quality)
        found_event.set()
        return True
    result_holder.submit_fallback(lyrics, source.romaji_quality)
    return False


def _run_source_pipeline(source, urls, found_event, result_holder, run_log,
                         artists=None):
    """Run one source through its full fetcher pipeline independently.

    1. Fast attempt: REQUESTS (sequential per URL, fast)
    2. If 403: all remaining fetchers in parallel (Selenium || Chrome || ...)
    """
    if found_event.is_set() or not urls:
        return

    # Phase 1: Fast attempt with REQUESTS
    blocked_urls = []
    if Fetcher.REQUESTS in source.fetchers:
        lyrics, blocked_urls, converted = _try_source_with_fetcher(
            source, urls, Fetcher.REQUESTS,
            run_log=run_log, phase=1, cancel_event=found_event,
            artists=artists,
        )
        if _submit_result(lyrics, source, found_event, result_holder,
                          converted=converted):
            return

    if found_event.is_set() or not blocked_urls:
        return

    # Phase 2: Escalation — all remaining fetchers in parallel (daemon threads)
    escalation_fetchers = [f for f in source.fetchers if f != Fetcher.REQUESTS]
    if not escalation_fetchers:
        return

    def _try_escalation(fetcher_type):
        if found_event.is_set():
            return
        fetcher_cls = _get_fetcher_class(fetcher_type)
        with fetcher_cls() as fi:
            if found_event.is_set():
                return
            lyrics, _, converted = _try_source_with_fetcher(
                source, blocked_urls, fetcher_type, fi,
                run_log=run_log, phase=2, cancel_event=found_event,
                artists=artists,
            )
            _submit_result(lyrics, source, found_event, result_holder,
                           converted=converted)

    threads = []
    for f in escalation_fetchers:
        t = threading.Thread(target=_try_escalation, args=(f,), daemon=True)
        t.start()
        threads.append(t)
    _wait_for_completion(threads, found_event, result_holder)


def _search_one(source, title, artists, run_log):
    """Search a single source. Called from ThreadPoolExecutor."""
    t0 = time.time()
    try:
        urls = source.search(title, artists)
        if urls:
            filtered = [u for u in urls if _is_non_romaji_language_url(u)]
            for u in filtered:
                print(f"  ... {source.name} | skipped (language marker) | {u}")
            urls = [u for u in urls if not _is_non_romaji_language_url(u)]
        duration = time.time() - t0
        run_log.add_search_event(SearchEvent(
            source_name=source.name,
            duration=duration,
            num_urls_found=len(urls) if urls else 0,
        ))
        return source, urls, None
    except Exception as e:
        duration = time.time() - t0
        run_log.add_search_event(SearchEvent(
            source_name=source.name,
            duration=duration,
            num_urls_found=0,
            error=str(e),
        ))
        print(f"... Search failed for {source.name}: {e}")
        return source, None, e


def _finalize_run(run_log):
    """Print summary and persist the run log."""
    print(run_log.format_summary())
    try:
        append_log(run_log.to_jsonl())
    except Exception as e:
        print(f"Warning: could not save log: {e}")


# Grace period: once a fallback result exists, wait up to this many seconds
# for escalation to find an acceptable result before returning the fallback.
_FALLBACK_GRACE_PERIOD = 10


def _wait_for_completion(tasks, found_event, result_holder=None,
                         poll_interval=0.05):
    """Wait until all tasks are done, found_event is set, or grace period expires.

    Tasks can be concurrent.futures.Future objects or threading.Thread objects.

    Returns as soon as:
    - found_event is set (acceptable result found), OR
    - all tasks are done, OR
    - result_holder has a fallback AND _FALLBACK_GRACE_PERIOD elapsed since
      that fallback was first noticed (gives escalation a window to find
      something better, but caps the wait for slow fetchers like ChromeFetcher).
    """
    def _is_done(task):
        if hasattr(task, 'done'):
            return task.done()
        return not task.is_alive()

    def _collect_results():
        for task in tasks:
            if hasattr(task, 'result'):
                task.result()

    fallback_deadline = None
    while True:
        if found_event.is_set():
            return
        if all(_is_done(t) for t in tasks):
            _collect_results()
            return
        if result_holder is not None and result_holder.has_any_result:
            if fallback_deadline is None:
                fallback_deadline = time.time() + _FALLBACK_GRACE_PERIOD
            elif time.time() >= fallback_deadline:
                return
        found_event.wait(timeout=poll_interval)


def get_romaji_lyrics(title: str, artists: list) -> str:
    """Fetch romaji lyrics using per-source concurrent pipelines.

    Each source runs independently in its own thread. Within a source,
    REQUESTS is tried first; on 403, all remaining fetchers launch in
    parallel. The first acceptable result triggers early-exit for all.
    """
    run_log = RunLog(title, list(artists))
    sources = build_registry()

    # Parallel search (unchanged)
    print(f"\n... Searching lyrics for: {title} - {' '.join(artists)}\n")
    source_urls = {}

    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        futures = {
            executor.submit(_search_one, s, title, artists, run_log): s
            for s in sources
        }
        for future in as_completed(futures):
            source, urls, error = future.result()
            if urls:
                source_urls[source.name] = urls

    if not source_urls:
        _finalize_run(run_log)
        return _no_lyrics_found(title, artists)

    # Per-source concurrent pipelines
    found_event = threading.Event()
    result_holder = _ResultHolder()

    pipeline_sources = [s for s in sources if s.name in source_urls]
    executor = ThreadPoolExecutor(max_workers=len(pipeline_sources))
    futures = [
        executor.submit(
            _run_source_pipeline,
            source, source_urls[source.name],
            found_event, result_holder, run_log,
            artists=artists,
        )
        for source in pipeline_sources
    ]
    # Wait for: acceptable result (found_event), all done, or grace period expiry.
    _wait_for_completion(futures, found_event, result_holder)
    executor.shutdown(wait=False)

    _finalize_run(run_log)
    result = result_holder.acceptable
    if result is not None:
        return _format_result(title, artists, result)
    return _no_lyrics_found(title, artists)


def _format_result(title: str, artists: list, lyrics: str) -> str:
    return f"{title} - {' '.join(artists)}\n\n{lyrics}"


def _no_lyrics_found(title: str, artists: list) -> str:
    return (
        f"{title} - {' '.join(artists)}\n\n"
        "... Paroles non trouvées automatiquement.\n"
        "Essaye manuellement sur Google."
    )
