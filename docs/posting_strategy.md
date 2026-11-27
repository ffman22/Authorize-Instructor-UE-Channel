# Posting strategy

## Who does what
| Step | Owner | Claude |
|---|---|---|
| Choose competitor channels | picks 3–5 | analyzes them (VidIQ, `tools/best_times.py`) |
| Find viral clips | contacts the creators / licenses the clips | `tools/find_viral.py` lists candidates by views and virality ratio |
| Build the video | RankReel in the browser (or `tools/build_video.py`) | fills the manifest, checks the render |
| Title, description, hashtags, first comment, Instagram caption | approves | writes them (Haiku drafts, Sonnet picks) |
| Upload and schedule | none after setup | `tools/youtube_upload.py`, `tools/instagram_publish.py` |
| Analytics review | reads the summary | Opus every 30 videos |

A RankReel MP4 goes to `out/<id>.mp4`; the manifest still logs every clip (source, rights, take).

## Posting times (◇ defaults until `data/schedule.json` has data)
- Slot A: 17:00 UTC (18:00 Madrid, 12:00 New York) — Europe evening and US lunch.
- Slot B: 00:00 UTC (01:00 Madrid, 19:00 New York) — US evening.
- Replace with the view-weighted slots from `tools/best_times.py` after analyzing 3–5 channels; re-run monthly.
- One video per slot at most; keep 1 per day until each video has distinct clips.

## Copy rules
- Full rules: `docs/research_rules.md`.
- YouTube title: ≤ 100 characters, no hashtags.
- Description: workshop link in the first 2 lines, topic, credits, 3 hashtags at the end.
- Instagram caption: hook line, question to the viewer, max 5 hashtags.
- Hashtag mix on Instagram and TikTok (5 max): 2 post-specific, 2 niche, 1 broad. Instagram caps at 5 (Dec 2025); count first-comment hashtags too.
- YouTube tags, three categories: post-specific (manifest `tags`, 3–8 phrases that describe the video), niche and broad (`tools/tags_base.json`). Tags matter little on YouTube; title, thumbnail and description matter more.
- First comment (both platforms): a technical question about the tip. It is posted by the owner's account through the API; never fake accounts or engagement pods.

## Review
- After 30 videos: views, retention, subscribers per video by topic cluster and slot; keep what beats the median, cut the rest.
