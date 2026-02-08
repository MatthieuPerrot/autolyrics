#!/usr/bin/env bash

# Flags
DRY_RUN=false
FORCE=false

# Temporary files tracking
RAW_LYRICS_PATH=""
RAW_SUBPATH=""

# Cleanup function for temporary files
cleanup() {
    local exit_code=$?
    if [ "$DRY_RUN" = false ]; then
        if [ -n "$RAW_LYRICS_PATH" ] && [ -f "$RAW_LYRICS_PATH" ]; then
            rm -f "$RAW_LYRICS_PATH"
            echo "🧹 Cleaned up temporary lyrics file"
        fi
        if [ -n "$RAW_SUBPATH" ] && [ -f "$RAW_SUBPATH" ]; then
            rm -f "$RAW_SUBPATH"
            echo "🧹 Cleaned up temporary subtitle file"
        fi
        # Also clean up debug files if they exist
        if [ -n "$AUDIOPATH" ]; then
            local debug_json="${AUDIOPATH%.mp3}_stable_ts_debug.json"
            if [ -f "$debug_json" ]; then
                rm -f "$debug_json"
                echo "🧹 Cleaned up debug JSON file"
            fi
        fi
    fi
    exit $exit_code
}

# Set up cleanup trap for normal exit, errors, and interrupts
trap cleanup EXIT INT TERM

usage() {
    echo "Usage: $0 [OPTIONS] <audiofile> [<subtitlefile>]"
    echo "Usage: $0 [OPTIONS] --current-playing [<subtitlefile>]"
    echo ""
    echo "Options:"
    echo "  --dry-run          Display commands that would be executed without running them"
    echo "  --force            Regenerate subtitle file even if it already exists"
    echo "  --current-playing  Extract lyrics from currently playing audio in mplayer"
    echo ""
    echo "Arguments:"
    echo "  audiofile          Path to the audio file (e.g., song.mp3)"
    echo "  subtitlefile       Path to save the extracted lyrics (e.g., song.srt)."
    echo "                     If not provided, creates <audiofile>.srt next to the audio file."
    echo ""
    echo "By default, skips files that already have subtitles (use --force to override)."
    exit 1
}

# Function to execute or display commands
# Properly escapes arguments for safe copy-paste
run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        # Display command with proper escaping for copy-paste
        printf "%q" "$1"
        shift
        for arg in "$@"; do
            printf " %q" "$arg"
        done
        printf "\n"
    else
        # Execute the command
        "$@"
    fi
}

# Parse options
if [ "$#" -lt 1 ]; then
    usage
fi

# Parse all options (--dry-run, --force, and --current-playing can be in any order)
CURRENT_PLAYING=false
while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --current-playing)
            CURRENT_PLAYING=true
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            ;;
        *)
            # First positional argument
            break
            ;;
    esac
done

# Handle --current-playing mode
if [ "$CURRENT_PLAYING" = true ]; then
    AUDIOPATH=$(lsof  -c mplayer -F 2>/dev/null | cut -c 2- | grep '\.mp3')
    if [ -z "$AUDIOPATH" ]; then
        echo "No audio file is currently being played by mplayer."
        exit 1
    fi
    if [ "$#" -ge 1 ]; then
        SUBPATH=$1
    else
        # Create .srt next to the .mp3 file (keep full path)
        SUBPATH="${AUDIOPATH%.mp3}.srt"
    fi
else
    # Normal mode: require audio file as argument
    if [ "$#" -lt 1 ]; then
        echo "Error: Audio file argument is required."
        usage
    fi
    AUDIOPATH=$1
    if [ ! -f "$AUDIOPATH" ] && [ "$DRY_RUN" = false ]; then
        echo "Audio file '$AUDIOPATH' does not exist."
        exit 1
    fi
    if [ "$#" -ge 2 ]; then
        SUBPATH=$2
    else
        # Create .srt next to the .mp3 file (keep full path)
        SUBPATH="${AUDIOPATH%.mp3}.srt"
    fi
fi

# Check if subtitle file already exists (skip if not --force)
if [ -f "$SUBPATH" ] && [ "$FORCE" = false ]; then
    echo "ℹ️  Subtitle file already exists: $SUBPATH"
    echo "   Use --force to regenerate"
    exit 0
fi

if [ "$FORCE" = true ] && [ -f "$SUBPATH" ]; then
    echo "🔄 Force mode: Regenerating existing subtitle file"
fi

# Temporary files in temporary directory
if [ "$DRY_RUN" = true ]; then
    # In dry-run mode, use placeholder paths for display
    RAW_LYRICS_PATH="/tmp/raw_lyrics.XXXXXX.txt"
    RAW_SUBPATH="/tmp/raw_sub.XXXXXX.srt"
else
    # In normal mode, create actual temporary files
    RAW_LYRICS_PATH=$(mktemp /tmp/raw_lyrics.XXXXXX.txt)
    RAW_SUBPATH=$(mktemp /tmp/raw_sub.XXXXXX.srt)
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_cmd python3 "${SCRIPT_DIR}/lyrics_fetcher_cli.py" -o "${RAW_LYRICS_PATH}" "${AUDIOPATH}"
run_cmd python3 "${SCRIPT_DIR}/sync_lyrics.py" -o "${RAW_SUBPATH}" --mode auto_stablets "${AUDIOPATH}" "${RAW_LYRICS_PATH}"
run_cmd python3 "${SCRIPT_DIR}/postprocess_srt.py" "${RAW_SUBPATH}" "${RAW_LYRICS_PATH}" "${SUBPATH}" --display_mode line_plus_next
