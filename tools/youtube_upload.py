#!/usr/bin/env python3
"""Upload a Short or a long video to YouTube (private or scheduled by default).

Usage: youtube_upload.py --auth
       youtube_upload.py <manifest.json> [--video out/<id>.mp4] [--long] [--dry-run]
Video: --video, else manifest "video_file", else out/<id>.mp4.
Shorts get "#shorts" in the title; --long (or manifest "format": "long") skips it.
Credentials: client_secret.json -> token.json at the repo root (never printed).
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rights_gate  # noqa: E402
from publish_common import (norm_hashtags, resolve_video, video_id, with_hashtags,  # noqa: E402
                            write_published)

REPO_ROOT = rights_gate.REPO_ROOT
CLIENT_SECRET = REPO_ROOT / "client_secret.json"
TOKEN = REPO_ROOT / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # first comment (commentThreads.insert)
]
CATEGORY_ID = "24"  # Entertainment
MAX_TITLE, MAX_DESC, MAX_TAGS_CHARS = 100, 5000, 500
AUDIT_HINT = ("The API project is not verified/audited for this call. See docs/setup_checklist.md "
              "item q-yt-audit (request the YouTube API compliance audit, or upload manually meanwhile).")


def is_long(manifest, cli_long=False):
    return cli_long or str(manifest.get("format") or "short").strip().lower() == "long"


def build_title(manifest, long_video=False):
    title = " ".join(str(manifest.get("title") or "").split())
    if long_video:
        return title[:MAX_TITLE]
    suffix = " #shorts"
    if "#shorts" in title.lower():
        return title[:MAX_TITLE]
    return title[:MAX_TITLE - len(suffix)].rstrip() + suffix


TAGS_BASE = Path(__file__).resolve().parent / "tags_base.json"


def base_tags(manifest, long_video=False):
    """Extra tags: manifest "tags", then topic, format and channel tags from tags_base.json."""
    base = {}
    if TAGS_BASE.is_file():
        base = json.loads(TAGS_BASE.read_text(encoding="utf-8"))
    topic = str(manifest.get("topic") or "").strip().lower()
    topics = {k.lower(): v for k, v in (base.get("topics") or {}).items()}
    fmt = "long" if long_video else "short"
    return (list(manifest.get("tags") or []) + topics.get(topic, [])
            + (base.get("formats") or {}).get(fmt, []) + base.get("channel", []))


def build_tags(hashtags, extra=()):
    tags, seen, total = [], set(), 0
    for h in list(hashtags) + list(extra):
        t = str(h).strip().lstrip("#").lower()
        cost = len(t) + (2 if " " in t else 0) + (1 if tags else 0)
        if t and t not in seen and total + cost <= MAX_TAGS_CHARS:
            tags.append(t)
            seen.add(t)
            total += cost
    return tags


def parse_publish_at(value):
    """Return an RFC3339 UTC string, or raise ValueError."""
    t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("publish_at needs a time zone offset (e.g. 2026-11-23T17:00:00Z)")
    if t <= dt.datetime.now(dt.timezone.utc):
        raise ValueError(f"publish_at {value} is in the past")
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def build_request(manifest, long_video=False):
    """Return (body, first_comment, errors)."""
    errors = []
    tags = norm_hashtags(manifest)
    if long_video:
        tags = [t for t in tags if t.lower() != "#shorts"]
    desc = with_hashtags(manifest.get("description", ""), tags)
    if len(desc) > MAX_DESC:
        errors.append(f"description: {len(desc)} chars, max {MAX_DESC}")
    if "<" in desc or ">" in desc:
        errors.append("description: YouTube rejects '<' and '>'")
    title = build_title(manifest, long_video)
    if not title.replace("#shorts", "").strip():
        errors.append("title: empty")
    if long_video and "#shorts" in title.lower():
        errors.append("title: contains #shorts but the upload is a long video")
    privacy = str(manifest.get("privacy") or "private").strip()
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    publish_at = str(manifest.get("publish_at") or "").strip()
    if publish_at:
        try:
            status["publishAt"] = parse_publish_at(publish_at)
            status["privacyStatus"] = "private"  # scheduled uploads must be private
        except ValueError as e:
            errors.append(f"publish_at: {e}")
    body = {
        "snippet": {"title": title, "description": desc, "tags": build_tags(tags, base_tags(manifest, long_video)),
                    "categoryId": CATEGORY_ID},
        "status": status,
    }
    return body, str(manifest.get("first_comment") or "").strip(), errors


def load_credentials(interactive=False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = None
    if TOKEN.is_file():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
        if creds and not set(SCOPES).issubset(set(creds.scopes or [])):
            creds = None  # scopes changed: re-consent
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif interactive:
        from google_auth_oauthlib.flow import InstalledAppFlow
        if not CLIENT_SECRET.is_file():
            raise FileNotFoundError("client_secret.json not found at the repo root (docs/setup_checklist.md)")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)
    else:
        raise RuntimeError("no valid token.json: run youtube_upload.py --auth first")
    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    try:
        TOKEN.chmod(0o600)
    except OSError:
        pass
    return creds


def explain_http_error(e):
    status = getattr(getattr(e, "resp", None), "status", None)
    reason = ""
    try:
        reason = e.error_details[0].get("reason", "") if e.error_details else ""
    except (AttributeError, IndexError, TypeError):
        pass
    if reason == "quotaExceeded":
        return f"HTTP {status} quotaExceeded: daily API quota used up; retry tomorrow."
    if status == 403:
        return f"HTTP 403 {reason or 'forbidden'}: {AUDIT_HINT}"
    if status == 401:
        return f"HTTP 401: token rejected; run youtube_upload.py --auth again."
    return f"HTTP {status} {reason}".strip()


def upload(creds, video, body):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk(num_retries=5)
    return yt, resp


def post_comment(yt, vid, text):
    body = {"snippet": {"videoId": vid, "topLevelComment": {"snippet": {"textOriginal": text}}}}
    return yt.commentThreads().insert(part="snippet", body=body).execute()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Upload a Short to YouTube (private/scheduled by default).")
    ap.add_argument("manifest", nargs="?", help="path to videos/<id>/manifest.json")
    ap.add_argument("--video", help="MP4 to upload (default: manifest video_file, else out/<id>.mp4)")
    ap.add_argument("--auth", action="store_true", help="run the OAuth consent flow and save token.json")
    ap.add_argument("--long", action="store_true", help="long video: no #shorts in title or tags (also manifest format: long)")
    ap.add_argument("--dry-run", action="store_true", help="validate everything, no network")
    args = ap.parse_args(argv)

    if args.auth:
        try:
            load_credentials(interactive=True)
        except Exception as e:  # noqa: BLE001
            print(f"YOUTUBE AUTH FAIL: {type(e).__name__}: {e}")
            return 1
        print(f"YOUTUBE AUTH OK: token saved to {TOKEN.name}")
        return 0
    if not args.manifest:
        ap.error("manifest is required unless --auth")

    ok, manifest, errors, _ = rights_gate.run(args.manifest)
    if not ok:
        print(f"YOUTUBE REFUSED {args.manifest}: rights gate failed")
        return 1
    video = resolve_video(manifest, args.manifest, args.video)
    long_video = is_long(manifest, args.long)
    body, first_comment, errors = build_request(manifest, long_video)
    warnings = []
    if not video.is_file():
        errors.append(f"video: not found: {video}")
    elif video.stat().st_size == 0:
        errors.append(f"video: empty file: {video}")
    if body["status"]["privacyStatus"] == "public":
        warnings.append("privacy public: the video goes live immediately")
    if not TOKEN.is_file():
        (warnings if args.dry_run else errors).append("token.json missing: run --auth")
        if not CLIENT_SECRET.is_file():
            warnings.append("client_secret.json missing (docs/setup_checklist.md)")

    s = body["status"]
    sched = f", publishAt {s['publishAt']}" if "publishAt" in s else ""
    mode = "DRY-RUN" if args.dry_run else "UPLOAD"
    print(f"YOUTUBE {mode} {('OK' if args.dry_run else 'READY') if not errors else 'FAIL'} {video_id(manifest, args.manifest)}: "
          f"{'long' if long_video else 'short'}, '{body['snippet']['title']}', {s['privacyStatus']}{sched}, "
          f"{len(body['snippet']['tags'])} tags, first comment {'yes' if first_comment else 'none'}")
    for e in errors:
        print(f"  ERROR {e}")
    for w in warnings:
        print(f"  WARN {w}")
    if errors:
        return 1
    if args.dry_run:
        return 0

    from googleapiclient.errors import HttpError
    try:
        creds = load_credentials()
        yt, resp = upload(creds, video, body)
    except HttpError as e:
        print(f"  ERROR upload: {explain_http_error(e)}")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR upload: {type(e).__name__}: {e}")
        return 1
    vid = resp["id"]
    url = f"https://www.youtube.com/watch?v={vid}" if long_video else f"https://youtube.com/shorts/{vid}"
    record = {"video_id": vid, "url": url, "format": "long" if long_video else "short",
              "privacy": s["privacyStatus"], "publish_at": s.get("publishAt", ""),
              "uploaded_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "file": str(video)}
    if first_comment:
        try:
            c = post_comment(yt, vid, first_comment)
            record["first_comment_id"] = c.get("id", "")
        except HttpError as e:
            record["first_comment_error"] = explain_http_error(e)
            print(f"  WARN first comment not posted: {record['first_comment_error']}")
    path = write_published(manifest, args.manifest, "youtube", record)
    print(f"  uploaded {record['url']} -> {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
