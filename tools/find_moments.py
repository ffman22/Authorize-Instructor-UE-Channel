#!/usr/bin/env python3
"""Find Short-sized tip moments in one of the owner's own long videos with Gemini.

Usage: find_moments.py <video> --own [--topic Lighting] [--max 5] [--make-manifests] [--force]
Steps: ffmpeg makes a small proxy (360p, 2 fps, mono audio) so the upload and the tokens stay low,
Gemini watches the proxy at low media resolution once, and the answer is cached per video
(out/gemini/moments/<name>.json; --force asks again). Candidates are checked against the real
duration; --make-manifests writes draft manifests (ready_to_publish false, rights own).
Privacy: the proxy is uploaded to Google and deleted right after. Own footage only: --own is
required; never use clips that carry third-party rights.
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
import rights_gate  # noqa: E402
from build_video import media_duration  # noqa: E402

REPO_ROOT = rights_gate.REPO_ROOT
MOMENTS_DIR = gc.OUT_DIR / "moments"
MIN_SECONDS, MAX_SECONDS = 15, 59

PROMPT = """You are the editor of an Unreal Engine animation channel. Watch this tutorial (screen recording
with the author's voice). Find up to {n} self-contained tip moments that work as a vertical Short:
one tip, a clear beginning and end, {lo}-{hi} seconds, understandable without the rest of the video.
{topic}
Return JSON only: a list of objects with exactly these keys:
 "start": "mm:ss" or "h:mm:ss" (when the tip starts, from the video clock),
 "duration": seconds as a number ({lo}-{hi}),
 "title": on-screen headline, max 55 characters, imperative and concrete, no emoji,
 "topic": one of Animation, Lighting, Materials, Niagara, Sequencer, Blueprints, Rigging, Other,
 "tip": one sentence saying what the viewer learns,
 "hook": the first spoken or shown line that grabs attention (max 12 words),
 "score": 1-10 for how well it works as a standalone Short.
Order by score, best first. Do not invent moments; return fewer if the video has fewer."""


def make_proxy(src, dst):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", "scale=-2:360,fps=2",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "34", "-c:a", "aac", "-b:a", "32k", "-ac", "1",
           str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise gc.GeminiError(f"ffmpeg proxy failed: {r.stderr.strip()[-300:]}")


def fmt_time(seconds):
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


def clean(items, total_s, n):
    """Keep valid candidates: parseable start inside the video, 15-59 s, sorted by score."""
    out = []
    for it in items if isinstance(items, list) else []:
        try:
            start = rights_gate.parse_seconds(it["start"])
            dur = float(it["duration"])
        except (KeyError, ValueError, TypeError):
            continue
        dur = min(dur, MAX_SECONDS)
        if dur < MIN_SECONDS or start < 0 or start + dur > total_s + 1:
            continue
        title = " ".join(str(it.get("title") or "").split())[:rights_gate.MAX_HEADLINE]
        if not title:
            continue
        out.append({"start": fmt_time(start), "duration": round(dur), "title": title,
                    "topic": str(it.get("topic") or "Other"), "tip": str(it.get("tip") or ""),
                    "hook": str(it.get("hook") or ""), "score": it.get("score", 0)})
    out.sort(key=lambda x: -float(x["score"] or 0))
    return out[:n]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "tip"


def write_manifests(video, cands, base_slug):
    template = json.loads((REPO_ROOT / "videos" / "_template" / "manifest.json").read_text(encoding="utf-8"))
    footer = template["description"].split("\n\n", 1)[1] if "\n\n" in template["description"] else ""
    made = []
    for i, c in enumerate(cands, 1):
        vid = f"{base_slug}-{i:02d}-{slug(c['title'])}"
        d = REPO_ROOT / "videos" / vid
        if d.exists():
            continue
        m = dict(template)
        m.update({"id": vid, "format": "short", "topic": c["topic"], "title": c["title"],
                  "source": {"drive_file_id": "", "file": str(video.relative_to(REPO_ROOT)).replace("\\", "/")
                             if video.is_relative_to(REPO_ROOT) else str(video)},
                  "start": c["start"], "duration": c["duration"], "rights": "own",
                  "description": (c["tip"] + " Full video on the channel.\n\n" + footer).strip(),
                  "tags": [], "first_comment": "", "ig_caption": "", "ready_to_publish": False,
                  "privacy": "private", "publish_at": ""})
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
        made.append(vid)
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description="Find tip moments in an own long video with Gemini.")
    ap.add_argument("video", help="own source video (data/clips/...)")
    ap.add_argument("--own", action="store_true", help="confirm the footage is the owner's own (required)")
    ap.add_argument("--topic", default="", help="focus, e.g. Lighting")
    ap.add_argument("--max", type=int, default=5, help="max candidates (default 5)")
    ap.add_argument("--make-manifests", action="store_true", help="write draft manifests under videos/")
    ap.add_argument("--force", action="store_true", help="ignore the cached answer")
    args = ap.parse_args(argv)

    video = Path(args.video).resolve()
    if not args.own:
        print("MOMENTS REFUSED: pass --own to confirm this footage is yours (it is uploaded to Google)")
        return 1
    if not video.is_file():
        print(f"MOMENTS FAIL: video not found: {video}")
        return 1
    cache = MOMENTS_DIR / f"{video.stem}.json"
    try:
        total_s = media_duration(video)
        if cache.is_file() and not args.force:
            cands = json.loads(cache.read_text(encoding="utf-8"))
            source = "cache"
        else:
            key = gc.load_key()
            with tempfile.TemporaryDirectory() as tmp:
                proxy = Path(tmp) / "proxy.mp4"
                make_proxy(video, proxy)
                info = gc.upload_video(proxy, key, display=video.stem)
            try:
                topic = f"Focus on: {args.topic}." if args.topic else ""
                prompt = PROMPT.format(n=args.max, lo=MIN_SECONDS, hi=MAX_SECONDS, topic=topic)
                text = gc.generate([gc.video_part(info), gc.text_part(prompt)], task="find_moments",
                                   json_mode=True, low_media=True, use_cache=False)
            finally:
                gc.delete_file(info["name"], key)
            cands = clean(gc.parse_json(text), total_s, args.max)
            MOMENTS_DIR.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(cands, indent=2, ensure_ascii=False), encoding="utf-8")
            source = "gemini"
    except (gc.GeminiError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
        print(f"MOMENTS FAIL {video.name}: {e}")
        return 1

    print(f"MOMENTS OK {video.name}: {len(cands)} candidates from {source}, video {fmt_time(total_s)} -> "
          f"{cache.relative_to(REPO_ROOT)}")
    for c in cands:
        print(f"  {c['start']} +{c['duration']}s  [{c['score']}] {c['title']}  | {c['hook']}")
    if args.make_manifests and cands:
        made = write_manifests(video, cands, slug(video.stem))
        print(f"  drafts: {', '.join(made) or 'none (already exist)'} (ready_to_publish false; review the cut)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
