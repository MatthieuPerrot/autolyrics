# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

autolyrics is a Python-based tool for fetching, synchronizing, and displaying lyrics for audio files, particularly focused on Japanese songs with romaji (romanized) lyrics. The project consists of:

1. **Lyrics Fetching**: Web scraping from multiple sources (animelyrics, nautiljon, genius, etc.)
2. **Lyrics Synchronization**: Manual and automatic (Whisper-based) sync with audio
3. **Post-processing**: Transform detailed SRT files into various karaoke display formats
4. **MPV Integration**: Test scripts for overlay display

## Key Commands

### Running Scripts

All main scripts are in `script/` directory:

```bash
# Fetch lyrics from MP3 metadata
python3 script/lyrics_fetcher_cli.py audio.mp3

# Fetch and automatically sync lyrics
python3 script/lyrics_fetcher_cli.py audio.mp3 --sync

# Manual line-by-line synchronization
python3 script/sync_lyrics.py audio.mp3 lyrics.txt --mode line

# Automatic synchronization with Whisper/stable-ts
python3 script/sync_lyrics.py audio.mp3 lyrics.txt --mode auto_stablets --st_model base --st_lang ja

# Post-process detailed SRT files
python3 script/postprocess_srt.py input.srt original_lyrics.txt output.srt --display_mode line --highlight_style preserve
```

### Testing MPV Overlay

```bash
# Test MPV overlay display (modify VIDEO_OUTPUT variable in script)
./test_mpv_overlay.sh
```

## Architecture

### Core Components

**`script/lyrics_fetcher/`** - Modular lyrics scraping system
- `fallback.py`: Orchestrates fallback chain across multiple sources
- `animelyrics.py`, `nautiljon.py`, `genius.py`, etc.: Site-specific scrapers
- `utils.py`: Google Custom Search integration, script detection utilities
- Each scraper returns `None` on failure; `fallback.py` tries sources in sequence

**`script/lyrics_fetcher_cli.py`** - Main entry point
- Extracts MP3 metadata (title, artists) using mutagen
- Calls `get_romaji_lyrics()` with fallback chain
- Optionally launches `sync_lyrics.py` via subprocess

**`script/sync_lyrics.py`** - Lyrics synchronization
- `LyricsSyncer` class with two modes:
  - `line`: Manual sync using pygame for audio playback, user input for timing
  - `auto_stablets`: Automatic sync using stable-whisper (Whisper model for speech recognition)
- Outputs `.srt` format (not `.lrc`) with detailed word/syllable-level timestamps and HTML font tags for highlighting

**`script/postprocess_srt.py`** - SRT transformation
- Converts detailed SRT (full lyrics + progressive highlighting) into display-ready formats
- Display modes: `word` (isolated words), `line` (full line), `line_plus_next` (line + next line)
- Highlight styles: `preserve` (original tags), `line_all` (full line color), `none` (plain text)

### Important Technical Details

1. **MP3 Metadata Extraction**: Recent commit (97982ea) improved artist extraction - now splits on `/` to handle multiple artists in single field

2. **Output Format**: `sync_lyrics.py` generates `.srt` files, not `.lrc` - the detailed format includes:
   - Word/syllable-level granularity
   - Full lyrics text repeated in each entry
   - Active segment marked with `<font color="...">` tags

3. **Lyrics Fetching Flow**:
   ```
   MP3 → extract metadata → search query → Google Custom Search API →
   scrape first matching URL → fallback to next source if empty
   ```

4. **Dependencies** (no requirements.txt, inferred from imports):
   - `mutagen` (MP3 metadata)
   - `pygame` (audio playback for manual sync)
   - `stable-whisper` + `torch` + `torchaudio` + `openai-whisper` (auto sync)
   - `requests` + `beautifulsoup4` (web scraping)
   - `googleapiclient` (Google Custom Search)

5. **Credential Warning**: `utils.py` contains a hardcoded Google API key and Custom Search Engine ID - should not be committed in production

## File Organization

- `script/` - All Python scripts and main logic
- `script/tests/` - Test outputs and sample files
- `archives/` - Old/deprecated implementations
- `docs/` - Markdown documentation of technical exploration and decisions
- Root level contains test files: `test_audio.mp3`, `test_lyrics.srt`, `test_mpv_overlay.sh`

## Development Notes

- Use `python3` for all Python commands (not `python`)
- No formal test suite - `script/tests/` contains output samples and manual test results
- Project uses direct script execution (no package installation with pip)
- Comments and code should be in English (README and docs are in French)
- Web scraping relies on site structure - may break if sources change HTML structure
