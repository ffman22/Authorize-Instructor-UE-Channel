---
name: publish
description: Write the copy, then upload a ranked Short to YouTube (private or scheduled) and Instagram Reels at the best slots. Use for "/publish <id>".
---
# Publish
1. The video is `out/<id>.mp4` or the manifest's `video_file` (RankReel export). `rights_gate.py` must pass; else stop.
2. Copy: have `haiku-checker` draft 3 variants of title, hashtags, Instagram caption and first comment from the topic; pick one using `docs/posting_strategy.md` copy rules and write it into the manifest.
3. Slot: take the next free slot from `data/schedule.json` (`eu_us_slots`); if absent, the defaults in `docs/posting_strategy.md`. Set `publish_at`.
4. `privacy` stays `private`/scheduled unless the owner said "publica" in this conversation.
5. YouTube: `.venv/bin/python tools/youtube_upload.py videos/<id>/manifest.json`. A 403 about an unverified API project means private-only: report `q-yt-audit`.
6. Instagram: host the MP4 at a public URL (`q-ig-host`), then `.venv/bin/python tools/instagram_publish.py videos/<id>/manifest.json --video-url <url>`.
7. Reply in 3–5 lines: YouTube link, Instagram status, slot.
