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
| `docs/channel_audit_2026-11-27.md` | Live YouTube errors and research-doc review |
| `docs/creator_brief.md` | Owner's standing requirements for thumbnails, audience, scripts, metrics, intro video (Gemini and Claude as manager and coach) |
| `docs/script_intro.md` | Channel trailer (on camera, about 2 min), its separate vertical version for Instagram, TikTok and Threads, and the short and long credibility intros |
| `docs/script_format.md` | The format every script follows: result first, Short and long beats, editing, idea backlog |
| `docs/series_ue5_secret.md` | Series "AAA UE5 Secret:" episodes 1-3: scripts, recording list, gates; drafts in `videos/ue5-secret-0*/` and `videos/channel-intro/` |
| `.claude/hooks/gemini-route.mjs` | Routes video analysis and long texts to Gemini: reminder on the prompt, asks the owner before Claude does that work |
| `docs/creator_playbook.md` | Gemini-drafted playbook from the brief: thumbnail system, viewer profiles, script templates, metrics loop, intro video plan, weekly routine |
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
| `tools/build_video.py` | Renders `out/<id>.mp4` 1080x1920 from the cut: blurred-fill fit, headline, source audio, optional `cta` end card (workshop) or animated splash appended after a 1 s fade to black and silence; `--selftest` |
| `data/brand/` | Local brand images (ignored by git, master copies on Drive) and `thumbs.json` (cover settings) |
| `tools/youtube_upload.py` | Private/scheduled upload after owner approval; no hashtags in titles, 3 in the description; tags = manifest `tags` + hashtags + niche and broad from `tags_base.json` |
| `tools/approval.py` | Owner approval gate: review sheet, approval record, HD and spec checks |
| `tools/psd_layers.py` | Reads layers of the owner's PSD templates |
| `docs/research_rules.md` | Adopted rules from the social media research (Drive docs 01-08) |
| `tools/tags_base.json` | YouTube niche tags (by topic, Unreal, common) and broad tags; post-specific tags live in each manifest |
| `tools/gemini_client.py` | Shared Gemini client: text, images, video (Files API), JSON mode; cache in `out/gemini/cache/`, token log `out/gemini/usage.jsonl`, daily cap `GEMINI_DAILY_TOKENS` |
| `tools/gemini_task.py` | Sends a text task (+ optional `--file` or `--youtube URL`) to Gemini; refuses credential files; `--usage` shows today's tokens |
| `tools/gemini_review.py` | Gemini watches and listens to an own or permitted video or audio file and reports if it fits its type; loudness and resolution measured locally; report in `out/gemini/reviews/` |
| `tools/gemini_image.py` | Creates or edits draft images with Gemini (needs billing: free tier quota is 0) |
| `tools/find_moments.py` | Gemini watches an own long video (360p proxy, once, cached) and lists Short-sized tip moments; `--make-manifests` writes drafts with `ready_to_publish` false |
| `tools/gemini_copy.py` | One Gemini call writes YouTube, Instagram, TikTok, Threads and Community copy for a manifest; `--apply` merges it if the rights gate passes |
| `tools/make_thumbnail.py` | Best frame (Gemini picks, sharpness fallback) + brand headline: `out/thumbs/<id>-yt.jpg` 1280x720 and `<id>-cover.jpg` 1080x1920; `--critique` |
| `tools/channel_thumbs.py` | Covers from a video frame or the owner's template art (settings in `data/brand/thumbs.json`); Shorts use the template positions; `--set` uploads only owner-approved ones |
| `tools/social_stats.py` | Pulls YouTube channel and video stats via the Data API into `data/social_stats.json`; `--ig/--tiktok/--threads followers,following,posts` add the other accounts. Feeds the Social Tracker artifact |
| `.claude/skills/gemini/` | `/gemini <task>` quick access to `gemini_task.py` |
| `.env.example` | Names of the `.env` keys (no values); copy to `.env` |
| `installers/Instalar_Estudio_Voz_y_HyperFrames.bat` | Owner-run menu: local voice studio (Voicebox, CUDA) and HyperFrames Studio + skills for Claude and Gemini |
| `data/voice_profiles/` | Owner's voice samples for Voicebox cloning (WAV 48 kHz, 24 bit, mono); contents git-ignored, own voice only |
| `tools/` (others) | Instagram publisher, slot picker, budget check |
| `.claude/` | Agents, skills (`make-video`, `publish`, `daily-run`) and rules; `kit.json` (mod settings), `kit.lock.json` (installed kit version), kit hooks and `kit-*` skills |
| `tools/kit/` | Project kit (github.com/ffman22/claude-project-kit): `kit.py status` / `update`; managed, do not edit |
| `tools/agents-office/` | Live view of agents: `/agentes-office` or double-click `open-office.cmd` |
| `.gitattributes` | Line endings (project kit block) |

## Quick use
```
cp -r videos/_template videos/unreal-lighting-01   # edit manifest.json
.venv/Scripts/python.exe tools/rights_gate.py videos/unreal-lighting-01/manifest.json
.venv/Scripts/python.exe tools/build_video.py videos/unreal-lighting-01/manifest.json
```
