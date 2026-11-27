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
| 24 Nov 2026 | Voiceovers: owner records EN himself; Spanish Shorts only occasionally, generated | Owner decision; EN is the default for copy, captions and voice scripts |
| 24 Nov 2026 | Every Short and video gets a written script with a hook (no channel welcome); thumbnails use owner's face + 2-4 word promise; each video names one ideal-viewer segment; metrics drive weekly decisions | Owner brief in `docs/creator_brief.md`; Gemini playbook in `docs/creator_playbook.md` |

## 2026-11-23 Lyra Short built from a pre-trimmed cut
- Pipeline renders one contiguous cut, so the multi-part Short is first concatenated with ffmpeg into `data/clips/lyra-short-cut.mp4` (own footage: 120.3-128.1 recap tail (earlier part repeated the demo narration), 146.4-180.9 and 185.9-194.9 demo of `lyra-melee-combo.mp4`), then `videos/lyra-short` renders it (51.3 s). Not uploaded yet.

## 2026-11-23 TikTok scheduled via Studio web (manual path)
- Uploaded through TikTok Studio in Chrome, 22:00 Paris on each YouTube date: curves-short 24 Nov, promo-01 27 Nov, reel-ac-short 28 Nov, reel-nec-short 30 Nov, promo-02 1 Dec, promo-03 4 Dec, promo-04 8 Dec. lyra-short is on TikTok dated 23 Nov 10:45 (not 22:00). Files are <10 MB re-encodes in `out/post-ready/tiktok/` (the browser upload tool caps at ~10 MB). Long videos not posted to TikTok.

## 2026-11-23 Workshop promos moved earlier (YouTube + TikTok)
- Workshop ends in December and ianimate.net is already advertising, so promos moved: promo-01 26 Nov, promo-02 27 Nov, promo-03 29 Nov, promo-04 1 Dec (22:00 Madrid / 21:00 UTC). YouTube via videos.update; TikTok scheduled posts cannot be edited, so they were deleted and re-uploaded.

## 2026-11-23 Workshop link on every video; channel link and watermark
- `rights_gate` now fails a manifest whose description lacks the workshop URL unless `cta` is set; `_template` carries the link block. `build_video` supports `cta` (red end card below the video, last 3.5 s). Uploaded YouTube Shorts cannot be re-edited (no file swap), so the card applies to new renders only.
- Channel: link "Join the Workshop" added in Studio profile; watermark (face on gold + UE U) published by the owner, display time "End of video". YouTube "Join" button is memberships (needs YPP) and cannot point to the workshop.
| 23 Nov 2026 | Second Instagram account @carlo.animator for the channel; posts and stories drafted in `docs/instagram_plan.md`, nothing published until "publica" | Owner created it in the app, same Accounts Center login |
| 23 Nov 2026 | Reel 1 (curves-short) published on @carlo.animator via web on owner "publica" | Instagram web has no scheduling or drafts |
| 23 Nov 2026 | Intro post (owner photo) published on @carlo.animator with ffman22 as collaborator, on owner "publica" | Owner order; stories and highlights need the Instagram app |
| 23 Nov 2026 | Bios aligned with owner LinkedIn: Instagram (125 chars), TikTok (79 chars), YouTube About (under 1000, adds Gold rank and iAnimate workshop); intro caption rewritten | Owner order: reflect real experience; employer mention OK per owner |
| 23 Nov 2026 | Intro card `data/brand/carlo-intro-card.jpg` (owner photo, title, text-only gold badge) used for a YouTube Community post; not the official Epic badge | No Gold certificate file in Drive; owner can supply it |
| 23 Nov 2026 | Intro card rebuilt with the official Unreal Authorized Instructor badge from Drive (`1771968068176.jpg`, saved as `data/brand/unreal-authorized-instructor-gold.jpg`) | Owner supplied the official badge; replaces the text-only badge |
| 23 Nov 2026 | YouTube Community post (intro card + long text + workshop link) published on owner "sube" | Owner order |
| 23 Nov 2026 | ffman22 added as collaborator on Reel 1 (invite sent, owner must accept from ffman22) | Owner order |

