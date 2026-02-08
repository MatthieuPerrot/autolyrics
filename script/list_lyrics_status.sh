#!/usr/bin/env bash

usage() {
    echo "Usage: $0 [directory]"
    echo ""
    echo "Lists all MP3 files in a directory and shows their subtitle status."
    echo ""
    echo "Arguments:"
    echo "  directory    Path to directory to scan (default: current directory)"
    echo ""
    echo "Options:"
    echo "  --help, -h   Show this help message"
    echo ""
    echo "Legend:"
    echo "  ✅  .srt file exists"
    echo "  ❌  .srt file missing"
    exit 1
}

# Parse arguments
if [ "$#" -ge 1 ]; then
    if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        usage
    fi
    SEARCH_DIR="$1"
else
    SEARCH_DIR="."
fi

# Validate directory
if [ ! -d "$SEARCH_DIR" ]; then
    echo "Error: Directory '$SEARCH_DIR' not found!"
    exit 1
fi

# Convert to absolute path for cleaner display
SEARCH_DIR=$(cd "$SEARCH_DIR" && pwd)

echo "🔍 Scanning directory: $SEARCH_DIR"
echo ""

# Initialize counters
total_mp3=0
with_srt=0
without_srt=0

# Arrays to store results
declare -a files_with_srt
declare -a files_without_srt

# Find all MP3 files recursively
while IFS= read -r -d '' mp3_file; do
    total_mp3=$((total_mp3 + 1))

    # Check if corresponding .srt exists
    srt_file="${mp3_file%.mp3}.srt"

    if [ -f "$srt_file" ]; then
        with_srt=$((with_srt + 1))
        files_with_srt+=("$mp3_file")
    else
        without_srt=$((without_srt + 1))
        files_without_srt+=("$mp3_file")
    fi
done < <(find "$SEARCH_DIR" -type f -name "*.mp3" -print0 | sort -z)

# Display results
if [ $total_mp3 -eq 0 ]; then
    echo "No MP3 files found in $SEARCH_DIR"
    exit 0
fi

echo "📊 Summary:"
echo "  Total MP3 files: $total_mp3"
echo "  With subtitles:  $with_srt ($(awk "BEGIN {printf \"%.1f\", ($with_srt/$total_mp3)*100}")%)"
echo "  Without:         $without_srt ($(awk "BEGIN {printf \"%.1f\", ($without_srt/$total_mp3)*100}")%)"
echo ""

# Display files with subtitles
if [ ${#files_with_srt[@]} -gt 0 ]; then
    echo "✅ Files with subtitles ($with_srt):"
    for file in "${files_with_srt[@]}"; do
        # Make path relative to search dir for cleaner display
        rel_path="${file#$SEARCH_DIR/}"
        echo "  ✅ $rel_path"
    done
    echo ""
fi

# Display files without subtitles
if [ ${#files_without_srt[@]} -gt 0 ]; then
    echo "❌ Files without subtitles ($without_srt):"
    for file in "${files_without_srt[@]}"; do
        # Make path relative to search dir for cleaner display
        rel_path="${file#$SEARCH_DIR/}"
        echo "  ❌ $rel_path"
    done
    echo ""
fi

# Suggest next actions
if [ $without_srt -gt 0 ]; then
    echo "💡 Tip: To extract lyrics for a file, use:"
    echo "   ./extract_lyrics.sh <audiofile>"
    echo ""
    echo "   To process all missing files, you could use:"
    echo "   for f in <files>; do ./extract_lyrics.sh \"\$f\"; done"
fi
