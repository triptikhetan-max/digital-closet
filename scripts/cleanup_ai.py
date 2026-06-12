#!/usr/bin/env python3
"""Way 2 — AI cleanup with whichever key you already have.

Erases hangers/hands/background while keeping the garment IDENTICAL, using:

  provider   key (env or .env)              model
  fal        FAL_KEY                        nano-banana erase + BiRefNet matting
  gemini     GEMINI_API_KEY/GOOGLE_API_KEY  gemini-2.5-flash-image (free tier!)
  openai     OPENAI_API_KEY                 gpt-image-1 edit

Auto-detects in that order, or force one with --provider.

Usage:
    python3 scripts/cleanup_ai.py                          # closet/inbox/
    python3 scripts/cleanup_ai.py photo.jpg
    python3 scripts/cleanup_ai.py photo.jpg --desc "a grey wrap skirt, no sleeves"
    python3 scripts/cleanup_ai.py --provider gemini

--desc anchors the AI when a photo is ambiguous (held up, crumpled): say what
the garment IS and it won't invent sleeves or change its type.

Needs only Pillow. If `rembg` is installed (requirements-local.txt) the result
is also matted to a transparent PNG; otherwise it stays on clean white, which
looks identical on the app's white cards.

No key at all? Use the free path:  python3 scripts/cleanup_local.py
"""
import base64
import io
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageChops

from closetlib import INBOX, PHOTOS, ROOT, bbox_crop, ensure_dirs, load_rgb, slugify

ERASE = (
    "Remove the clothes hanger, any hands or fingers, and the background entirely. "
    "Keep the GARMENT exactly as photographed — identical type, shape, length, neckline, "
    "sleeves (or lack of sleeves), colour, print, fabric texture and details. Do NOT redesign, "
    "restyle or change proportions. Present it upright and straight, alone on a plain white background."
)
PROVIDERS = ("fal", "gemini", "openai")
KEY_VARS = {"fal": ["FAL_KEY"], "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            "openai": ["OPENAI_API_KEY"]}


def env_key(provider):
    vals = dict(os.environ)
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                vals.setdefault(k.strip(), v.strip().strip("'\""))
    for var in KEY_VARS[provider]:
        if vals.get(var):
            return vals[var]
    return None


def pick_provider(forced):
    if forced:
        key = env_key(forced)
        if not key:
            sys.exit(f"--provider {forced} but no {' / '.join(KEY_VARS[forced])} found "
                     "(set the env var or put it in .env)")
        return forced, key
    for p in PROVIDERS:
        key = env_key(p)
        if key:
            return p, key
    sys.exit("No AI key found. Set ONE of: FAL_KEY, GEMINI_API_KEY (free tier at "
             "aistudio.google.com), OPENAI_API_KEY — or use the keyless path: "
             "python3 scripts/cleanup_local.py")


def jpeg_bytes(img: Image.Image, maxdim=1280) -> bytes:
    img = img.copy()
    img.thumbnail((maxdim, maxdim))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def post_json(url, payload, headers, timeout=200):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def erase_fal(img, key, prompt):
    uri = "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes(img)).decode()
    res = post_json("https://fal.run/fal-ai/gemini-25-flash-image/edit",
                    {"image_urls": [uri], "prompt": prompt, "sync_mode": True},
                    {"Authorization": f"Key {key}"})
    url = (res.get("images", [{}])[0] or {}).get("url", "")
    if url.startswith("data:"):
        return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))
    raise RuntimeError("fal: no image returned")


def matte_fal(img, key):
    uri = "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes(img.convert("RGB"))).decode()
    res = post_json("https://fal.run/fal-ai/birefnet",
                    {"image_url": uri, "sync_mode": True},
                    {"Authorization": f"Key {key}"})
    url = (res.get("image") or {}).get("url", "")
    if url.startswith("data:"):
        return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGBA")
    return None


