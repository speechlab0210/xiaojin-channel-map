#!/usr/bin/env python3
"""Build graph data JSON for the visualization site.

Combines:
- video_index.json (nodes)
- refs/resolved.jsonl (edges)

Output:
- data/graph.json : { "nodes": [...], "edges": [...] }

Node:
{
  "id": "videoId",
  "title": "...",
  "duration_s": ...,
  "url": "...",
  "course": "playlist title (primary)",
  "course_id": "playlist id (primary)",
  "course_position": int,
  "all_courses": [...],
  "incoming_count": int,
  "outgoing_count": int,
}

Edge:
{
  "source": "videoId",
  "target": "videoId",
  "source_t": float (seconds in source video),
  "category": "CROSS_SPECIFIC | CROSS_VAGUE | PREREQUISITE",
  "confidence": "HIGH | MEDIUM | LOW",
  "evidence": "...",
  "keyword_match": "...",
  "context": "(short, first 200 chars)"
}
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX_PATH = ROOT / "data" / "video_index.json"
RESOLVED_PATH = ROOT / "refs" / "resolved.jsonl"
OUT_PATH = ROOT / "data" / "graph.json"


def main():
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    videos = idx["videos"]
    playlists = idx["playlists"]

    # Build nodes
    nodes = {}
    for vid, v in videos.items():
        primary_pl = v["playlists"][0] if v["playlists"] else None
        course_title = playlists[primary_pl["playlist_id"]]["title"] if primary_pl else "(無系列)"
        course_id = primary_pl["playlist_id"] if primary_pl else None
        course_pos = primary_pl["position"] if primary_pl else None
        nodes[vid] = {
            "id": vid,
            "title": v["title"],
            "duration_s": v["duration_s"],
            "url": v["url"],
            "course": course_title,
            "course_id": course_id,
            "course_position": course_pos,
            "all_courses": [
                {"playlist_id": p["playlist_id"], "title": playlists[p["playlist_id"]]["title"], "position": p["position"]}
                for p in v["playlists"]
            ],
            "incoming_count": 0,
            "outgoing_count": 0,
        }

    # Build edges from resolved.jsonl
    edges = []
    if RESOLVED_PATH.exists():
        with open(RESOLVED_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                c = json.loads(line)
                cls = c.get("classification", {})
                r = c.get("resolved")
                if not r:
                    continue
                tgt = r.get("target_video_id")
                if not tgt or tgt not in nodes:
                    continue
                src = c["source_video_id"]
                if src == tgt:
                    continue
                vv = c.get("visual_verification")
                edges.append({
                    "source": src,
                    "target": tgt,
                    "source_t": c["hit_start_s"],
                    "category": cls.get("category"),
                    "confidence": r.get("confidence"),
                    "evidence": r.get("evidence"),
                    "needs_visual_check": r.get("needs_visual_check", False),
                    "keyword_match": c.get("keyword_match"),
                    "context": c.get("context", "")[:300],
                    "alt_candidates": r.get("alt_candidates", []),
                    "visual_verified": vv.get("verified") if vv else None,
                    "visual_evidence": vv.get("evidence") if vv else None,
                })
                if src in nodes:
                    nodes[src]["outgoing_count"] += 1
                if tgt in nodes:
                    nodes[tgt]["incoming_count"] += 1

    out = {
        "metadata": {
            "video_count": len(nodes),
            "edge_count": len(edges),
            "playlists": [{"id": pid, "title": pl["title"], "video_count": len(pl["videos"])} for pid, pl in playlists.items()],
        },
        "nodes": list(nodes.values()),
        "edges": edges,
    }

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    print(f"  {len(nodes)} nodes")
    print(f"  {len(edges)} edges")
    # Top videos by incoming reference count
    top_in = sorted(nodes.values(), key=lambda n: -n["incoming_count"])[:10]
    print("\nTop 10 most-referenced videos (by incoming refs):")
    for n in top_in:
        if n["incoming_count"] == 0:
            break
        print(f"  {n['incoming_count']} <- {n['id']} | {n['title'][:60]}")
    top_out = sorted(nodes.values(), key=lambda n: -n["outgoing_count"])[:10]
    print("\nTop 10 reference-heavy videos (by outgoing refs):")
    for n in top_out:
        if n["outgoing_count"] == 0:
            break
        print(f"  {n['outgoing_count']} -> {n['id']} | {n['title'][:60]}")


if __name__ == "__main__":
    main()
