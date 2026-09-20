"""Local review dashboard: play every test/created video before uploading to YouTube.

    python dashboard/server.py            # opens http://127.0.0.1:8765

Serves only video files found under the whitelisted folders below (by id, never by raw path), with HTTP Range
support so seeking works. Binds to localhost only. Review notes are saved to dashboard/review.json.

Remote access: set DASHBOARD_PASSWORD and every request must carry it (HTTP Basic, any username). Reach it from
anywhere through a tunnel to 127.0.0.1 -- see operate/README.md. With no password set it stays open, which is only
acceptable while nothing but this machine can reach the port.
"""
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import unicodedata
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
THUMBS = HERE / ".thumbs"
REVIEW = HERE / "review.json"
PORT = 8765
PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")
EXTS = {".mp4", ".webm", ".mov", ".mkv", ".m4v"}

# (folder, recursive) -> group classifier below
SOURCES = [(ROOT / "video", False), (ROOT / "blender_agent" / "work", True), (ROOT / "reference vedios", True),
           (ROOT / "recreate" / "out", False)]

# Uploads arrive as sequential raw-byte chunks (one POST each) so a file of any size passes a tunnel that caps a
# single request body (Cloudflare's free tier: 100 MB). The bytes accumulate in "<name>.part", which scan() ignores,
# and become "<name>" only after the last chunk lands and ffprobe can read it.
REFERENCE_DIR = ROOT / "reference vedios"
UPLOAD_CHUNK_MAX = 64 * 1024 * 1024
UPLOAD_DISK_HEADROOM = 2 * 1024 ** 3

_meta_cache = {}
_lock = threading.Lock()
_upload_lock = threading.Lock()


def vid_id(path: Path) -> str:
    return hashlib.sha1(str(path.relative_to(ROOT)).replace("\\", "/").encode()).hexdigest()[:12]


def classify(path: Path) -> str:
    rel = path.relative_to(ROOT).parts
    name = path.stem.lower()
    if rel[0] == "reference vedios":
        return "Reference"
    if rel[0] == "blender_agent":
        return "Blender segments"
    # A rebuild of a reference clip measures the agent; it is someone else's script and
    # art, so it must never sit in the group that feeds uploads.
    if rel[0] == "recreate":
        return "Recreations (benchmarks)"
    if name.startswith("recreation_"):
        return "Recreations (benchmarks)"
    if name.startswith("_") or "test" in name or "preview" in name:
        return "Tests & previews"
    return "Created"


def scan():
    out = []
    for folder, recursive in SOURCES:
        if not folder.exists():
            continue
        for p in (folder.rglob("*") if recursive else folder.glob("*")):
            if p.suffix.lower() in EXTS and p.is_file() and not p.stem.endswith("_raw"):
                out.append(p)
    return sorted(out, key=lambda p: p.stat().st_mtime, reverse=True)


def probe(path: Path) -> dict:
    st = path.stat()
    key = (str(path), st.st_mtime, st.st_size)
    with _lock:
        if key in _meta_cache:
            return _meta_cache[key]
    info = {"duration": 0, "width": 0, "height": 0, "fps": 0, "audio": False, "vcodec": ""}
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                           capture_output=True, text=True, timeout=30, encoding="utf-8", errors="ignore")
        data = json.loads(r.stdout or "{}")
        info["duration"] = float(data.get("format", {}).get("duration") or 0)
        for s in data.get("streams", []):
            if s.get("codec_type") == "video" and not info["width"]:
                info.update(width=s.get("width", 0), height=s.get("height", 0), vcodec=s.get("codec_name", ""))
                try:
                    n, d = s.get("r_frame_rate", "0/1").split("/")
                    info["fps"] = round(float(n) / float(d), 1) if float(d) else 0
                except Exception:
                    pass
            elif s.get("codec_type") == "audio":
                info["audio"] = True
    except Exception:
        pass
    with _lock:
        _meta_cache[key] = info
    return info


