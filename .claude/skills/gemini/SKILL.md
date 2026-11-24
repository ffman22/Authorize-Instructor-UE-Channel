---
name: gemini
description: Hand a mechanical text task (summary, transcript cleanup, long-video notes) to Gemini. Use for "/gemini <task>".
---
# Gemini
1. Only own content and non-secret files. Never send `.env`, `token*.json` or `client_secret*.json` (the tool refuses them).
2. Run `.venv/Scripts/python.exe tools/gemini_task.py "<task>" [--file F ...] [--out FILE]`.
3. On HTTP 503 retry once after a minute; on 404 check `DEFAULT_MODEL` in the tool.
4. Reply in 3–5 lines: the answer first, then the file path if `--out` was used.
5. Video moments: `tools/find_moments.py <video> --own`; copy per platform: `tools/gemini_copy.py <manifest>`; thumbnails: `tools/make_thumbnail.py <manifest>`; tokens today: `gemini_task.py --usage`.
