#!/usr/bin/env python3
"""pipeline/api_client.py — direct mimo-v2.5 API client.

mimo-v2.5 is a reasoning model: ~100 tokens reasoning, then content.
Need max_tokens >= 300 to get actual output.

Usage:
  python3 pipeline/api_client.py --prompt "What is 2+2?"
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

API_URL = "https://opencode.ai/zen/go/v1/chat/completions"
MODEL = "mimo-v2.5"
MIN_TOKENS = 300


def _get_api_key() -> str:
    for p in [Path("/root/.hermes/profiles/patala/.env"), Path("/root/.hermes/.env")]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("OPENCODE_GO_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get("OPENCODE_GO_API_KEY", "")


def call_api(prompt: str, max_tokens: int = 400) -> dict:
    """Call mimo-v2.5. Returns content string."""
    api_key = _get_api_key()
    if not api_key:
        return {"content": "", "error": "no API key", "usage": {}}

    actual_max = max(max_tokens, MIN_TOKENS)
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": actual_max,
    }

    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", "30", "-X", "POST", API_URL,
             "-H", f"Authorization: Bearer {api_key}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload)],
            capture_output=True, text=True, timeout=45,
        )
        resp = json.loads(proc.stdout)
        if "error" in resp:
            return {"content": "", "error": str(resp["error"]), "usage": {}}
        msg = resp["choices"][0]["message"]
        content = msg.get("content") or ""
        usage = resp.get("usage", {})
        return {"content": content, "error": None, "usage": usage}
    except Exception as e:
        return {"content": "", "error": str(e), "usage": {}}


def call_json(prompt: str, max_tokens: int = 400) -> dict:
    """Call API and extract JSON."""
    r = call_api(prompt, max_tokens)
    parsed = _extract_json(r["content"]) if r["content"] else None
    return {"raw": r["content"], "parsed": parsed, "error": r["error"], "usage": r["usage"]}


def _extract_json(text: str):
    for start, end in [('{', '}'), ('[', ']')]:
        depth = 0
        si = None
        for i, c in enumerate(text):
            if c == start:
                if depth == 0: si = i
                depth += 1
            elif c == end:
                depth -= 1
                if depth == 0 and si is not None:
                    try:
                        return json.loads(text[si:i+1])
                    except json.JSONDecodeError:
                        si = None
    return None


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.json:
        print(json.dumps(call_json(a.prompt, a.max_tokens), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(call_api(a.prompt, a.max_tokens), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
