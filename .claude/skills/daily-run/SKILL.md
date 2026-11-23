---
name: daily-run
description: Run the full daily loop for one tip Short: topic, manifest, render, publish. Use for "/daily-run" or from a scheduled task.
---
# Daily run
1. Read the checkpoint in `docs/handoff.md` and the unused topics in `data/topics/`. Pick the next topic that has cleared clips available in `data/clips/`; if none, stop and say which clips are missing (do not source uncleared clips).
2. `/make-video` for it, then `/publish` (private or scheduled).
3. Mark the topic used in its topics file.
4. If a scheduled task runs this: finish by overwriting the checkpoint with the video id and any blocker. Commit and push to `main` only if the owner has authorized scheduled pushes in `docs/decisions.md`.
5. Reply in 3 lines: video, status, blocker.
