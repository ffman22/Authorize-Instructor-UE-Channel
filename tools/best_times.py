#!/usr/bin/env python3
"""Best posting times for Shorts from competitor channels (official YouTube Data API v3).

For each channel: channels.list (uploads playlist) -> playlistItems.list (recent
uploads) -> videos.list (duration, views). Shorts (<= 60 s) feed a view-weighted
histogram of publish hour (UTC) and weekday.

Merging: each channel's histogram is normalized to sum 1 before summing, so one
big channel cannot drown the others. Top 3 UTC hours are converted to
Europe/Madrid and America/New_York. eu_us_slots picks the best data hour that
lands 18:00-23:00 in Madrid (Europe evening) and the best one that lands
18:00-23:00 in New York (US evening); with no data in a window it falls back to
20:00 Madrid / 19:00 New York and says so. Under 30 Shorts in total is flagged thin.

API key: env YOUTUBE_API_KEY or a YOUTUBE_API_KEY= line in .env (never printed).
Quota: channels.list, playlistItems.list and videos.list cost 1 unit per call.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

API = "https://www.googleapis.com/youtube/v3/"
ROOT = Path(__file__).resolve().parent.parent
MAX_SHORT_S = 60
THIN = 30
ZONES = {"Europe/Madrid": ZoneInfo("Europe/Madrid"), "America/New_York": ZoneInfo("America/New_York")}
EVENING = range(18, 24)
FALLBACK = {"eu": ("Europe/Madrid", 20), "us": ("America/New_York", 19)}
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CHANNEL_ID = re.compile(r"\bUC[0-9A-Za-z_-]{22}\b")


def load_key():
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("YOUTUBE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    return key


def api_get(endpoint, params, key):
    url = API + endpoint + "?" + urllib.parse.urlencode({**params, "key": key})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            msg = json.load(e).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        sys.exit(f"error: {endpoint}.list HTTP {e.code} {msg}".rstrip())  # URL holds the key: never echo it


def iso_duration_s(text):
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?", text or "")
    if not m or text in ("P", "PT"):
        return None
    d, h, mi, s = (float(g) if g else 0.0 for g in m.groups())
    return int(d * 86400 + h * 3600 + mi * 60 + s)


def ids_from_file(path):
    return CHANNEL_ID.findall(Path(path).read_text(encoding="utf-8"))


def histogram(videos_json):
    hours, days, n = [0] * 24, [0] * 7, 0
    for v in videos_json.get("items", []):
        dur = iso_duration_s(v.get("contentDetails", {}).get("duration"))
        if dur is None or dur > MAX_SHORT_S:
            continue
        t = datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00")).astimezone(timezone.utc)
        views = int(v.get("statistics", {}).get("viewCount", 0) or 0)
        hours[t.hour] += views
        days[t.weekday()] += views
        n += 1
    return {"shorts": n, "hour_views_utc": hours, "weekday_views_utc": dict(zip(WEEKDAYS, days))}


def local_of(utc_hour, ref):
    base = ref.replace(hour=utc_hour, minute=0, second=0, microsecond=0)
    return {z: base.astimezone(tz).strftime("%H:%M") for z, tz in ZONES.items()}


def merge(per_channel, ref):
    merged = [0.0] * 24
    for h in per_channel.values():
        total = sum(h["hour_views_utc"])
        if total:
            merged = [m + x / total for m, x in zip(merged, h["hour_views_utc"])]
    k = len([h for h in per_channel.values() if sum(h["hour_views_utc"])]) or 1
    merged = [round(m / k, 4) for m in merged]
    ranked = sorted((h for h in range(24) if merged[h] > 0), key=lambda h: merged[h], reverse=True)
    top = [{"utc": f"{h:02d}:00", "share": merged[h], "local": local_of(h, ref)} for h in ranked[:3]]

    def pick(tag):
        zone, fb_hour = FALLBACK[tag]
        tz = ZONES[zone]
        window = [h for h in range(24)
                  if ref.replace(hour=h, minute=0, second=0, microsecond=0).astimezone(tz).hour in EVENING]
        best = max(window, key=lambda h: merged[h])
        if merged[best] > 0:
            src = "data"
        else:
            local = ref.astimezone(tz).replace(hour=fb_hour, minute=0, second=0, microsecond=0)
            best, src = local.astimezone(timezone.utc).hour, "default (no data in window)"
        return {"for": "Europe evening" if tag == "eu" else "US evening", "utc": f"{best:02d}:00",
                "share": merged[best], "local": local_of(best, ref), "source": src}

    return merged, top, [pick("eu"), pick("us")]


def build_schedule(per_channel, ref):
    merged, top, slots = merge(per_channel, ref)
    total = sum(h["shorts"] for h in per_channel.values())
    days = {d: sum(h["weekday_views_utc"][d] for h in per_channel.values()) for d in WEEKDAYS}
    out = {
        "generated_utc": ref.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local_times_for_date": ref.strftime("%Y-%m-%d"),
        "method": "view-weighted publish hour of Shorts (<=60 s); channels normalized to equal weight",
        "shorts_analyzed": total,
        "thin_data": total < THIN,
        "per_channel": per_channel,
        "merged_hour_share_utc": merged,
        "weekday_views_utc": days,
        "top_utc_slots": top,
        "eu_us_slots": slots,
    }
    if total < THIN:
        out["note"] = f"only {total} Shorts (< {THIN}): treat slots as a weak signal; add channels or --videos"
    return out


def plan(channel_ids, n_videos):
    pages = -(-n_videos // 50)
    ch_calls = -(-len(channel_ids) // 50)
    return ch_calls, len(channel_ids) * pages, len(channel_ids) * pages


def dry_run(channel_ids, args):
    ch, pl, vi = plan(channel_ids, args.videos)
    print("planned calls (no network):")
    print(f"  channels.list x{ch}  part=contentDetails,snippet id={','.join(channel_ids[:50])}")
    print(f"  playlistItems.list x{pl}  part=contentDetails playlistId=<uploads> maxResults=50 (up to {args.videos} per channel)")
    print(f"  videos.list x{vi}  part=snippet,contentDetails,statistics id=<up to 50 ids>")
    print(f"quota: {ch + pl + vi} units (1 per call; daily default 10,000)")


def run(channel_ids, args):
    key = load_key()
    if not key:
        sys.exit("error: YOUTUBE_API_KEY missing (env or .env)")
    uploads, used = {}, 0
    for i in range(0, len(channel_ids), 50):
        r = api_get("channels", {"part": "contentDetails,snippet", "id": ",".join(channel_ids[i:i + 50])}, key)
        used += 1
        for c in r.get("items", []):
            uploads[c["id"]] = (c["contentDetails"]["relatedPlaylists"]["uploads"], c["snippet"]["title"])
    for cid in channel_ids:
        if cid not in uploads:
            print(f"error: channel {cid} not found", file=sys.stderr)
    per_channel = {}
    for cid, (playlist, title) in uploads.items():
        vids, token = [], None
        while len(vids) < args.videos:
            p = {"part": "contentDetails", "playlistId": playlist, "maxResults": min(50, args.videos - len(vids))}
            if token:
                p["pageToken"] = token
            r = api_get("playlistItems", p, key)
            used += 1
            vids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
            token = r.get("nextPageToken")
            if not token:
                break
        videos = {"items": []}
        for i in range(0, len(vids), 50):
            r = api_get("videos", {"part": "snippet,contentDetails,statistics", "id": ",".join(vids[i:i + 50])}, key)
            used += 1
            videos["items"] += r.get("items", [])
        per_channel[cid] = {"title": title, "videos_fetched": len(videos["items"]), **histogram(videos)}
    return per_channel, used


# ---------- selftest fixtures ----------
def _v(vid, when, dur, views):
    return {"id": vid, "snippet": {"publishedAt": when}, "contentDetails": {"duration": dur},
            "statistics": {"viewCount": str(views)}}


FIX_REF = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)   # winter: Madrid UTC+1, New York UTC-5
FIX_A = {"items": [
    _v("a1", "2026-11-20T19:05:00Z", "PT40S", 900_000),    # Fri 19 UTC = 20 Madrid
    _v("a2", "2026-11-19T19:30:00Z", "PT55S", 100_000),
    _v("a3", "2026-11-18T23:10:00Z", "PT1M", 500_000),     # Wed 23 UTC = 18 New York
    _v("a4", "2026-11-17T15:00:00Z", "PT3M", 9_000_000),   # long video: ignored
]}
FIX_B = {"items": [
    _v("b1", "2026-11-21T00:00:00Z", "PT30S", 10_000_000),  # Sat 00 UTC = 19 New York
    _v("b2", "2026-11-16T19:00:00Z", "PT20S", 10_000_000),  # Mon 19 UTC
]}


def selftest():
    assert iso_duration_s("PT59S") == 59 and iso_duration_s("PT1M1S") == 61 and iso_duration_s("x") is None
    ha, hb = histogram(FIX_A), histogram(FIX_B)
    assert ha["shorts"] == 3 and ha["hour_views_utc"][19] == 1_000_000 and ha["hour_views_utc"][15] == 0
    assert ha["weekday_views_utc"]["Fri"] == 900_000 and hb["weekday_views_utc"]["Sat"] == 10_000_000
    per = {"UCa": {"title": "A", **ha}, "UCb": {"title": "B", **hb}}
    s = build_schedule(per, FIX_REF)
    m = s["merged_hour_share_utc"]
    assert abs(sum(m) - 1) < 1e-3 and m[19] == round((1 / 1.5 + 0.5) / 2, 4)   # normalized per channel
    assert [t["utc"] for t in s["top_utc_slots"]] == ["19:00", "00:00", "23:00"], s["top_utc_slots"]
    assert s["top_utc_slots"][0]["local"] == {"Europe/Madrid": "20:00", "America/New_York": "14:00"}
    eu, us = s["eu_us_slots"]
    assert eu["utc"] == "19:00" and eu["source"] == "data"
    assert us["utc"] == "00:00" and us["local"]["America/New_York"] == "19:00" and us["source"] == "data"
    assert s["thin_data"] and "note" in s
    empty = build_schedule({"UCx": {"title": "X", **histogram({"items": []})}}, FIX_REF)
    assert empty["top_utc_slots"] == [] and empty["eu_us_slots"][0]["local"]["Europe/Madrid"] == "20:00"
    assert empty["eu_us_slots"][1]["local"]["America/New_York"] == "19:00"
    assert empty["eu_us_slots"][0]["source"].startswith("default")
    summer = build_schedule(per, datetime(2026, 7, 1, 12, tzinfo=timezone.utc))
    assert summer["top_utc_slots"][0]["local"]["Europe/Madrid"] == "21:00"     # DST via zoneinfo
    assert ids_from_file.__name__ and CHANNEL_ID.findall("| @x | UCabcdefghijklmnopqrstuv | n |") == ["UCabcdefghijklmnopqrstuv"]
    json.dumps(s)
    print("selftest ok: shorts filter, weighted histogram, merge, top slots, zones and DST, eu/us picks, thin flag")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("channel_ids", nargs="*", help="competitor channel IDs (UC...)")
    ap.add_argument("--from-file", help="read UC... IDs from a file (e.g. data/topics/channels.md)")
    ap.add_argument("--videos", type=int, default=50, help="recent uploads per channel (50)")
    ap.add_argument("--out", default=str(ROOT / "data" / "schedule.json"), help="output JSON (data/schedule.json)")
    ap.add_argument("--dry-run", action="store_true", help="print planned calls and quota, no network")
    ap.add_argument("--selftest", action="store_true", help="run histogram and slot tests on fixtures")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    ids = list(args.channel_ids) + (ids_from_file(args.from_file) if args.from_file else [])
    ids = list(dict.fromkeys(ids))
    if not ids:
        ap.error("give channel IDs or --from-file with UC... IDs")
    if args.dry_run:
        return dry_run(ids, args)
    per_channel, used = run(ids, args)
    sched = build_schedule(per_channel, datetime.now(timezone.utc))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sched, indent=2) + "\n", encoding="utf-8")
    slots = ", ".join(f"{s['for']} {s['utc']} UTC ({'/'.join(s['local'].values())})" for s in sched["eu_us_slots"])
    thin = " THIN DATA" if sched["thin_data"] else ""
    print(f"best_times: {sched['shorts_analyzed']} Shorts from {len(per_channel)} channels -> {out}; {slots}{thin} ({used} quota units)")


if __name__ == "__main__":
    main()
