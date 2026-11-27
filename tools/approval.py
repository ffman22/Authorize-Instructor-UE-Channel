#!/usr/bin/env python3
"""Owner approval gate: nothing goes to a platform until the owner has seen it and approved it.

Usage: approval.py sheet <id ...> [--live] [--out FILE]   build the review page the owner approves
       approval.py approve <id> --quote "owner's words"   record the approval (only after the owner says so)
       approval.py check <id>                             exit 0 only if the approval is still valid

An approval is tied to the exact metadata, video file and thumbnail (SHA-256). Any change voids it.
SD never passes: the source and the video must be 720p or higher.
spec_errors() is the ground-truth spec check (spec.json next to the manifest) used before render and upload.
"""
import argparse
import base64
import datetime as dt
import hashlib
import html
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rights_gate  # noqa: E402
from publish_common import resolve_video  # noqa: E402

ROOT = rights_gate.REPO_ROOT
META_FIELDS = ("format", "title", "description", "hashtags", "tags", "first_comment", "ig_caption",
               "tiktok_caption", "threads_post", "community_post", "privacy", "publish_at")
SPEC_FIELDS = ("engine_and_version", "core_technical_thesis", "shown_in_video", "not_in_video",
               "verified_timestamps", "candidate_thumbnail_timestamps")


def manifest_path(vid):
    return ROOT / "videos" / vid / "manifest.json"


def load(vid):
    return json.loads(manifest_path(vid).read_text(encoding="utf-8"))


def thumbnail_path(vid):
    return ROOT / "out" / "thumbs" / f"{vid}-brand.jpg"


def video_path(manifest, vid):
    return resolve_video(manifest, manifest_path(vid))


def source_path(manifest, vid):
    name = rights_gate.source_file(manifest)
    return rights_gate.resolve_clip_path(name, manifest_path(vid)) if name else None


def spec_errors(manifest_file):
    path = Path(manifest_file).resolve().parent / "spec.json"
    if not path.is_file():
        return [f"spec: {path.parent.name}/spec.json is missing (ground-truth spec, docs/research_rules.md)"]
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
        empty = [k for k in SPEC_FIELDS if not spec.get(k)]
    except (ValueError, AttributeError) as e:
        return [f"spec: {path.parent.name}/spec.json is not a valid JSON object: {e}"]
    return [f"spec: empty fields: {', '.join(empty)}"] if empty else []


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def youtube_view(manifest):
    """The title, description and tags exactly as youtube_upload.py would send them."""
    import youtube_upload as yu
    body = yu.build_request(manifest, yu.is_long(manifest))[0]["snippet"]
    return {k: body[k] for k in ("title", "description", "tags")}


def metadata_hash(manifest):
    data = {"manifest": {k: manifest.get(k) for k in META_FIELDS}, "youtube": youtube_view(manifest)}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def current_hashes(manifest, vid, video=None, thumb=None):
    video = Path(video) if video else video_path(manifest, vid)
    thumb = Path(thumb) if thumb else thumbnail_path(vid)
    return {"metadata": metadata_hash(manifest),
            "video": file_hash(video) if video.is_file() else "",
            "thumbnail": file_hash(thumb) if thumb.is_file() else ""}


def media_errors(manifest, vid, video=None):
    """HD only: the source and the file to publish must both exist and be 720p or higher."""
    errors = []
    for label, path in (("source", source_path(manifest, vid)),
                        ("video", Path(video) if video else video_path(manifest, vid))):
        if not path or not path.is_file():
            errors.append(f"{label}: file not found, HD not verified")
        elif rights_gate.hd_error(path):
            errors.append(f"{label}: {rights_gate.hd_error(path)}")
    return errors


