---
name: publish
description: Write the copy, then upload a ranked Short to YouTube (private or scheduled) and Instagram Reels at the best slots. Use for "/publish <id>".
---
# Publish
1. The video is `out/<id>.mp4` or the manifest's `video_file`. `rights_gate.py` must pass; else stop.
2. Copy: follow `docs/research_rules.md`; offer 3-5 titles and 3-4 thumbnail texts, and write the owner's pick into the manifest.
3. Slot: take the next free slot from `data/schedule.json` (`eu_us_slots`); if absent, the defaults in `docs/posting_strategy.md`. Set `publish_at`.
4. Approval: run `tools/approval.py sheet <id>`, send the page to the owner and stop. Only after they approve that video: `tools/approval.py approve <id> --quote "<their words>"`. Never write approval.json by hand. `privacy` stays `private`/scheduled unless they said "publica".
5. YouTube: `.venv/bin/python tools/youtube_upload.py videos/<id>/manifest.json`. A 403 about an unverified API project means private-only: report `q-yt-audit`.
6. Instagram: host the MP4 at a public URL (`q-ig-host`), then `.venv/bin/python tools/instagram_publish.py videos/<id>/manifest.json --video-url <url>`.
7. Reply in 3–5 lines: YouTube link, Instagram status, slot.
