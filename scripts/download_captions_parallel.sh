#!/bin/bash
# Parallel caption download via xargs -P
# Usage: bash download_captions_parallel.sh <ids_file> [parallel_jobs]
set -e
export PYTHONIOENCODING=utf-8

ROOT="C:/Users/tlkag/.openclaw/workspace/.openclaw/channel_map"
OUT_DIR="$ROOT/captions"
mkdir -p "$OUT_DIR"

IDS_FILE="$1"
JOBS="${2:-6}"

cat "$IDS_FILE" | tr -d '\r' | grep -v '^$' | xargs -P "$JOBS" -I{} bash -c '
    vid="$1"
    out_dir="$2"
    # Skip if exists
    if ls "$out_dir/${vid}".*.ttml 1>/dev/null 2>&1 || ls "$out_dir/${vid}".*.vtt 1>/dev/null 2>&1; then
        echo "skip $vid"
        exit 0
    fi
    # Try manual subs (ttml preferred) first
    if yt-dlp --skip-download --write-subs \
        --sub-langs "zh-Hant,zh-TW,zh-Hans,zh,en" \
        --sub-format "ttml/srv1/srv2/srv3/vtt/best" \
        -o "$out_dir/%(id)s.%(ext)s" \
        "https://www.youtube.com/watch?v=$vid" 2>/dev/null | grep -q "Writing"; then
        echo "got_manual $vid"
    else
        # Fall back to auto subs
        yt-dlp --skip-download --write-auto-subs \
            --sub-langs "zh-TW,zh-Hant,zh-Hans,zh,en" \
            --sub-format "vtt" \
            -o "$out_dir/%(id)s.%(ext)s" \
            "https://www.youtube.com/watch?v=$vid" 2>/dev/null
        if ls "$out_dir/${vid}".*.vtt 1>/dev/null 2>&1; then
            echo "got_auto $vid"
        else
            echo "no_subs $vid"
        fi
    fi
' _ {} "$OUT_DIR"

echo ""
echo "Total caption files: $(ls "$OUT_DIR" | wc -l)"
