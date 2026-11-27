# Channel audit, 27 Nov 2026

Sources: Drive research docs 01-08 (both 05s) and the live YouTube API, read at 09:21 UTC. The three `PROMPT_CLAUDE_*` docs were seen only as search snippets. Instagram, TikTok and Threads were not checked live. Nothing live was changed.

## Live errors (verified)
| # | Error | Fix |
|---|---|---|
| 1 | `f-_v3SD4Kv8` (curves Short, public) links to `Dn_iRxQiN2M`, which is private: broken link | Point to `CYHdjr9YwV0` (public HD) |
| 2 | `a-LFa0dxDCM` (Lyra Short, public) shows `Full tutorial: (link after upload)` | Remove the line until the long video exists |
| 3 | Lyra Short comes from a 640x360 source (upscaled to 1080x1920): breaks HD only | Owner: 1080p re-export; set unlisted or keep until then |
| 4 | Curves Short cut starts at 3:31.5, after the problem and the setup | Re-cut with hook, setup and proof |
| 5 | Both reels (AC Shadows: Anvil engine) and their Shorts carry `ue5` / `unreal engine` tags (checked on `m447R2Lt3vI`, `246Bwxt6YpQ`, `R_N6gR8UifE`, `5LVCkL862zw`) | Replace with engine-agnostic tags; confirm the Necromunda engine before any Unreal tag |
| 6 | Two copies of the curves long video: `CYHdjr9YwV0` public (category 22, description starts "HD version", no workshop link in the first lines), `1P_TL46FKUA` private | Keep `CYHdjr9YwV0`, fix title, description and thumbnail; leave `1P_TL46FKUA` private |
| 7 | `#shorts` in live Short titles; `youtube_upload.py` adds it | Remove from titles and code |
| 8 | 29 Nov 21:00 UTC has two uploads: `R_N6gR8UifE` and `3ir-LMQZszI` | Move the Necromunda full reel to 3 Dec |

## Live calendar (21:00 UTC)
27 Nov promo-02; 28 AC Short; 29 Necromunda full + promo-03; 30 Necromunda Short; 1 Dec promo-04; 2 Dec AC full. Lyra full (planned 27 Nov 17:00 UTC) is blocked by the HD rule. `handoff.md` and the `reel-nec-full` manifest disagree with the live dates. `workshop-promo-01` went public 26 Nov 17:00 UTC.

## Times
The docs give no data-based hour. "1-2 h before the audience peak" needs the audience graph, and the channel has 0 subscribers. Keep 21:00 UTC (22:00 Madrid, 16:00 New York) and review with data.

## Thumbnails (local files in `out/thumbs/`; live images not compared)
- New promo versions from the owner (26 Nov) are in Drive and `out/thumbs/`; not confirmed on YouTube.
- Promo 02 and 03 "Youtube" versions are 1080x1559 and 1080x1573, not 9:16.
- Promos say "Comment UNREALZERO"; the docs say "UNREAL". Pick one; replies are manual.
- AC Short: HUD text competes with the headline. AC full: dark, grey box top right. Necromunda full: dark.
- Lyra: soft because of the 360p source.

## Errors and risks inside the research docs
- Doc 07 cut map is labelled 35-45 s but its ranges add up to 100 s (over the 60 s limit).
- Doc 05 blueprint titles end in `#shorts`; docs 06 and 08 forbid it.
- Doc 06 asks for 3 YouTube hashtags, doc 04 for 5 on short-form; the AAA flash is 2 s in one place and 3 s in another.
- Two different documents are numbered 05.
- Unverified creator opinions, not platform rules: 200-viewer sample, account warm-up against bots, one Short per day under 100k, 70-80% swipe targets.
- Delete and re-upload under 100 views in 48 h: do not automate; delete nothing without the owner's order.
- Doc 02 curves chapters differ from the manifest chapters; check against the video before use.
- AC footage inside every Short raises claim risk: the logged proof is a YouTube upload, not written permission from Ubisoft.

## Repo recommendation (not from the docs)
Drop `viral`, `viral video`, `for you` from `tools/tags_base.json`: they do not describe the videos (misleading metadata). Not seen in the live tags checked.

## Owner corrections and follow-up, 27 Nov (these override the sections above)
- Error 1: `Dn_iRxQiN2M` is the SD copy, hidden by the owner. The curves Short must link to `CYHdjr9YwV0`.
- Error 6: closed. `CYHdjr9YwV0` is already corrected; do not touch it.
- `UNREALZERO` (workshop ads) and `UNREAL` (channel and series) are both correct.
- The research rules are adopted (`research_rules.md`).
- Cropped covers: fixed locally with the owner's template; not uploaded.
- New finding: the live curves Short `f-_v3SD4Kv8` was uploaded on 23 Nov, before the HD source existed (25 Nov), so it is an SD upscale, like the Lyra Short `a-LFa0dxDCM`. The HD render in `out/curves-short.mp4` was never uploaded. Instagram Reel 1 (curves) and the 23 Nov TikTok files date from the same SD period (not checked live).
- Videos already scheduled on YouTube have no owner approval record. `workshop-promo-02` publishes 27 Nov 21:00 UTC unless the owner decides otherwise.
- Prepared in the repo only (not live): HD curves link, Lyra placeholder removed, workshop link in line 1, Necromunda full reel to 3 Dec. Approval sheet: `out/review/approval-sheet.html`.

