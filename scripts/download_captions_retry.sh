#!/bin/bash
# Retry for missing videos — try every common lang and any subtitle format
set -e
export PYTHONIOENCODING=utf-8

ROOT="C:/Users/tlkag/.openclaw/workspace/.openclaw/channel_map"
OUT_DIR="$ROOT/captions"

IDS_FILE="$1"
PARALLEL="${2:-5}"

cat "$IDS_FILE" | tr -d '\r' | grep -v '^$' | xargs -P "$PARALLEL" -I{} bash -c '
    vid="$1"
    out_dir="$2"
    if ls "$out_dir/${vid}".*.ttml 1>/dev/null 2>&1 || ls "$out_dir/${vid}".*.vtt 1>/dev/null 2>&1; then
        exit 0
    fi
    # Try every plausible lang + format combo
    yt-dlp --skip-download --write-subs --write-auto-subs \
        --sub-langs "zh-TW,zh-Hant,zh-Hans,zh,en-US,en,zh-Hant-en,zh-TW-en" \
        --sub-format "ttml/vtt/srv3/srv2/srv1/best" \
        -o "$out_dir/%(id)s.%(ext)s" \
        "https://www.youtube.com/watch?v=$vid" 2>&1 | grep -E "Writing|ERROR" | head -2
' _ {} "$OUT_DIR"

echo ""
echo "Total: $(ls "$OUT_DIR" | grep -E "\\.(ttml|vtt)$" | wc -l) captions"
