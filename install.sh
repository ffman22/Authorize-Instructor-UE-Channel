#!/usr/bin/env bash
# One-time setup for a fresh clone. Safe to run again.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is missing. Install it first (Ubuntu: sudo apt-get install -y ffmpeg; macOS: brew install ffmpeg)." >&2
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

mkdir -p out data/clips data/topics
touch out/.gitkeep data/clips/.gitkeep

.venv/bin/python tools/context_budget.py --strict >/dev/null && echo "budget check: ok" || echo "budget check: see tools/context_budget.py"
echo "Done. Next: docs/setup_checklist.md"
