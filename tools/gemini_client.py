"""Shared Gemini client: text, images, video (Files API), JSON mode, cache and token budget.

Cost control (the balance must last):
- MODELS: cheap "lite" for text/copy and image picks; the same lite model with low media
  resolution for video. Pick the tier per task, never the biggest model by default.
- Cache: identical requests (model + parts + options) are answered from out/gemini/cache/.
- Budget: every call logs its tokens to out/gemini/usage.jsonl; calls stop when today's total
  passes GEMINI_DAILY_TOKENS (env or .env, default DEFAULT_DAILY_TOKENS).
Credentials: GEMINI_API_KEY from the environment or .env (never printed).
"""
import base64
import datetime as dt
import hashlib
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS = {"lite": "gemini-3.1-flash-lite"}  # one tier today; add "pro" here when the balance allows
DEFAULT_MODEL = MODELS["lite"]
API = "https://generativelanguage.googleapis.com"
OUT_DIR = REPO_ROOT / "out" / "gemini"
CACHE_DIR = OUT_DIR / "cache"
USAGE_LOG = OUT_DIR / "usage.jsonl"
DEFAULT_DAILY_TOKENS = 2_000_000
MAX_FILE_BYTES = 500_000


class GeminiError(RuntimeError):
    pass


def _env(name):
    val = os.environ.get(name, "").strip()
    f = REPO_ROOT / ".env"
    if not val and f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip().removeprefix("export ").strip() == name:
                val = v.strip().strip('"').strip("'")
    return val


def load_key():
    key = _env("GEMINI_API_KEY")
    if not key:
        raise GeminiError("GEMINI_API_KEY missing; add it to .env (see .env.example)")
    return key


def is_secret_file(path):
    n = Path(path).name.lower()
    return n == ".env" or n.startswith(("token", "client_secret", ".env."))


# ---------- budget ----------

def tokens_today():
    if not USAGE_LOG.is_file():
        return 0
    today = dt.date.today().isoformat()
    total = 0
    for line in USAGE_LOG.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("date") == today:
            total += int(row.get("total", 0))
    return total


def daily_cap():
    try:
        return int(_env("GEMINI_DAILY_TOKENS") or DEFAULT_DAILY_TOKENS)
    except ValueError:
        return DEFAULT_DAILY_TOKENS


def log_usage(model, task, usage):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    row = {"date": dt.date.today().isoformat(), "model": model, "task": task,
           "prompt": usage.get("promptTokenCount", 0), "output": usage.get("candidatesTokenCount", 0),
           "total": usage.get("totalTokenCount", 0)}
    with USAGE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


# ---------- http ----------

def _request(req, timeout=300):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            msg = ""
        raise GeminiError(f"Gemini HTTP {e.code} {msg}".strip()) from None
    except urllib.error.URLError as e:
        raise GeminiError(f"cannot reach Gemini ({e.reason})") from None


def text_part(text):
    return {"text": text}


def image_part(path):
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(Path(path).read_bytes()).decode()}}


def file_parts(paths):
    """Text files as parts; credential files and big files are refused."""
    parts = []
    for p in paths:
        path = Path(p)
        if is_secret_file(path):
            raise GeminiError(f"refusing to send {path.name} (credentials file)")
        if not path.is_file():
            raise GeminiError(f"file not found: {p}")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise GeminiError(f"{p} is over {MAX_FILE_BYTES // 1000} KB; send an excerpt")
        parts.append(text_part(f"--- {path.name} ---\n{path.read_text(encoding='utf-8', errors='replace')}"))
    return parts


