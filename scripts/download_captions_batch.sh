#!/bin/bash
# Faster batch download: split missing IDs into batches and run yt-dlp with --batch-file
# Each batch shares one JS-challenge solve.
set -e
export PYTHONIOENCODING=utf-8

ROOT="C:/Users/tlkag/.openclaw/workspace/.openclaw/channel_map"
OUT_DIR="$ROOT/captions"
TMP_DIR="$ROOT/data/batches"
mkdir -p "$OUT_DIR" "$TMP_DIR"

IDS_FILE="$1"
BATCH_SIZE="${2:-30}"
PARALLEL="${3:-4}"

# Build list of URLs for missing videos only
URLS_FILE="$TMP_DIR/all_urls.txt"
> "$URLS_FILE"
while IFS= read -r vid; do
    [ -z "$vid" ] && continue
    # Skip if already have caption
    if ls "$OUT_DIR/${vid}".*.ttml 1>/dev/null 2>&1 || ls "$OUT_DIR/${vid}".*.vtt 1>/dev/null 2>&1; then
        continue
    fi
    echo "https://www.youtube.com/watch?v=$vid" >> "$URLS_FILE"
done < "$IDS_FILE"

total=$(wc -l < "$URLS_FILE")
echo "URLs to fetch: $total"

# Split into batches
split -l "$BATCH_SIZE" -d "$URLS_FILE" "$TMP_DIR/batch_"
batch_files=("$TMP_DIR"/batch_*)
echo "Created ${#batch_files[@]} batches of $BATCH_SIZE"

# Run yt-dlp batch in parallel
run_one_batch() {
    local bfile="$1"
    local out_dir="$2"
    yt-dlp --skip-download \
        --write-subs --write-auto-subs \
        --sub-langs "zh-Hant,zh-TW,zh-Hans,zh,en" \
        --sub-format "ttml/srv1/srv2/srv3/vtt/best" \
        -o "$out_dir/%(id)s.%(ext)s" \
        --batch-file "$bfile" 2>&1 | grep -E "Writing|ERROR" | head -100
    echo "BATCH_DONE: $bfile"
}
export -f run_one_batch

printf '%s\n' "${batch_files[@]}" | xargs -P "$PARALLEL" -I{} bash -c 'run_one_batch "$1" "$2"' _ {} "$OUT_DIR"

echo ""
echo "Final total captions: $(ls "$OUT_DIR" | wc -l)"
rm -f "$TMP_DIR"/batch_*
rm -f "$URLS_FILE"
