# Model routing

The main session runs Sonnet. Work goes to another model only when the table says so; never switch `/model` mid-session (it drops the prompt cache). Delegate with an agent instead.

| Work | Model | How |
|---|---|---|
| Daily loop: manifests, `/make-video`, `/publish`, `/daily-run`, topic files, chat replies, doc edits | Sonnet | main session |
| Writing or changing `tools/*.py`, OAuth and API debugging, render bugs, new automation | Opus | agent `opus-engineer` |
| Strategy: niche choice, analytics review (every 30 videos), monetization plan, policy and rights edge cases, review before the first public publish | Opus | agent `opus-strategist` |
| Mechanical checks: ffprobe verification, manifest lint, title/hashtag/description drafts, renaming and moving files | Haiku | agent `haiku-checker` |

Rules:
- Escalate to Opus after two failed Sonnet attempts at the same error, or when a change touches the rights gate, credentials or upload logic.
- Give an agent a closed brief: files to read, the question, the output format. Its report is the only thing that returns; keep it under 15 lines.
- Do not use Opus for routine edits or records; do not use Haiku for anything that decides content quality or rights.
