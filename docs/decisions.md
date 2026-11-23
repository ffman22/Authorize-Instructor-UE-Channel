# Decisions log

| Date | Decision | Why |
|---|---|---|
| 23 Nov 2026 | Repo starts clean from the ranking studio: pipeline tools, rights gate, uploaders, slot picker only | No content from other channels; owner's new Unreal channel |
| 23 Nov 2026 | Shorts are cut only from the owner's own videos | No third-party rights |
| 23 Nov 2026 | Upload default private/scheduled until the owner says "publica" | Unaudited API uploads stay private |
| 23 Nov 2026 | Instagram posts at slot time by the scheduled task (API has no scheduling) | Graph API limit |
| 23 Nov 2026 | Heavy media lives in Google Drive (carlo.animator), repo keeps text and catalog only | Repo size; owner's Drive folder tree in `docs/drive_catalog.md` |
| 23 Nov 2026 | Channel publishes as many long videos as Shorts; Shorts keep it active | Owner's plan; `youtube_upload.py` still forces `#shorts`, so long-video upload mode is open work |
| 23 Nov 2026 | Owner confirmed all 3 source videos (promo V2, Lyra melee combo, animation curves) are own footage, rights `own` | Owner statement in chat; no third-party material |
| 23 Nov 2026 | Drive `1-source-videos` holds only the owner's own videos; anything there is rights `own` | Owner statement in chat |
| 23 Nov 2026 | Manifest is one tip = one cut (`source`, `start`, `duration` <= 60 s, `title` headline) replacing the 5-7 clip ranking schema; non-private needs `publish_at`; long videos use `format: long` / `--long` (no `#shorts`) | Channel is Unreal tips from the owner's own videos, not rankings |
| 23 Nov 2026 | 4 workshop promo Shorts scheduled Fri/Tue 22:00 Madrid (21:00 UTC), 27 Nov to 8 Dec | Owner wants 2 per week; slots provisional (thin data) |
| 23 Nov 2026 | Game reels (AC Shadows Claws of Awaji, Necromunda) published as rights `permission`; proof = owner's existing public uploads (YouTube BHfA_afUE2k, Vimeo 775571162) | Owner says he may publish them; game footage belongs to the studios, so proof URL is required in `proof` |
| 23 Nov 2026 | Channel scope widened: tutorials, demo reels and industry commentary, not only Unreal tips | Owner: it is his professional animator channel |

## 2026-11-23 Lyra Short built from a pre-trimmed cut
- Pipeline renders one contiguous cut, so the multi-part Short is first concatenated with ffmpeg into `data/clips/lyra-short-cut.mp4` (own footage: 120.3-128.1 recap tail (earlier part repeated the demo narration), 146.4-180.9 and 185.9-194.9 demo of `lyra-melee-combo.mp4`), then `videos/lyra-short` renders it (51.3 s). Not uploaded yet.

## 2026-11-23 TikTok scheduled via Studio web (manual path)
- Uploaded through TikTok Studio in Chrome, 22:00 Paris on each YouTube date: curves-short 24 Nov, promo-01 27 Nov, reel-ac-short 28 Nov, reel-nec-short 30 Nov, promo-02 1 Dec, promo-03 4 Dec, promo-04 8 Dec. lyra-short is on TikTok dated 23 Nov 10:45 (not 22:00). Files are <10 MB re-encodes in `out/post-ready/tiktok/` (the browser upload tool caps at ~10 MB). Long videos not posted to TikTok.

## 2026-11-23 Workshop promos moved earlier (YouTube + TikTok)
- Workshop ends in December and ianimate.net is already advertising, so promos moved: promo-01 26 Nov, promo-02 27 Nov, promo-03 29 Nov, promo-04 1 Dec (22:00 Madrid / 21:00 UTC). YouTube via videos.update; TikTok scheduled posts cannot be edited, so they were deleted and re-uploaded.

## 2026-11-23 Workshop link on every video; channel link and watermark
- `rights_gate` now fails a manifest whose description lacks the workshop URL unless `cta` is set; `_template` carries the link block. `build_video` supports `cta` (red end card, last 5 s). Uploaded YouTube Shorts cannot be re-edited (no file swap), so the card applies to new renders only.
- Channel: link "Join the Workshop" added in Studio profile; watermark (face on gold + UE U) published by the owner, display time "End of video". YouTube "Join" button is memberships (needs YPP) and cannot point to the workshop.
