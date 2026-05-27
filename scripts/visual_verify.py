#!/usr/bin/env python3
"""Visual verification of MEDIUM-confidence resolutions.

Downloads the source video segment around hit_start_s, extracts 2-3 frames,
sends to vision LLM to check if there's visual evidence supporting the
resolver's chosen target (slide content, embedded YouTube URL, slide title).

Pipeline:
  for each MEDIUM/LOW resolved edge:
    1. Download 20s segment of source video around hit_start_s
    2. Extract 3 frames (at hit_start_s-5, hit_start_s, hit_start_s+10)
    3. Vision LLM: "look at these frames. Is there visual evidence (slide content,
       embedded video preview, written text) that connects to the proposed target
       <target_title>? If not, what does the slide actually reference?"
    4. Update resolved.jsonl with verified=True/False/PARTIAL and visual_evidence
"""
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llm_client import get_openai_key  # noqa
import urllib.request

ROOT = Path(__file__).parent.parent
RESOLVED_PATH = ROOT / "refs" / "resolved.jsonl"
OUT_PATH = ROOT / "refs" / "visual_verified.jsonl"
VIDEO_DIR = ROOT / "tmp_segments"
FRAMES_DIR = ROOT / "tmp_frames"

YTDLP = "C:/Users/tlkag/AppData/Local/Microsoft/WindowsApps/yt-dlp.exe"
FFMPEG_DIR = "C:/Users/tlkag/.openclaw/workspace/ffmpeg-8.0.1-essentials_build/bin"
FFMPEG = f"{FFMPEG_DIR}/ffmpeg.exe"
FFPROBE = f"{FFMPEG_DIR}/ffprobe.exe"


def download_segment(video_id: str, start: float, dur: float = 20.0) -> Path:
    """Use yt-dlp --download-sections to grab a small segment."""
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    out = VIDEO_DIR / f"{video_id}_{int(start)}.mp4"
    if out.exists() and out.stat().st_size > 1000:
        return out
    s = max(0, start - 5)
    e = s + dur
    sec_str = f"*{int(s)}-{int(e)}"
    cmd = [
        YTDLP,
        "--download-sections", sec_str,
        "--ffmpeg-location", FFMPEG_DIR,
        "-f", "best[height<=480]/best",
        "-o", str(out),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    subprocess.run(cmd, check=False, capture_output=True)
    return out if out.exists() else None


def extract_frame(video: Path, t_rel: float) -> Path:
    """Extract a single frame at t_rel seconds (relative to segment start)."""
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    out = FRAMES_DIR / f"{video.stem}_t{int(t_rel)}.jpg"
    if out.exists():
        return out
    cmd = [
        FFMPEG, "-y", "-ss", str(t_rel), "-i", str(video),
        "-frames:v", "1", "-q:v", "3",
        str(out),
    ]
    subprocess.run(cmd, check=False, capture_output=True)
    return out if out.exists() else None


def vision_check(frames: list, target_title: str, context: str, alt_candidates: list, idx: dict):
    """Send frames + context to vision LLM. Returns verification result."""
    if not frames:
        return {"verified": "UNKNOWN", "evidence": "no frames", "alt_match": None}

    images = []
    for f in frames:
        if not f or not f.exists():
            continue
        b = base64.b64encode(f.read_bytes()).decode()
        images.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}"}})

    if not images:
        return {"verified": "UNKNOWN", "evidence": "no readable frames", "alt_match": None}

    alt_titles = [idx["videos"].get(c, {}).get("title", "?") for c in alt_candidates[:3]]
    alt_text = "\n".join(f"- {c}: {t[:60]}" for c, t in zip(alt_candidates, alt_titles))

    prompt_text = f"""這幾張是李宏毅老師上課影片的截圖（投影片）。老師在 caption 裡說：

「{context[:300]}」

我猜他指的是另一支影片：「{target_title[:80]}」

請看投影片畫面，回答以下三件事（用 JSON）：

1. verified: "YES" / "NO" / "PARTIAL" / "UNKNOWN"
   - YES = 畫面上有強證據（投影片有顯示這個 reference，譬如貼了該影片連結、寫了該影片標題、有相關截圖）
   - NO = 畫面上的內容明顯指向另一支影片或主題（請在 evidence 說明）
   - PARTIAL = 主題相關但無法確定就是這支
   - UNKNOWN = 投影片內容無法判斷
2. evidence: 看到的關鍵 visual cue（如「投影片有寫『機器學習導論 第三講』+ YouTube 連結」、「投影片畫了 transformer 結構圖跟講者描述吻合」）
3. alt_match: 如果有更可能的候選，從以下列表挑（不確定回 null）：
{alt_text}

JSON: {{"verified": "...", "evidence": "...", "alt_match": "<video_id>|null"}}
"""

    api_key = get_openai_key()
    body = {
        "model": "gpt-5",
        "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": prompt_text},
                *images,
            ]},
        ],
        "response_format": {"type": "json_object"},
        "reasoning_effort": "low",
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            return json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        return {"verified": "UNKNOWN", "evidence": f"ERROR {e}", "alt_match": None}


