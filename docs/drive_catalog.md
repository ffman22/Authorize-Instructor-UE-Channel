# Drive catalog

Heavy files (videos, images, renders) live in Google Drive, never in this repo. This repo keeps text, manifests and this catalog only.

Owner's Drive: carlo.animator@gmail.com. Root folder: **Unreal Shorts Studio**
https://drive.google.com/drive/folders/1a2K5ul8jKEWDUTlUJLMT_ntwkIDUd5fk

| Folder | Drive ID | What goes here | Link |
|---|---|---|---|
| 1-source-videos | 1uznlnLJCIbSE3kCagAwQ2xbGAnu4EMDG | Owner's long source videos (Unreal tutorials) | https://drive.google.com/drive/folders/1uznlnLJCIbSE3kCagAwQ2xbGAnu4EMDG |
| 2-shorts-rendered | 13GQzDP3uqp9is4DzLIHCp4PBGuoZrNgb | Rendered Shorts `out/<id>.mp4` ready to upload | https://drive.google.com/drive/folders/13GQzDP3uqp9is4DzLIHCp4PBGuoZrNgb |
| 3-thumbnails-images | 1u_IcMY6aPy63PIUcq-2p-X6GC78SYF5g | Thumbnails, screenshots, logos | https://drive.google.com/drive/folders/1u_IcMY6aPy63PIUcq-2p-X6GC78SYF5g |
| 4-personal-channel-reupload | 1SZVelepcJVfWqRfmBhQldjvgnWnR-rxz | Older personal-channel videos to re-upload | https://drive.google.com/drive/folders/1SZVelepcJVfWqRfmBhQldjvgnWnR-rxz |
| 5-archive | 11JSMUuDVXnqJ0WqriugiDEPehwqNrW8k | Old renders and finished uploads | https://drive.google.com/drive/folders/11JSMUuDVXnqJ0WqriugiDEPehwqNrW8k |
| 6-EditableAssets | 1FwVmMnXV_2mLdak_eCiBW-TUAbl7b2r5 | Owner's PSD templates (vertical thumbnail, UNREALZERO block); local copy in `out/Assets/` | https://drive.google.com/drive/folders/1FwVmMnXV_2mLdak_eCiBW-TUAbl7b2r5 |
| 7-Brand | 1ARix4S_DfLVmNGoreegHt6s_VJl_0dUJ | Watermarks, banner, brand images | https://drive.google.com/drive/folders/1ARix4S_DfLVmNGoreegHt6s_VJl_0dUJ |
| 8-gemini-analysis | 1VUl-xqDKOe8HYk1VRK1agnS2dLWtUXR9 | Gemini analysis of YouTube, Instagram and TikTok videos; prompt in 00_GEMINI_ANALYSIS_INSTRUCTIONS | https://drive.google.com/drive/folders/1VUl-xqDKOe8HYk1VRK1agnS2dLWtUXR9 |
| 8-gemini-analysis/1-videos-to-analyze | 1DVKvDDPLv4FaK6sOxfDctmum-aKrFfBf | Input: videos, screenshots or link lists | https://drive.google.com/drive/folders/1DVKvDDPLv4FaK6sOxfDctmum-aKrFfBf |
| 8-gemini-analysis/2-results | 1kQpLrIhyWTdsBZjOFr3DVgSZDtp_zK0X | Gemini results; Claude copies the text into `docs/analysis/` | https://drive.google.com/drive/folders/1kQpLrIhyWTdsBZjOFr3DVgSZDtp_zK0X |

## Naming
- Source: `<topic>-<yyyymmdd>-<n>.mp4`, e.g. `lighting-20261125-1.mp4`
- Short: `<id>.mp4`, the same `<id>` as `videos/<id>/manifest.json`
- Image: `<id>-thumb.png`

## Rules
- Git keeps code and text only. Images, renders and exports stay on disk (ignored by git); their master copy goes to Drive.
- Manifests point to Drive by ID in `drive_file_id`, never a local path to a heavy file.
- Drive is the owner's account. Share a file only with the owner's approval.
