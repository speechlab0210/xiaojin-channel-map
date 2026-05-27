#!/bin/bash
# Download captions for a list of video IDs into channel_map/captions/
# Skip if already exists.
set -e
export PYTHONIOENCODING=utf-8

ROOT="C:/Users/tlkag/.openclaw/workspace/.openclaw/channel_map"
OUT_DIR="$ROOT/captions"
mkdir -p "$OUT_DIR"

VIDEO_IDS_FILE="$1"
if [ -z "$VIDEO_IDS_FILE" ]; then
    echo "usage: $0 <file_with_one_video_id_per_line>"
    exit 1
fi

while IFS= read -r vid; do
    [ -z "$vid" ] && continue
    if ls "$OUT_DIR/${vid}".*.ttml 1>/dev/null 2>&1 || ls "$OUT_DIR/${vid}".*.vtt 1>/dev/null 2>&1 || ls "$OUT_DIR/${vid}".*.srv* 1>/dev/null 2>&1; then
        echo "skip $vid (already have captions)"
        continue
    fi
    echo "downloading $vid..."
    yt-dlp --skip-download \
        --write-subs --write-auto-subs \
        --sub-langs "zh-Hant,zh-TW,zh-Hans,zh,en" \
        --sub-format "ttml/srv1/srv2/srv3/vtt/best" \
        -o "$OUT_DIR/%(id)s.%(ext)s" \
        "https://www.youtube.com/watch?v=$vid" 2>&1 | grep -E "Writing|ERROR" | head -3
done < "$VIDEO_IDS_FILE"

echo ""
echo "Done. Caption files in $OUT_DIR:"
ls "$OUT_DIR" | wc -l
