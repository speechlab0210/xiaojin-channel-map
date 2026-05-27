#!/usr/bin/env python3
"""Parse all_videos.tsv -> data/video_index.json with playlist membership."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
TSV = ROOT / "all_videos.tsv"
PLAYLISTS_TSV = ROOT / "all_playlists.tsv"
OUT = ROOT / "data" / "video_index.json"


def parse_tsv(path: Path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("|||")
            rows.append(parts)
    return rows


def main():
    video_rows = parse_tsv(TSV)
    playlist_rows = parse_tsv(PLAYLISTS_TSV)

    videos = {}
    for r in video_rows:
        if len(r) < 4:
            continue
        vid, title, duration_s, upload_date = r[0], r[1], r[2], r[3]
        try:
            dur = float(duration_s) if duration_s and duration_s != "NA" else None
        except ValueError:
            dur = None
        videos[vid] = {
            "id": vid,
            "title": title,
            "duration_s": dur,
            "duration_hms": _hms(dur) if dur else None,
            "upload_date": upload_date if upload_date != "NA" else None,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "playlists": [],
        }

    playlists = {}
    for r in playlist_rows:
        if len(r) < 2:
            continue
        pid, title = r[0], r[1]
        playlists[pid] = {"id": pid, "title": title, "videos": []}

    out = {
        "video_count": len(videos),
        "playlist_count": len(playlists),
        "videos": videos,
        "playlists": playlists,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {OUT}: {len(videos)} videos, {len(playlists)} playlists")
    # Print summary by course
    print("\nCourses (by playlist title):")
    for pid, p in playlists.items():
        print(f"  - {p['title']}")


def _hms(s):
    if not s:
        return None
    s = int(s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


if __name__ == "__main__":
    main()
