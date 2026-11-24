"""Shared helpers for the publish tools: video path, hashtags, published.json."""
import json
from pathlib import Path

from rights_gate import REPO_ROOT


def video_id(manifest, manifest_path):
    return manifest.get("id") or Path(manifest_path).resolve().parent.name


def resolve_video(manifest, manifest_path, cli_value=None):
    """--video, else manifest video_file, else out/<id>.mp4."""
    value = cli_value or str(manifest.get("video_file") or "").strip()
    if not value:
        return REPO_ROOT / "out" / f"{video_id(manifest, manifest_path)}.mp4"
    p = Path(value)
    return p if p.is_absolute() else REPO_ROOT / p


def not_ready(manifest):
    """Return an error string unless the manifest says ready_to_publish: true, else None."""
    if manifest.get("ready_to_publish") is True:
        return None
    return ("ready_to_publish is not true: review the manifest, then set \"ready_to_publish\": true "
            "(drafts never upload)")


def norm_hashtags(manifest):
    out = []
    for h in manifest.get("hashtags") or []:
        h = str(h).strip().replace(" ", "")
        if h:
            out.append(h if h.startswith("#") else f"#{h}")
    return out


def with_hashtags(text, tags):
    """Append the hashtags that the text does not already contain."""
    text = str(text or "").strip()
    lower = text.lower().split()
    missing = [t for t in tags if t.lower() not in lower]
    return (text + ("\n\n" if text else "") + " ".join(missing)).strip() if missing else text


def write_published(manifest, manifest_path, key, data):
    path = REPO_ROOT / "videos" / video_id(manifest, manifest_path) / "published.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    current = {}
    if path.is_file():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {}
    current[key] = data
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    return path