def check(vid, video=None, parts=("metadata", "video", "thumbnail")):
    """Return errors unless the owner approved exactly what is about to be published."""
    path = ROOT / "videos" / vid / "approval.json"
    if not path.is_file():
        return [f"approval: {vid} has no owner approval; run approval.py sheet {vid} and show it to the owner"]
    record = json.loads(path.read_text(encoding="utf-8"))
    now = current_hashes(load(vid), vid, video)
    changed = [p for p in parts if not now[p] or record.get("hashes", {}).get(p) != now[p]]
    return [f"approval: {', '.join(changed)} changed or missing since the owner approved; show it again"] \
        if changed else []


def approve(vid, quote):
    manifest = load(vid)
    errors = media_errors(manifest, vid)
    if not thumbnail_path(vid).is_file():
        errors.append("thumbnail: not rendered; the owner approves it together with the video")
    if not quote.strip():
        errors.append("quote: the owner's words are required")
    if errors:
        return errors
    record = {"id": vid, "approved_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "owner_quote": quote.strip(), "hashes": current_hashes(manifest, vid)}
    (ROOT / "videos" / vid / "approval.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return []


# ---------- review page ----------

def probe_size(path):
    import subprocess
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
                             capture_output=True, text=True, timeout=60)
        return out.stdout.strip().splitlines()[0]
    except (OSError, IndexError, subprocess.SubprocessError):
        return "unreadable"


def data_uri(image, width):
    image = image.copy()
    image.thumbnail((width, width * 2))
    buf = io.BytesIO()
    image.convert("RGB").save(buf, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def thumb_html(vid, short):
    from PIL import Image
    path = thumbnail_path(vid)
    if not path.is_file():
        return "<p class='bad'>No thumbnail rendered.</p>"
    im = Image.open(path).convert("RGB")
    views = [("Full", im)]
    if short:
        top = (im.height - im.width * 4 // 3) // 2
        views.append(("Profile grid 3:4", im.crop((0, top, im.width, im.height - top))))
        top = (im.height - im.width * 5 // 4) // 2
        views.append(("Feed 4:5", im.crop((0, top, im.width, im.height - top))))
    return "".join(f"<figure><img src='{data_uri(i, 270 if short else 480)}'><figcaption>{n}</figcaption></figure>"
                   for n, i in views)


def thumb_origin(vid, manifest):
    cfg_path = ROOT / "data" / "brand" / "thumbs.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")).get(vid) if cfg_path.is_file() else None
    if not cfg:
        return "not in thumbs.json"
    if "art" in cfg:
        base = f"art layer {cfg['art']} of your template Template_Thumb_vertical_WorkshopPromo"
    else:
        base = f"frame at {cfg['at']} s of {rights_gate.source_file(manifest)}"
    extra = "UNREALZERO workshop block" if cfg.get("workshop") else "channel watermark"
    return f"{base} + {extra}; text: {' / '.join(cfg['text'])}"


def live_snippets(ids):
    import youtube_upload as yu
    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=yu.load_credentials(), cache_discovery=False)
    vids = {}
    for vid in ids:
        record = ROOT / "videos" / vid / "published.json"
        if record.is_file():
            yid = json.loads(record.read_text(encoding="utf-8")).get("youtube", {}).get("video_id")
            if yid:
                vids[yid] = vid
    items = yt.videos().list(part="snippet,status", id=",".join(vids)).execute()["items"] if vids else []
    return {vids[i["id"]]: i for i in items}


def row(label, value, bad=False):
    cls = " class='bad'" if bad else ""
    return f"<tr><th>{html.escape(label)}</th><td{cls}>{html.escape(str(value))}</td></tr>"


def card(vid, live):
    m = load(vid)
    short = str(m.get("format") or "short") == "short"
    view = youtube_view(m)
    src, video = source_path(m, vid), video_path(m, vid)
    problems = media_errors(m, vid)
    if rights_gate.WORKSHOP_URL not in "\n".join(view["description"].splitlines()[:2]):
        problems.append("research rule: workshop link is not in the first 2 lines of the description")
    problems += spec_errors(manifest_path(vid))
    rows = []
    if live:
        s, status = live["snippet"], live["status"]
        when = status.get("publishAt") or "not scheduled"
        rows += [row("YouTube now", f"{live['id']} | {status['privacyStatus']} | {when}"),
                 row("Title now", s["title"])]
        if s["description"].strip() != view["description"].strip():
            rows.append(row("Description now", s["description"]))
        gone = sorted(set(s.get("tags", [])) - set(view["tags"]))
        if gone:
            rows.append(row("Tags that would be removed", ", ".join(gone)))
    rows += [row("New title", view["title"]), row("New description", view["description"]),
             row("New tags", ", ".join(view["tags"])), row("Date (manifest)", m.get("publish_at") or "none"),
             row("Instagram caption", m.get("ig_caption") or "none"),
             row("TikTok caption", m.get("tiktok_caption") or "none"),
             row("Threads post", m.get("threads_post") or "none"),
             row("YouTube community post", m.get("community_post") or "none"),
             row("First comment", m.get("first_comment") or "none"),
             row("Source file", f"{src.name} {probe_size(src)}" if src and src.is_file() else "missing"),
             row("Cut", f"start {m.get('start', 0)} s, duration {m.get('duration', 'full')} s"),
             row("Video file", f"{video.name} {probe_size(video)}" if video.is_file() else "missing"),
             row("Thumbnail built from", thumb_origin(vid, m)),
             row("Thumbnail file", thumbnail_path(vid).name)]
    if problems:
        rows.append(row("Problems", "\n".join(problems), bad=True))
    return (f"<section><h2>{html.escape(vid)}</h2><div class='shots'>{thumb_html(vid, short)}</div>"
            f"<table>{''.join(rows)}</table></section>")


PAGE = """<!doctype html><meta charset="utf-8"><title>Approval sheet</title><style>
body{{font:14px system-ui;margin:24px;background:#16181c;color:#e8e8e8}}section{{border-top:2px solid #444;padding:12px 0}}
.shots{{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start}}figure{{margin:0}}img{{max-width:100%}}
table{{border-collapse:collapse;margin-top:8px;width:100%}}th,td{{border:1px solid #444;padding:6px;text-align:left;vertical-align:top}}
th{{width:170px}}td{{white-space:pre-wrap;overflow-wrap:anywhere}}.bad{{color:#ff8a80}}</style>
<h1>Approval sheet, {date}</h1><p>Nothing here is uploaded or changed until you approve it by name.</p>{cards}"""


def sheet(ids, out, use_live):
    live = live_snippets(ids) if use_live else {}
    out.parent.mkdir(parents=True, exist_ok=True)
    date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out.write_text(PAGE.format(date=date, cards="".join(card(v, live.get(v)) for v in ids)), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Owner approval gate: review sheet, approve, check.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("sheet", help="build the review page")
    p.add_argument("ids", nargs="+")
    p.add_argument("--live", action="store_true", help="show what YouTube has now next to the new values")
    p.add_argument("--out", help="default: out/review/approval-sheet.html")
    p = sub.add_parser("approve", help="record the owner's approval")
    p.add_argument("id")
    p.add_argument("--quote", required=True, help="the owner's own words approving this video")
    p = sub.add_parser("check", help="verify the approval is still valid")
    p.add_argument("id")
    args = ap.parse_args(argv)

    if args.cmd == "sheet":
        out = Path(args.out) if args.out else ROOT / "out" / "review" / "approval-sheet.html"
        sheet(args.ids, out, args.live)
        print(f"APPROVAL SHEET OK {len(args.ids)} videos -> {out}")
        return 0
    errors = approve(args.id, args.quote) if args.cmd == "approve" else check(args.id)
    print(f"APPROVAL {args.cmd.upper()} {'FAIL' if errors else 'OK'} {args.id}")
    for e in errors:
        print(f"  ERROR {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
