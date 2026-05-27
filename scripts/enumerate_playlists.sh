#!/bin/bash
# Enumerate every playlist's videos so we have ordered list per course
set -e
export PYTHONIOENCODING=utf-8

ROOT="C:/Users/tlkag/.openclaw/workspace/.openclaw/channel_map"
PL_TSV="$ROOT/all_playlists.tsv"
OUT_DIR="$ROOT/data/playlists"
mkdir -p "$OUT_DIR"

# Read playlist IDs from TSV
while IFS='|||' read -r pid rest; do
    [ -z "$pid" ] && continue
    OUT_FILE="$OUT_DIR/${pid}.tsv"
    if [ -f "$OUT_FILE" ] && [ -s "$OUT_FILE" ]; then
        echo "skip $pid (exists)"
        continue
    fi
    echo "fetching $pid -> $OUT_FILE"
    yt-dlp --flat-playlist --print-to-file "%(playlist_index)s|||%(id)s|||%(title)s" "$OUT_FILE" \
        "https://www.youtube.com/playlist?list=$pid" 2>&1 | tail -2
done < "$PL_TSV"

echo ""
echo "Done. Playlists in $OUT_DIR:"
ls -la "$OUT_DIR" | head -30
