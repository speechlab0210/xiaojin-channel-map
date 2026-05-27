#!/usr/bin/env python3
"""Stage 2: for each CROSS_SPECIFIC / CROSS_VAGUE / PREREQUISITE candidate,
resolve the target video.

Input: refs/classified.jsonl
Output: refs/resolved.jsonl (adds target_video_id, target_video_title,
        target_evidence, target_confidence, target_needs_visual)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llm_client import chat_json  # noqa

ROOT = Path(__file__).parent.parent
INDEX_PATH = ROOT / "data" / "video_index.json"
IN_PATH = ROOT / "refs" / "classified.jsonl"
OUT_PATH = ROOT / "refs" / "resolved.jsonl"


SYSTEM = """你是一個資料解析器。給你一段字幕脈絡（在某支影片裡，老師提到「另一支影片/另一堂課」），請從候選影片清單裡找出最有可能的目標影片。

回 JSON：
{
  "target_video_id": "<ID> or null（如果找不到任何符合）",
  "target_video_title": "<title> or null",
  "evidence": "<短中文 1-2 句說明為什麼選這個，引用文本中對應的片段>",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "needs_visual_check": true | false,
  "alt_candidates": ["<video_id_1>", "<video_id_2>"]  // 可能也對的 (最多 3 個) 或 []
}

策略（依優先順序）：
1. 「上一堂」「上一講」「前一講」→ 同 playlist 中當前位置減 1
2. 「第 N 講」「第 N 堂課」→ **首先在同 playlist 中找位置 N**；找不到才看其他 playlist
3. 「上學期/上個學期的課」→ **跨課程往時間軸最近的前一個學期找**（例：機器學習2026 的「上學期」= 生成式人工智慧與機器學習導論2025 或 生成式AI時代下的機器學習(2025)）
4. 「2018 年的時候講過 / 我之前 2018 年那套課」→ 對應年份的 playlist
5. 提到具體名稱（「機器學習導論」「OpenClaw」「Diffusion」）：
   - **「機器學習導論」如果出現在 2025+ 影片，通常指 2025 年的「生成式人工智慧與機器學習導論2025」或 「生成式AI時代下的機器學習(2025)」**，不是 2016 的老 ML 課
   - 提到 OpenClaw → 對應到 2rcJdFuNbZQ「解剖小龍蝦」
   - 提到 Diffusion → 對應到 Diffusion Model playlist
6. 模糊提示但有具體內容 hint（如「Meta 研究員讓 AI 收信」）→ 對照影片標題搜
7. **時間軸限制**：source 影片是 2026 的，target 通常 ≤2026；不要選比 source 還新的影片
8. **needs_visual_check=true**：當你看到關鍵詞「投影片」「連結」「URL」「QR」「我放在投影片上的這部影片」「請先看」「預習」「你看這部」「介紹過」這類強烈暗示投影片可能直接顯示 target URL 時，標 true
9. 找不到對應就回 null（不要瞎猜），confidence=LOW
"""


def build_candidate_view(idx, current_video_id, top_n_playlists=8):
    """Return compact text describing same-playlist + other playlists.
    Truncate each playlist to ~15 videos to keep prompt size reasonable.
    """
    cv = idx["videos"][current_video_id]
    cv_playlists = cv["playlists"]
    if not cv_playlists:
        cv_playlists = []
    cur_pid = cv_playlists[0]["playlist_id"] if cv_playlists else None
    cur_position = cv_playlists[0]["position"] if cv_playlists else None

    sections = []

    # Current playlist (full)
    if cur_pid:
        pl = idx["playlists"][cur_pid]
        sections.append(f"### 當前 playlist「{pl['title']}」（這支是位置 #{cur_position}）")
        for v in pl["videos"]:
            marker = " ←【當前影片】" if v["video_id"] == current_video_id else ""
            # Truncate title to 70 chars
            title = v["title"][:70]
            sections.append(f"  #{v['position']:02d}|{v['video_id']}|{title}{marker}")

    # All other playlists (very compact: 5 first videos per playlist)
    sections.append("\n### 其他課程（簡列）：")
    for pid, pl in idx["playlists"].items():
        if pid == cur_pid:
            continue
        sections.append(f"\n#### {pl['title'][:50]} ({pid}, 共 {len(pl['videos'])} 部)")
        # Show first 5 + last 2 if long
        vids = pl["videos"]
        if len(vids) <= 7:
            shown = vids
        else:
            shown = vids[:5] + [{"position": "...", "video_id": "(略)", "title": f"(略過 {len(vids)-7} 部)"}] + vids[-2:]
        for v in shown:
            title = v["title"][:55]
            sections.append(f"  #{v['position']}|{v['video_id']}|{title}")

    return "\n".join(sections)


def resolve(c, idx, candidate_view):
    cls = c["classification"]
    src = c["source_video_id"]
    src_title = c["source_video_title"]

    user = f"""【來源影片】{src_title}（ID: {src}）
【觸發關鍵詞】{c['keyword_match']}（{c['keyword_category']}）
【分類器結果】{cls['category']}, hint={cls.get('target_hint')}

【字幕脈絡】
{c['context']}

【可用影片清單】
{candidate_view}

請從清單中找出最有可能的目標 video_id。"""
    return chat_json(
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        model="gpt-4o-mini",
        reasoning_effort="minimal",
    )


def main():
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    cands = []
    with open(IN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cands.append(json.loads(line))

    targets_to_resolve = [c for c in cands if c["classification"]["category"] in ("CROSS_SPECIFIC", "CROSS_VAGUE", "PREREQUISITE")]
    print(f"Resolving {len(targets_to_resolve)} cross-ref candidates (out of {len(cands)} total)...")

    # Cache candidate view per source video (since it's the same for all candidates of same video)
    view_cache = {}

    n_done = 0
    out_rows = []
    for c in cands:
        cat = c["classification"]["category"]
        if cat not in ("CROSS_SPECIFIC", "CROSS_VAGUE", "PREREQUISITE"):
            out_rows.append(c)
            continue
        src = c["source_video_id"]
        if src not in view_cache:
            view_cache[src] = build_candidate_view(idx, src)
        try:
            r = resolve(c, idx, view_cache[src])
            c["resolved"] = r
        except Exception as e:
            c["resolved"] = {"target_video_id": None, "evidence": f"ERROR: {e}", "confidence": "LOW", "needs_visual_check": False, "alt_candidates": []}
        out_rows.append(c)
        n_done += 1
        if n_done % 3 == 0 or n_done == len(targets_to_resolve):
            r = c["resolved"]
            tgt = r.get("target_video_id")
            tgt_title = idx["videos"].get(tgt, {}).get("title", "?") if tgt else "(none)"
            print(f"  {n_done}/{len(targets_to_resolve)} | {c['source_video_id']}@{c['hit_start_s']:.0f}s -> {tgt} | {tgt_title[:50]} | conf={r.get('confidence')}", flush=True)

    OUT_PATH.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in out_rows) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT_PATH}")

    # Summary
    resolved_count = sum(1 for c in out_rows if c.get("resolved", {}).get("target_video_id"))
    by_conf = {}
    for c in out_rows:
        r = c.get("resolved")
        if r and r.get("target_video_id"):
            by_conf[r["confidence"]] = by_conf.get(r["confidence"], 0) + 1
    print(f"\nResolved {resolved_count} / {len(targets_to_resolve)} cross-refs to a target video")
    print(f"  by confidence: {by_conf}")


if __name__ == "__main__":
    main()