- reel-ac-short headline corrected to "Lead gameplay animator on AC Shadows: Claws of Awaji" (title, description, captions). Re-rendered and replaced everywhere: YouTube old lnFWG2gPMcY deleted, new 92FbF7tYSrg private, scheduled 28 Nov 21:00 UTC; TikTok old post deleted, new one scheduled 28 Nov 22:00 Paris. Instagram Reel 3 not posted yet (uses the new render).
| 23 Nov 2026 | Threads account @carlo.animator created by owner on phone (Threads web had only the older ffman22 profile) | Threads links one profile to one Instagram account; brand must live on carlo.animator |
| 23 Nov 2026 | YouTube tags base in `tools/tags_base.json` (channel, format and topic tags) merged by `youtube_upload.py` after the manifest hashtags and optional `tags`; dedupe, lowercase, max 500 chars. Live tags reviewed in YouTube: lyra-short, workshop-promo-01 and 04 had richer tags from Studio, the rest only the 3-5 hashtags | Owner improved some tags in Studio; this makes them the default for every new upload |
| 24 Nov 2026 | `tools/gemini_task.py` + `.env.example`: Gemini key stored as `GEMINI_API_KEY` in git-ignored `.env`, same pattern as Instagram keys; tool refuses credential files | Owner wants to delegate mechanical tasks (transcripts, long-video analysis) to Gemini; content sent goes to Google |
| 24 Nov 2026 | `/gemini` skill and Gemini CLI (`npm i -g @google/gemini-cli`, v0.71.1) installed for quick access; both use `GEMINI_API_KEY` | Owner asked for quick access from Claude Code |
| 24 Nov 2026 | `ready_to_publish` in every manifest: `youtube_upload.py` and `instagram_publish.py` refuse a real upload unless it is `true` (dry-run only warns). Existing uploaded manifests set to true, template false, `find_moments.py` drafts false | Owner wants no draft uploaded by mistake |
| 24 Nov 2026 | Gemini pipeline (`gemini_client.py`, `find_moments.py`, `gemini_copy.py`, `make_thumbnail.py`). Balance plan: one lite model for all; video only as a 360p/2 fps proxy at low media resolution, once per video (cached, deleted from Google right after); copy is one call per video returning all platforms; thumbnail picks use 480 px previews; every call cached and logged, hard daily cap. Test: 4:48 video = 27k tokens, so 56 min is about 310k | Owner asked to spread Gemini work so the balance lasts |
| 24 Nov 2026 | HyperFrames (HeyGen, Apache open source) plugin `hyperframes@hyperframes` v0.9.88 installed in Claude Code (user scope) for HTML-to-video edits. Gemini-side skill install was blocked by the permission classifier; not done | Owner asked Claude and Gemini to edit videos together with it |
| 24 Nov 2026 | `installers/Instalar_Estudio_Voz_y_HyperFrames.bat`: owner-run menu that installs Voicebox (local voice studio) and HyperFrames Studio with skills for Claude and Gemini; not executed by Claude | Owner asked for a local voice studio and HyperFrames Studio |

## 24 Nov 2026 — Social stats refresh
- `social_stats.py` keeps previous IG/TikTok/Threads numbers unless flags are given (it used to zero them). Daily scheduled task `social-stats-daily` (09:00 local, app must be open) refreshes YouTube via API and IG/TikTok via vidIQ.