def suggest_title(path: Path) -> str:
    """Prefer the title stored in the matching script/plan json; fall back to a cleaned filename."""
    base = re.sub(r"(_final|_blender|_preview|_normal|_shorts)+$", "", path.stem)
    for cand in (ROOT / "scripts" / f"{base}_script.json", ROOT / "blender_agent" / "work" / base / "plan.json"):
        try:
            t = json.loads(cand.read_text(encoding="utf-8")).get("title")
            if t:
                return t
        except Exception:
            pass
    return re.sub(r"[_\-]+", " ", base).strip().title()


def video_list():
    items = []
    for p in scan():
        m = probe(p)
        items.append({"id": vid_id(p), "name": p.name, "rel": str(p.relative_to(ROOT)).replace("\\", "/"), "group": classify(p),
                      "size": p.stat().st_size, "mtime": p.stat().st_mtime, "title": suggest_title(p), **m})
    return items


def find_by_id(i: str):
    return next((p for p in scan() if vid_id(p) == i), None)


def thumb_for(path: Path):
    THUMBS.mkdir(exist_ok=True)
    out = THUMBS / f"{vid_id(path)}_{int(path.stat().st_mtime)}.jpg"
    if not out.exists():
        dur = probe(path)["duration"]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{min(1.0, dur / 3):.2f}", "-i", str(path), "-frames:v", "1",
                        "-vf", "scale=320:-2", str(out)], capture_output=True, timeout=60)
    return out if out.exists() else None


def sanitise_upload_name(raw: str):
    """Bare file name safe to create inside REFERENCE_DIR, or None when it is not a video name we accept."""
    name = unicodedata.normalize("NFC", raw).replace("\\", "/").rsplit("/", 1)[-1]
    stem, ext = os.path.splitext(re.sub(r"[^\w .()\[\]-]", "_", name).strip(" ."))
    if ext.lower() not in EXTS or not stem.strip(" ._-"):
        return None
    return stem[:120].rstrip(" .") + ext.lower()


def choose_free_name(name: str) -> str:
    """`name` if unused in REFERENCE_DIR, else `stem (2).ext`, `stem (3).ext` ... -- never overwrites an existing video."""
    stem, ext = os.path.splitext(name)
    candidate, n = name, 1
    while (REFERENCE_DIR / candidate).exists():
        n += 1
        candidate = f"{stem} ({n}){ext}"
    return candidate


def receive_upload_chunk(name: str, offset: int, total: int, body: bytes):
    """Append one chunk to REFERENCE_DIR/<name>.part; (http_status, json_dict). The final chunk publishes the file."""
    with _upload_lock:
        REFERENCE_DIR.mkdir(exist_ok=True)
        part = REFERENCE_DIR / (name + ".part")
        if offset == 0:
            if shutil.disk_usage(REFERENCE_DIR).free < total + UPLOAD_DISK_HEADROOM:
                return 507, {"error": "not enough free disk space on the server"}
            part.write_bytes(b"")
        have = part.stat().st_size if part.exists() else 0
        if have != offset:
            return 409, {"error": "chunk offset does not match what the server holds", "received": have}
        if offset + len(body) > total:
            part.unlink(missing_ok=True)
            return 400, {"error": "upload is larger than the announced size"}
        with open(part, "ab") as fh:
            fh.write(body)
        if offset + len(body) < total:
            return 200, {"done": False, "received": offset + len(body)}
        final = REFERENCE_DIR / choose_free_name(name)
        part.rename(final)
    if not probe(final)["duration"]:
        final.unlink(missing_ok=True)
        return 422, {"error": "file is not a readable video (ffprobe found no duration)"}
    return 200, {"done": True, "name": final.name, "size": total}


