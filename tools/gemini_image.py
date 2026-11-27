#!/usr/bin/env python3
"""Create or edit an image with Gemini (thumbnail backgrounds, concepts, overlays).

Usage: gemini_image.py "<prompt>" --out out/gemini/images/<name>.png [--ref IMAGE ...] [--aspect 16:9]
       [--model NAME]
Images are drafts: the owner approves them before use. Never present a generated picture as an
in-engine result or as game footage. References are sent to Google.
"""
import argparse
import base64
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_client as gc  # noqa: E402

DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", action="append", default=[], help="reference image (repeatable)")
    ap.add_argument("--aspect", default="16:9", choices=["16:9", "9:16", "1:1", "4:5", "3:4"])
    ap.add_argument("--model", default=DEFAULT_IMAGE_MODEL)
    a = ap.parse_args()
    try:
        used, cap = gc.tokens_today(), gc.daily_cap()
        if used >= cap:
            raise gc.GeminiError(f"daily Gemini token cap reached ({used}/{cap})")
        for ref in a.ref:
            if gc.is_secret_file(ref) or Path(ref).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                raise gc.GeminiError(f"not an image reference: {ref}")
        parts = [gc.text_part(a.prompt), *[gc.image_part(r) for r in a.ref]]
        body = {"contents": [{"parts": parts}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": a.aspect}}}
        req = urllib.request.Request(f"{gc.API}/v1beta/models/{a.model}:generateContent",
                                     data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": gc.load_key()})
        data = json.loads(gc._request(req, timeout=600)[0].decode())
        gc.log_usage(a.model, "image", data.get("usageMetadata", {}))
        candidates = data.get("candidates") or [{}]
        answer = candidates[0].get("content", {}).get("parts", [])
        blob = next((p.get("inlineData") or p.get("inline_data") for p in answer
                     if p.get("inlineData") or p.get("inline_data")), None)
        if not blob:
            raise gc.GeminiError("Gemini returned no image: " + " ".join(p.get("text", "") for p in answer)[:300])
    except (gc.GeminiError, OSError) as e:
        gc.die(e)
    mime = blob.get("mimeType") or blob.get("mime_type") or "image/png"
    out = Path(a.out).with_suffix({"image/jpeg": ".jpg", "image/webp": ".webp"}.get(mime, ".png"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(blob["data"]))
    print(f"ok: {a.model} image -> {out}")


if __name__ == "__main__":
    main()