## 25 Nov 2026 — HD only
- Owner rule: only HD (720p) or higher. `rights_gate.py` probes the local source; `youtube_upload.py` also probes the upload file. The curves, Lyra and AC Shadows sources are 640x360 (their Drive copies too), so their 1080x1920 renders are upscales.
- Thumbnails (25 Nov): frame plus two lines of text (second in yellow), watermark-150-u large, always bottom right, no large owner face for now (owner's call). `channel_thumbs.py` renders and sets them.
| 26 Nov 2026 | Tags in three categories: post-specific (manifest `tags`), niche (`tags_base.json`, by topic) and broad (owner list, space reserved in the 500 limit). Reel topics skip Unreal and tutorial-broad tags. Instagram and TikTok: max 5 hashtags (2 specific, 2 niche, 1 broad); `instagram_publish.py` enforces 5. Live videos not updated yet | Owner asked to split tags by category; Instagram caps hashtags at 5 |

## 27 Nov 2026 — Owner rules after the research audit
- Nothing is uploaded, scheduled or changed on a platform before the owner approves it. Enforced by `tools/approval.py` (hashes of metadata, video and thumbnail) in the YouTube, Instagram and thumbnail tools. Videos scheduled earlier have no approval record.
- Never SD.
- Keyword `UNREALZERO` = iAnimate workshop code, workshop ads only; `UNREAL` for channel and series videos.
- Research docs 01-08 adopted (`docs/research_rules.md`); no hashtags in titles; 3 YouTube hashtags; `spec.json` required to render and upload.
- Vertical covers use the owner's PSD template; reference: workshop-promo-01 v2 (title cap top at 398 of 1920).
- `Dn_iRxQiN2M` is the SD copy the owner hid. `CYHdjr9YwV0` (HD, public) is the curves long video; the owner fixed it: do not touch.
- Media leaves git (`.gitignore` and `git rm --cached`; old commits still hold the brand images). Gemini analyses videos through Drive `8-gemini-analysis`.
- Owner paused workshop-promo-02: YouTube schedule removed, video stays private until approved.
- Owner approved the promo-03 cover; rejected AC Short and both Necromunda covers as blurry or badly framed. Covers use sharp, well-framed frames; `drop` in `thumbs.json` adds dark headroom so the subject sits under the title.
- Owner approved the new Necromunda covers (full and Short) and promo-04; chose the reel frame at 10.8 s for the AC Short cover (recorded mouse cursor erased via `erase` in `thumbs.json`).
- Owner approved the new AC Short cover.
- Tip Shorts end with a 3.5 s full-screen splash (end placement keeps the hook and retention): "full" (watch the full video + subscribe) or "soon" (subscribe + notifications). Design awaits owner approval; no Short re-rendered yet. Owner asked for both variants to animate a cursor clicking Subscribe and then the YouTube bell, with "Turn on notifications".
- Subscribe button follows the owner's guide GIF: white "Subscribe", pink flash with red sparks, dark "Subscribed" with bell and chevron; same size in both states. Notification bell unchanged.
- Owner approved the YouTube splash and paused AC Short (verified: private, no date). Instagram/TikTok copies use their own splash (Follow, comment UNREAL, full video on YouTube): build_video.py --splash social_soon|social_full.
- AC Shadows is not Unreal: never ask for `UNREAL` there. Non-Unreal footage uses `GAMEANIM` (owner offered AAAGameDev or GameAnim) and "game animation content" in the splash.
- Workshop Shorts get their own end splash (`cta.type` "workshop", all platforms): comment UNREALZERO for more information. Design awaits approval; promos not re-rendered.
- Owner approved GAMEANIM and the workshop splash; asked to fix the abrupt end of the Authorized Instructor Short (promo-02) and add splash sounds. Cuts end on a finished sentence; the workshop splash is appended after the cut; sounds are synthesized in build_video.py. promo-03 and 04 unscheduled.
- Owner approved the new cuts and splash sounds ("dejalos asi"): AC Short (YouTube and social) and promos 01-04. Texts, dates and spec files are not approved yet.
- The course promo video (`promo-workshop-v2`) is on the iAnimate.net channel, which is not the owner's. The owner, an iAnimate instructor, may use parts of it to advertise their workshop and ruled that this statement is enough proof: promos 01-04 are now `rights: permission` (rights gate passes).
| 27 Nov 2026 | Project kit 0.5.0 installed: hooks, `kit.py`, Agents Office. Project docs and own agents kept: no `docs/pipeline/`, `docs/catalog/`, `docs/CLAUDE.md`, `docs/economics.md`, `rules/docs.md`; `kit-agents` off; `session-start.mjs` not wired (it reads `docs/pipeline/handoff.md`) | Avoids two sources of truth |
| 27 Nov 2026 | Animated splashes never cover the cut: picture fades to black and sound to zero (1 s; `cta.fade` overrides, AC Short uses 0.6 s and ends at source 60.75 s, where its sequence ends), then the splash is appended; cut + 3.5 s must stay ≤ 60 s. AC Short (YouTube and social) re-rendered, 58.3 s, awaiting approval | Owner: the hard ending looked bad |
| 27 Nov 2026 | Owner approved the AC Short v2 ending ("ok asi"). Texts, cover, date and spec.json not approved yet | Owner review |
| 27 Nov 2026 | Non-Unreal keyword is now `GAMEANIMATION` (was `GAMEANIM`). Every platform carries a comment call to action. AC Short tests an 18:00 Madrid/Paris (17:00 UTC) slot instead of 22:00; Instagram caption adds workshop and iAnimate YouTube links | Owner order; reach through comments and an earlier slot |
| 27 Nov 2026 | Owner approved the AC Short sheet ("Sí, la pruebo"). Uploaded `VLqWpu-oKA4` private, scheduled 28 Nov 17:00 UTC, cover set; verified HD 1080x1920. Old copies `92FbF7tYSrg` and `m447R2Lt3vI` stay private with no date | Approved upload; 18:00 slot test |
| 27 Nov 2026 | Old AC Short copies `92FbF7tYSrg` and `m447R2Lt3vI` deleted from YouTube (both private, undated, 0 views); `published-sd.json` and `published-nosplash.json` stay as history. `installers/.agents/` is git-ignored | Owner order; third-party files and fonts stay out of git |
| 27 Nov 2026 | Whisper test (test only, nothing published; `out/transcripts/promo-workshop-v2/`): `large-v3-turbo` + terms + `condition_on_previous_text=False` gives best text (terms without the flag loop); `small.en` times pauses better. GPU needs venv `nvidia-cublas-cu12`, `nvidia-cudnn-cu12` and DLL dirs on PATH; PyAV 19 breaks file input (pipe ffmpeg PCM) | Basis for the proposed editor pilot |
- Gemini routing (owner asked why Gemini was not used and to save Claude tokens): cause was no Gemini row in `model_routing.md` and no hook; its last logged call here was 24 Nov. Added the row, a CLAUDE.md rule, `.claude/hooks/gemini-route.mjs` and `gemini_task.py --youtube` (test on a public own video: 26k Gemini tokens).
- Intro and series scripts drafted from Gemini docs 02, 04 and 08, corrected: "13 years of animation experience" (not "13+ years in AAA"), State Alias wording, episodes cut to 65-80 words, no link to a long video that does not exist, comment UNREAL everywhere. Owner approval pending.
- Owner wants Gemini to analyse video in context (with sound), check Drive uploads per video type, create images and do what is hard in Claude (not edits). Added `gemini_review.py` (`gemini-flash-latest`, not the lite model, for accuracy; test on the AC Short: 19k tokens) and `gemini_image.py`. Image test: HTTP 429, free-tier limit 0 for `gemini-3.1-flash-image`; billing is the owner's step.
- Scripts follow `docs/script_format.md` (owner: the result must hook in the first seconds, as in Gemini's creator research): result 0-3 s, open loop, credibility, lesson. Series hooks rewritten that way.
- Channel trailer rewritten as about 2 min on camera, more energetic than the iAnimate promo (reviewed with Gemini, reference only, iAnimate's footage). Separate 40 s vertical piece for Instagram, TikTok and Threads that explains the whole channel (`videos/channel-intro-social/`). Owner approval pending.
- Gemini review fallback: `gemini-flash-latest` returned HTTP 503; `gemini-3.5-flash` worked through `--model`.
- Owner confirmed credits: 13+ years; Lead Gameplay Animator on AC Black Flag Resynced and Claws of Awaji; Lead Animator on Daimon Blades (Streum On Studio; Gemini had transcribed "Airstream"). Replaces the earlier "13 years" note.
- Rights: for the owner's work footage under NDA his approval is the permission proof (recorded as a dated attestation; the rights gate is unchanged).
- Scripts rewritten in a spoken voice from the owner's Animotion interview (read in Chrome; automatic fetch cut it off); its tips joined the idea backlog.
- Owner confirmed "Black Flag Resynced", 13+ years and seven series (`docs/creator_brief.md`); the first is named "AAA UE5 Secrets" (episodes still open "AAA UE5 secret..."). Both intro scripts list them all.
