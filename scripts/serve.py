#!/usr/bin/env python3
"""Run the closet as a private local web app (with gallery upload).

    python3 scripts/serve.py            # http://localhost:8765
    python3 scripts/serve.py 9000       # custom port

Open the printed phone link on your phone (same Wi-Fi) and "Add from gallery"
uploads photos straight into closet/inbox/ — then run a cleanup script (or ask
Claude Code to "add my clothes") to catalog them.

Private by design: binds to your machine/LAN only, nothing leaves your network
except the weather lookup in the page itself.
"""
import json
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from closetlib import CLOSET, INBOX, ROOT, ensure_dirs, load_wardrobe

TEMPLATE = ROOT / "app" / "template.html"
EXT_OK = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif"}
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif", ".heic": "image/heic"}


def page() -> bytes:
    items, allowed = [], set()
    for it in load_wardrobe():
        photo = it.get("photo", "")
        p = Path(photo)
        if not p.is_absolute():
            p = CLOSET / photo
        if p.exists():
            allowed.add(str(p))
        items.append({
            "id": it.get("id"), "name": it.get("name", ""), "type": it.get("type", "top"),
            "img": "/file?p=" + str(p).replace(" ", "%20"),
            "formality": it.get("formality", "casual"), "warmth": it.get("warmth", "medium"),
            "seasons": it.get("seasons", []), "colors": it.get("colors", []),
            "vibe": it.get("vibe", ""), "tags": it.get("tags", []),
        })
    page.allowed = allowed
    return TEMPLATE.read_text().replace("__DATA__", json.dumps(items)).encode()


page.allowed = set()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            self._send(200, page())
        elif u.path == "/file":
            p = unquote(u.query[2:]) if u.query.startswith("p=") else ""
            if p in page.allowed and Path(p).exists():
                data = Path(p).read_bytes()
                self._send(200, data, MIME.get(Path(p).suffix.lower(), "application/octet-stream"))
            else:
                self._send(404, b"not found", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path != "/api/upload":
            self._send(404, b"not found", "text/plain")
            return
        name = unquote(self.headers.get("X-Filename", "photo.jpg"))
        ext = Path(name).suffix.lower() or ".jpg"
        if ext not in EXT_OK:
            self._send(400, b'{"error":"unsupported type"}', "application/json")
            return
        size = int(self.headers.get("Content-Length", 0))
        if not 0 < size <= 30_000_000:
            self._send(400, b'{"error":"bad size"}', "application/json")
            return
        out = INBOX / f"{time.strftime('%Y%m%d-%H%M%S')}-{int(time.time()*1000) % 1000:03d}{ext}"
        out.write_bytes(self.rfile.read(size))
        self._send(200, json.dumps({"saved": out.name}).encode(), "application/json")


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    ensure_dirs()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"Your closet:   http://localhost:{port}")
    print(f"On your phone: http://{lan_ip()}:{port}   (same Wi-Fi)")
    print("Ctrl+C to stop. Uploads land in closet/inbox/.")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


if __name__ == "__main__":
    main()
