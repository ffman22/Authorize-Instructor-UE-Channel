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
| `docs/rights_and_policy.md` | Clip rights and platform policy |
| `docs/model_routing.md` | Which model does which work |
| `docs/drive_catalog.md` | Where videos, images and renders live in Google Drive |
| `docs/tools.md` | Every tool and API used |
| `docs/context_budget.md` | Token budgets |
| `docs/decisions.md` | Decisions log |
| `docs/handoff.md` | Checkpoint |
| `videos/_template/manifest.json` | Copy this to start a Short |
| `tools/` | Rights gate, renderer, uploaders, slot picker, budget check |
| `.claude/` | Agents, skills (`make-video`, `publish`, `daily-run`) and rules |

## Quick use
```
cp -r videos/_template videos/unreal-lighting-01   # edit manifest.json
.venv/bin/python tools/rights_gate.py videos/unreal-lighting-01/manifest.json
.venv/bin/python tools/build_video.py videos/unreal-lighting-01/manifest.json
```
