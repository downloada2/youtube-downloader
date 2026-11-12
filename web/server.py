"""Web version of YouTube Downloader: the same page (ui/index.html) served by a tiny stdlib HTTP server.

Each browser gets a private session (random id kept in localStorage). A download runs on the server with
yt-dlp + ffmpeg into a per-session temp folder; the finished file is handed to the browser as a normal
download and deleted after a while. Only YouTube links, no playlists, one job per visitor.

    pip install yt-dlp imageio-ffmpeg        # (or ffmpeg from the OS)
    python web/server.py [--host 127.0.0.1] [--port 8080]
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yt_dlp  # noqa: E402

import yt_downloader as core  # noqa: E402

UI = ROOT / "ui"
WORK = Path(tempfile.gettempdir()) / "ytdl-web"
SID_RE = re.compile(r"^[0-9a-f]{32}$")
KEEP_SECONDS = 30 * 60          # finished files / idle sessions are deleted after this
MAX_RUNNING = 3                 # simultaneous downloads on the whole server
MAX_STARTS_PER_HOUR = 20        # per client IP
MAX_DURATION = 3 * 3600         # refuse videos longer than 3 h and live streams

_orig_build_opts = core.build_opts


def _limited_opts(*a, **kw):
    o = _orig_build_opts(*a, **kw)
    o["match_filter"] = yt_dlp.utils.match_filter_func(f"duration < {MAX_DURATION} & !is_live")
    return o


core.build_opts = _limited_opts


def _ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


core.ffmpeg_location = _ffmpeg


class WebApi(core.Api):
    """core.Api minus everything that touches the local disk config / desktop shell."""

    def __init__(self, sid):
        self._window = None
        self._lock = threading.Lock()
        self._cfg = {}
        self._job = {"state": "idle"}
        self._cancel = False
        self._history = []
        self._exit_ok = False
        self.sid = sid
        self.dir = WORK / sid
        self.files = {}
        self.seen = time.time()
        self.starts = []

    def _save(self):
        pass

    # --- file handles for the browser
    def _url(self, path):
        tok = hashlib.sha1(str(path).encode()).hexdigest()[:12]
        self.files[tok] = Path(path)
        return f"/f/{self.sid}/{tok}/{quote(Path(path).name)}"

    def _hist(self):
        return [dict(h, path=self._url(h["path"])) for h in self._history if Path(h["path"]).exists()]

    def get_state(self):
        st = super().get_state()
        st.update(platform="web", history=self._hist(), dirs={"audio": "", "video": ""})
        return st

    def poll(self):
        j = super().poll()
        if j.get("state") == "done":
            j = dict(j, history=self._hist(), path=self._url(j["path"]) if j.get("path") else "")
        return j

    def clear_history(self):
        for h in self._history:
            Path(h["path"]).unlink(missing_ok=True)
        self._history = []


SESSIONS = {}
SLOCK = threading.Lock()


def session(sid):
    with SLOCK:
        s = SESSIONS.get(sid)
        if s is None:
            s = SESSIONS[sid] = WebApi(sid)
        s.seen = time.time()
        return s


def janitor():
    while True:
        time.sleep(60)
        now = time.time()
        with SLOCK:
            for sid, s in list(SESSIONS.items()):
                if s._job.get("state") != "running" and now - s.seen > KEEP_SECONDS:
                    shutil.rmtree(s.dir, ignore_errors=True)
                    del SESSIONS[sid]
        if WORK.exists():
            for d in WORK.iterdir():
                if d.name not in SESSIONS and d.is_dir():
                    shutil.rmtree(d, ignore_errors=True)


def running_count():
    with SLOCK:
        return sum(1 for s in SESSIONS.values() if s._job.get("state") == "running")


def is_youtube(url):
    host = (urlparse(url).hostname or "").lower()
    return host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")


class H(BaseHTTPRequestHandler):
    server_version = "ytdl-web"

    def log_message(self, *a):
        pass

    def _client_ip(self):
        return (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    # ---------- static + file download
    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path.startswith("/f/"):
            return self._file(path)
        if path in ("/", "/index.html"):
            html = (UI / "index.html").read_text(encoding="utf-8")
            html = html.replace("</head>", '<script src="/shim.js"></script></head>', 1)
            return self._bytes(html.encode(), "text/html; charset=utf-8")
        if path == "/shim.js":
            return self._bytes((Path(__file__).parent / "shim.js").read_bytes(), "application/javascript")
        f = (UI / path.lstrip("/")).resolve()
        if UI in f.parents and f.is_file():
            ctype = {".ttf": "font/ttf", ".woff2": "font/woff2", ".png": "image/png", ".svg": "image/svg+xml"}.get(
                f.suffix, "application/octet-stream")
            return self._bytes(f.read_bytes(), ctype, cache=True)
        self.send_error(404)

    def _bytes(self, data, ctype, cache=False):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if cache:
            self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path):
        parts = path.split("/")  # ['', 'f', sid, tok, name]
        if len(parts) < 5 or not SID_RE.match(parts[2]):
            return self.send_error(404)
        s = SESSIONS.get(parts[2])
        p = s.files.get(parts[3]) if s else None
        if not p or not p.is_file():
            return self.send_error(404)
        s.seen = time.time()
        size = p.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(p.name)}")
        self.end_headers()
        with open(p, "rb") as fh:
            shutil.copyfileobj(fh, self.wfile, 1 << 20)

    # ---------- JSON API: POST /api/<method>  body {"args": [...]}   header X-Sid
    def do_POST(self):
        m = re.match(r"^/api/([a-z_]+)$", urlparse(self.path).path)
        sid = self.headers.get("X-Sid", "")
        if not m or not SID_RE.match(sid):
            return self._json({"error": "bad_request"}, 400)
        try:
            args = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 20000)) or b"{}").get("args", [])
        except ValueError:
            return self._json({"error": "bad_json"}, 400)
        s, name = session(sid), m.group(1)
        if name in ("get_state", "set_theme", "set_mode", "cancel", "poll", "clear_history"):
            return self._json(getattr(s, name)(*args))
        if name == "start":
            return self._json(self._start(s, args))
        self._json({"error": "unknown"}, 404)

    def _start(self, s, args):
        url, mode, quality = (args + ["", "audio", ""])[:3]
        url = str(url).strip()
        if not is_youtube(url):
            return {"ok": False, "error": "Принимаются только ссылки на YouTube"}
        mode = "video" if mode == "video" else "audio"
        allowed = core.VIDEO_Q if mode == "video" else core.AUDIO_Q
        quality = quality if quality in allowed else allowed[0]
        now = time.time()
        s.starts = [t for t in s.starts if now - t < 3600]
        ip = self._client_ip()
        with SLOCK:
            hits = [t for t in IP_STARTS.get(ip, []) if now - t < 3600]
            if len(hits) >= MAX_STARTS_PER_HOUR:
                return {"ok": False, "error": "Слишком много загрузок за час, попробуйте позже"}
            IP_STARTS[ip] = hits + [now]
        if running_count() >= MAX_RUNNING:
            return {"ok": False, "error": "Сервер занят, попробуйте через минуту"}
        s.dir.mkdir(parents=True, exist_ok=True)
        return core.Api.start(s, url, mode, quality, False, str(s.dir))


IP_STARTS = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=janitor, daemon=True).start()
    print(f"YouTube Downloader web: http://{a.host}:{a.port}")
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()


if __name__ == "__main__":
    main()
