#!/usr/bin/env python3
"""Hand a text task to Google Gemini and print or save the answer.

Usage: gemini_task.py "<prompt>" [--file TEXT_FILE ...] [--model NAME] [--out FILE]
Credentials: GEMINI_API_KEY from the environment or .env (never printed).
Privacy: the prompt and any --file content are sent to Google. Never pass secrets;
.env, token*.json and client_secret*.json are refused.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "gemini-3.1-flash-lite"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_FILE_BYTES = 500_000


def load_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    f = REPO_ROOT / ".env"
    if not key and f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip().removeprefix("export ").strip() == "GEMINI_API_KEY":
                key = v.strip().strip('"').strip("'")
    return key


def is_secret_file(path):
    n = path.name.lower()
    return n == ".env" or n.startswith(("token", "client_secret", ".env."))


def read_files(paths):
    parts = []
    for p in paths:
        path = Path(p)
        if is_secret_file(path):
            sys.exit(f"error: refusing to send {path.name} (credentials file)")
        if not path.is_file():
            sys.exit(f"error: file not found: {p}")
        if path.stat().st_size > MAX_FILE_BYTES:
            sys.exit(f"error: {p} is over {MAX_FILE_BYTES // 1000} KB; send an excerpt")
        parts.append(f"--- {path.name} ---\n{path.read_text(encoding='utf-8', errors='replace')}")
    return parts


def ask(key, model, text):
    body = json.dumps({"contents": [{"parts": [{"text": text}]}]}).encode()
    req = urllib.request.Request(
        ENDPOINT.format(model=model), data=body, method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        sys.exit(f"error: Gemini HTTP {e.code} {msg}".strip())
    except urllib.error.URLError as e:
        sys.exit(f"error: cannot reach Gemini ({e.reason})")
    try:
        return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError):
        reason = data.get("promptFeedback", {}).get("blockReason", "no candidates")
        sys.exit(f"error: Gemini returned no text ({reason})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", help="task for Gemini")
    ap.add_argument("--file", action="append", default=[], help="text file to include (repeatable)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"default {DEFAULT_MODEL}")
    ap.add_argument("--out", help="write the answer here instead of stdout")
    a = ap.parse_args()

    key = load_key()
    if not key:
        sys.exit("error: GEMINI_API_KEY missing; add it to .env (see .env.example)")
    answer = ask(key, a.model, "\n\n".join([a.prompt, *read_files(a.file)])).strip()
    if a.out:
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(answer + "\n", encoding="utf-8")
        print(f"ok: {a.model} answered {len(answer)} chars -> {out}")
    else:
        print(answer)


if __name__ == "__main__":
    main()
