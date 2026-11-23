---
name: make-video
description: Build a tip Short from a manifest (rights gate, then render). Use for "/make-video <id>" or when a manifest is ready to render.
---
# Make video
1. If `videos/<id>/manifest.json` does not exist, copy `videos/_template/manifest.json` and fill it from the chosen topic and the files in `data/clips/` (6 clips, labels, takes, a non-sequential `playback_order`). Follow `.claude/rules/content.md`.
2. Run `.venv/bin/python tools/rights_gate.py videos/<id>/manifest.json`. On failure, list the clips that failed and stop; never edit `rights` to pass.
3. Run `.venv/bin/python tools/build_video.py videos/<id>/manifest.json` → `out/<id>.mp4`.
4. Check with `ffprobe`: 1080x1920, 30–60 s, has an audio stream. Extract one frame to look at (`ffmpeg -ss 3 -i out/<id>.mp4 -frames:v 1 out/<id>.png`).
5. Reply in 3–5 lines: path, duration, order shown, any warning.
