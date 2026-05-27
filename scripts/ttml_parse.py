#!/usr/bin/env python3
"""Parse TTML or VTT caption -> list of {start, end, text} segments."""
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"tt": "http://www.w3.org/ns/ttml"}


def parse_time(ts: str) -> float:
    """HH:MM:SS.mmm or H:MM:SS.mmm -> seconds float."""
    if not ts:
        return 0.0
    ts = ts.strip()
    m = re.match(r"(\d+):(\d+):(\d+(?:[.,]\d+)?)", ts)
    if not m:
        m = re.match(r"(\d+):(\d+(?:[.,]\d+)?)", ts)
        if m:
            mn, s = m.groups()
            return int(mn) * 60 + float(s.replace(",", "."))
        return 0.0
    h, mn, s = m.groups()
    return int(h) * 3600 + int(mn) * 60 + float(s.replace(",", "."))


def parse_ttml(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    body = root.find(".//tt:body", NS)
    segments = []
    if body is None:
        return segments
    for p in body.iter("{http://www.w3.org/ns/ttml}p"):
        b = p.attrib.get("begin")
        e = p.attrib.get("end")
        txt = "".join(p.itertext()).strip()
        if not txt:
            continue
        segments.append({"start": parse_time(b), "end": parse_time(e), "text": txt})
    return segments


def parse_vtt(path: Path):
    text = path.read_text(encoding="utf-8")
    # Strip WEBVTT header
    lines = text.split("\n")
    segments = []
    i = 0
    last_text = None  # to dedupe yt auto-caption rolling lines
    while i < len(lines):
        line = lines[i].strip()
        # Time line e.g. 00:00:01.000 --> 00:00:03.000
        m = re.match(r"(\d+:\d+(?::\d+)?(?:[.,]\d+)?)\s+-->\s+(\d+:\d+(?::\d+)?(?:[.,]\d+)?)", line)
        if not m:
            i += 1
            continue
        start = parse_time(m.group(1))
        end = parse_time(m.group(2))
        i += 1
        # Read text lines until empty line
        txt_lines = []
        while i < len(lines) and lines[i].strip():
            t = lines[i].strip()
            # Strip cue tags like <c.colorE5E5E5>...
            t = re.sub(r"<[^>]+>", "", t)
            # Strip timestamp tags like <00:00:01.500>
            t = re.sub(r"<\d+:\d+:\d+\.\d+>", "", t).strip()
            if t:
                txt_lines.append(t)
            i += 1
        txt = " ".join(txt_lines).strip()
        if not txt:
            continue
        # Dedupe rolling auto-caption (same as last segment's text)
        if txt == last_text:
            # Extend the previous segment's end time
            if segments:
                segments[-1]["end"] = end
            continue
        segments.append({"start": start, "end": end, "text": txt})
        last_text = txt
    return segments


def parse_caption(path: Path):
    if path.suffix == ".ttml":
        return parse_ttml(path)
    if path.suffix == ".vtt":
        return parse_vtt(path)
    # Try extension-agnostic detection
    head = path.read_text(encoding="utf-8")[:200]
    if "WEBVTT" in head:
        return parse_vtt(path)
    if "<tt " in head or "<tt:" in head or "ttml" in head:
        return parse_ttml(path)
    return []


if __name__ == "__main__":
    p = Path(sys.argv[1])
    segs = parse_caption(p)
    print(f"Segments: {len(segs)}")
    if segs:
        print(f"First: {segs[0]}")
        print(f"Last: {segs[-1]}")
        print(f"Duration: {segs[-1]['end']:.1f}s")
