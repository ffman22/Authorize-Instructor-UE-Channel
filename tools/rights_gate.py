#!/usr/bin/env python3
"""Rights gate: block render and upload when a tip manifest breaks the rules.

Usage: rights_gate.py <manifest.json> [--check-files]
A manifest is one cut from one source video (format "short": <= 60 s, 9:16 render)
or a whole long video (format "long": uploaded as is from video_file).
Exit 0 only when every check passes. Prints one summary line, then one line per error.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ALLOWED_RIGHTS = {"own", "licensed", "permission", "cc"}
ALLOWED_PRIVACY = {"private", "unlisted", "public"}
ALLOWED_FORMATS = {"short", "long"}
MAX_SHORT_SECONDS = 60.0
MAX_HEADLINE = 60   # on-screen headline of a Short
MAX_YT_TITLE = 100  # YouTube title limit (long videos)
REPO_ROOT = Path(__file__).resolve().parent.parent
TIME_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{1,2}(?:\.\d+)?)$")


def resolve_clip_path(file_value, manifest_path=None):
    """Return the file path: absolute as is, else relative to the repo root, else to the manifest."""
    p = Path(file_value)
    if p.is_absolute():
        return p
    candidate = REPO_ROOT / p
    if candidate.exists() or manifest_path is None:
        return candidate
    alt = Path(manifest_path).resolve().parent / p
    return alt if alt.exists() else candidate


def parse_seconds(value):
    """Seconds from a number or '[hh:]mm:ss[.ms]' string; raise ValueError otherwise."""
    if isinstance(value, bool):
        raise ValueError(f"{value!r} is not a time")
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    m = TIME_RE.match(s)
    if m:
        h, mnt, sec = m.groups()
        return int(h or 0) * 3600 + int(mnt) * 60 + float(sec)
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"'{value}' is not seconds or [hh:]mm:ss") from None


def manifest_format(manifest):
    return str(manifest.get("format") or "short").strip().lower()


def source_file(manifest):
    src = manifest.get("source")
    return str(src.get("file") or "").strip() if isinstance(src, dict) else ""


WORKSHOP_URL = "https://ianimate.net/workshops/unreal-for-animators"


def check(manifest, check_files=False, manifest_path=None):
    """Return (errors, warnings) for a manifest dict."""
    errors, warnings = [], []
    fmt = manifest_format(manifest)
    if fmt not in ALLOWED_FORMATS:
        errors.append(f"format: '{fmt}' not in {sorted(ALLOWED_FORMATS)}")

    if not str(manifest.get("id") or "").strip():
        errors.append("id: empty")

    title = manifest.get("title")
    max_title = MAX_YT_TITLE if fmt == "long" else MAX_HEADLINE
    if not isinstance(title, str) or not title.strip():
        errors.append("title: missing or empty")
    elif len(title.strip()) > max_title:
        errors.append(f"title: {len(title.strip())} chars, max {max_title}")

    # Source: one video of the owner (or cleared), on Drive and/or local under data/clips/.
    src = manifest.get("source")
    if not isinstance(src, dict):
        errors.append("source: missing or not an object {drive_file_id, file}")
        src = {}
    drive_id = str(src.get("drive_file_id") or "").strip()
    local = source_file(manifest)
    if not drive_id and not local:
        errors.append("source: needs drive_file_id or file")
    if check_files:
        if fmt == "short" and not local:
            errors.append("source.file: a local file is needed to render (download the Drive file to data/clips/)")
        elif local and not resolve_clip_path(local, manifest_path).is_file():
            errors.append(f"source.file: not found: {local}")

    # Rights: the gate itself.
    rights = str(manifest.get("rights", "")).strip()
    if rights not in ALLOWED_RIGHTS:
        errors.append(f"rights: '{rights}' not in {sorted(ALLOWED_RIGHTS)}")
    elif rights != "own":
        if not str(manifest.get("proof", "")).strip():
            errors.append(f"rights: '{rights}' needs proof")
        if rights == "cc" and not str(manifest.get("credit", "")).strip():
            errors.append("rights: 'cc' needs credit")

    # Cut: start and duration in the source.
    try:
        start = parse_seconds(manifest.get("start", 0))
        if start < 0:
            errors.append("start: negative")
    except ValueError as e:
        errors.append(f"start: {e}")
    dur_raw = manifest.get("duration")
    if fmt == "short":
        try:
            dur = parse_seconds(dur_raw)
            if dur <= 0:
                errors.append("duration: must be > 0")
            elif dur > MAX_SHORT_SECONDS:
                errors.append(f"duration: {dur:g}s, max {MAX_SHORT_SECONDS:g}s for a Short")
        except ValueError as e:
            errors.append(f"duration: {e}")
    elif fmt == "long" and not str(manifest.get("video_file") or "").strip():
        warnings.append("video_file: empty for a long video; upload falls back to out/<id>.mp4")

    # Copy fields.
    hashtags = manifest.get("hashtags", [])
    if not isinstance(hashtags, list) or not all(isinstance(h, str) and h.strip() for h in hashtags):
        errors.append("hashtags: must be a list of non-empty strings")
    tags = manifest.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(t, str) and t.strip() for t in tags):
        errors.append("tags: must be a list of non-empty strings")
    for key in ("ig_caption", "tiktok_caption", "threads_post", "community_post", "first_comment", "video_file", "publish_at", "description", "topic"):
        if key in manifest and not isinstance(manifest[key], str):
            errors.append(f"{key}: must be a string")

    if "ready_to_publish" in manifest and not isinstance(manifest["ready_to_publish"], bool):
        errors.append("ready_to_publish: must be true or false")

    # Every video points to the workshop: link in the description, or a burned-in cta card.
    if WORKSHOP_URL not in str(manifest.get("description") or "") and not manifest.get("cta"):
        errors.append(f"description: must include the workshop link {WORKSHOP_URL} (or set cta)")

    # Privacy: private, or scheduled with publish_at.
    privacy = str(manifest.get("privacy", "private") or "private").strip()
    publish_at = str(manifest.get("publish_at") or "").strip()
    if privacy not in ALLOWED_PRIVACY:
        errors.append(f"privacy: '{privacy}' not in {sorted(ALLOWED_PRIVACY)}")
    elif privacy != "private" and not publish_at:
        errors.append(f"privacy: '{privacy}' without publish_at; use private or schedule with publish_at")
    if publish_at:
        try:
            t = dt.datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
            if t.tzinfo is None:
                errors.append("publish_at: needs a time zone offset (e.g. 2026-11-23T17:00:00Z)")
        except ValueError:
            errors.append(f"publish_at: '{publish_at}' is not ISO 8601")

    return errors, warnings


def run(manifest_path, check_files=False, quiet=False):
    """Load and check a manifest file. Return (ok, manifest, errors, warnings)."""
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("top level is not an object")
    except (OSError, ValueError) as e:
        errors = [f"manifest: cannot read {manifest_path}: {e}"]
        if not quiet:
            print(f"RIGHTS GATE FAIL {manifest_path}: 1 error")
            print(f"  ERROR {errors[0]}")
        return False, None, errors, []
    errors, warnings = check(manifest, check_files, manifest_path)
    ok = not errors
    if not quiet:
        status = "PASS" if ok else "FAIL"
        print(f"RIGHTS GATE {status} {manifest_path}: {manifest_format(manifest)}, "
              f"rights {manifest.get('rights', '?')}, {len(errors)} errors, {len(warnings)} warnings")
        for e in errors:
            print(f"  ERROR {e}")
        for w in warnings:
            print(f"  WARN {w}")
    return ok, manifest, errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Block a tip video whose source lacks rights or whose cut breaks the rules.")
    ap.add_argument("manifest", help="path to videos/<id>/manifest.json")
    ap.add_argument("--check-files", action="store_true", help="also require the local source file to exist")
    args = ap.parse_args(argv)
    ok, *_ = run(args.manifest, args.check_files)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
