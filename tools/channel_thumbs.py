#!/usr/bin/env python3
"""Brand thumbnails (frame + 2-4 words; owner face optional, per docs/creator_brief.md) and optional YouTube upload.

Usage: channel_thumbs.py [id ...]           render out/thumbs/<id>-brand.jpg
       channel_thumbs.py --set [id ...]     send the rendered files to YouTube (thumbnails.set)
Settings per video are in data/brand/thumbs.json: "at" (seconds in the source file), "crop"
(x0,y0,x1,y1 fractions of the frame), "text" (two lines; the second gets the accent colour)
and "face" (true adds the owner portrait; off by default). Longs are 1280x720, Shorts 1080x1920.
Shorts follow the owner's editable template (out/Assets, master copy on Drive 6-EditableAssets):
"art" takes the background from a template layer instead of the video frame, and "workshop": true
adds the UNREALZERO block (workshop promos only); other Shorts get the template watermark.
--set uploads only thumbnails the owner approved (tools/approval.py).
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approval  # noqa: E402
import build_video as bv  # noqa: E402
import make_thumbnail as mt  # noqa: E402
import psd_layers  # noqa: E402

ROOT = mt.REPO_ROOT
CONFIG = ROOT / "data" / "brand" / "thumbs.json"
PORTRAIT = ROOT / "data" / "brand" / "carlo-portrait.jpg"
WATERMARK = ROOT / "data" / "brand" / "watermark-150-u.png"
ACCENT, WHITE = (255, 204, 0), (255, 255, 255)
TEMPLATE = ROOT / "out" / "Assets" / "Template_Thumb_vertical_WorkshopPromo"
# Template layer indexes (psd_layers.py lists them): centred UNREALZERO block and corner watermark.
LAYER_WORKSHOP_BLOCK, LAYER_WATERMARK = 6, 10
# Owner's reference (workshop-promo-01 v2): top of the first line's capitals on a 1080x1920 cover.
# Title and blocks stay inside y 240-1680, the 3:4 profile grid crop.
SHORT_TITLE_CAP_TOP, SHORT_TITLE_WIDTH, SHORT_TITLE_SIZE = 398, 880, 180


def manifest(vid):
    return json.loads((ROOT / "videos" / vid / "manifest.json").read_text(encoding="utf-8"))


def text_lines(canvas, lines, x, y, width, size, center):
    d = ImageDraw.Draw(canvas)
    font_path = bv.find_font_path()
    for i, line in enumerate(lines):
        s = size
        while s > 30 and bv.text_w(d, line, bv.load_font(s, font_path), s // 12) > width:
            s -= 4
        font, stroke = bv.load_font(s, font_path), s // 12
        lx = x + (width - bv.text_w(d, line, font, stroke)) // 2 if center else x
        d.text((lx, y), line, font=font, fill=ACCENT if i else WHITE, stroke_width=stroke, stroke_fill=(0, 0, 0))
        y += int(s * 1.18)


def template_layer(index):
    """One template layer as an RGBA 1080x1920 sheet, in its template position."""
    if not TEMPLATE.is_file():
        raise FileNotFoundError(f"{TEMPLATE.relative_to(ROOT)} not found: copy it from Drive 6-EditableAssets")
    sheet = psd_layers.flatten(TEMPLATE, [index])
    scale = max(1080 / sheet.width, 1920 / sheet.height)
    sheet = sheet.resize((round(sheet.width * scale), round(sheet.height * scale)), Image.LANCZOS)
    x, y = (sheet.width - 1080) // 2, (sheet.height - 1920) // 2
    return sheet.crop((x, y, x + 1080, y + 1920))


def add_face(canvas, box, fade_left=0, fade_top=0):
    """Paste the portrait (head and shoulders) into box=(x, y, w, h) with soft edges."""
    x, y, w, h = box
    src = Image.open(PORTRAIT).convert("RGB")
    src = src.crop((40, 150, 610, 760))  # head and shoulders of carlo-portrait.jpg
    face = ImageEnhance.Contrast(mt.cover_fill(src, (w, h))).enhance(1.1)
    mask = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(mask)
    for i in range(fade_left):
        d.line((i, 0, i, h), fill=int(255 * i / fade_left))
    for j in range(fade_top):
        d.line((0, j, w, j), fill=int(255 * j / fade_top))
    canvas.paste(face, (x, y), mask)


def video_frame(m, cfg):
    src = mt.rights_gate.resolve_clip_path(m["source"]["file"])
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "f.jpg"
        mt.grab(src, cfg["at"], f)
        frame = Image.open(f).convert("RGB")
    # "erase": [x, y, w, h] in source pixels (e.g. a recorded mouse cursor), covered with the patch left of it.
    if "erase" in cfg:
        x, y, w, h = cfg["erase"]
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rectangle((3, 3, w - 4, h - 4), fill=255)
        frame.paste(frame.crop((x - w, y, x, y + h)), (x, y), mask.filter(ImageFilter.GaussianBlur(2)))
    x0, y0, x1, y1 = cfg["crop"]
    frame = frame.crop((int(x0 * frame.width), int(y0 * frame.height), int(x1 * frame.width), int(y1 * frame.height)))
    return ImageEnhance.Color(ImageEnhance.Brightness(frame).enhance(cfg.get("bright", 1.1))).enhance(1.25)


def render(vid, cfg):
    m = manifest(vid)
    short = str(m.get("format") or "short") == "short"
    if short and "art" in cfg:
        art = template_layer(cfg["art"])
        frame = Image.new("RGB", art.size, (0, 0, 0))
        frame.paste(art, (0, 0), art)
    else:
        frame = video_frame(m, cfg)
    face = cfg.get("face", False)
    black = (0, 0, 0)
    if short:
        # "drop": pixels of dark headroom above the frame, so the subject sits under the title.
        drop = cfg.get("drop", 0)
        canvas = Image.new("RGB", (1080, 1920), black)
        art_fill = mt.cover_fill(frame, (1080, 1920 - drop))
        fade = Image.new("L", art_fill.size, 255)
        for j in range(min(drop, 260)):
            ImageDraw.Draw(fade).line((0, j, 1080, j), fill=int(255 * j / min(drop, 260)))
        canvas.paste(art_fill, (0, drop), fade)
        canvas.paste(Image.new("RGB", canvas.size, black), (0, 0), mt.gradient(canvas.size, True, 190))
        if face:
            add_face(canvas, (0, 1000, 1080, 920), fade_top=260)
        font = bv.load_font(SHORT_TITLE_SIZE, bv.find_font_path())
        top = SHORT_TITLE_CAP_TOP - ImageDraw.Draw(canvas).textbbox((0, 0), cfg["text"][0], font=font)[1]
        text_lines(canvas, cfg["text"], (1080 - SHORT_TITLE_WIDTH) // 2, top, SHORT_TITLE_WIDTH,
                   SHORT_TITLE_SIZE, center=True)
        overlay = template_layer(LAYER_WORKSHOP_BLOCK if cfg.get("workshop") else LAYER_WATERMARK)
        canvas.paste(overlay, (0, 0), overlay)
    else:
        canvas = mt.cover_fill(frame, (1280, 720))
        canvas.paste(Image.new("RGB", canvas.size, black), (0, 0), mt.gradient(canvas.size, False, 215))
        if face:
            add_face(canvas, (780, 0, 500, 720), fade_left=180)
        text_lines(canvas, cfg["text"], 55, 220, 740 if face else 620, 140, center=False)
        # Owner's rule for 16:9: the watermark is large and in the bottom right corner.
        logo = Image.open(WATERMARK).convert("RGBA").resize((230, 230), Image.LANCZOS)
        canvas.paste(logo, (canvas.width - 254, canvas.height - 254), logo)
    out = mt.THUMBS / f"{vid}-brand.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, quality=90)
    return out


def set_thumbnails(ids):
    import youtube_upload as yu
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    yt = build("youtube", "v3", credentials=yu.load_credentials(), cache_discovery=False)
    failed = 0
    for vid in ids:
        blocked = approval.check(vid, parts=("thumbnail",))
        if blocked:
            failed += 1
            print(f"SET REFUSED {vid}: {blocked[0]}")
            continue
        record = json.loads((ROOT / "videos" / vid / "published.json").read_text(encoding="utf-8"))["youtube"]
        image = mt.THUMBS / f"{vid}-brand.jpg"
        try:
            yt.thumbnails().set(videoId=record["video_id"],
                                media_body=MediaFileUpload(str(image), mimetype="image/jpeg")).execute()
            print(f"SET OK {vid} {record['video_id']}")
        except HttpError as e:
            failed += 1
            print(f"SET FAIL {vid} {record['video_id']}: {yu.explain_http_error(e)} {str(e)[:200]}")
    return 1 if failed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render or upload the brand thumbnails.")
    ap.add_argument("ids", nargs="*", help="video ids (default: all in thumbs.json)")
    ap.add_argument("--set", action="store_true", help="upload the already rendered files to YouTube")
    args = ap.parse_args(argv)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    ids = args.ids or list(config)
    if args.set:
        return set_thumbnails(ids)
    for vid in ids:
        print(f"THUMB OK {render(vid, config[vid]).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
