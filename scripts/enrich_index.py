#!/usr/bin/env python3
"""Enrich video_index.json with playlist memberships and per-playlist order."""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX = ROOT / "data" / "video_index.json"
PL_DIR = ROOT / "data" / "playlists"


def main():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    videos = idx["videos"]
    playlists = idx["playlists"]

    for pl_file in PL_DIR.glob("*.tsv"):
        pid = pl_file.stem
        if pid not in playlists:
            print(f"WARN: playlist {pid} not in index", flush=True)
            continue
        order = []
        with open(pl_file, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|||")
                if len(parts) < 3:
                    continue
                idx_str, vid, title = parts[0], parts[1], parts[2]
                try:
                    pos = int(idx_str)
                except ValueError:
                    continue
                order.append({"position": pos, "video_id": vid, "title": title})
                if vid in videos:
                    videos[vid]["playlists"].append({"playlist_id": pid, "position": pos})
        order.sort(key=lambda x: x["position"])
        playlists[pid]["videos"] = order
        print(f"{pid}: {playlists[pid]['title'][:40]} -> {len(order)} videos")

    # Sanity: count videos with no playlist (might be unlisted-via-playlist or standalone)
    orphans = [v for v in videos.values() if not v["playlists"]]
    print(f"\nOrphan videos (no playlist): {len(orphans)}")
    print(f"In >=1 playlist: {len(videos) - len(orphans)}")

    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {INDEX}")


if __name__ == "__main__":
    main()
