#!/usr/bin/env bash

usage() {
    echo "Usage: $0 <audiofile> [<subtitlefile.srt>]"
    echo "Usage: $0 --current-playing"
    echo ""
    echo "Plays an audio file with optional synchronized subtitles (.srt) using mpv."
    echo ""
    echo "Options:"
    echo "  --current-playing  Play the audio file currently playing in mplayer"
    echo ""
    echo "Arguments:"
    echo "  audiofile          Path to the audio file (e.g., song.mp3)"
    echo "  subtitlefile       Path to subtitle file (.srt format). Optional."
    echo "                     If not provided, looks for <audiofile>.srt in the same directory."
    echo ""
    echo "If the .srt file doesn't exist, you'll be prompted to extract lyrics automatically."
    exit 1
}

# Check for help flag or --current-playing first
CURRENT_PLAYING=false
if [ "$#" -ge 1 ]; then
    if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        usage
    elif [ "$1" = "--current-playing" ]; then
        CURRENT_PLAYING=true
    fi
fi

if [ "$#" -lt 1 ]; then
    usage
fi

# Determine audio file path
if [ "$CURRENT_PLAYING" = true ]; then
    AUDIOPATH=$(lsof -c mplayer -F 2>/dev/null | cut -c 2- | grep '\.mp3')
    if [ -z "$AUDIOPATH" ]; then
        echo "Error: No audio file is currently being played by mplayer."
        exit 1
    fi
    echo "Info: Detected currently playing: $AUDIOPATH"
else
    AUDIOPATH=$1
fi

if [ ! -f "$AUDIOPATH" ]; then
    echo "Error: Audio file '$AUDIOPATH' not found!"
    exit 1
fi

# Determine subtitle file path
SUBPATH=""
if [ "$CURRENT_PLAYING" = false ] && [ "$#" -eq 2 ]; then
    # User explicitly provided subtitle file
    if [ ! -f "$2" ]; then
        echo "Error: Subtitle file '$2' not found!"
        exit 1
    fi
    # Check if it's an .srt file
    if [[ ! "$2" =~ \.srt$ ]]; then
        echo "Warning: Subtitle file '$2' is not a .srt file. Subtitles may not work properly."
    fi
    SUBPATH=$2
else
    # Look for .srt file next to the audio file (same path, .srt extension)
    SUBPATH="${AUDIOPATH%.mp3}.srt"

    if [ ! -f "$SUBPATH" ]; then
        echo "⚠️  No subtitle file found at: $SUBPATH"
        echo ""
        echo "Would you like to extract lyrics automatically?"
        echo "This will:"
        echo "  1. Fetch lyrics from online sources"
        echo "  2. Sync them with the audio using Whisper"
        echo "  3. Create a .srt file with synchronized subtitles"
        echo ""
        read -p "Extract lyrics now? [y/N] " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🎵 Extracting lyrics..."

            # Get script directory (where extract_lyrics.sh is located)
            SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

            # Run extract_lyrics.sh
            if [ -f "$SCRIPT_DIR/extract_lyrics.sh" ]; then
                "$SCRIPT_DIR/extract_lyrics.sh" "$AUDIOPATH"

                # Check if .srt was created successfully
                if [ -f "$SUBPATH" ]; then
                    echo "✅ Subtitles extracted successfully!"
                else
                    echo "❌ Failed to extract subtitles. Playing without them."
                    SUBPATH=""
                fi
            else
                echo "❌ Error: extract_lyrics.sh not found in $SCRIPT_DIR"
                SUBPATH=""
            fi
        else
            echo "▶️  Playing without subtitles..."
            SUBPATH=""
        fi
    else
        echo "Info: Using subtitle file: $SUBPATH"
    fi
fi

# Build mpv command
MPV_ARGS=(
    --input-cursor-passthrough=yes
    --ontop
    --no-audio-display
    --force-window
    --force-rgba-osd-rendering
    --background=#00000000
    --alpha=yes
    --geometry="$(xwininfo -root | grep geometry | sed 's/.*geometry //g')"
    --title="plop"
    --loop=0
    --ontop-level=system
    --no-border
    --gpu-context=x11egl
)

# Only add --sub-file if we have a subtitle file
if [ -n "$SUBPATH" ]; then
    MPV_ARGS+=(--sub-file="${SUBPATH}")
fi

# Add audio file last
MPV_ARGS+=("${AUDIOPATH}")

# Execute mpv
mpv "${MPV_ARGS[@]}"