def load_review():
    try:
        return json.loads(REVIEW.read_text(encoding="utf-8"))
    except Exception:
        return {}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body: bytes, ctype="application/json", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def is_authorised(self) -> bool:
        """True when no password is configured, or the request carries it as the HTTP Basic password."""
        if not PASSWORD:
            return True
        header = self.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                given = base64.b64decode(header[6:]).decode("utf-8", "ignore").partition(":")[2]
            except ValueError:
                return False
            return hmac.compare_digest(given.encode(), PASSWORD.encode())
        return False

    def refuse_unauthorised(self):
        self.close_connection = True  # the unread request body must not be parsed as the next request
        self._send(401, b"password required", "text/plain", {"WWW-Authenticate": 'Basic realm="video review"'})

    def handle_upload_chunk(self):
        """POST /api/upload?name=<file>&offset=<bytes so far>&total=<file bytes>, body = the raw next chunk."""
        query = parse_qs(urlparse(self.path).query)
        try:
            name = sanitise_upload_name(query.get("name", [""])[0])
            offset, total = int(query.get("offset", [""])[0]), int(query.get("total", [""])[0])
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            name, offset, total, length = None, -1, 0, 0
        problem = None
        if name is None:
            problem = (400, "not an accepted video file name (allowed: " + ", ".join(sorted(EXTS)) + ")")
        elif offset < 0 or total <= 0 or length <= 0:
            problem = (400, "bad offset, total or empty chunk")
        elif length > UPLOAD_CHUNK_MAX:
            problem = (413, f"chunk larger than {UPLOAD_CHUNK_MAX} bytes")
        if problem:
            self.close_connection = True
            return self._send(problem[0], json.dumps({"error": problem[1]}).encode())
        body = self.rfile.read(length)
        if len(body) != length:
            self.close_connection = True
            return
        code, result = receive_upload_chunk(name, offset, total, body)
        self._send(code, json.dumps(result).encode())

    def _file(self, path: Path, ctype: str):
        size = path.stat().st_size
        start, end, code = 0, size - 1, 200
        rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else size - 1
                elif m.group(2):
                    start = max(0, size - int(m.group(2)))
                end = min(end, size - 1)
                if start > end:
                    return self._send(416, b"", extra={"Content-Range": f"bytes */{size}"})
                code = 206
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(path, "rb") as fh:
            fh.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = fh.read(min(256 * 1024, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)

    def do_GET(self):
        try:
            if not self.is_authorised():
                return self.refuse_unauthorised()
            url = urlparse(self.path).path
            if url in ("/", "/index.html"):
                return self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
            if url == "/api/videos":
                return self._send(200, json.dumps({"videos": video_list(), "review": load_review()}).encode())
            m = re.fullmatch(r"/(video|thumb)/([0-9a-f]{12})(?:\.jpg)?", unquote(url))
            if m:
                p = find_by_id(m.group(2))
                if p is None:
                    return self._send(404, b"not found", "text/plain")
                if m.group(1) == "thumb":
                    t = thumb_for(p)
                    return self._file(t, "image/jpeg") if t else self._send(404, b"no thumb", "text/plain")
                return self._file(p, mimetypes.guess_type(p.name)[0] or "video/mp4")
            self._send(404, b"not found", "text/plain")
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass

    def do_POST(self):
        try:
            if not self.is_authorised():
                return self.refuse_unauthorised()
            path = urlparse(self.path).path
            if path == "/api/upload":
                return self.handle_upload_chunk()
            if path != "/api/review":
                return self._send(404, b"not found", "text/plain")
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(n) or b"{}")
            rel, entry = data.get("rel"), data.get("entry")
            if not isinstance(rel, str) or not isinstance(entry, dict):
                return self._send(400, b'{"error":"bad request"}')
            clean = {k: str(entry.get(k, ""))[:5000] for k in ("status", "title", "description", "notes")}
            if clean["status"] not in ("pending", "approved", "rejected"):
                clean["status"] = "pending"
            review = load_review()
            review[rel] = clean
            REVIEW.write_text(json.dumps(review, indent=2), encoding="utf-8")
            self._send(200, b'{"ok":true}')
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"Video review dashboard running at {url}  (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
