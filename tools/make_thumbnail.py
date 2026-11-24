#!/usr/bin/env python3
"""Make a thumbnail and a vertical cover for a manifest: best frame of the cut + brand headline.

Usage: make_thumbnail.py <manifest.json> [--frames 6] [--no-gemini] [--critique]
Frames are sampled across the cut (long videos: across the whole video). Gemini picks the most
readable frame from small previews (cheap); without a key, or with --no-gemini, the sharpest wins.
Outputs: out/thumbs/<id>-yt.jpg (1280x720, YouTube) and out/thumbs/<id>-cover.jpg (1080x1920,
Instagram/TikTok cover). --critique asks Gemini to score the 16:9 result (one more small call).
The previews are sent to Google; own footage only (rights gate must pass).
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_video as bv  # noqa: E402
import gemini_client as gc  # noqa: E402
import rights_gate  # noqa: E402
from publish_common import video_id  # noqa: E402

REPO_ROOT = rights_gate.REPO_ROOT
THUMBS = REPO_ROOT / "out" / "thumbs"
BRAND = REPO_ROOT / "data" / "brand" / "watermark-150.png"


def sample_times(manifest, path, n):
    start = rights_gate.parse_seconds(manifest.get("start", 0))
    if str(manifest.get("format") or "short") == "short":
        dur = rights_gate.parse_seconds(manifest["duration"])
        lo, hi = start + dur * 0.1, start + dur * 0.9
    else:
        total = bv.media_duration(path)
        lo, hi = total * 0.05, total * 0.9
    return [lo + (hi - lo) * i / max(n - 1, 1) for i in range(n)]


def grab(src, t, dst):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
           "-q:v", "2", str(dst)]
    if subprocess.run(cmd, capture_output=True).returncode != 0 or not dst.is_file():
        raise RuntimeError(f"ffmpeg could not read a frame at {t:.1f}s")


def sharpness(img):
    return ImageStat.Stat(img.convert("L").filter(ImageFilter.FIND_EDGES)).stddev[0]


def pick_with_gemini(frames):
    parts = [gc.text_part(
        "These are candidate frames (numbered from 0) of an Unreal Engine tutorial. Pick the one that "
        "works best as a thumbnail: clear subject (viewport, character, node graph), readable at small size, "
        "no motion blur, no empty or loading screen. Return JSON: {\"best\": index, \"reason\": short}.")]
    for i, f in enumerate(frames):
        small = f.copy()
        small.thumbnail((480, 270))
        tmp = Path(tempfile.gettempdir()) / f"thumb_pick_{i}.jpg"
        small.convert("RGB").save(tmp, quality=70)
        parts += [gc.text_part(f"Frame {i}:"), gc.image_part(tmp)]
        tmp.unlink(missing_ok=True)
    data = gc.generate_json(parts, task="thumb_pick")
    idx = int(data["best"])
    if not 0 <= idx < len(frames):
        raise gc.GeminiError(f"best index {idx} out of range")
    return idx, str(data.get("reason", ""))


def cover_fill(img, size):
    r = max(size[0] / img.width, size[1] / img.height)
    big = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x, y = (big.width - size[0]) // 2, (big.height - size[1]) // 2
    return big.crop((x, y, x + size[0], y + size[1]))


def draw_headline(canvas, title, font_path, box, anchor="left"):
    """Headline with stroke inside box=(x0,y0,x1,y1) on a dark gradient for contrast."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(canvas)
    size, stroke, lines = bv.layout_headline(d, title, font_path, x1 - x0)
    font = bv.load_font(size, font_path)
    line_h = int(size * 1.15)
    y = y0 + max(0, (y1 - y0 - line_h * len(lines)) // 2)
    for ln in lines:
        x = x0 if anchor == "left" else x0 + (x1 - x0 - bv.text_w(d, ln, font, stroke)) // 2
        d.text((x, y), ln, font=font, fill=(255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0))
        y += line_h


def gradient(size, vertical_from_top=True, strength=190):
    """Mask that is dark at the top (or left) and fades out across the image."""
    span = size[1] if vertical_from_top else size[0]
    line = Image.new("L", (1, span))
    line.putdata([int(strength * (1 - i / span) ** 1.3) for i in range(span)])
    if vertical_from_top:
        return line.resize(size)
    return line.rotate(90, expand=True).transpose(Image.FLIP_TOP_BOTTOM).resize(size)


def stamp_brand(canvas, corner):
    if BRAND.is_file():
        logo = Image.open(BRAND).convert("RGBA")
        canvas.paste(logo, corner, logo)


def make_yt(frame, title, font_path):
    canvas = cover_fill(frame.convert("RGB"), (1280, 720))
    shade = Image.new("RGB", canvas.size, (0, 0, 0))
    canvas.paste(shade, (0, 0), gradient(canvas.size, vertical_from_top=False, strength=210))
    draw_headline(canvas, title, font_path, (60, 120, 760, 600))
    stamp_brand(canvas, (1280 - 150 - 24, 720 - 150 - 24))
    return canvas


def make_cover(frame, title, font_path):
    canvas = cover_fill(frame.convert("RGB"), (1080, 1920))
    shade = Image.new("RGB", canvas.size, (0, 0, 0))
    canvas.paste(shade, (0, 0), gradient(canvas.size, vertical_from_top=True, strength=200))
    draw_headline(canvas, title, font_path, (90, 220, 990, 700), anchor="center")
    stamp_brand(canvas, (1080 - 150 - 40, 1920 - 150 - 260))
    return canvas


def critique(path):
    data = gc.generate_json([gc.text_part(
        "Score this YouTube thumbnail 1-10 for click appeal and legibility at 160px wide. Return JSON: "
        "{\"score\": n, \"fix\": one concrete improvement}."), gc.image_part(path)], task="thumb_critique")
    return data.get("score"), str(data.get("fix", ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Thumbnail (16:9) and cover (9:16) from a manifest.")
    ap.add_argument("manifest")
    ap.add_argument("--frames", type=int, default=6, help="candidate frames (default 6)")
    ap.add_argument("--no-gemini", action="store_true", help="pick the sharpest frame locally")
    ap.add_argument("--critique", action="store_true", help="ask Gemini to score the 16:9 result")
    args = ap.parse_args(argv)

    ok, manifest, errors, _ = rights_gate.run(args.manifest, check_files=True, quiet=True)
    vid = video_id(manifest or {}, args.manifest)
    if not ok:
        print(f"THUMB REFUSED {vid}: rights gate failed: {'; '.join(errors)}")
        return 1
    src = rights_gate.resolve_clip_path(rights_gate.source_file(manifest), args.manifest)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for i, t in enumerate(sample_times(manifest, src, args.frames)):
                f = Path(tmp) / f"f{i}.jpg"
                grab(src, t, f)
                frames.append(Image.open(f).convert("RGB"))
            best, why = max(range(len(frames)), key=lambda i: sharpness(frames[i])), "sharpest"
            if not args.no_gemini:
                try:
                    best, why = pick_with_gemini(frames)
                except (gc.GeminiError, KeyError, ValueError) as e:
                    why = f"sharpest (Gemini skipped: {e})"
            frame = frames[best]
    except (RuntimeError, OSError) as e:
        print(f"THUMB FAIL {vid}: {e}")
        return 1

    font_path = bv.find_font_path()
    title = str(manifest["title"]).strip()
    THUMBS.mkdir(parents=True, exist_ok=True)
    yt, cover = THUMBS / f"{vid}-yt.jpg", THUMBS / f"{vid}-cover.jpg"
    make_yt(frame, title, font_path).save(yt, quality=90)
    make_cover(frame, title, font_path).save(cover, quality=90)
    print(f"THUMB OK {vid}: frame {best + 1}/{len(frames)} ({why}) -> {yt.relative_to(REPO_ROOT)}, "
          f"{cover.relative_to(REPO_ROOT)}")
    if args.critique:
        try:
            score, fix = critique(yt)
            print(f"  critique {score}/10: {fix}")
        except gc.GeminiError as e:
            print(f"  WARN critique skipped: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
