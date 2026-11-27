# Model routing

The main session runs Sonnet. Work goes to another model only when the table says so; never switch `/model` mid-session (it drops the prompt cache). Delegate with an agent instead.

| Work | Model | How |
|---|---|---|
| Daily loop: manifests, `/make-video`, `/publish`, `/daily-run`, topic files, chat replies, doc edits | Sonnet | main session |
| Writing or changing `tools/*.py`, OAuth and API debugging, render bugs, new automation | Opus | agent `opus-engineer` |
| Strategy: niche choice, analytics review (every 30 videos), monetization plan, policy and rights edge cases, review before the first public publish | Opus | agent `opus-strategist` |
| Mechanical checks: ffprobe verification, manifest lint, title/hashtag/description drafts, renaming and moving files | Haiku | agent `haiku-checker` |

## Gemini first (saves Claude tokens)
Hook `.claude/hooks/gemini-route.mjs` reminds on matching requests and asks the owner before Claude watches a video or reads a text over 30 KB.

| Work | Command |
|---|---|
| Public YouTube analysis, competitors | `tools/gemini_task.py "<task>" --youtube <url> --out out/gemini/<name>.md` |
| Long transcript, notes, summary, first drafts | `tools/gemini_task.py "<task>" --file <text> --out <file>` |
| Review a video or audio file (picture, speech, sound, fit for its type) | `tools/gemini_review.py <file> --type short\|series\|tutorial\|intro\|reel\|ad [--spec F] [--script F]`; required before the approval sheet |
| New or edited images (drafts; needs Gemini billing) | `tools/gemini_image.py "<prompt>" --out <png> [--ref F] [--aspect 9:16]` |
| Moments in an own long video | `tools/find_moments.py <video> --own` |
| Copy per platform, thumbnail frames | `tools/gemini_copy.py`, `tools/make_thumbnail.py` |
| Instagram/TikTok video (no URL access) | owner: Gemini app + Drive `8-gemini-analysis` |

- Claude keeps: rights, approval gates, uploads, code and the final check of scripts. Verify technical claims from Gemini (lite model) against `spec.json` or the video.
- Drive docs read through the connector cost Claude tokens: read only the one needed, then keep the result in the repo.
- Drive files: Gemini tools read from disk. Use `data/clips/` or a Drive for Desktop path; never download through the connector into Claude.
- Video editing stays in the studio tools; Gemini analyses and creates assets.
- Never send secrets or third-party private data to Gemini.

Rules:
- Escalate to Opus after two failed Sonnet attempts at the same error, or when a change touches the rights gate, credentials or upload logic.
- Give an agent a closed brief: files to read, the question, the output format. Its report is the only thing that returns; keep it under 15 lines.
- Do not use Opus for routine edits or records; do not use Haiku for anything that decides content quality or rights.
