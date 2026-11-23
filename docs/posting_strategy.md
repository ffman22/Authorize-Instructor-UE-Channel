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
- YouTube title: two-line title joined, ≤ 100 characters, `#shorts` last.
- Description: topic line, credits, 3–5 hashtags (the first three show above the title).
- Instagram caption: hook line, question to the viewer, 5–8 hashtags (mix of niche and broad).
- First comment (both platforms): a question that invites a ranking debate ("What's your #1?"). It is posted by the owner's account through the API; never fake accounts or engagement pods.

## Review
- After 30 videos: views, retention, subscribers per video by topic cluster and slot; keep what beats the median, cut the rest.
