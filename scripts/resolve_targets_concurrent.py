#!/usr/bin/env python3
"""Parallel target resolver."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llm_client import chat_json  # noqa
from resolve_targets import SYSTEM, build_candidate_view, resolve  # noqa

ROOT = Path(__file__).parent.parent
INDEX_PATH = ROOT / "data" / "video_index.json"
IN_PATH = ROOT / "refs" / "classified.jsonl"
OUT_PATH = ROOT / "refs" / "resolved.jsonl"


def main():
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    cands = []
    with open(IN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cands.append(json.loads(line))

    targets_to_resolve = [(i, c) for i, c in enumerate(cands) if c["classification"]["category"] in ("CROSS_SPECIFIC", "CROSS_VAGUE", "PREREQUISITE")]
    print(f"Resolving {len(targets_to_resolve)} cross-ref candidates (out of {len(cands)} total)...")

    view_cache = {}

    def worker(i, c):
        src = c["source_video_id"]
        if src not in view_cache:
            view_cache[src] = build_candidate_view(idx, src)
        try:
            r = resolve(c, idx, view_cache[src])
            return i, r
        except Exception as e:
            return i, {"target_video_id": None, "evidence": f"ERROR: {str(e)[:200]}", "confidence": "LOW", "needs_visual_check": False, "alt_candidates": []}

    results = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = [pool.submit(worker, i, c) for i, c in targets_to_resolve]
        done = 0
        for fut in as_completed(futs):
            i, r = fut.result()
            results[i] = r
            done += 1
            if done % 10 == 0 or done == len(targets_to_resolve):
                tgt = r.get("target_video_id")
                tgt_title = idx["videos"].get(tgt, {}).get("title", "?")[:50] if tgt else "(none)"
                print(f"  {done}/{len(targets_to_resolve)} | last: -> {tgt} | {tgt_title} | {r.get('confidence')}", flush=True)

    for i, c in enumerate(cands):
        if i in results:
            c["resolved"] = results[i]

    OUT_PATH.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in cands) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT_PATH}")

    resolved_count = sum(1 for c in cands if c.get("resolved", {}).get("target_video_id"))
    by_conf = {}
    for c in cands:
        r = c.get("resolved")
        if r and r.get("target_video_id"):
            by_conf[r["confidence"]] = by_conf.get(r["confidence"], 0) + 1
    print(f"\nResolved {resolved_count} / {len(targets_to_resolve)} cross-refs to a target video")
    print(f"  by confidence: {by_conf}")


if __name__ == "__main__":
    main()