def main():
    # If --queue, use refs/visual_queue.jsonl as input (selected smart subset)
    if len(sys.argv) > 1 and sys.argv[1] == "--queue":
        queue_path = ROOT / "refs" / "visual_queue.jsonl"
        target_confidence = None  # ignored
        rows_path = queue_path
    else:
        rows_path = RESOLVED_PATH
        if len(sys.argv) > 1 and sys.argv[1] == "--all":
            target_confidence = ("HIGH", "MEDIUM", "LOW")
        elif len(sys.argv) > 1 and sys.argv[1] == "--low":
            target_confidence = ("LOW",)
        else:
            target_confidence = ("MEDIUM",)

    idx = json.loads((ROOT / "data" / "video_index.json").read_text(encoding="utf-8"))

    rows = []
    with open(rows_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    if target_confidence is None:
        to_verify = [r for r in rows if r.get("resolved", {}).get("target_video_id")]
    else:
        to_verify = [r for r in rows if r.get("resolved", {}).get("confidence") in target_confidence and r["resolved"].get("target_video_id")]
    print(f"To verify: {len(to_verify)}", flush=True)

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def process_one(c):
        r = c["resolved"]
        tgt = r["target_video_id"]
        src = c["source_video_id"]
        t = c["hit_start_s"]
        seg = download_segment(src, t, 25.0)
        if not seg:
            return c, {"verified": "UNKNOWN", "evidence": "segment download failed"}
        f1 = extract_frame(seg, 2)
        f2 = extract_frame(seg, 7)
        f3 = extract_frame(seg, 15)
        target_title = idx["videos"].get(tgt, {}).get("title", "?")
        alt_cands = r.get("alt_candidates") or []
        vr = vision_check([f for f in [f1, f2, f3] if f], target_title, c.get("context", ""), alt_cands, idx)
        return c, vr

    done = 0
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(process_one, c) for c in to_verify]
        for fut in as_completed(futs):
            c, vr = fut.result()
            c["visual_verification"] = vr
            results.append(c)
            done += 1
            if done % 5 == 0 or done == len(to_verify):
                # Incremental write
                OUT_PATH.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
                print(f"[{done}/{len(to_verify)}] last: {c['source_video_id']}@{int(c['hit_start_s'])}s verified={vr.get('verified')} ev={vr.get('evidence', '')[:60]}", flush=True)

    OUT_PATH.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT_PATH}")

    summary = {}
    for c in rows:
        v = c.get("visual_verification")
        if v:
            summary[v["verified"]] = summary.get(v["verified"], 0) + 1
    print(f"\nVerification summary: {summary}")


if __name__ == "__main__":
    main()
