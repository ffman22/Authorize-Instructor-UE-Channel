# Setup checklist (owner, one time)

Mark each item when done. ⏳ = waiting on the owner.

## 1. Research (VidIQ in Claude)
- ⏳ Install the free VidIQ Chrome extension.
- ⏳ In claude.ai, open the VidIQ dropdown → "Connect YouTube Insights" → Authorize.
- ⏳ Add the connector "VidIQ for Claude" in Connectors. Cloud sessions use the account's connectors.

## 2. YouTube channel and API
- ⏳ Create the channel (brand account) and verify the phone number (needed for uploads over 15 min and some features).
- ⏳ Google Cloud console: new project → enable YouTube Data API v3 → OAuth consent screen → create an OAuth client (Desktop) → download `client_secret.json` to the repo root (gitignored).
- ⏳ Run `python3 tools/youtube_upload.py --auth` once on a machine with a browser; it writes `token.json` (gitignored).
- Limit: uploads from an API project that has not passed YouTube's API compliance audit are locked to private. Fix: request the audit (form in the API docs), or upload manually the first weeks. Open question `q-yt-audit`.

## 2b. API key for discovery
- ⏳ Same Google Cloud project: create an API key (restricted to YouTube Data API v3), put `YOUTUBE_API_KEY=...` in `.env`. Free quota 10,000 units/day (one `find_viral` search = 100 units).

## 3. Instagram
- ⏳ Convert the account to Professional (Creator or Business) and link a Facebook Page.
- ⏳ Meta developer app with Instagram Graph API; get `IG_USER_ID` and a long-lived `IG_ACCESS_TOKEN`; put them in `.env` (gitignored).
- Reels need a public `video_url` Meta can fetch. Open question `q-ig-host`: where the MP4 is hosted (object-storage bucket with a public URL, free tier).

- Instagram has no scheduling in the API: `publish_at` is ignored there, so the scheduled daily task must run at the slot time to post the Reel. YouTube schedules natively.
- Check `GRAPH_VERSION` in `tools/instagram_publish.py` against Meta's current stable version. YouTube may refuse the first comment while a video is private or scheduled; the error is logged in `published.json` as `first_comment_error`.

## 3b. YouTube Studio and accounts (research rules)
- ⏳ Settings > Channel > Advanced: audience "No, it's not made for kids".
- ⏳ Turn on automatic dubbing.
- ⏳ Daily genuine engagement for 2-3 weeks on the new accounts (owner only).
- ⏳ Append `?sub_confirmation=1` to external links that point to the YouTube channel.

## 3c. Drive sync
- ⏳ Install Google Drive for Desktop and sign in with the channel account, so renders, thumbnails and analysis files reach Drive without manual uploads.

## 4. Scheduling
- ⏳ After one manual video works end to end, create a daily scheduled task in Claude that runs `/daily-run`.

## 5. Clips
- ⏳ Decide the clip source(s) (see `docs/rights_and_policy.md`). Without a source there is nothing to rank.
