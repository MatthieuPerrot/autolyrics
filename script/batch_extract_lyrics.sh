#!/usr/bin/env bash

usage() {
    echo "Usage: $0 [OPTIONS] <directory|file1 file2 ...>"
    echo ""
    echo "Batch extract lyrics for multiple audio files."
    echo ""
    echo "Options:"
    echo "  --force         Regenerate subtitles even if they already exist"
    echo "  --recursive     Scan directory recursively (when directory is provided)"
    echo "  --help, -h      Show this help message"
    echo ""
    echo "Arguments:"
    echo "  directory       Process all .mp3 files in this directory"
    echo "  file1 file2...  Process specific audio files"
    echo ""
    echo "Examples:"
    echo "  $0 /music/folder              # Process all mp3 in folder (non-recursive)"
    echo "  $0 --recursive /music         # Process all mp3 recursively"
    echo "  $0 song1.mp3 song2.mp3        # Process specific files"
    echo "  $0 --force /music/folder      # Force regenerate all"
    exit 1
}

# Parse options
FORCE=false
RECURSIVE=false

while [ "$#" -gt 0 ]; do
    case "$1" in
        --force)
            FORCE=true
            shift
            ;;
        --recursive)
            RECURSIVE=true
            shift
            ;;
        --help|-h)
            usage
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

if [ "$#" -lt 1 ]; then
    echo "Error: No directory or files provided"
    usage
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTRACT_SCRIPT="$SCRIPT_DIR/extract_lyrics.sh"

if [ ! -f "$EXTRACT_SCRIPT" ]; then
    echo "Error: extract_lyrics.sh not found in $SCRIPT_DIR"
    exit 1
fi

# Collect files to process
declare -a files_to_process

if [ "$#" -eq 1 ] && [ -d "$1" ]; then
    # Directory mode
    DIR="$1"
    echo "🔍 Scanning directory: $DIR"

    if [ "$RECURSIVE" = true ]; then
        # Recursive search
        while IFS= read -r -d '' file; do
            files_to_process+=("$file")
        done < <(find "$DIR" -type f -name "*.mp3" -print0 | sort -z)
    else
        # Non-recursive search
        while IFS= read -r -d '' file; do
            files_to_process+=("$file")
        done < <(find "$DIR" -maxdepth 1 -type f -name "*.mp3" -print0 | sort -z)
    fi
else
    # File mode - process provided files
    for file in "$@"; do
        if [ -f "$file" ]; then
            files_to_process+=("$file")
        else
            echo "⚠️  File not found, skipping: $file"
        fi
    done
fi

# Check if any files found
total_files=${#files_to_process[@]}
if [ $total_files -eq 0 ]; then
    echo "No .mp3 files found to process"
    exit 0
fi

echo "📋 Found $total_files file(s) to process"
echo ""

# Process files
success_count=0
skip_count=0
error_count=0
current=0

for file in "${files_to_process[@]}"; do
    current=$((current + 1))
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[$current/$total_files] Processing: $(basename "$file")"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Build command
    cmd=("$EXTRACT_SCRIPT")
    if [ "$FORCE" = true ]; then
        cmd+=(--force)
    fi
    cmd+=("$file")

    # Execute
    if "${cmd[@]}"; then
        # Check exit code and output to determine if skipped or successful
        srt_file="${file%.mp3}.srt"
        if [ -f "$srt_file" ]; then
            success_count=$((success_count + 1))
            echo "✅ Success"
        else
            skip_count=$((skip_count + 1))
            echo "⏭️  Skipped"
        fi
    else
        error_count=$((error_count + 1))
        echo "❌ Failed"
    fi

    echo ""
done

# Final summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Batch Processing Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Total files:    $total_files"
echo "  ✅ Successful:  $success_count"
echo "  ⏭️  Skipped:     $skip_count"
echo "  ❌ Failed:      $error_count"
echo ""

if [ $error_count -gt 0 ]; then
    echo "⚠️  Some files failed to process. Check the output above for details."
    exit 1
else
    echo "🎉 All files processed successfully!"
    exit 0
fi
