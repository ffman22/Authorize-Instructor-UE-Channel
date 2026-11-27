#!/usr/bin/env python3
"""Gemini watches and listens to an own or permitted video (or audio file) and reports if it fits its type.

Usage: gemini_review.py <file> --type short|tutorial|series|intro|reel|ad [--spec spec.json]
       [--script FILE] [--ask "extra question"] [--model NAME] [--out FILE]
Resolution, duration and loudness are measured locally; Gemini judges picture, speech, sound and pacing.
The file is sent to Google as a smaller proxy and deleted there after the answer.
Drive files must be on disk first (data/clips/ or a Drive for Desktop path).
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_client as gc  # noqa: E402

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
LONG_SECONDS = 600  # above this the proxy and media resolution drop to save tokens

TYPES = {
    "short": "Vertical tip Short, max 60 s. The result or problem is on frame 0, no greeting, core idea spoken "
             "in the first 3 s, captions of 1-2 words, no static panel over 2 s, ends with a comment CTA.",
    "series": "Series Short 'AAA UE5 Secret:', 20-35 s: spoken series hook, top banner AAA UE5 SECRET, about "
              "3 s credibility line after the hook, one fix zoomed on the node, comment CTA.",
    "tutorial": "Long tutorial, 12-16 min: payoff in engine at 0:00, short credibility reel, workshop pitch, "
                "chapters, a visual change at least every 15 s, stress test and CTA at the end.",
    "intro": "Channel introduction, about 60 s: problem hook, who the speaker is, what the channel teaches, "
             "who it is for, one clear call to action.",
    "reel": "Animation demo reel: best work first, readable motion, clear role per shot, clean edit and music.",
    "ad": "Workshop advertisement: pain, promise, proof, who it is for, one call to action.",
}

PROMPT = """You review a video for a gameplay animation and Unreal Engine channel (English audience).
Video type and requirements: {rules}
Measured locally (trust these over your own estimate): {facts}
{extra}
Watch and listen to the whole file. Report only what you can see or hear, with timestamps (m:ss);
write "not visible" or "not audible" when unsure. Write in English, concise Markdown, with:
1. Verdict: FITS / NEEDS FIXES / DOES NOT FIT, with one sentence.
2. Requirements: each one pass or fail, with the timestamp.
3. Picture: hook, framing, readability on a phone, pacing, static or confusing moments.
4. Speech: what is said (short summary), clarity, delivery, mistakes, technical claims to verify.
5. Sound: voice level, noise, clicks, music and effects balance, silences, sync with the picture.
6. Fixes in priority order, at most 7.
7. Transcript with timestamps."""


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def measure(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
             "-of", "json", str(path)])
    if r.returncode != 0:
        raise gc.GeminiError(f"ffprobe failed: {r.stderr.strip()[-300:]}")
    info = json.loads(r.stdout)
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video" and s.get("width")), None)
    facts = {"duration_s": round(float(info.get("format", {}).get("duration") or 0), 1),
             "resolution": f"{video['width']}x{video['height']}" if video else None,
             "has_audio": any(s.get("codec_type") == "audio" for s in streams)}
    if facts["has_audio"]:
        r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true",
                 "-f", "null", "-"])
        summary = r.stderr.rsplit("Summary:", 1)[-1]
        for key, pat in (("loudness_lufs", r"I:\s+(-?[\d.]+) LUFS"), ("true_peak_dbfs", r"Peak:\s+(-?[\d.]+) dBFS")):
            m = re.search(pat, summary)
            if m:
                facts[key] = float(m.group(1))
    return facts


def make_proxy(src, dst, long, audio_only):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src)]
    if audio_only:
        cmd += ["-vn", "-c:a", "aac", "-b:a", "128k"]
    else:
        side = 360 if long else 720  # short side, so node text stays readable on Shorts
        scale = f"scale='if(gt(iw,ih),-2,min({side},iw))':'if(gt(iw,ih),min({side},ih),-2)'"
        cmd += ["-vf", f"{scale},fps={2 if long else 8}", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "30", "-c:a", "aac", "-b:a", "96k"]
    r = run(cmd + [str(dst)])
    if r.returncode != 0:
        raise gc.GeminiError(f"ffmpeg proxy failed: {r.stderr.strip()[-300:]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--type", required=True, choices=sorted(TYPES))
    ap.add_argument("--spec", help="spec.json: claims are checked against it")
    ap.add_argument("--script", help="approved script: differences are listed")
    ap.add_argument("--ask", help="extra question")
    ap.add_argument("--model", default="gemini-flash-latest", help="default gemini-flash-latest")
    ap.add_argument("--out")
    a = ap.parse_args()
    src = Path(a.file)
    try:
        if gc.is_secret_file(src) or not src.is_file():
            raise gc.GeminiError(f"not a usable media file: {src}")
        facts = measure(src)
        audio_only = src.suffix.lower() in AUDIO_EXT
        long = facts["duration_s"] > LONG_SECONDS
        extra = []
        if a.spec:
            extra.append("Spec: flag anything said or shown that contradicts it or is listed in not_in_video:\n"
                         + Path(a.spec).read_text(encoding="utf-8"))
        if a.script:
            extra.append("Approved script, list the differences:\n" + Path(a.script).read_text(encoding="utf-8"))
        if audio_only:
            extra.append("This is an audio file: skip the picture section.")
        if a.ask:
            extra.append("Also answer: " + a.ask)
        prompt = PROMPT.format(rules=TYPES[a.type], facts=json.dumps(facts), extra="\n".join(extra))
        key = gc.load_key()
        with tempfile.TemporaryDirectory() as tmp:
            proxy = Path(tmp) / ("proxy.m4a" if audio_only else "proxy.mp4")
            make_proxy(src, proxy, long, audio_only)
            info = gc.upload_video(proxy, key, display=src.stem)
        try:
            part = gc.video_part(info, fps=None if audio_only or long else 4)
            if audio_only:
                part["file_data"]["mime_type"] = info.get("mimeType", "audio/mp4")
            answer = gc.generate([part, gc.text_part(prompt)], model=a.model, task=f"review_{a.type}",
                                 low_media=long, use_cache=False)
        finally:
            gc.delete_file(info["name"], key)
    except (gc.GeminiError, OSError) as e:
        gc.die(e)
    out = Path(a.out) if a.out else gc.OUT_DIR / "reviews" / f"{src.stem}-{a.type}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    header = f"# Gemini review: {src.name} ({a.type}, {a.model})\n\nMeasured: `{json.dumps(facts)}`\n\n"
    out.write_text(header + answer + "\n", encoding="utf-8")
    print(f"ok: review -> {out}")


if __name__ == "__main__":
    main()
