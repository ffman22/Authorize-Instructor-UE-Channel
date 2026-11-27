#!/usr/bin/env python3
"""Pull own-channel stats from the YouTube Data API into data/social_stats.json.

Instagram, TikTok and Threads have no OAuth here: their numbers are added with
--ig/--tiktok/--threads (followers, following, posts) after reading them in the app.
Usage: python tools/social_stats.py [--ig 11,11,2] [--tiktok 1,2,1] [--threads 0,0,1]
"""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import youtube_upload as yu

OUT = Path(__file__).resolve().parent.parent / "data" / "social_stats.json"


def seconds(iso):
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    h, mi, s = (int(x or 0) for x in m.groups()) if m else (0, 0, 0)
    return h * 3600 + mi * 60 + s


def youtube():
    from googleapiclient.discovery import build

    yt = build("youtube", "v3", credentials=yu.load_credentials(), cache_discovery=False)
    ch = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, token = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50, pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        token = r.get("nextPageToken")
        if not token:
            break
    videos = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,statistics,status,contentDetails", id=",".join(ids[i:i + 50])).execute()
        for v in r["items"]:
            st, sn, sx = v["statistics"], v["snippet"], v["status"]
            dur = seconds(v["contentDetails"]["duration"])
            videos.append({
                "id": v["id"], "title": sn["title"], "kind": "Short" if dur <= 60 else "Long",
                "privacy": sx["privacyStatus"], "when": sx.get("publishAt") or sn["publishedAt"],
                "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
            })
    s = ch["statistics"]
    return {"title": ch["snippet"]["title"], "subs": int(s["subscriberCount"]),
            "views": int(s["viewCount"]), "videos": int(s["videoCount"])}, videos


def triple(text):
    a, b, c = (int(x) for x in text.split(","))
    return {"followers": a, "following": b, "posts": c}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ig")
    ap.add_argument("--tiktok")
    ap.add_argument("--threads")
    a = ap.parse_args()
    # Platforms without OAuth keep their last known numbers unless new ones are given.
    old = {}
    if OUT.exists():
        old = {x["platform"]: x for x in json.loads(OUT.read_text(encoding="utf-8")).get("accounts", [])}

    def keep(name, arg):
        if arg:
            return triple(arg)
        o = old.get(name, {})
        return {"followers": o.get("followers", 0), "following": o.get("following", 0), "posts": o.get("posts", 0)}
    ch, videos = youtube()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data = {"generated_utc": now, "youtube": ch, "videos": videos,
            "accounts": [
                {"platform": "YouTube", "handle": ch["title"], "followers": ch["subs"], "following": 0,
                 "posts": ch["videos"], "views": ch["views"], "source": "YouTube Data API"},
                {"platform": "Instagram", "handle": "@carlo.animator", **keep("Instagram", a.ig), "views": None,
                 "source": "Read in the app"},
                {"platform": "TikTok", "handle": "@carloaninator", **keep("TikTok", a.tiktok), "views": None,
                 "source": "Read in the app"},
                {"platform": "Threads", "handle": "@carlo.animator", **keep("Threads", a.threads), "views": None,
                 "source": "Read in the app"}]}
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({len(videos)} videos)")


if __name__ == "__main__":
    main()
