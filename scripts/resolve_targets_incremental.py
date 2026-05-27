#!/usr/bin/env python3
"""Resolver with incremental write — writes after each batch of N completions.
Allows progress observability and crash recovery.
"""
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

    targets = [(i, c) for i, c in enumerate(cands) if c["classification"]["category"] in ("CROSS_SPECIFIC", "CROSS_VAGUE", "PREREQUISITE")]
    print(f"Resolving {len(targets)} cross-ref candidates (out of {len(cands)} total)...", flush=True)

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
    done = 0
    write_every = 25

    def flush():
        for i, r in results.items():
            cands[i]["resolved"] = r
        OUT_PATH.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in cands) + "\n", encoding="utf-8")

    with ThreadPoolExecutor(max_workers=6) as pool:  # reduced from 10 to 6 for rate limit
        futs = [pool.submit(worker, i, c) for i, c in targets]
        for fut in as_completed(futs):
            i, r = fut.result()
            results[i] = r
            done += 1
            if done % write_every == 0 or done == len(targets):
                flush()
                tgt = r.get("target_video_id")
                tgt_title = idx["videos"].get(tgt, {}).get("title", "?")[:50] if tgt else "(none)"
                print(f"  {done}/{len(targets)} | last: -> {tgt} | {tgt_title} | {r.get('confidence')}", flush=True)

    flush()
    print(f"\nWrote {OUT_PATH}")

    resolved_count = sum(1 for c in cands if c.get("resolved", {}).get("target_video_id"))
    by_conf = {}
    for c in cands:
        r = c.get("resolved")
        if r and r.get("target_video_id"):
            by_conf[r["confidence"]] = by_conf.get(r["confidence"], 0) + 1
    print(f"Resolved {resolved_count} / {len(targets)} to a target")
    print(f"  by confidence: {by_conf}")


if __name__ == "__main__":
    main()
