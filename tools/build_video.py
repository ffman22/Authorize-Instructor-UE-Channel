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
import math
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approval  # noqa: E402
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
FADE_SECONDS = 1.0          # picture to black and sound to zero before an appended splash
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


# Animated end splash for tip Shorts: manifest "cta": {"type": "full"} when the long video is
# already public, {"type": "soon"} when it is not. A cursor clicks Subscribe, then the bell.
# Everything stays clear of the Shorts UI (bottom, right edge).
SPLASHES = {
    "full": [("WATCH THE", 112, "white"), ("FULL VIDEO", 132, "gold"), ("on my channel", 58, "white")],
    "soon": [("FULL VIDEO", 124, "white"), ("COMING SOON", 108, "gold"), ("don't miss it", 58, "white")],
}
GOLD, GREY = (255, 204, 0, 255), (72, 72, 72, 255)
PILL_OFF, PILL_ON = (241, 241, 241, 255), (50, 50, 50, 255)
PILL_TEXT, PINK, SPARK = (15, 15, 15, 255), (255, 110, 180, 255), (255, 0, 51, 255)
CLICK_SUB, CLICK_BELL = 1.0, 2.1          # seconds into the splash
SUB_AT, BELL_AT = (430, 1090), (820, 1090)


def bell_icon(on, angle):
    """YouTube-style bell, 150 px: outline when off, filled with ring marks when on."""
    k = 4
    bell = Image.new("RGBA", (150 * k, 150 * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(bell)

    def pts(seq):
        return [(x * k, y * k) for x, y in seq]
    body = pts([(35, 108), (47, 94), (47, 66), (50, 52), (58, 42), (68, 37), (75, 36), (82, 37),
                (92, 42), (100, 52), (103, 66), (103, 94), (115, 108)])
    if on:
        d.polygon(body, fill=WHITE)
    d.line(body + body[:1], fill=WHITE, width=7 * k, joint="curve")
    d.ellipse(pts([(68, 24), (82, 38)]), fill=WHITE)
    d.pieslice(pts([(62, 103), (88, 129)]), 0, 180, fill=WHITE)
    bell = bell.rotate(angle, resample=Image.BICUBIC, center=(75 * k, 32 * k))
    if on:
        d = ImageDraw.Draw(bell)
        for a, b in ((180, 225), (315, 360)):
            d.arc(pts([(12, 22), (138, 148)]), a, b, fill=GOLD, width=7 * k)
    return bell.resize((150, 150), Image.LANCZOS)


def button_font(fallback):
    bold = "C:/Windows/Fonts/segoeuib.ttf"  # lighter than the headline font, like YouTube buttons
    return bold if Path(bold).is_file() else fallback


def draw_sparks(d, t):
    """Red stars and dots that burst around the button right after the click."""
    u = (t - CLICK_SUB) / 0.55
    if not 0 <= u < 1:
        return
    sx, sy = SUB_AT
    spread, size = 1.0 + 0.18 * u, 1.0 - u * 0.7
    for n, (dx, dy) in enumerate(((-262, -50), (-205, -106), (-60, -112), (110, -104), (215, -108),
                                  (-218, 108), (-70, 104), (95, 112), (268, 40))):
        x, y = sx + dx * spread, sy + dy * spread
        if n % 2:
            r = 11 * size
            d.ellipse((x - r, y - r, x + r, y + r), fill=SPARK)
        else:
            a, b = 24 * size, 6 * size
            d.polygon([(x, y - a), (x + b, y - b), (x + a, y), (x + b, y + b),
                       (x, y + a), (x - b, y + b), (x - a, y), (x - b, y - b)], fill=SPARK)


def draw_subscribe(img, t, font_path):
    """YouTube's two states at one size: white "Subscribe", then a dark "Subscribed" pill
    with a small bell and a chevron. A pink flash marks the change."""
    d = ImageDraw.Draw(img)
    sx, sy = SUB_AT
    since = t - CLICK_SUB
    shrink = 6 if 0 <= since < 0.12 else 0
    box = (sx - 270 + shrink, sy - 75 + shrink, sx + 270 - shrink, sy + 75 - shrink)
    if since < 0:
        d.rounded_rectangle(box, radius=75, fill=PILL_OFF)
        d.text((sx, sy), "Subscribe", font=load_font(64, button_font(font_path)), fill=PILL_TEXT, anchor="mm")
        return
    flash = max(0.0, 1 - max(0.0, since - 0.15) / 0.3)
    fill = tuple(int(b + (a - b) * flash) for a, b in zip(PINK, PILL_ON))
    d.rounded_rectangle(box, radius=75 - shrink, fill=fill)
    wiggle = 22 * math.sin(since * 24) * max(0.0, 1 - since / 0.8)
    img.alpha_composite(bell_icon(False, wiggle).resize((92, 92), Image.LANCZOS), (sx - 248, sy - 46))
    d = ImageDraw.Draw(img)
    d.text((sx + 4, sy), "Subscribed", font=load_font(56, button_font(font_path)), fill=WHITE, anchor="mm")
    d.line([(sx + 188, sy - 10), (sx + 208, sy + 10), (sx + 228, sy - 10)], fill=WHITE, width=7, joint="curve")
    draw_sparks(d, t)


def draw_cursor(d, x, y, scale):
    shape = [(0, 0), (0, 74), (18, 58), (31, 88), (47, 81), (34, 52), (58, 52)]
    pts = [(x + px * scale, y + py * scale) for px, py in shape]
    d.polygon(pts, fill=WHITE)
    d.line(pts + pts[:1], fill=BLACK, width=5, joint="curve")


def cursor_at(t, path=None):
    """Eased path; by default from the lower right to Subscribe, then to the bell."""
    path = path or [(0.25, (780, 1500)), (CLICK_SUB - 0.1, (500, 1100)), (CLICK_SUB + 0.3, (500, 1100)),
            (CLICK_BELL - 0.1, (822, 1100)), (CLICK_BELL + 0.35, (822, 1100)),
            (CLICK_BELL + 0.8, (925, 1180))]
    if t <= path[0][0]:
        return path[0][1]
    for (t0, a), (t1, b) in zip(path, path[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            u = u * u * (3 - 2 * u)
            return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
    return path[-1][1]


# Instagram and TikTok: tap Follow, then the channel keyword types itself into a comment box.
# Keyword: manifest "cta.keyword". UNREAL only on Unreal footage (the default), GAMEANIMATION on other
# engines (AC Shadows is Anvil); UNREALZERO is only for workshop ads.
KEYWORD = "UNREAL"


def more_line(keyword):
    return "for more Unreal content" if keyword == "UNREAL" else "for more game animation content"


SOCIAL_SPLASHES = {
    "social_full": [("FULL VIDEO", 128, "white"), ("ON YOUTUBE", 116, "gold"), ("@Carlo-Animator", 58, "white")],
    "social_soon": [("FULL VIDEO SOON", 100, "white"), ("ON YOUTUBE", 116, "gold"), ("@Carlo-Animator", 58, "white")],
    # workshop ads, all platforms: no Follow step, keyword UNREALZERO
    "workshop": [("UNREAL FOR", 124, "white"), ("ANIMATORS", 124, "gold"), ("workshop at iAnimate", 62, "white")],
}
WORKSHOP_KEYWORD = "UNREALZERO"
FOLLOW_AT, SEND_AT = (540, 960), (850, 1210)
BLUE = (0, 122, 255, 255)
TYPE_FROM, CLICK_SEND = 1.5, 2.5


def social_frame(kind, t, font_path, keyword=KEYWORD):
    img = Image.new("RGBA", (W, H), (0, 0, 0, int(205 * min(1.0, t / 0.25))))
    d = ImageDraw.Draw(img)
    y = 480
    for text, size, style in SOCIAL_SPLASHES[kind]:
        font = load_font(size, font_path)
        d.text(((W - text_w(d, text, font, 4)) // 2, y), text, font=font,
               fill=GOLD if style == "gold" else WHITE, stroke_width=4, stroke_fill=BLACK)
        y += int(size * 1.3)
    workshop = kind == "workshop"
    type_from, click_send = (0.8, 2.2) if workshop else (TYPE_FROM, CLICK_SEND)
    if workshop:
        keyword = WORKSHOP_KEYWORD
    bold = button_font(font_path)
    fx, fy = FOLLOW_AT
    followed = t >= CLICK_SUB
    shrink = 6 if 0 <= t - CLICK_SUB < 0.12 else 0
    if not workshop:
        d.rounded_rectangle((fx - 270 + shrink, fy - 70 + shrink, fx + 270 - shrink, fy + 70 - shrink),
                            radius=34, fill=PILL_ON if followed else BLUE)
        d.text((fx, fy), "Following" if followed else "Follow", font=load_font(64, bold), fill=WHITE, anchor="mm")

    # comment box: x stays left of the platform buttons on the right edge
    sent = t >= click_send
    # long keywords shrink so the line stays clear of the platform buttons on the right
    size = 70
    while size > 40 and text_w(d, "COMMENT " + keyword, load_font(size, font_path), 4) > 800:
        size -= 2
    d.text((520, 1100), "COMMENT " + keyword, font=load_font(size, font_path),
           fill=GOLD if sent else WHITE, anchor="mm", stroke_width=4, stroke_fill=BLACK)
    d.rounded_rectangle((130, 1150, 920, 1270), radius=60, fill=PILL_OFF)
    step = type_step(keyword, type_from, click_send)
    letters = max(0, min(len(keyword), int((t - type_from) / step) + 1)) if t >= type_from else 0
    d.text((190, 1210), keyword[:letters] if letters else "Add a comment...", font=load_font(52, bold),
           fill=PILL_TEXT if letters else (120, 120, 120, 255), anchor="lm")
    sx, sy = SEND_AT
    r = 46 - (6 if 0 <= t - click_send < 0.12 else 0)
    d.ellipse((sx - r, sy - r, sx + r, sy + r), fill=BLUE)
    d.line([(sx, sy + 22), (sx, sy - 22)], fill=WHITE, width=9)
    d.line([(sx - 19, sy - 3), (sx, sy - 22), (sx + 19, sy - 3)], fill=WHITE, width=9, joint="curve")
    d.text((520, 1350), "for more information" if workshop else "and I'll send you the link", font=load_font(46, font_path),
           fill=WHITE, anchor="mm", stroke_width=3, stroke_fill=BLACK)

    start = [(1.4, (800, 1450))] if workshop else [(0.25, (820, 1450)), (CLICK_SUB - 0.1, (610, 975)),
                                                 (CLICK_SUB + 0.4, (610, 975))]
    path = start + [(click_send - 0.1, (852, 1215)), (click_send + 0.35, (852, 1215)),
                    (click_send + 0.8, (900, 1330))]
    clicks = (click_send,) if workshop else (CLICK_SUB, click_send)
    draw_cursor(d, *cursor_at(t, path), 1.05 if any(0 <= t - c < 0.12 for c in clicks) else 1.25)
    return img


def splash_frame(kind, t, font_path, keyword=KEYWORD):
    """Transparent 1080x1920 frame of the splash, t seconds after it starts."""
    if kind in SOCIAL_SPLASHES:
        return social_frame(kind, t, font_path, keyword)
    img = Image.new("RGBA", (W, H), (0, 0, 0, int(205 * min(1.0, t / 0.25))))
    d = ImageDraw.Draw(img)
    y = 560
    for text, size, style in SPLASHES[kind]:
        font = load_font(size, font_path)
        d.text(((W - text_w(d, text, font, 4)) // 2, y), text, font=font,
               fill=GOLD if style == "gold" else WHITE, stroke_width=4, stroke_fill=BLACK)
        y += int(size * 1.3)

    subbed, ringing = t >= CLICK_SUB, t >= CLICK_BELL
    draw_subscribe(img, t, font_path)
    d = ImageDraw.Draw(img)

    bx, by = BELL_AT
    r = 85 - (8 if 0 <= t - CLICK_BELL < 0.12 else 0)
    d.ellipse((bx - r, by - r, bx + r, by + r), fill=GREY)
    since = t - CLICK_BELL
    angle = 24 * math.sin(since * 26) * max(0.0, 1 - since / 0.9) if ringing else 0
    img.alpha_composite(bell_icon(ringing, angle), (bx - 75, by - 75))

    d = ImageDraw.Draw(img)
    d.text((W // 2, 1285), "TURN ON NOTIFICATIONS", font=load_font(66, font_path),
           fill=GOLD if ringing else WHITE, anchor="mm", stroke_width=4, stroke_fill=BLACK)
    d.text((W // 2, 1370), more_line(keyword), font=load_font(46, font_path),
           fill=WHITE, anchor="mm", stroke_width=3, stroke_fill=BLACK)
    for click, (cx, cy) in ((CLICK_BELL, (822, 1100)),):
        if 0 <= t - click < 0.35:
            rr = 20 + (t - click) * 260
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=GOLD, width=8)
    pressed = any(0 <= t - c < 0.12 for c in (CLICK_SUB, CLICK_BELL))
    draw_cursor(d, *cursor_at(t), 1.05 if pressed else 1.25)
    return img


def make_splash_frames(kind, folder, font_path, seconds, keyword=KEYWORD):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for n in range(int(seconds * FPS) + 1):
        splash_frame(kind, n / FPS, font_path, keyword).save(folder / f"{n:04d}.png", compress_level=1)
    return folder / "%04d.png"


# ---------- splash sounds (synthesized here, so there is nothing to license) ----------

def type_step(keyword, type_from, click_send):
    """Seconds per typed letter: 0.1, faster when a long keyword must finish before Send."""
    return min(0.1, (click_send - type_from - 0.15) / len(keyword))


def splash_events(kind, keyword=KEYWORD):
    """(time, sound) pairs matching the clicks and typing of each splash."""
    if kind in SPLASHES:
        return [(CLICK_SUB, "click"), (CLICK_SUB + 0.05, "pop"), (CLICK_BELL, "click"), (CLICK_BELL + 0.05, "bell")]
    workshop = kind == "workshop"
    keyword = WORKSHOP_KEYWORD if workshop else keyword
    type_from, click_send = (0.8, 2.2) if workshop else (TYPE_FROM, CLICK_SEND)
    events = [] if workshop else [(CLICK_SUB, "click"), (CLICK_SUB + 0.05, "pop")]
    step = type_step(keyword, type_from, click_send)
    events += [(type_from + step * n, "key") for n in range(len(keyword))]
    return events + [(click_send, "click"), (click_send + 0.05, "bell")]


def sound(name):
    def t(seconds):
        return np.arange(int(AR * seconds)) / AR
    noise = np.random.default_rng(7)
    if name in ("click", "key"):
        x = t(0.05)
        tone = np.sin(2 * np.pi * (1800 if name == "click" else 3200) * x)
        level = 0.55 if name == "click" else 0.22
        return level * (0.6 * tone + 0.4 * noise.uniform(-1, 1, x.size)) * np.exp(-x * 120)
    if name == "pop":
        x = t(0.18)
        return 0.45 * np.sin(2 * np.pi * (450 * x + 2200 * x * x)) * np.exp(-x * 18)
    x = t(0.9)  # bell
    partials = ((1318, 1.0, 5), (2637, 0.45, 7), (3951, 0.2, 10))
    return 0.33 * sum(a * np.sin(2 * np.pi * f * x) * np.exp(-x * d) for f, a, d in partials)


def make_splash_audio(kind, path, seconds, keyword=KEYWORD):
    track = np.zeros(int(AR * seconds))
    for at, name in splash_events(kind, keyword):
        i = int(AR * at)
        clip = sound(name)[:max(0, track.size - i)]
        track[i:i + clip.size] += clip
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(AR)
        w.writeframes((np.clip(track, -1, 1) * 32767).astype("<i2").tobytes())


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


def render_cut(src, overlay_png, start, duration, out_path, cta_png=None, hold=0.0, sfx=None,
               fade_s=FADE_SECONDS):
    """One pass: cut, blurred-background 9:16 fit, headline overlay, optional end CTA, source audio (or silence)."""
    """hold > 0 fades picture and sound out at the end of the cut, then appends the splash on black."""
    audio = has_audio(src)
    total = duration + hold
    cmd = ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(src),
           "-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}", "-i", str(overlay_png)]
    animated = bool(cta_png) and "%" in Path(cta_png).name  # splash frame sequence
    if animated:
        cmd += ["-framerate", str(FPS), "-i", str(cta_png)]
    elif cta_png:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}", "-i", str(cta_png)]
    if not audio:
        cmd += ["-f", "lavfi", "-t", f"{duration:.3f}", "-i", f"anullsrc=r={AR}:cl=stereo"]
    audio_idx = 3 if cta_png else 2
    t0 = duration if hold else max(0.0, duration - CTA_SECONDS)
    fade_at = max(0.0, duration - fade_s)
    sfx_idx = audio_idx + (0 if audio else 1)
    if sfx:
        cmd += ["-i", str(sfx)]
    if cta_png:
        shift = f"[2:v]setpts=PTS+{t0:.3f}/TB[cta];" if animated else "[2:v]null[cta];"
        # black one frame or two before the cut ends, so the cloned frames behind the splash are black
        out_fade = f",fade=t=out:st={fade_at:.3f}:d={max(0.1, fade_s - 0.1):.3f}" if hold else ""
        tail = (f"[base][1:v]overlay=0:0:format=auto{out_fade}[hl];{shift}"
                f"[hl][cta]overlay=0:0:format=auto:eof_action=repeat:enable='gte(t,{t0:.2f})',"
                "format=yuv420p,setsar=1[v]")
    else:
        tail = "[base][1:v]overlay=0:0:format=auto,format=yuv420p,setsar=1[v]"
    vf = (
        f"[0:v]fps={FPS},setsar=1,split=2[s1][s2];"
        f"[s1]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:3,"
        f"eq=brightness=-0.08[bg];"
        f"[s2]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"scale=trunc(iw/2)*2:trunc(ih/2)*2[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,tpad=stop_mode=clone:stop_duration={hold:.3f}[base];"
        + tail
    )
    a_in = "0:a:0" if audio else f"{audio_idx}:a"
    stereo = f"aresample={AR},aformat=sample_fmts=fltp:channel_layouts=stereo"
    fade = f",afade=t=out:st={fade_at:.3f}:d={duration - fade_at:.3f}" if hold else ""
    if sfx:
        af = (f";[{a_in}]{stereo}{fade},apad[voice];"
              f"[{sfx_idx}:a]{stereo},adelay={int(t0 * 1000)}:all=1[fx];"
              "[voice][fx]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
    else:
        af = f";[{a_in}]{stereo}{fade},apad[a]"
    cmd += ["-filter_complex", vf + af, "-map", "[v]", "-map", "[a]",
            "-t", f"{total:.3f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-c:a", "aac", "-b:a", "160k", "-ar", str(AR), "-ac", str(AC),
            "-movflags", "+faststart", str(out_path)]
    run_ffmpeg(cmd, f"render {Path(src).name}")
    return audio


# ---------- build ----------

def build(manifest_path, out_path=None, splash=None):
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
    spec = approval.spec_errors(manifest_path)
    if spec:
        print(f"BUILD REFUSED {manifest_path}: {spec[0]}")
        return 1
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
        if splash:
            cta = {**(cta if isinstance(cta, dict) else {}), "type": splash}
        cta_png, sfx_wav, hold = None, None, 0.0
        kind = cta.get("type") if isinstance(cta, dict) else None
        if kind and kind not in {*SPLASHES, *SOCIAL_SPLASHES}:
            print(f"BUILD FAIL {manifest_path}: cta.type must be one of {', '.join([*SPLASHES, *SOCIAL_SPLASHES])}")
            return 1
        if kind:
            cta_png = make_splash_frames(kind, Path(tmp) / "splash", font_path, CTA_SECONDS,
                                         cta.get("keyword") or KEYWORD)
            sfx_wav = Path(tmp) / "splash.wav"
            make_splash_audio(kind, sfx_wav, CTA_SECONDS, cta.get("keyword") or KEYWORD)
            # an animated splash never covers the cut: fade to black and silence, then the splash
            hold = CTA_SECONDS
            if duration + hold > 60:
                print(f"BUILD FAIL {manifest_path}: cut plus splash is {duration + hold:g}s, over 60 s")
                return 1
        elif cta:
            cta = {**CTA_DEFAULT, **(cta if isinstance(cta, dict) else {})}
            cta_png = Path(tmp) / "cta.png"
            make_cta_overlay(cta, cta_png, font_path)
        try:
            fade_s = float(cta.get("fade") or FADE_SECONDS) if isinstance(cta, dict) else FADE_SECONDS
            audio = render_cut(src, png, start, duration, out_path, cta_png, hold, sfx_wav, fade_s)
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
    specs = [("1280x720", True), ("1920x1080", False), ("720x1280", True), ("1080x1080", False)]
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

        # Renderer: one cut per source shape; the first is the minimum-HD 16:9 case.
        for i, (size, audio) in enumerate(specs):
            f = tmp / f"src{i}.mp4"
            cmd = ["-f", "lavfi", "-i", f"testsrc2=size={size}:rate=25:duration=8"]
            if audio:
                cmd += ["-f", "lavfi", "-i", f"sine=frequency={300 + 100 * i}:sample_rate=48000:duration=8"]
            cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
            cmd += (["-c:a", "aac", "-shortest"] if audio else [])
            run_ffmpeg(cmd + [str(f)], f"test source {size}")
            m = dict(base, id=f"selftest{i}", source={"drive_file_id": "", "file": str(f)})
            if i < 2:  # appended splash: source with audio, then silent source
                m["cta"] = {"type": "soon"} if i == 0 else {"type": "workshop"}
            mpath = tmp / f"m{i}.json"
            mpath.write_text(json.dumps(m, indent=2), encoding="utf-8")
            (mpath.parent / "spec.json").write_text(json.dumps({k: "selftest" for k in approval.SPEC_FIELDS}), encoding="utf-8")
            out = tmp / f"out{i}.mp4"
            if build(mpath, out) != 0 or not out.is_file():
                failures.append(f"build failed for {size}")
                continue
            failures += [f"{size}: {x}" for x in probe_ok(out, cut_s + (CTA_SECONDS if i < 2 else 0))]
            if i == 0 and keep:
                Path(keep).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(out, keep)

        low = tmp / "low.mp4"
        run_ffmpeg(["-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25:duration=2", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(low)], "low-res source")
        errs, _ = rights_gate.check(dict(base, source={"file": str(low)}))
        if not any("below HD" in e for e in errs):
            failures.append("gate accepted a 360p source")

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
    ap.add_argument("--splash", help="override cta.type, e.g. social_soon for the Instagram/TikTok copy")
    ap.add_argument("--selftest", action="store_true", help="check the gate, render synthetic sources, verify output")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest(args.out)
    if not args.manifest:
        ap.error("manifest is required unless --selftest")
    return build(args.manifest, args.out, args.splash)


if __name__ == "__main__":
    sys.exit(main())
