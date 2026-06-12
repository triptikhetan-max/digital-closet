"""Shared helpers for the digital-closet scripts."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CLOSET = ROOT / "closet"
INBOX = CLOSET / "inbox"
PHOTOS = CLOSET / "photos"
WARDROBE = CLOSET / "wardrobe.json"


def ensure_dirs():
    for d in (CLOSET, INBOX, PHOTOS):
        d.mkdir(parents=True, exist_ok=True)
    if not WARDROBE.exists():
        WARDROBE.write_text("[]\n")


def load_wardrobe():
    ensure_dirs()
    return json.loads(WARDROBE.read_text())


def save_wardrobe(items):
    WARDROBE.write_text(json.dumps(items, indent=2) + "\n")


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "item"


def load_rgb(path) -> Image.Image:
    """Open any image as RGB; falls back to `sips` for HEIC on macOS."""
    path = Path(path)
    try:
        return Image.open(path).convert("RGB")
    except Exception:
        if sys.platform == "darwin" and path.suffix.lower() in (".heic", ".heif"):
            tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
            subprocess.run(
                ["sips", "-s", "format", "jpeg", str(path), "--out", str(tmp)],
                check=True, capture_output=True,
            )
            return Image.open(tmp).convert("RGB")
        raise


def bbox_crop(img: Image.Image, pad: int = 14) -> Image.Image:
    """Trim a transparent RGBA image to its content plus a little padding."""
    bb = img.getbbox()
    if not bb:
        return img
    x0, y0, x1, y1 = bb
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(img.width, x1 + pad), min(img.height, y1 + pad)
    return img.crop((x0, y0, x1, y1))
