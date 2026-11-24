#!/usr/bin/env python3
"""Hand a text task to Google Gemini and print or save the answer.

Usage: gemini_task.py "<prompt>" [--file TEXT_FILE ...] [--model NAME] [--out FILE] [--usage]
Credentials: GEMINI_API_KEY from the environment or .env (never printed).
Privacy: the prompt and any --file content are sent to Google. Never pass secrets;
.env, token*.json and client_secret*.json are refused.
Cost: answers are cached and counted against GEMINI_DAILY_TOKENS (see gemini_client.py);
--usage prints today's tokens and exits.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_client as gc  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?", help="task for Gemini")
    ap.add_argument("--file", action="append", default=[], help="text file to include (repeatable)")
    ap.add_argument("--model", default=gc.DEFAULT_MODEL, help=f"default {gc.DEFAULT_MODEL}")
    ap.add_argument("--out", help="write the answer here instead of stdout")
    ap.add_argument("--usage", action="store_true", help="print today's token use and exit")
    a = ap.parse_args()

    if a.usage:
        print(f"GEMINI USAGE today {gc.tokens_today()} / {gc.daily_cap()} tokens")
        return
    if not a.prompt:
        ap.error("prompt is required unless --usage")
    try:
        parts = [gc.text_part(a.prompt), *gc.file_parts(a.file)]
        answer = gc.generate(parts, model=a.model, task="gemini_task")
    except gc.GeminiError as e:
        gc.die(e)
    if a.out:
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(answer + "\n", encoding="utf-8")
        print(f"ok: {a.model} answered {len(answer)} chars -> {out}")
    else:
        print(answer)


if __name__ == "__main__":
    main()