def upload_video(path, key, display="video"):
    """Upload through the Files API (resumable) and wait until ACTIVE. Return the file dict."""
    path = Path(path)
    size = path.stat().st_size
    mime = mimetypes.guess_type(str(path))[0] or "video/mp4"
    start = urllib.request.Request(
        f"{API}/upload/v1beta/files", method="POST",
        data=json.dumps({"file": {"display_name": display}}).encode(),
        headers={"x-goog-api-key": key, "X-Goog-Upload-Protocol": "resumable",
                 "X-Goog-Upload-Command": "start", "X-Goog-Upload-Header-Content-Length": str(size),
                 "X-Goog-Upload-Header-Content-Type": mime, "Content-Type": "application/json"})
    _, headers = _request(start)
    url = next((v for k, v in headers.items() if k.lower() == "x-goog-upload-url"), "")
    if not url:
        raise GeminiError("upload start returned no upload URL")
    up = urllib.request.Request(
        url, method="POST", data=path.read_bytes(),
        headers={"Content-Length": str(size), "X-Goog-Upload-Offset": "0",
                 "X-Goog-Upload-Command": "upload, finalize"})
    body, _ = _request(up, timeout=1800)
    info = json.loads(body.decode())["file"]
    for _ in range(90):  # up to ~7 min of processing
        if info.get("state") == "ACTIVE":
            return info
        if info.get("state") == "FAILED":
            raise GeminiError("Gemini could not process the video")
        time.sleep(5)
        body, _ = _request(urllib.request.Request(f"{API}/v1beta/{info['name']}", headers={"x-goog-api-key": key}))
        info = json.loads(body.decode())
    raise GeminiError("video still processing after 7 minutes")


def delete_file(name, key):
    try:
        _request(urllib.request.Request(f"{API}/v1beta/{name}", method="DELETE", headers={"x-goog-api-key": key}))
    except GeminiError:
        pass  # files expire by themselves after 48 h


def video_part(info, fps=None):
    part = {"file_data": {"mime_type": info.get("mimeType", "video/mp4"), "file_uri": info["uri"]}}
    if fps:
        part["video_metadata"] = {"fps": fps}
    return part


# ---------- generate ----------

def generate(parts, model=DEFAULT_MODEL, task="text", json_mode=False, low_media=False, use_cache=True, accept=None):
    """Return the answer text. Cached by content, counted against the daily token cap."""
    config = {}
    if json_mode:
        config["responseMimeType"] = "application/json"
    if low_media:
        config["mediaResolution"] = "MEDIA_RESOLUTION_LOW"
    body = {"contents": [{"parts": parts}]}
    if config:
        body["generationConfig"] = config
    raw = json.dumps(body, sort_keys=True).encode()
    cache_key = hashlib.sha256(model.encode() + raw).hexdigest()[:32]
    cache_file = CACHE_DIR / f"{cache_key}.txt"
    if use_cache and cache_file.is_file():
        return cache_file.read_text(encoding="utf-8")

    used, cap = tokens_today(), daily_cap()
    if used >= cap:
        raise GeminiError(f"daily Gemini token cap reached ({used}/{cap}); raise GEMINI_DAILY_TOKENS or wait")
    key = load_key()
    req = urllib.request.Request(f"{API}/v1beta/models/{model}:generateContent", data=raw, method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    last = None
    for attempt in range(3):  # 503 "high demand" is usually brief
        try:
            data = json.loads(_request(req, timeout=600)[0].decode())
            break
        except GeminiError as e:
            last = e
            if "HTTP 503" not in str(e) or attempt == 2:
                raise
            time.sleep(20 * (attempt + 1))
    else:
        raise last
    log_usage(model, task, data.get("usageMetadata", {}))
    try:
        text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]).strip()
    except (KeyError, IndexError):
        reason = data.get("promptFeedback", {}).get("blockReason", "no candidates")
        raise GeminiError(f"Gemini returned no text ({reason})") from None
    if use_cache:
        if accept:
            accept(text)  # raises on an invalid answer, which is then not cached
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(text, encoding="utf-8")
    return text


def parse_json(text):
    """Parse a JSON answer, tolerating a ```json fence."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    try:
        return json.loads(t)
    except json.JSONDecodeError as e:
        raise GeminiError(f"Gemini answer is not valid JSON: {e}") from None


def generate_json(parts, model=DEFAULT_MODEL, task="json", low_media=False, use_cache=True, tries=2):
    """JSON-mode generate(): cached by content, but only a valid answer is cached; retry on bad JSON."""
    last = None
    for _ in range(tries):
        text = generate(parts, model, task, json_mode=True, low_media=low_media, use_cache=use_cache,
                        accept=parse_json)
        try:
            return parse_json(text)
        except GeminiError as e:  # cached text from an older bad run
            last = e
            use_cache = False
    raise last


def die(e):
    sys.exit(f"error: {e}")
