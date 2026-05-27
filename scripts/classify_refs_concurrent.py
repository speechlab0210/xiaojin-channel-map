#!/usr/bin/env python3
"""Parallel classifier — same logic as classify_refs.py but with ThreadPoolExecutor."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llm_client import chat_json  # noqa

ROOT = Path(__file__).parent.parent
IN_PATH = ROOT / "refs" / "candidates.jsonl"
OUT_PATH = ROOT / "refs" / "classified.jsonl"


SYSTEM = """你是一個分類器，判斷字幕片段中的「之前/上次/前面/講過...」這類詞句到底是不是在指向「另一支影片」。

輸入是一段字幕脈絡 + 該影片的標題。

請判斷分類，並用 JSON 回覆。

類別：
- "INTRA":      在同一支影片內 referring back（例如「之前發生的事情」、「剛才講的」、「我前面提到」、「上一頁投影片」、「之前的迴圈」）
- "CROSS_SPECIFIC": 明確指向另一支具體影片或某一講（例如「上一堂課」、「第三講我們講過」、「之前那支影片」、「我們上次講」）
- "CROSS_VAGUE":   提到「以前介紹過 / 之前的影片有講過」但沒有指明哪一支
- "PREREQUISITE":  指向另一門課作為先修（例如「機器學習導論」、「假設你看過 X 的錄影」）
- "OTHER":         例如「上課的時候」當作副詞、「上個課」當動詞、「之前」用做時間副詞，與影片無關

JSON 格式：
{
  "category": "INTRA" | "CROSS_SPECIFIC" | "CROSS_VAGUE" | "PREREQUISITE" | "OTHER",
  "reason": "<短中文 1 句說明>",
  "target_hint": "<如果可以從文本看出指向哪一講/哪一支，請寫出來；不確定寫 null>"
}
"""


def classify(c):
    user = f"""影片標題：{c['source_video_title']}
時間戳：{c['hit_start_s']:.0f}s ~ {c['hit_end_s']:.0f}s
觸發關鍵詞：{c['keyword_match']}（{c['keyword_category']}）

字幕脈絡（~10 句）：
{c['context']}"""
    return chat_json(
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        model="gpt-5-mini",
        reasoning_effort="minimal",
    )


def main():
    cands = []
    with open(IN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cands.append(json.loads(line))

    print(f"Classifying {len(cands)} candidates (concurrent, 10 workers)...")

    results = [None] * len(cands)

    def worker(i):
        try:
            return i, classify(cands[i])
        except Exception as e:
            return i, {"category": "ERROR", "reason": str(e)[:200], "target_hint": None}

    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = [pool.submit(worker, i) for i in range(len(cands))]
        done = 0
        for fut in as_completed(futs):
            i, cls = fut.result()
            results[i] = cls
            done += 1
            if done % 20 == 0 or done == len(cands):
                print(f"  {done}/{len(cands)}", flush=True)

    out_lines = []
    for c, cls in zip(cands, results):
        c["classification"] = cls
        out_lines.append(json.dumps(c, ensure_ascii=False))
    OUT_PATH.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")

    cnt = {}
    for cls in results:
        cnt[cls["category"]] = cnt.get(cls["category"], 0) + 1
    print("\nClassification summary:")
    for k, v in sorted(cnt.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
