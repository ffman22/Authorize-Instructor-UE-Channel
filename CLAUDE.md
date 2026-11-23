# Unreal Shorts studio — notes for Claude sessions

Read this first; open only the file the task needs (map in `README.md`). Budgets: `docs/context_budget.md`.

## Intent
- Professional animator channel (Unreal tutorials, reels, industry commentary). Long videos and Shorts in equal numbers; Shorts keep the channel active. Shorts = one tip each, cut by Claude from the owner's own long videos (own footage only).
- Playlists by Unreal topic (e.g. Lighting, Materials, Niagara, Sequencer). Uploads stay private/scheduled until the owner says "publica".
- Older personal-channel videos are re-uploaded here by the same pipeline.

## Pipeline (one manifest per Short: `videos/<id>/manifest.json`)
1. Owner drops the source video in `data/clips/` and names the tip.
2. Claude cuts the Short (≤ 60 s, 9:16) and fills the manifest (rights `own`, source, timestamps).
3. `tools/rights_gate.py` must pass, then `tools/build_video.py` renders `out/<id>.mp4`.
4. `tools/youtube_upload.py` uploads private/scheduled; `tools/instagram_publish.py` if set up.
5. Slots from `tools/best_times.py` (vidIQ or YouTube Data API) into `docs/posting_strategy.md`.

## Rules (verifiable)
- Language: chat in Spanish; files, code, commits in English. Check: commit message and file names are English.
- Rights: only `own` footage or licensed/permission clips with proof. Never scrape or rip platform videos. Check: `python3 tools/rights_gate.py videos/<id>/manifest.json` exits 0 before render and upload.
- Upload default is private/scheduled, never public-now, until the owner says "publica". Check: `privacy` is `private` or `publish_at` is set.
- Never commit tokens, `client_secret.json`, `token.json` or `.env`. Check: `git status` shows none.
- Model routing: Sonnet does the daily loop; hard code and API debugging go to `opus-engineer`; mechanical checks to `haiku-checker`; strategy to `opus-strategist` ([model_routing.md](docs/model_routing.md)).
- Workshop link: every Short and Unreal video links the workshop (`https://ianimate.net/workshops/unreal-for-animators`) in its description, or sets `cta` for a burned-in end card. Check: `rights_gate.py` exits 0.
- Short chat replies: 3–5 lines; answer first.
- Record every change in the same commit: new files in `README.md` map, decisions in `docs/decisions.md`, checkpoint in `docs/handoff.md`.
- After editing any `CLAUDE.md`, rule or skill: `python3 tools/context_budget.py --strict`. Check: exit code 0.

## Gotchas
- Cloud Python: use a virtual environment (`./install.sh` creates it).
- ffmpeg must exist (`ffmpeg -version`).
- The owner dictates in Spanish with speech-to-text errors: read for intent.
