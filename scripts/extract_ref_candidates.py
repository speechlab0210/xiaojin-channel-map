#!/usr/bin/env python3
"""Scan TTML captions for cross-reference keyword hits.

Outputs JSONL with one record per candidate:
{
  "source_video_id": "...",
  "source_video_title": "...",
  "hit_start_s": float,
  "hit_end_s": float,
  "keyword": "之前 / 上次 / 前面 / 第 N 講 / ...",
  "context": "<window of ~10 segments around the hit, joined>",
  "context_start_s": float,
  "context_end_s": float,
}

Next stage: LLM filter for REAL cross-video vs intra-video references.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ttml_parse import parse_caption  # noqa: E402

ROOT = Path(__file__).parent.parent
CAPTIONS_DIR = ROOT / "captions"
SAMPLE_DIR = ROOT / "sample_subs"
INDEX_PATH = ROOT / "data" / "video_index.json"
OUT_PATH = ROOT / "refs" / "candidates.jsonl"

# Keyword patterns. Each is (pattern, category)
PATTERNS = [
    # Strong cross-video signals
    (r"上(一|個|堂|集|門|次)?(課|堂|講|集|門|影片|門|影|片|個影片)", "previous_lecture"),
    (r"第\s*[一二三四五六七八九十0-9]+\s*(講|課|堂|集|集|篇)", "numbered_lecture"),
    (r"另外(一|個)?(個)?影片", "other_video"),
    (r"(以前|之前|過去|曾經)(.*?)(影片|課|講|介紹|提|講|示範)", "past_mentioned"),
    (r"(在|有)?(另外|另一|有)(一|個|支)?支?影片", "other_video"),
    # Weaker hints
    (r"之前(.*?)講過|之前(.*?)介紹過|之前(.*?)提過|之前(.*?)示範", "previously_x"),
    (r"我們(.*?)介紹過|我們(.*?)講過|我們(.*?)提過", "we_x_before"),
    # Common cross-ref phrasings observed
    (r"上[一]?次", "last_time"),
    (r"前面(我|我們)?(.*?)(提|講|介紹|示範)", "earlier_x"),
    (r"前(一|幾)?[堂集講次門]", "earlier_lecture"),
    (r"(以前|早期|去年|今年|這學期)的(.*?)(課|影片)", "past_course"),
]

COMPILED = [(re.compile(p), tag) for p, tag in PATTERNS]


def find_hits(segments):
    """Yield (i, keyword, matched_text) for each hit."""
    for i, seg in enumerate(segments):
        text = seg["text"]
        for rx, tag in COMPILED:
            m = rx.search(text)
            if m:
                yield i, tag, m.group(0)
                break  # one hit per segment is enough


def context_window(segments, i, before=4, after=8):
    lo = max(0, i - before)
    hi = min(len(segments), i + after + 1)
    return segments[lo:hi]


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    videos = index["videos"]

    # Look in captions/ for any caption file. Prefer .ttml over .vtt per video.
    candidates_by_video = {}
    files_by_vid = {}
    for d in [CAPTIONS_DIR]:
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix not in (".ttml", ".vtt"):
                continue
            vid = f.stem.split(".")[0]
            cur = files_by_vid.get(vid)
            if cur is None:
                files_by_vid[vid] = f
            elif cur.suffix == ".vtt" and f.suffix == ".ttml":
                files_by_vid[vid] = f  # prefer ttml

    for video_id, f in files_by_vid.items():
        if video_id not in videos:
            print(f"WARN: {video_id} not in index, skipping", file=sys.stderr)
            continue
        segs = parse_caption(f)
        if not segs:
            print(f"WARN: empty parse for {f}", file=sys.stderr)
            continue
        hits = list(find_hits(segs))
        print(f"{video_id}: {len(segs)} segments, {len(hits)} keyword hits")
        cands = []
        for i, tag, kw in hits:
            window = context_window(segs, i)
            ctx_text = " ".join(s["text"] for s in window)
            cands.append({
                "source_video_id": video_id,
                "source_video_title": videos[video_id]["title"],
                "hit_start_s": segs[i]["start"],
                "hit_end_s": segs[i]["end"],
                "keyword_category": tag,
                "keyword_match": kw,
                "context": ctx_text,
                "context_start_s": window[0]["start"],
                "context_end_s": window[-1]["end"],
            })
        candidates_by_video[video_id] = cands

    total = sum(len(c) for c in candidates_by_video.values())
    print(f"\nTotal candidates: {total} across {len(candidates_by_video)} videos")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for vid, cands in candidates_by_video.items():
            for c in cands:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