def erase_gemini(img, key, prompt):
    payload = {"contents": [{"parts": [
        {"text": prompt},
        {"inline_data": {"mime_type": "image/jpeg",
                         "data": base64.b64encode(jpeg_bytes(img)).decode()}},
    ]}]}
    res = post_json(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent",
        payload, {"x-goog-api-key": key})
    for cand in res.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob and blob.get("data"):
                return Image.open(io.BytesIO(base64.b64decode(blob["data"])))
    raise RuntimeError("gemini: no image returned (check the key has image output enabled)")


def erase_openai(img, key, prompt):
    boundary = f"----closet{int(time.time() * 1000)}"
    parts = []
    for name, val in (("model", "gpt-image-1"), ("prompt", prompt), ("size", "auto")):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{val}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
                 f"filename=\"garment.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode()
                 + jpeg_bytes(img) + b"\r\n")
    body = b"".join(parts) + f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/edits", data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    b64 = (res.get("data", [{}])[0] or {}).get("b64_json")
    if not b64:
        raise RuntimeError("openai: no image returned")
    return Image.open(io.BytesIO(base64.b64decode(b64)))


def to_cutout(white_bg: Image.Image, provider, key):
    """Erased image (garment on white) -> transparent PNG, best effort."""
    if provider == "fal":
        cut = matte_fal(white_bg, key)
        if cut is not None:
            return bbox_crop(cut)
    try:  # local matting if extras are installed
        import numpy as np
        from scipy import ndimage
        from rembg import new_session, remove
        if not hasattr(to_cutout, "_sess"):
            to_cutout._sess = new_session("isnet-general-use")
        img = white_bg.convert("RGB")
        img.thumbnail((1400, 1400))
        arr = np.array(remove(img, session=to_cutout._sess))
        a = arr[:, :, 3]
        if a.max():
            lbl, _ = ndimage.label(a > 30)
            counts = np.bincount(lbl.ravel())
            counts[0] = 0
            arr[:, :, 3] = np.where(lbl == counts.argmax(), a, 0)
            return bbox_crop(Image.fromarray(arr))
    except ImportError:
        pass
    # Pillow-only fallback: knock out near-white background (white garments stay
    # on a white card — visually identical in the app).
    rgba = white_bg.convert("RGBA")
    diff = ImageChops.difference(rgba.convert("RGB"), Image.new("RGB", rgba.size, "white"))
    mask = diff.convert("L").point(lambda v: 0 if v < 16 else 255)
    rgba.putalpha(mask)
    out = bbox_crop(rgba)
    return out if out.getbbox() else white_bg.convert("RGBA")


def main():
    args = sys.argv[1:]
    desc = forced = None
    if "--desc" in args:
        i = args.index("--desc")
        desc = args[i + 1]
        args = args[:i] + args[i + 2:]
    if "--provider" in args:
        i = args.index("--provider")
        forced = args[i + 1]
        args = args[:i] + args[i + 2:]
        if forced not in PROVIDERS:
            sys.exit(f"--provider must be one of {PROVIDERS}")
    ensure_dirs()
    srcs = [Path(p) for p in args] or sorted(
        p for p in INBOX.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"))
    if not srcs:
        sys.exit("Nothing to clean — drop photos in closet/inbox/ first.")
    provider, key = pick_provider(forced)
    print(json.dumps({"provider": provider, "items": len(srcs)}))
    erase = {"fal": erase_fal, "gemini": erase_gemini, "openai": erase_openai}[provider]
    prompt = (f"This garment is {desc}. " if desc else "") + ERASE
    for src in srcs:
        try:
            img = load_rgb(src)
            erased = None
            for attempt in range(2):
                try:
                    erased = erase(img, key, prompt)
                    break
                except Exception:
                    if attempt == 0:
                        time.sleep(2)
                    else:
                        raise
            out = PHOTOS / f"{slugify(src.stem)}.png"
            to_cutout(erased, provider, key).save(out)
            print(json.dumps({"src": str(src), "out": str(out)}))
        except Exception as e:
            print(json.dumps({"src": str(src), "error": repr(e)[:140]}))


if __name__ == "__main__":
    main()
