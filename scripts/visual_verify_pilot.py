#!/usr/bin/env python3
"""Pilot visual verification on 3 hand-picked MEDIUM cases."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from visual_verify import download_segment, extract_frame, vision_check  # noqa

ROOT = Path(__file__).parent.parent


def main():
    idx = json.loads((ROOT / "data" / "video_index.json").read_text(encoding="utf-8"))

    pilots = [
        # (source_id, hit_t, target_id, context)
        ("2rcJdFuNbZQ", 90, "CXgbekl66jc", "本學期的課程是假設你已經看過機器學習導論過去的錄影 你可以先預習機器學習導論這門課的上課錄影"),
        ("CbIPjrOj2Tc", 10, "TigfpYPJk1s", "在過去的幾堂課裡面 我們花了很多力氣講了各式各樣 生成式 AI 的技術"),
        ("CbIPjrOj2Tc", 4187, "lMIN1iKYNmA", "我在 2022 年 還沒有 ChatGPT 的時候 曾經給過一個演講 講這樣子的模型 是怎麼被訓練出來的"),
    ]

    for src, t, tgt, ctx in pilots:
        print(f"\n=== {src}@{t}s -> {tgt} ===")
        seg = download_segment(src, t, 25.0)
        if not seg:
            print(f"  segment download failed")
            continue
        print(f"  segment: {seg.name} ({seg.stat().st_size//1024} KB)")
        f1 = extract_frame(seg, 2)
        f2 = extract_frame(seg, 7)
        f3 = extract_frame(seg, 15)
        frames = [f for f in [f1, f2, f3] if f]
        print(f"  frames: {len(frames)}")

        target_title = idx["videos"].get(tgt, {}).get("title", "?")
        v = vision_check(frames, target_title, ctx, [], idx)
        print(f"  verified={v.get('verified')}")
        print(f"  evidence: {v.get('evidence', '')[:200]}")


if __name__ == "__main__":
    main()
