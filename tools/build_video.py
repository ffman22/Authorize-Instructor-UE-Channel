#!/usr/bin/env python3
"""Render a ranking Short (1080x1920, 30 fps, H.264/AAC) from a manifest.

Usage: build_video.py <manifest.json> [--out out/<id>.mp4]
       build_video.py --selftest
The rights gate runs first; a failing manifest is refused.
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
DEFAULT_CLIP_SECONDS = 6.0
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
]
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)


# ---------- fonts and overlay ----------

def find_font_path():
    for p in FONT_CANDIDATES:
        if Path(p).is_file():
            return p
    for p in sorted(Path("/usr/share/fonts").rglob("*")) if Path("/usr/share/fonts").is_dir() else []:
        name = p.name.lower()
        if p.suffix.lower() in (".ttf", ".otf") and ("dejavusans-bold" in name or "inter-bold" in name):
            return str(p)
    return None


def load_font(size, path):
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def hex_to_rgba(value, default=(0, 201, 183)):
    v = str(value or "").lstrip("#")
    try:
        rgb = tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)) if len(v) == 6 else default
    except ValueError:
        rgb = default
    return rgb + (255,)


def text_w(draw, text, font, stroke):
    l, _, r, _ = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    return r - l


def fit_size(draw, lines, font_path, start, max_w, stroke_ratio=0.09):
    size = start
    while size > 20:
        f = load_font(size, font_path)
        s = max(2, int(size * stroke_ratio))
        if all(text_w(draw, ln, f, s) <= max_w for ln in lines):
            return size
        size -= 4
    return size


def draw_centered(draw, y, text, font, fill, stroke):
    x = (W - text_w(draw, text, font, stroke)) // 2
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke, stroke_fill=BLACK)


def draw_title_line(draw, y, line, font, stroke, keywords, kw_color):
    """Draw one title line word by word, keywords in kw_color."""
    words = line.split()
    space = text_w(draw, " ", font, 0)
    widths = [text_w(draw, w, font, stroke) for w in words]
    x = (W - (sum(widths) + space * (len(words) - 1))) // 2
    for w, ww in zip(words, widths):
        bare = w.strip(".,!?:;'\"").upper()
        fill = kw_color if bare in keywords else WHITE
        draw.text((x, y), w, font=font, fill=fill, stroke_width=stroke, stroke_fill=BLACK)
        x += ww + space


def make_overlay(manifest, clip, path, font_path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lines = [str(x).upper() for x in manifest.get("title_lines", [])][:2]
    keywords = {str(k).upper() for k in manifest.get("keywords", [])}
    kw_color = hex_to_rgba(manifest.get("keyword_color"))

    # Title: two lines at the top, heavy outline.
    tsize = fit_size(d, lines, font_path, 96, W - 80, 0.1)
    tfont = load_font(tsize, font_path)
    tstroke = max(4, int(tsize * 0.1))
    y = 150
    for ln in lines:
        draw_title_line(d, y, ln, tfont, tstroke, keywords, kw_color)
        y += int(tsize * 1.2)

    # Rank number and label at the bottom.
    rsize = 220
    rfont = load_font(rsize, font_path)
    rstroke = 12
    rank_text = f"#{clip['rank']}"
    label = str(clip.get("label", "")).upper()
    lsize = fit_size(d, [label], font_path, 84, W - 120)
    lfont = load_font(lsize, font_path)
    lstroke = max(4, int(lsize * 0.09))
    label_y = H - 300
    rank_y = label_y - rsize - 10
    draw_centered(d, rank_y, rank_text, rfont, kw_color, rstroke)
    draw_centered(d, label_y, label, lfont, WHITE, lstroke)

    # Take caption above the rank number.
    take = str(clip.get("take", ""))
    csize = fit_size(d, [take], font_path, 64, W - 120)
    cfont = load_font(csize, font_path)
    cstroke = max(3, int(csize * 0.08))
    draw_centered(d, rank_y - csize - 50, take, cfont, WHITE, cstroke)

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


def render_segment(src, overlay_png, start, duration, out_path):
    audio = has_audio(src)
    cmd = ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(src),
           "-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.3f}", "-i", str(overlay_png)]
    if not audio:
        cmd += ["-f", "lavfi", "-t", f"{duration:.3f}", "-i", f"anullsrc=r={AR}:cl=stereo"]
    vf = (
        f"[0:v]fps={FPS},setsar=1,split=2[s1][s2];"
        f"[s1]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:3,"
        f"eq=brightness=-0.08[bg];"
        f"[s2]scale={W}:{H}:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[base];"
        f"[base][1:v]overlay=0:0:format=auto,format=yuv420p,setsar=1[v]"
    )
    a_in = "0:a:0" if audio else "2:a"
    af = f";[{a_in}]aresample={AR},aformat=sample_fmts=fltp:channel_layouts=stereo,apad[a]"
    cmd += ["-filter_complex", vf + af, "-map", "[v]", "-map", "[a]",
            "-t", f"{duration:.3f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-c:a", "aac", "-b:a", "160k", "-ar", str(AR), "-ac", str(AC),
            str(out_path)]
    run_ffmpeg(cmd, f"segment {Path(src).name}")


def concat(segments, out_path, workdir):
    listfile = Path(workdir) / "concat.txt"
    listfile.write_text("".join(f"file '{Path(s).as_posix()}'\n" for s in segments), encoding="utf-8")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy",
                "-movflags", "+faststart", str(out_path)], "concat")


# ---------- build ----------

def build(manifest_path, out_path=None):
    need_tool("ffmpeg")
    need_tool("ffprobe")
    ok, manifest, errors, _ = rights_gate.run(manifest_path, check_files=True)
    if not ok:
        print(f"BUILD REFUSED {manifest_path}: rights gate failed ({len(errors)} errors)")
        return 1
    vid = manifest.get("id") or Path(manifest_path).resolve().parent.name
    out_path = Path(out_path) if out_path else REPO_ROOT / "out" / f"{vid}.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    by_rank = {c["rank"]: c for c in manifest["clips"]}
    font_path = find_font_path()

    with tempfile.TemporaryDirectory(prefix="rss_build_") as tmp:
        segments = []
        for i, rank in enumerate(manifest["playback_order"]):
            clip = by_rank[rank]
            src = rights_gate.resolve_clip_path(clip["file"], manifest_path)
            start = float(clip.get("start") or 0)
            duration = float(clip.get("duration") or 0)
            if duration <= 0:
                duration = max(0.5, min(DEFAULT_CLIP_SECONDS, media_duration(src) - start))
            png = Path(tmp) / f"ov_{i:02d}.png"
            make_overlay(manifest, clip, png, font_path)
            seg = Path(tmp) / f"seg_{i:02d}.mp4"
            try:
                render_segment(src, png, start, duration, seg)
            except RuntimeError as e:
                print(f"BUILD FAIL {manifest_path}: {e}")
                return 1
            segments.append(seg)
        try:
            concat(segments, out_path, tmp)
        except RuntimeError as e:
            print(f"BUILD FAIL {manifest_path}: {e}")
            return 1

    total = media_duration(out_path)
    font_note = Path(font_path).name if font_path else "Pillow default"
    print(f"BUILD OK {out_path}: {len(segments)} clips, {total:.1f}s, {W}x{H}@{FPS}, font {font_note}")
    return 0


# ---------- selftest ----------

def selftest():
    need_tool("ffmpeg")
    need_tool("ffprobe")
    specs = [  # (size, with audio)
        ("1280x720", True), ("720x1280", False), ("1080x1080", True),
        ("640x480", False), ("1920x1080", True), ("480x854", False),
    ]
    clip_s = 2.0
    failures = []
    with tempfile.TemporaryDirectory(prefix="rss_selftest_") as tmp:
        tmp = Path(tmp)
        clips = []
        for i, (size, audio) in enumerate(specs):
            f = tmp / f"t{i + 1}.mp4"
            cmd = ["-f", "lavfi", "-i", f"testsrc2=size={size}:rate=25:duration=3"]
            if audio:
                cmd += ["-f", "lavfi", "-i", f"sine=frequency={300 + 100 * i}:sample_rate=48000:duration=3"]
            cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
            cmd += (["-c:a", "aac", "-shortest"] if audio else [])
            run_ffmpeg(cmd + [str(f)], f"test clip {i + 1}")
            clips.append({"rank": i + 1, "file": str(f), "label": f"test {i + 1}",
                          "take": f"Selftest take {i + 1}", "start": 0.5, "duration": clip_s,
                          "rights": "own", "source_url": "", "credit": "", "proof": ""})
        manifest = {
            "id": "selftest", "title_lines": ["RANKING THE BEST", "SELFTEST CLIPS"],
            "keywords": ["SELFTEST", "CLIPS"], "keyword_color": "#00C9B7",
            "playback_order": [3, 6, 2, 5, 4, 1], "clips": clips,
            "description": "Selftest #shorts", "privacy": "private", "publish_at": "",
        }
        mpath = tmp / "manifest.json"
        mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # The gate must refuse an uncleared clip.
        bad = json.loads(json.dumps(manifest))
        bad["clips"][0]["rights"] = "unknown"
        bpath = tmp / "bad.json"
        bpath.write_text(json.dumps(bad), encoding="utf-8")
        if build(bpath, tmp / "bad.mp4") == 0 or (tmp / "bad.mp4").exists():
            failures.append("gate did not refuse a clip with rights 'unknown'")

        out = tmp / "selftest.mp4"
        if build(mpath, out) != 0 or not out.is_file():
            failures.append("build failed")
        else:
            info = ffprobe_json(out, "-show_entries",
                                "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration")
            v = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
            a = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
            dur = float(info.get("format", {}).get("duration", 0))
            expected = clip_s * len(specs)
            if not v or (v[0].get("width"), v[0].get("height")) != (W, H):
                failures.append(f"video size {v[0].get('width') if v else None}x{v[0].get('height') if v else None}")
            if v and v[0].get("codec_name") != "h264":
                failures.append(f"video codec {v[0].get('codec_name')}")
            if v and v[0].get("r_frame_rate") != f"{FPS}/1":
                failures.append(f"frame rate {v[0].get('r_frame_rate')}")
            if not a or a[0].get("codec_name") != "aac":
                failures.append("no AAC audio stream")
            if abs(dur - expected) > 1.0:
                failures.append(f"duration {dur:.2f}s, expected about {expected:.1f}s")
            keep = REPO_ROOT / "out" / "selftest.mp4"
            keep.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(out, keep)
            print(f"SELFTEST probe: {v[0].get('width')}x{v[0].get('height')} {v[0].get('codec_name')} "
                  f"{v[0].get('r_frame_rate')}, audio {a[0].get('codec_name') if a else 'none'}, "
                  f"{dur:.2f}s (copy at {keep})")
    if failures:
        print(f"SELFTEST FAIL: {len(failures)} errors")
        for f in failures:
            print(f"  ERROR {f}")
        return 1
    print("SELFTEST PASS")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a 1080x1920 ranking Short from a manifest.")
    ap.add_argument("manifest", nargs="?", help="path to videos/<id>/manifest.json")
    ap.add_argument("--out", help="output MP4 (default out/<id>.mp4)")
    ap.add_argument("--selftest", action="store_true", help="render synthetic clips and verify the output")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.manifest:
        ap.error("manifest is required unless --selftest")
    return build(args.manifest, args.out)


if __name__ == "__main__":
    sys.exit(main())
