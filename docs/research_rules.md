# Research rules (adopted by the owner, 27 Nov 2026)

Source: Drive docs 01-08 (creators with 1M+ followers and competitor breakdowns). The owner adopted them as channel rules. Where a doc conflicts with an owner rule, the owner rule wins.

## Owner rules on top of the research
- Nothing is uploaded or changed on any platform until the owner has seen it (name, source, image, texts, date) and approved it: `tools/approval.py`.
- Never SD on any platform.
- Comment keyword: `UNREALZERO` only on iAnimate workshop ads (it is the workshop code); `UNREAL` on Unreal channel and series videos, `GAMEANIMATION` on footage from other engines (AC Shadows).
- Thumbnails follow the owner's template and example (Drive `6-EditableAssets`; layout in `tools/channel_thumbs.py`).

## Titles and metadata
- No hashtags in titles. YouTube: 3 hashtags at the end of the description. Instagram and TikTok: max 5.
- Workshop link in the first 2 description lines; the keyword and the link also close the video.
- Non-Unreal footage (AC Shadows runs on Anvil) never gets `ue5` or `unreal` tags. Confirm the engine before tagging.
- `?sub_confirmation=1` only on external links to the YouTube channel.

## Before production (4 gates, one stop each)
0. `videos/<id>/spec.json`: `engine_and_version`, `core_technical_thesis`, `shown_in_video`, `not_in_video`, `verified_timestamps`, `candidate_thumbnail_timestamps`. Nothing in `not_in_video` may appear in titles, captions or scripts.
1. Spec checked with the owner.
2. Title: offer 3-5 options and 3-4 overlay texts (2-4 words). The owner picks.
3. Thumbnail: contact sheet of 4-6 frames. The owner picks.
4. Final cut and metadata: approval sheet. The owner approves.
- Assemble in stages (hook, lesson, ending) and show each stage. Before a stage, list the clips needed and their resolution.

## Shorts
- Formats: micro-tip 20-30 s; progressive escalation 50-60 s (same clip 3 times, step badge); series "AAA UE5 Secret:" 20-35 s (spoken hook, top banner `AAA UE5 SECRET`).
- Frame 0 shows the result or the problem; no greetings. State the core concept aloud in the first 3 s.
- Credibility flash (about 3 s, 2 s in micro-tips) around 0:04 without pausing the voice.
- Captions of 1-2 words every 1-1.5 s; no static panel over 2 s.
- End: arrow to the YouTube Related Video; on Instagram and TikTok, comment keyword and "watch on YouTube, subscribe".
- Each script: animator's pain, non-obvious studio tactic, clear visual, something to try today.

## Long videos
- 12-16 min. 0:00 payoff in engine, 0:10 reel sizzle (12-13 s), 0:23-0:35 workshop pitch, then chapters; a visual change at least every 15 s; end with stress test and workshop.

## Publishing and growth
- At most 1 Short per day (under 100k subscribers); 3-5 a week.
- Schedule 1-2 h before the audience peak once YouTube shows the audience graph.
- Targets: viewed vs swiped at least 70% (80%+ strong); long videos AVD over 50% and CTR over 6%.
- Short under 100 views after 48 h: propose a new title and first 2 s and a re-upload on another day. Deleting needs the owner's order.
- Owner tasks: YouTube Studio automatic dubbing on, "not made for kids", 2-3 weeks of daily genuine engagement on new accounts. Claude never fakes engagement.
- Stay on one audience: gameplay animators and game developers.

## Research items that need a fix before use
- Doc 07 curves cut map: labelled 35-45 s, ranges add up to 100 s. Re-plan under 60 s.
- Docs 03 downloads competitor videos with yt-dlp; the channel rule says never rip platform videos. Open until the owner decides.
