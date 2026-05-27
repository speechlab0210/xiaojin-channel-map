#!/usr/bin/env python3
"""Select candidates to run visual verification on.

Heuristic:
- All MEDIUM/LOW confidence resolutions
- HIGH confidence ones where context strongly suggests visual cue
  (keywords: 投影片, 連結, URL, QR code, 你看這, 我放, 在...影片上)
- HIGH confidence ones that look like "prerequisite" type (often have URL slides)

Output: refs/visual_queue.jsonl — list of candidates to verify
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
IN_PATH = ROOT / "refs" / "resolved.jsonl"
OUT_PATH = ROOT / "refs" / "visual_queue.jsonl"


VISUAL_HINTS = re.compile(
    r"投影片|連結|放(在)?投影片|"
    r"youtu|YouTube|QR\s*code|我放|附在|"
    r"預習|預修|請(先)?看|你可以(去)?看|請(去)?看|"
    r"請看(這|那)|今天我們(放|放在|帶|放上)|"
    r"我把(.{0,20})放(在|到)",
    re.IGNORECASE
)


def main():
    rows = []
    with open(IN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    queue = []
    counts = {"medium_low": 0, "high_visual_hint": 0, "high_prereq": 0}
    for c in rows:
        r = c.get("resolved")
        if not r or not r.get("target_video_id"):
            continue
        cat = c.get("classification", {}).get("category")
        conf = r.get("confidence")
        ctx = c.get("context", "")

        reason = None
        if conf in ("MEDIUM", "LOW"):
            reason = "medium_low_confidence"
            counts["medium_low"] += 1
        elif cat == "PREREQUISITE":
            reason = "prerequisite_likely_has_slide_url"
            counts["high_prereq"] += 1
        elif VISUAL_HINTS.search(ctx):
            reason = "visual_hint_in_context"
            counts["high_visual_hint"] += 1

        if reason:
            queue.append({**c, "visual_queue_reason": reason})

    OUT_PATH.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in queue) + "\n", encoding="utf-8")
    print(f"Selected {len(queue)} cases for visual verification")
    print(f"  reasons: {counts}")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
