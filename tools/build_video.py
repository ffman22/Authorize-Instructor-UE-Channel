#!/usr/bin/env python3
"""Render a tip Short (1080x1920, 30 fps, H.264/AAC) from one cut of one source video.

Usage: build_video.py <manifest.json> [--out out/<id>.mp4]
       build_video.py --selftest [--out FILE]
The source is fitted over a blurred copy of itself (nothing cropped), the title headline is
burned at the top, and the source audio is kept. The rights gate runs first; a failing
manifest is refused. Long videos (format "long") are uploaded as is, not rendered here.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rights_gate  # noqa: E402

W, H, FPS = 1080, 1920, 30
AR, AC = 44100, 2
REPO_ROOT = rights_gate.REPO_ROOT
HEADLINE_TOP = 220          # px from the top; clear of the YouTube Shorts top bar
HEADLINE_MAX_LINES = 3
HEADLINE_SIDE_MARGIN = 90
FONT_CANDIDATES = [
    "C:/Windows/Fonts/seguibl.ttf",   # Segoe UI Black
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)


# ---------- fonts and overlay ----------

def find_font_path():
    for p in FONT_CANDIDATES:
        if Path(p).is_file():
            return p
    root = Path("/usr/share/fonts")
    for p in sorted(root.rglob("*")) if root.is_dir() else []:
        name = p.name.lower()
        if p.suffix.lower() in (".ttf", ".otf") and ("dejavusans-bold" in name or "inter-bold" in name):
            return str(p)
    return None


def load_font(size, path):
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def text_w(draw, text, font, stroke):
    l, _, r, _ = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    return r - l


def wrap_words(draw, words, font, stroke, max_w):
    """Greedy word wrap; a single over-long word stays on its own line."""
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if not cur or text_w(draw, trial, font, stroke) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def layout_headline(draw, text, font_path, max_w):
    """Return (size, stroke, lines): the largest font that fits in HEADLINE_MAX_LINES lines."""
    words = text.upper().split()
    size = 110
    while True:
        font = load_font(size, font_path)
        stroke = max(3, int(size * 0.09))
        lines = wrap_words(draw, words, font, stroke, max_w)
        fits = len(lines) <= HEADLINE_MAX_LINES and all(text_w(draw, ln, font, stroke) <= max_w for ln in lines)
        if fits or size <= 32:
            return size, stroke, lines[:HEADLINE_MAX_LINES]
        size -= 4


def make_overlay(title, path, font_path):
    """Transparent 1080x1920 PNG with the headline on a translucent band at the top."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size, stroke, lines = layout_headline(d, title, font_path, W - 2 * HEADLINE_SIDE_MARGIN)
    font = load_font(size, font_path)
    line_h = int(size * 1.18)
    pad = 36
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(band).rounded_rectangle(
        (HEADLINE_SIDE_MARGIN - pad, HEADLINE_TOP - pad,
         W - HEADLINE_SIDE_MARGIN + pad, HEADLINE_TOP + line_h * len(lines) + pad // 2),
        radius=28, fill=(0, 0, 0, 120))
    img = Image.alpha_composite(img, band)
    d = ImageDraw.Draw(img)
    y = HEADLINE_TOP
    for ln in lines:
        x = (W - text_w(d, ln, font, stroke)) // 2
        d.text((x, y), ln, font=font, fill=WHITE, stroke_width=stroke, stroke_fill=BLACK)
        y += line_h
    img.save(path)
    return len(lines)


CTA_SECONDS = 3.5
CTA_DEFAULT = {"text": "JOIN THE WORKSHOP", "sub": "Unreal for Animators - ianimate.net"}


def make_cta_overlay(cta, path, font_path):
    """Transparent 1080x1920 PNG with a call-to-action card (iAnimate 'i' + text) below the video."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    card_w, card_h, top = 940, 230, 1400
    x0 = (W - card_w) // 2
    d.rounded_rectangle((x0, top, x0 + card_w, top + card_h), radius=36, fill=(214, 40, 57, 235))
    pad = 30
    text_x = x0 + pad
    logo = REPO_ROOT / "data" / "brand" / "ianimate-i.png"
    if logo.exists():
        side = card_h - 2 * pad
        d.rounded_rectangle((x0 + pad, top + pad, x0 + pad + side, top + pad + side), radius=24, fill=(255, 255, 255, 255))
        li = Image.open(logo).convert("RGBA")
        scale = (side - 24) / li.height
        li = li.resize((max(1, int(li.width * scale)), side - 24), Image.LANCZOS)
        img.alpha_composite(li, (x0 + pad + (side - li.width) // 2, top + pad + 12))
        text_x = x0 + pad + side + pad
    max_w = x0 + card_w - pad - text_x
    def fit(txt, size, stroke):
        while size > 20 and text_w(d, txt, load_font(size, font_path), stroke) > max_w:
            size -= 2
        return load_font(size, font_path), size
    big, bs = fit(cta["text"], 84, 5)
    small, ss = fit(cta["sub"], 44, 2)
    block_h = int(bs * 1.15) + int(ss * 1.3)
    y = top + (card_h - block_h) // 2
    d.text((text_x, y), cta["text"], font=big, fill=WHITE, stroke_width=5, stroke_fill=BLACK)
    d.text((text_x, y + int(bs * 1.15)), cta["sub"], font=small, fill=WHITE, stroke_width=2, stroke_fill=BLACK)
    img.save(path)


# ---------- ffmpeg helpers ----------

def need_tool(name):
    if not shutil.which(name):
        sys.exit(f"BUILD FAIL: {name} not found on PATH")


def ffprobe_json(path, *args):
    out = subprocess.run(["ffprobe", "-v", "error", "-of", "json", *args, str(path)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {out.stderr.strip()}")
    return json.loads(out.stdout or "{}")


def has_audio(path):
    data = ffprobe_json(path, "-select_streams", "a", "-show_entries", "stream=index")
    return bool(data.get("streams"))


def media_duration(path):
    data = ffprobe_json(path, "-show_entries", "format=duration")
    return float(data.get("format", {}).get("duration", 0) or 0)


def run_ffmpeg(cmd, what):
    res = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *cmd],
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({what}): {res.stderr.strip()[-800:]}")


def render_cut(src, overlay_png, start, duration, out_path, cta_png=None):
    """One pass: cut, blurred-background 9:16 fit, headline overlay, optional end CTA, source audio (or silence)."""
    audio = has_audio(src)
    cmd = ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(src),
           "-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.3f}", "-i", str(overlay_png)]
    if cta_png:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.3f}", "-i", str(cta_png)]
    if not audio:
        cmd += ["-f", "lavfi", "-t", f"{duration:.3f}", "-i", f"anullsrc=r={AR}:cl=stereo"]
    audio_idx = 3 if cta_png else 2
    if cta_png:
        t0 = max(0.0, duration - CTA_SECONDS)
        tail = (f"[base][1:v]overlay=0:0:format=auto[hl];"
                f"[hl][2:v]overlay=0:0:format=auto:enable='gte(t,{t0:.2f})',format=yuv420p,setsar=1[v]")
    else:
        tail = "[base][1:v]overlay=0:0:format=auto,format=yuv420p,setsar=1[v]"
    vf = (
        f"[0:v]fps={FPS},setsar=1,split=2[s1][s2];"
        f"[s1]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:3,"
        f"eq=brightness=-0.08[bg];"
        f"[s2]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"scale=trunc(iw/2)*2:trunc(ih/2)*2[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[base];"
        + tail
    )
    a_in = "0:a:0" if audio else f"{audio_idx}:a"
    af = f";[{a_in}]aresample={AR},aformat=sample_fmts=fltp:channel_layouts=stereo,apad[a]"
    cmd += ["-filter_complex", vf + af, "-map", "[v]", "-map", "[a]",
            "-t", f"{duration:.3f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-c:a", "aac", "-b:a", "160k", "-ar", str(AR), "-ac", str(AC),
            "-movflags", "+faststart", str(out_path)]
    run_ffmpeg(cmd, f"render {Path(src).name}")
    return audio


# ---------- build ----------

def build(manifest_path, out_path=None):
    need_tool("ffmpeg")
    need_tool("ffprobe")
    ok, manifest, errors, _ = rights_gate.run(manifest_path, check_files=True)
    if not ok:
        print(f"BUILD REFUSED {manifest_path}: rights gate failed ({len(errors)} errors)")
        return 1
    if rights_gate.manifest_format(manifest) == "long":
        print(f"BUILD REFUSED {manifest_path}: format 'long' is uploaded as is from video_file, not rendered")
        return 1
    vid = manifest.get("id") or Path(manifest_path).resolve().parent.name
    out_path = Path(out_path) if out_path else REPO_ROOT / "out" / f"{vid}.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    src = rights_gate.resolve_clip_path(rights_gate.source_file(manifest), manifest_path)
    start = rights_gate.parse_seconds(manifest.get("start", 0))
    duration = rights_gate.parse_seconds(manifest.get("duration"))
    font_path = find_font_path()

    try:
        src_len = media_duration(src)
    except RuntimeError as e:
        print(f"BUILD FAIL {manifest_path}: {e}")
        return 1
    if start >= src_len:
        print(f"BUILD FAIL {manifest_path}: start {start:g}s is past the source end ({src_len:.1f}s)")
        return 1
    if start + duration > src_len + 0.05:
        print(f"BUILD FAIL {manifest_path}: cut {start:g}s+{duration:g}s runs past the source end "
              f"({src_len:.1f}s); shorten duration or move start")
        return 1

    with tempfile.TemporaryDirectory(prefix="rss_build_") as tmp:
        png = Path(tmp) / "headline.png"
        n_lines = make_overlay(str(manifest["title"]).strip(), png, font_path)
        cta = manifest.get("cta")
        cta_png = None
        if cta:
            cta = {**CTA_DEFAULT, **(cta if isinstance(cta, dict) else {})}
            cta_png = Path(tmp) / "cta.png"
            make_cta_overlay(cta, cta_png, font_path)
        try:
            audio = render_cut(src, png, start, duration, out_path, cta_png)
        except RuntimeError as e:
            print(f"BUILD FAIL {manifest_path}: {e}")
            return 1

    total = media_duration(out_path)
    font_note = Path(font_path).name if font_path else "Pillow default"
    print(f"BUILD OK {out_path}: {total:.1f}s from {src.name} @{start:g}s, {W}x{H}@{FPS}, "
          f"headline {n_lines} lines, audio {'source' if audio else 'silent'}, font {font_note}")
    return 0


# ---------- selftest ----------

def probe_ok(path, expected_s):
    """Return a list of failures for a rendered file."""
    failures = []
    info = ffprobe_json(path, "-show_entries",
                        "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration")
    v = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    a = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    dur = float(info.get("format", {}).get("duration", 0))
    if not v or (v[0].get("width"), v[0].get("height")) != (W, H):
        failures.append(f"video size {v[0].get('width') if v else None}x{v[0].get('height') if v else None}")
    elif v[0].get("codec_name") != "h264":
        failures.append(f"video codec {v[0].get('codec_name')}")
    elif v[0].get("r_frame_rate") != f"{FPS}/1":
        failures.append(f"frame rate {v[0].get('r_frame_rate')}")
    if not a or a[0].get("codec_name") != "aac":
        failures.append("no AAC audio stream")
    if abs(dur - expected_s) > 0.5:
        failures.append(f"duration {dur:.2f}s, expected {expected_s:.1f}s")
    return failures


def selftest(keep=None):
    need_tool("ffmpeg")
    need_tool("ffprobe")
    specs = [("640x360", True), ("1920x1080", False), ("720x1280", True), ("1080x1080", False)]
    cut_s = 4.0
    failures = []
    with tempfile.TemporaryDirectory(prefix="rss_selftest_") as tmp:
        tmp = Path(tmp)
        base = {
            "id": "selftest", "format": "short", "title": "Fix Lumen light leaks in one click",
            "source": {"drive_file_id": "", "file": ""}, "start": "0:02", "duration": cut_s,
            "rights": "own", "proof": "", "credit": "", "description": "Full tutorial. Workshop: https://ianimate.net/workshops/unreal-for-animators", "privacy": "private", "publish_at": "",
            "hashtags": ["#unrealengine"], "first_comment": "", "ig_caption": "",
        }
        # Gate: each bad manifest must be refused.
        bad_cases = {
            "rights unknown": {"rights": "unknown"},
            "licensed without proof": {"rights": "licensed"},
            "cc without credit": {"rights": "cc", "proof": "https://example.org/license"},
            "duration over 60 s": {"duration": 61},
            "no source": {"source": {"drive_file_id": "", "file": ""}},
            "public without publish_at": {"privacy": "public"},
            "empty title": {"title": " "},
            "naive publish_at": {"publish_at": "2026-12-01T17:00:00"},
        }
        ok_src = dict(base, source={"drive_file_id": "abc123", "file": ""})
        for name, patch in bad_cases.items():
            errs, _ = rights_gate.check(dict(ok_src, **patch))
            if not errs:
                failures.append(f"gate accepted: {name}")
        errs, _ = rights_gate.check(dict(ok_src, privacy="public", publish_at="2026-12-01T17:00:00Z"))
        if errs:
            failures.append(f"gate refused a scheduled manifest: {errs}")
        errs, _ = rights_gate.check(dict(ok_src, format="long", duration=None, title="A long Unreal tutorial"))
        if errs:
            failures.append(f"gate refused a long manifest: {errs}")

        # Renderer: one cut per source shape; the first is the low-res 16:9 case.
        for i, (size, audio) in enumerate(specs):
            f = tmp / f"src{i}.mp4"
            cmd = ["-f", "lavfi", "-i", f"testsrc2=size={size}:rate=25:duration=8"]
            if audio:
                cmd += ["-f", "lavfi", "-i", f"sine=frequency={300 + 100 * i}:sample_rate=48000:duration=8"]
            cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
            cmd += (["-c:a", "aac", "-shortest"] if audio else [])
            run_ffmpeg(cmd + [str(f)], f"test source {size}")
            m = dict(base, id=f"selftest{i}", source={"drive_file_id": "", "file": str(f)})
            mpath = tmp / f"m{i}.json"
            mpath.write_text(json.dumps(m, indent=2), encoding="utf-8")
            out = tmp / f"out{i}.mp4"
            if build(mpath, out) != 0 or not out.is_file():
                failures.append(f"build failed for {size}")
                continue
            failures += [f"{size}: {x}" for x in probe_ok(out, cut_s)]
            if i == 0 and keep:
                Path(keep).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(out, keep)

        # Renderer must refuse an uncleared source and a cut past the source end.
        src0 = str(tmp / "src0.mp4")
        for name, patch in {"rights unknown": {"rights": "unknown"}, "cut past end": {"start": 6}}.items():
            bpath = tmp / "bad.json"
            bpath.write_text(json.dumps(dict(base, source={"file": src0}, **patch)), encoding="utf-8")
            bout = tmp / "bad.mp4"
            if build(bpath, bout) == 0 or bout.exists():
                failures.append(f"build did not refuse: {name}")
    if failures:
        print(f"SELFTEST FAIL: {len(failures)} errors")
        for f in failures:
            print(f"  ERROR {f}")
        return 1
    print(f"SELFTEST PASS: {len(bad_cases)} gate refusals, {len(specs)} renders {W}x{H} h264/aac"
          + (f", sample at {keep}" if keep else ""))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a 1080x1920 tip Short from one cut of one source video.")
    ap.add_argument("manifest", nargs="?", help="path to videos/<id>/manifest.json")
    ap.add_argument("--out", help="output MP4 (default out/<id>.mp4; with --selftest, keep a sample there)")
    ap.add_argument("--selftest", action="store_true", help="check the gate, render synthetic sources, verify output")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest(args.out)
    if not args.manifest:
        ap.error("manifest is required unless --selftest")
    return build(args.manifest, args.out)


if __name__ == "__main__":
    sys.exit(main())
