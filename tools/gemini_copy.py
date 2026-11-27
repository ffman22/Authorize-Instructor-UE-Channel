#!/usr/bin/env python3
"""Write the copy for every platform from one manifest with Gemini (one call, cached).

Usage: gemini_copy.py <manifest.json> [--transcript FILE] [--apply] [--force]
One request returns YouTube (description, tags, first comment), Instagram caption, TikTok caption,
Threads post and YouTube Community post. The draft is saved to videos/<id>/copy.json.
--apply merges it into the manifest (never the title, rights, privacy or ready_to_publish), keeps
the workshop footer from the existing description, and writes only if the rights gate still passes.
Review before setting ready_to_publish. The text is sent to Google; no secrets in manifests.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_client as gc  # noqa: E402
import rights_gate  # noqa: E402
from publish_common import video_id  # noqa: E402

FOOTER_MARK = "Learn Unreal Engine animation systems with me:"
LIMITS = {"instagram": 2200, "tiktok": 2200, "threads": 500, "community": 1000, "first_comment": 300}

PROMPT = """You write social copy for Carlo, a professional game animator (Lead Animator) who teaches Unreal
Engine animation. Voice: direct, practical, first person, no hype, no emoji spam (max 1 per post), no
clickbait claims. English. Never invent features or results; use only the facts below.

Video: {fmt} | topic: {topic} | title: {title}
Facts (description and notes): {facts}
{transcript}
Return JSON only, with exactly these keys:
 "description": the YouTube description body (2-4 sentences, keywords early, NO links, NO hashtags),
 "hashtags": 3-5 hashtags with #, first three are the most relevant (e.g. #unrealengine, #ue5),
 "tags": 5-8 YouTube search tags without #, specific to THIS video (phrases viewers search); no generic
   niche or viral tags, those come from tools/tags_base.json,
 "first_comment": a question that invites replies (max 200 chars),
 "instagram": caption: hook line, one sentence of value, a question, then exactly 5 hashtags (2 about this video, 2 niche, 1 broad); no links,
 "tiktok": caption max 150 chars before the hashtags, then 3-5 hashtags; no links,
 "threads": post max 400 chars, conversational, ends with a question, at most one hashtag,
 "community": YouTube Community post max 600 chars, teases the video and asks a poll-style question."""


def split_footer(description):
    """Return (body, footer) where footer starts at the workshop block."""
    i = description.find(FOOTER_MARK)
    return (description[:i].strip(), description[i:].strip()) if i >= 0 else (description.strip(), "")


def clean_hashtags(items, limit=5):
    out = []
    for h in items if isinstance(items, list) else []:
        h = "#" + str(h).strip().lstrip("#").replace(" ", "")
        if len(h) > 1 and h.lower() not in [x.lower() for x in out]:
            out.append(h)
    return out[:limit]


def validate(copy):
    """Return (cleaned dict, errors). Trims nothing silently: over-limit text is an error."""
    errors = []
    out = {}
    for key in ("description", "first_comment", "instagram", "tiktok", "threads", "community"):
        val = str(copy.get(key) or "").strip()
        if not val:
            errors.append(f"{key}: empty")
        out[key] = val
    for key, limit in LIMITS.items():
        if len(out.get(key, "")) > limit:
            errors.append(f"{key}: {len(out[key])} chars, max {limit}")
    if "<" in out["description"] or ">" in out["description"]:
        errors.append("description: contains '<' or '>'")
    out["hashtags"] = clean_hashtags(copy.get("hashtags"))
    tags = [str(t).strip().lstrip("#") for t in copy.get("tags") or [] if str(t).strip()]
    out["tags"] = tags[:15]
    if len(out["hashtags"]) < 3:
        errors.append("hashtags: fewer than 3")
    if len(out["tags"]) < 5:
        errors.append("tags: fewer than 5")
    return out, errors


def apply_copy(manifest, copy):
    m = dict(manifest)
    _, footer = split_footer(str(manifest.get("description") or ""))
    m["description"] = copy["description"] + ("\n\n" + footer if footer else "")
    m["hashtags"] = copy["hashtags"]
    m["tags"] = copy["tags"]
    m["first_comment"] = copy["first_comment"]
    m["ig_caption"] = copy["instagram"]
    m["tiktok_caption"] = copy["tiktok"]
    m["threads_post"] = copy["threads"]
    m["community_post"] = copy["community"]
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate per-platform copy for a manifest with Gemini.")
    ap.add_argument("manifest", help="path to videos/<id>/manifest.json")
    ap.add_argument("--transcript", help="text file with the transcript or chapter notes (optional)")
    ap.add_argument("--apply", action="store_true", help="merge the copy into the manifest (gate must pass)")
    ap.add_argument("--force", action="store_true", help="ignore the cached answer")
    args = ap.parse_args(argv)

    path = Path(args.manifest)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"COPY FAIL {args.manifest}: {e}")
        return 1
    vid = video_id(manifest, path)
    body, _ = split_footer(str(manifest.get("description") or ""))
    try:
        transcript = ""
        if args.transcript:
            transcript = "Transcript or notes:\n" + gc.file_parts([args.transcript])[0]["text"]
        prompt = PROMPT.format(fmt=manifest.get("format", "short"), topic=manifest.get("topic", ""),
                               title=manifest.get("title", ""), facts=body or "(none)", transcript=transcript)
        data = gc.generate_json([gc.text_part(prompt)], task="copy", use_cache=not args.force)
        copy, errors = validate(data)
    except gc.GeminiError as e:
        print(f"COPY FAIL {vid}: {e}")
        return 1

    out = path.parent / "copy.json"
    out.write_text(json.dumps(copy, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"COPY {'FAIL' if errors else 'OK'} {vid}: {len(copy['hashtags'])} hashtags, {len(copy['tags'])} tags -> {out}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        return 1
    if args.apply:
        merged = apply_copy(manifest, copy)
        gate_errors, _ = rights_gate.check(merged, manifest_path=path)
        if gate_errors:
            print("  NOT APPLIED: rights gate would fail: " + "; ".join(gate_errors))
            return 1
        path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  applied to {path} (review it, then set ready_to_publish)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
