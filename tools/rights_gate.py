#!/usr/bin/env python3
"""Rights gate: block render and upload when a manifest breaks the clip rules.

Usage: rights_gate.py <manifest.json> [--check-files]
Exit 0 only when every check passes. Prints one summary line, then one line per error.
"""
import argparse
import json
import sys
from pathlib import Path

ALLOWED_RIGHTS = {"own", "licensed", "permission", "cc"}
ALLOWED_PRIVACY = {"private", "unlisted", "public"}
MIN_CLIPS, MAX_CLIPS = 5, 7
MAX_TAKE = 40
REPO_ROOT = Path(__file__).resolve().parent.parent


def resolve_clip_path(file_value, manifest_path=None):
    """Return the clip path: absolute as is, else relative to the repo root, else to the manifest."""
    p = Path(file_value)
    if p.is_absolute():
        return p
    candidate = REPO_ROOT / p
    if candidate.exists() or manifest_path is None:
        return candidate
    alt = Path(manifest_path).resolve().parent / p
    return alt if alt.exists() else candidate


def check(manifest, check_files=False, manifest_path=None):
    """Return (errors, warnings) for a manifest dict."""
    errors, warnings = [], []
    clips = manifest.get("clips")
    if not isinstance(clips, list):
        return ["clips: missing or not a list"], warnings

    n = len(clips)
    if not MIN_CLIPS <= n <= MAX_CLIPS:
        errors.append(f"clips: {n} clips, need {MIN_CLIPS}-{MAX_CLIPS}")

    ranks = []
    for i, c in enumerate(clips):
        tag = f"clip[{i}] rank {c.get('rank', '?')}"
        rank = c.get("rank")
        if not isinstance(rank, int) or isinstance(rank, bool):
            errors.append(f"{tag}: rank must be an integer")
        else:
            ranks.append(rank)

        rights = str(c.get("rights", "")).strip()
        if rights not in ALLOWED_RIGHTS:
            errors.append(f"{tag}: rights '{rights}' not in {sorted(ALLOWED_RIGHTS)}")
        elif rights != "own":
            if not str(c.get("source_url", "")).strip() and not str(c.get("proof", "")).strip():
                errors.append(f"{tag}: rights '{rights}' needs source_url or proof")
            if rights == "cc" and not str(c.get("credit", "")).strip():
                errors.append(f"{tag}: rights 'cc' needs credit")

        take = str(c.get("take", "")).strip()
        if not take:
            errors.append(f"{tag}: take is empty")
        elif len(take) > MAX_TAKE:
            errors.append(f"{tag}: take is {len(take)} chars, max {MAX_TAKE}")

        f = str(c.get("file", "")).strip()
        if not f:
            errors.append(f"{tag}: file is empty")
        elif check_files and not resolve_clip_path(f, manifest_path).is_file():
            errors.append(f"{tag}: file not found: {f}")

    if ranks:
        if len(set(ranks)) != len(ranks):
            errors.append(f"ranks: duplicates in {sorted(ranks)}")
        if sorted(ranks) != list(range(1, n + 1)):
            errors.append(f"ranks: {sorted(ranks)} is not 1..{n}")

    order = manifest.get("playback_order")
    if not isinstance(order, list) or not order:
        errors.append("playback_order: missing or empty")
    else:
        if sorted(order) != sorted(ranks) or len(order) != n:
            errors.append(f"playback_order: {order} is not a permutation of the ranks")
        if len(order) > 1 and all(order[i] > order[i + 1] for i in range(len(order) - 1)):
            errors.append(f"playback_order: {order} is strictly descending (plain countdown)")

    hashtags = manifest.get("hashtags", [])
    if not isinstance(hashtags, list) or not all(isinstance(h, str) and h.strip() for h in hashtags):
        errors.append("hashtags: must be a list of non-empty strings")
    for key in ("ig_caption", "first_comment", "video_file", "publish_at", "description"):
        if key in manifest and not isinstance(manifest[key], str):
            errors.append(f"{key}: must be a string")

    privacy = str(manifest.get("privacy", "private") or "private").strip()
    if privacy not in ALLOWED_PRIVACY:
        errors.append(f"privacy: '{privacy}' not in {sorted(ALLOWED_PRIVACY)}")
    elif privacy == "public":
        warnings.append("privacy: 'public' publishes immediately; default is private/scheduled")

    return errors, warnings


def run(manifest_path, check_files=False, quiet=False):
    """Load and check a manifest file. Return (ok, manifest, errors, warnings)."""
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        errors = [f"manifest: cannot read {manifest_path}: {e}"]
        if not quiet:
            print(f"RIGHTS GATE FAIL {manifest_path}: 1 error")
            print(f"  ERROR {errors[0]}")
        return False, None, errors, []
    errors, warnings = check(manifest, check_files, manifest_path)
    ok = not errors
    if not quiet:
        status = "PASS" if ok else "FAIL"
        print(f"RIGHTS GATE {status} {manifest_path}: {len(manifest.get('clips') or [])} clips, "
              f"{len(errors)} errors, {len(warnings)} warnings")
        for e in errors:
            print(f"  ERROR {e}")
        for w in warnings:
            print(f"  WARN {w}")
    return ok, manifest, errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Block a video whose clips lack rights or commentary.")
    ap.add_argument("manifest", help="path to videos/<id>/manifest.json")
    ap.add_argument("--check-files", action="store_true", help="also require every clip file to exist")
    args = ap.parse_args(argv)
    ok, *_ = run(args.manifest, args.check_files)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
