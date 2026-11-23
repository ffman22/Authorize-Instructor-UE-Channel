#!/usr/bin/env python3
"""Publish a Short as an Instagram Reel through the Instagram Graph API.

Usage: instagram_publish.py <manifest.json> --video-url https://... [--video FILE] [--dry-run]
The Graph API fetches the video from a public HTTPS URL; --video only checks the local copy
(manifest "video_file" or out/<id>.mp4, e.g. a RankReel export) before you host it.
Credentials: IG_USER_ID and IG_ACCESS_TOKEN from the environment or .env (never printed).
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rights_gate  # noqa: E402
from publish_common import (norm_hashtags, resolve_video, video_id, with_hashtags,  # noqa: E402
                            write_published)

GRAPH_VERSION = "v24.0"
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
REPO_ROOT = rights_gate.REPO_ROOT
POLL_TIMEOUT_S, POLL_EVERY_S = 300, 10
MAX_CAPTION, MAX_HASHTAGS = 2200, 30


def load_env():
    env = {}
    f = REPO_ROOT / ".env"
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().removeprefix("export ").strip()
            env[k] = v.strip().strip('"').strip("'")
    return {k: os.environ.get(k) or env.get(k, "") for k in ("IG_USER_ID", "IG_ACCESS_TOKEN")}


def build_caption(manifest):
    cap = str(manifest.get("ig_caption") or "").strip()
    return cap or with_hashtags(manifest.get("description", ""), norm_hashtags(manifest))


class GraphError(Exception):
    pass


def call(method, path, token, params=None):
    """Call the Graph API. The token goes in the POST body (or the GET query) and is never printed."""
    params = dict(params or {})
    params["access_token"] = token
    data = urllib.parse.urlencode(params)
    url = f"{GRAPH}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data}", method="GET")
    else:
        req = urllib.request.Request(url, data=data.encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", {})
            msg = f"HTTP {e.code} {err.get('type', '')} code {err.get('code', '')}: {err.get('message', '')}"
        except (ValueError, AttributeError):
            msg = f"HTTP {e.code}"
        raise GraphError(msg.replace(token, "***")) from None
    except urllib.error.URLError as e:
        raise GraphError(f"network: {e.reason}".replace(token, "***")) from None


def publish(user_id, token, video_url, caption):
    """Return (media_id, container_id)."""
    c = call("POST", f"{user_id}/media", token,
             {"media_type": "REELS", "video_url": video_url, "caption": caption, "share_to_feed": "true"})
    container = c.get("id")
    if not container:
        raise GraphError(f"no container id in response: {list(c)}")
    deadline = time.monotonic() + POLL_TIMEOUT_S
    while True:
        s = call("GET", container, token, {"fields": "status_code,status"})
        code = s.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise GraphError(f"container {container} {code}: {s.get('status', '')}")
        if time.monotonic() > deadline:
            raise GraphError(f"container {container} not FINISHED after {POLL_TIMEOUT_S}s (last {code})")
        time.sleep(POLL_EVERY_S)
    p = call("POST", f"{user_id}/media_publish", token, {"creation_id": container})
    if not p.get("id"):
        raise GraphError(f"no media id in publish response: {list(p)}")
    return p["id"], container


def main(argv=None):
    ap = argparse.ArgumentParser(description="Publish a Reel through the Instagram Graph API.")
    ap.add_argument("manifest", help="path to videos/<id>/manifest.json")
    ap.add_argument("--video-url", required=True, help="public HTTPS URL of the MP4")
    ap.add_argument("--video", help="local MP4 to check (default: manifest video_file, else out/<id>.mp4)")
    ap.add_argument("--dry-run", action="store_true", help="validate everything, no network")
    args = ap.parse_args(argv)

    ok, manifest, _, _ = rights_gate.run(args.manifest)
    if not ok:
        print(f"INSTAGRAM REFUSED {args.manifest}: rights gate failed")
        return 1
    errors, warnings = [], []
    caption = build_caption(manifest)
    first_comment = str(manifest.get("first_comment") or "").strip()
    if len(caption) > MAX_CAPTION:
        errors.append(f"caption: {len(caption)} chars, max {MAX_CAPTION}")
    if caption.count("#") > MAX_HASHTAGS:
        errors.append(f"caption: more than {MAX_HASHTAGS} hashtags")
    u = urllib.parse.urlparse(args.video_url)
    if u.scheme != "https" or not u.netloc:
        errors.append("video-url: must be a public https:// URL")
    local = resolve_video(manifest, args.manifest, args.video)
    if not local.is_file():
        warnings.append(f"local video not found: {local} (the URL must still serve the final MP4)")
    creds = load_env()
    missing = [k for k, v in creds.items() if not v]
    if missing:
        (warnings if args.dry_run else errors).append(f"missing {', '.join(missing)} in env or .env")
    if str(manifest.get("publish_at") or "").strip():
        warnings.append("publish_at is ignored: the Graph API publishes Reels immediately")

    mode = "DRY-RUN" if args.dry_run else "PUBLISH"
    print(f"INSTAGRAM {mode} {('OK' if args.dry_run else 'READY') if not errors else 'FAIL'} {video_id(manifest, args.manifest)}: "
          f"caption {len(caption)} chars, first comment {'yes' if first_comment else 'none'}, API {GRAPH_VERSION}")
    for e in errors:
        print(f"  ERROR {e}")
    for w in warnings:
        print(f"  WARN {w}")
    if errors:
        return 1
    if args.dry_run:
        return 0

    user_id, token = creds["IG_USER_ID"], creds["IG_ACCESS_TOKEN"]
    try:
        media_id, container = publish(user_id, token, args.video_url, caption)
    except GraphError as e:
        print(f"  ERROR publish: {e}")
        return 1
    record = {"media_id": media_id, "container_id": container, "video_url": args.video_url,
              "published_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    try:
        info = call("GET", media_id, token, {"fields": "permalink"})
        record["url"] = info.get("permalink", "")
    except GraphError as e:
        warnings.append(f"permalink not read: {e}")
    if first_comment:
        try:
            record["first_comment_id"] = call("POST", f"{media_id}/comments", token,
                                              {"message": first_comment}).get("id", "")
        except GraphError as e:
            record["first_comment_error"] = str(e)
            print(f"  WARN first comment not posted: {e}")
    path = write_published(manifest, args.manifest, "instagram", record)
    print(f"  published media {media_id} -> {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
