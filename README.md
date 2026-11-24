# Unreal Shorts studio

Cuts Unreal Engine tutorial Shorts from the owner's own videos, organizes playlists, and schedules uploads.

## Start
```
git clone <this repo>
cd unreal-shorts-studio
./install.sh            # creates .venv, installs requirements, checks ffmpeg
```
Then follow `docs/setup_checklist.md` (YouTube and Instagram access).

## Map
| Path | What it is |
|---|---|
| `CLAUDE.md` | Rules for Claude sessions (read first) |
| `docs/setup_checklist.md` | One-time owner steps |
| `docs/posting_strategy.md` | Slots, copy rules, who does what |
| `docs/instagram_plan.md` | Instagram Reels and Stories plan with captions |
| `docs/rights_and_policy.md` | Clip rights and platform policy |
| `docs/model_routing.md` | Which model does which work |
| `docs/drive_catalog.md` | Where videos, images and renders live in Google Drive |
| `docs/tools.md` | Every tool and API used |
| `docs/context_budget.md` | Token budgets |
| `docs/decisions.md` | Decisions log |
| `docs/handoff.md` | Checkpoint |
| `videos/_template/manifest.json` | Copy this to start a Short (one tip, one cut of one own video) |
| `tools/rights_gate.py` | Validates a tip manifest (rights, source, cut <= 60 s, privacy); exit 0 = pass |
| `tools/build_video.py` | Renders `out/<id>.mp4` 1080x1920 from the cut: blurred-fill fit, headline, source audio, optional `cta` end card (workshop); `--selftest` |
| `data/brand/` | Channel watermark PNGs (150x150) and `ianimate-i.png` (the iAnimate "i" used by the cta card) |
| `tools/youtube_upload.py` | Private/scheduled upload; `--long` or `format: long` skips `#shorts`; tags = hashtags + manifest `tags` + `tags_base.json` |
| `tools/tags_base.json` | Base YouTube tags by channel, format and topic (Animation, Lighting, Reel, Workshop...) |
| `tools/gemini_task.py` | Sends a text task (+ optional `--file`) to Gemini; key `GEMINI_API_KEY` from `.env`; refuses credential files |
| `.claude/skills/gemini/` | `/gemini <task>` quick access to `gemini_task.py` |
| `.env.example` | Names of the `.env` keys (no values); copy to `.env` |
| `tools/` (others) | Instagram publisher, slot picker, budget check |
| `.claude/` | Agents, skills (`make-video`, `publish`, `daily-run`) and rules |

## Quick use
```
cp -r videos/_template videos/unreal-lighting-01   # edit manifest.json
.venv/Scripts/python.exe tools/rights_gate.py videos/unreal-lighting-01/manifest.json
.venv/Scripts/python.exe tools/build_video.py videos/unreal-lighting-01/manifest.json
```
