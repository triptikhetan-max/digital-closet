#!/usr/bin/env python3
"""Build the closet app as a static file from closet/wardrobe.json.

    python3 scripts/build_closet.py            -> closet/closet.html
                                                  (relative image paths; open from the closet/ folder)
    python3 scripts/build_closet.py --embed    -> closet-app.html in the repo root
                                                  (images baked in; share/AirDrop it anywhere)

For live use — including the "Add from gallery" upload button — prefer:
    python3 scripts/serve.py
"""
import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

from closetlib import CLOSET, ROOT, ensure_dirs, load_wardrobe

TEMPLATE = ROOT / "app" / "template.html"


def public_items(embed: bool):
    items = []
    for it in load_wardrobe():
        photo = it.get("photo", "")
        p = Path(photo)
        if not p.is_absolute():
            p = CLOSET / photo
        rec = {
            "id": it.get("id"), "name": it.get("name", ""), "type": it.get("type", "top"),
            "img": "", "formality": it.get("formality", "casual"),
            "warmth": it.get("warmth", "medium"), "seasons": it.get("seasons", []),
            "colors": it.get("colors", []), "vibe": it.get("vibe", ""), "tags": it.get("tags", []),
        }
        if embed:
            try:
                im = Image.open(p).convert("RGBA")
                im.thumbnail((480, 480))
                buf = io.BytesIO()
                im.save(buf, "PNG", optimize=True)
                rec["img"] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
            except Exception:
                pass
        else:
            try:
                rec["img"] = str(p.relative_to(CLOSET))
            except ValueError:
                rec["img"] = str(p)  # absolute path outside closet/ — works locally only
        items.append(rec)
    return items


def main():
    ensure_dirs()
    embed = "--embed" in sys.argv
    html = TEMPLATE.read_text().replace("__DATA__", json.dumps(public_items(embed)))
    out = (ROOT / "closet-app.html") if embed else (CLOSET / "closet.html")
    out.write_text(html)
    print(f"built {out}" + (" (self-contained, share anywhere)" if embed else ""))


if __name__ == "__main__":
    main()
