#!/usr/bin/env python3
"""Tiny OpenAI HTTP client (no SDK dependency). Reads key from ~/.codex/auth.json."""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


def get_openai_key():
    p = Path.home() / ".codex" / "auth.json"
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            k = d.get("OPENAI_API_KEY")
            if k:
                return k
        except Exception:
            pass
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k
    raise RuntimeError("No OpenAI key found in ~/.codex/auth.json or env")


def chat(messages, model="gpt-5-mini", reasoning_effort="minimal", retries=3):
    """Call OpenAI chat completion. Returns parsed JSON if the last user msg
    requests JSON, else string."""
    api_key = get_openai_key()
    url = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": model,
        "messages": messages,
    }
    if "gpt-5" in model:
        body["reasoning_effort"] = reasoning_effort
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            last_err = f"HTTP {e.code}: {err_body[:400]}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(last_err)
        except urllib.error.URLError as e:
            last_err = str(e)
            time.sleep(2 ** attempt)
            continue
        except Exception as e:
            last_err = str(e)
            time.sleep(2 ** attempt)
            continue
    raise RuntimeError(f"All retries failed: {last_err}")


def chat_json(messages, model="gpt-5-mini", reasoning_effort="minimal", retries=5):
    """Like chat() but enforces JSON response and parses it."""
    api_key = get_openai_key()
    url = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    if "gpt-5" in model:
        body["reasoning_effort"] = reasoning_effort
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                txt = data["choices"][0]["message"]["content"]
                return json.loads(txt)
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            last_err = f"HTTP {e.code}: {err_body[:400]}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(last_err)
        except (urllib.error.URLError, json.JSONDecodeError, Exception) as e:
            last_err = str(e)
            time.sleep(2 ** attempt)
            continue
    raise RuntimeError(f"All retries failed: {last_err}")


if __name__ == "__main__":
    # Smoke test
    r = chat_json(
        messages=[
            {"role": "system", "content": "Respond with JSON {\"ok\": true, \"echo\": \"<input>\"}."},
            {"role": "user", "content": "hello"},
        ],
        model="gpt-5-mini",
    )
    print(r)
