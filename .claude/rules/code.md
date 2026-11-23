---
paths:
  - "tools/**"
---
# Code rules
- Python 3.11+, standard library first; third-party only what `requirements.txt` lists.
- Fix, never disconnect: an error is fixed at its cause, never hidden by removing or skipping the check (the rights gate included).
- Tools take a manifest path and print one summary line plus errors; no chatter.
- Secrets only from `.env` or `token.json`; never print them.
- Every tool has a `--help` and a row in `README.md`.
- Test a renderer change with `python3 tools/build_video.py --selftest`.
