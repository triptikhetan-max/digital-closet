#!/usr/bin/env python3
"""Way 2 — BEST quality cleanup via fal.ai (needs a FAL_KEY).

Two AI passes per photo, both garment-preserving:
  1. nano-banana "erase" edit  — removes hangers, hands and background while
     keeping the garment IDENTICAL (no redraw/restyle),
  2. BiRefNet matting          — cuts the result to a transparent PNG.

Cost: roughly $0.04 per photo. Get a key at https://fal.ai → put it in the
FAL_KEY env var or a `.env` file in the repo root (FAL_KEY=...).

Usage:
    python3 scripts/cleanup_fal.py                          # closet/inbox/
    python3 scripts/cleanup_fal.py photo.jpg                # specific files
    python3 scripts/cleanup_fal.py photo.jpg --desc "a grey wrap skirt, no sleeves"

--desc anchors the AI when a photo is ambiguous (held up by hand, crumpled):
tell it what the garment IS and it will not invent sleeves or change type.

Needs only Pillow:  pip install -r requirements.txt
Output: closet/photos/<name>.png  + one JSON line per item for cataloging.
"""
import base64
import io
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

from closetlib import INBOX, PHOTOS, ROOT, bbox_crop, ensure_dirs, load_rgb, slugify

ERASE = (
    "Remove the clothes hanger, any hands or fingers, and the background entirely. "
    "Keep the GARMENT exactly as photographed — identical type, shape, length, neckline, "
    "sleeves (or lack of sleeves), colour, print, fabric texture and details. Do NOT redesign, "
    "restyle or change proportions. Present it upright and straight, alone on a plain white background."
)


def fal_key():
    key = os.environ.get("FAL_KEY", "").strip()
    if not key:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.strip().startswith("FAL_KEY"):
                    key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        sys.exit("No FAL_KEY found. Set it:  export FAL_KEY=...  (or put FAL_KEY=... in .env)")
    return key


def data_uri(img: Image.Image, maxdim=1280) -> str:
    img = img.copy()
    img.thumbnail((maxdim, maxdim))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def call(model: str, payload: dict, key: str, timeout=200):
    req = urllib.request.Request(
        f"https://fal.run/{model}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def first_image(res):
    if not res:
        return None
    url = (res.get("images", [{}])[0] or {}).get("url") or (res.get("image") or {}).get("url")
    if url and url.startswith("data:"):
        return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))
    return None


def clean_one(src: Path, key: str, desc: str | None):
    img = load_rgb(src)
    prompt = (f"This garment is {desc}. " if desc else "") + ERASE
    erased = None
    for attempt in range(2):
        try:
            erased = first_image(call(
                "fal-ai/gemini-25-flash-image/edit",
                {"image_urls": [data_uri(img)], "prompt": prompt, "sync_mode": True}, key))
            if erased:
                break
        except Exception:
            time.sleep(2)
    if erased is None:
        raise RuntimeError("erase step failed")
    cut = first_image(call(
        "fal-ai/birefnet",
        {"image_url": data_uri(erased.convert("RGB")), "sync_mode": True}, key))
    if cut is None:
        raise RuntimeError("matting step failed")
    return bbox_crop(cut.convert("RGBA"))


def main():
    args = sys.argv[1:]
    desc = None
    if "--desc" in args:
        i = args.index("--desc")
        desc = args[i + 1]
        args = args[:i] + args[i + 2:]
    ensure_dirs()
    srcs = [Path(p) for p in args] or sorted(
        p for p in INBOX.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp")
    )
    if not srcs:
        sys.exit("Nothing to clean — drop photos in closet/inbox/ first.")
    key = fal_key()
    for src in srcs:
        try:
            out_img = clean_one(src, key, desc)
            out = PHOTOS / f"{slugify(src.stem)}.png"
            out_img.save(out)
            print(json.dumps({"src": str(src), "out": str(out)}))
        except Exception as e:
            print(json.dumps({"src": str(src), "error": repr(e)[:120]}))


if __name__ == "__main__":
    main()
