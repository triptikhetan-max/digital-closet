#!/usr/bin/env python3
"""Way 1 — FREE local cleanup (no API key).

Cuts each garment photo into a clean transparent PNG using rembg (isnet)
on your own machine. Good quality; struggles only when the garment colour
matches the background or someone is holding the item up.

Usage:
    python3 scripts/cleanup_local.py                 # everything in closet/inbox/
    python3 scripts/cleanup_local.py photo1.jpg ...  # specific files

Needs:  pip install -r requirements-local.txt   (rembg, numpy, scipy, pillow)
Output: closet/photos/<name>.png  + one JSON line per item for cataloging.
"""
import json
import sys
from pathlib import Path

from closetlib import INBOX, PHOTOS, bbox_crop, ensure_dirs, load_rgb, slugify

try:
    import numpy as np
    from scipy import ndimage
    from rembg import new_session, remove
except ImportError:
    sys.exit("Local mode needs extras:  pip install -r requirements-local.txt")


def cutout(img, session):
    img.thumbnail((1400, 1400))
    arr = np.array(remove(img, session=session))
    a = arr[:, :, 3]
    if a.max() == 0:
        return None
    # keep only the largest opaque blob — drops stray clutter
    lbl, _ = ndimage.label(a > 30)
    counts = np.bincount(lbl.ravel())
    counts[0] = 0
    arr[:, :, 3] = np.where(lbl == counts.argmax(), a, 0)
    from PIL import Image
    return bbox_crop(Image.fromarray(arr))


def main():
    ensure_dirs()
    srcs = [Path(p) for p in sys.argv[1:]] or sorted(
        p for p in INBOX.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp")
    )
    if not srcs:
        sys.exit("Nothing to clean — drop photos in closet/inbox/ first.")
    session = new_session("isnet-general-use")
    for src in srcs:
        try:
            out_img = cutout(load_rgb(src), session)
            if out_img is None:
                print(json.dumps({"src": str(src), "error": "no foreground found"}))
                continue
            out = PHOTOS / f"{slugify(src.stem)}.png"
            out_img.save(out)
            print(json.dumps({"src": str(src), "out": str(out)}))
        except Exception as e:
            print(json.dumps({"src": str(src), "error": repr(e)[:120]}))


if __name__ == "__main__":
    main()
