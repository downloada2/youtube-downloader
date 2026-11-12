"""YouTube Downloader for Windows and macOS: audio (MP3) or video (MP4).

One app, one switch - just yt-dlp + ffmpeg, no stem separation. The window is
an Edge WebView2 page (ui/index.html) in the same visual language as AI Music
Splitter; this file is the engine behind it. Every Api attribute that the page
must NOT call is `_`-prefixed (pywebview exposes the rest).
"""
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

APP_HOME = Path.home() / "YouTube Downloader"

# A --windowed exe has no stdout/stderr, and yt-dlp writes to them.
if sys.stdout is None or sys.stderr is None:
    try:
        APP_HOME.mkdir(parents=True, exist_ok=True)
        _f = open(APP_HOME / "app.log", "a", encoding="utf-8", buffering=1)
    except OSError:
        _f = open(os.devnull, "w")
    sys.stdout = sys.stdout or _f
    sys.stderr = sys.stderr or _f

import yt_dlp

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
TITLE = "YouTube Downloader"
VERSION = "3.0"
AUDIO_Q = ["320 kbps", "192 kbps", "128 kbps"]
VIDEO_Q = ["Лучшее", "1080p", "720p", "480p", "360p"]
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def ffmpeg_location() -> str:
    if IS_WIN:
        return str(ROOT / "ffmpeg")
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def default_dir(video: bool) -> Path:
    p = Path.home() / (("Videos" if IS_WIN else "Movies") if video else "Music")
    return p if p.exists() else Path.home() / "Downloads"


def build_opts(video: bool, quality: str, outdir: Path, playlist: bool, hook) -> dict:
    o = {
        "outtmpl": str(outdir / "%(title).150s.%(ext)s"),
        "noplaylist": not playlist,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "progress_hooks": [hook],
        "windowsfilenames": True,
        "ffmpeg_location": ffmpeg_location(),
    }
    if video:
        h = quality.rstrip("p")
        cap = f"[height<={h}]" if h.isdigit() else ""
        o["format"] = f"bv*{cap}[ext=mp4]+ba[ext=m4a]/bv*{cap}+ba/b{cap}/b"
        o["merge_output_format"] = "mp4"
    else:
        o["format"] = "bestaudio/best"
        o["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
             "preferredquality": quality.split()[0]},
            {"key": "FFmpegMetadata"},
        ]
    return o


def _clipboard_text() -> str:
    """Plain OS clipboard read (the WebView can't without a permission prompt)."""
    if not IS_WIN:
        return subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=3).stdout
    import ctypes
    from ctypes import wintypes
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    u32.GetClipboardData.argtypes = [wintypes.UINT]
    u32.GetClipboardData.restype = wintypes.HANDLE
    k32.GlobalLock.argtypes = [wintypes.HANDLE]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalUnlock.argtypes = [wintypes.HANDLE]
    if not u32.OpenClipboard(None):
        return ""
    try:
        h = u32.GetClipboardData(13)  # CF_UNICODETEXT
        if not h:
            return ""
        p = k32.GlobalLock(h)
        try:
            return ctypes.wstring_at(p) or ""
        finally:
            k32.GlobalUnlock(h)
    finally:
        u32.CloseClipboard()


def _entries(info):
    """Yield (title, filepath) for a finished single video or playlist."""
    if not info:
        return
    items = info.get("entries") or [info]
    for e in items:
        if not e:
            continue
        rd = e.get("requested_downloads") or []
        path = (rd[0].get("filepath") if rd else None) or e.get("filepath")
        yield e.get("title") or "", path


class Api:
    def __init__(self):
        self._window = None
        self._lock = threading.Lock()
        self._cfg_path = APP_HOME / "config.json"
        self._cfg = {}
        try:
            self._cfg = json.loads(self._cfg_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        self._job = {"state": "idle"}
        self._cancel = False
        self._history = list(self._cfg.get("history", []))
        self._exit_ok = False

    # ---- config
    def _save(self):
        try:
            APP_HOME.mkdir(parents=True, exist_ok=True)
            self._cfg["history"] = self._history[:40]
            self._cfg_path.write_text(json.dumps(self._cfg, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def get_state(self):
        return {
            "theme": self._cfg.get("theme", "night"),
            "mode": self._cfg.get("mode", "audio"),
            "dirs": {
                "audio": self._cfg.get("dir_audio") or str(default_dir(False)),
                "video": self._cfg.get("dir_video") or str(default_dir(True)),
            },
            "history": [h for h in self._history if Path(h["path"]).exists()],
            "version": VERSION, "platform": "mac" if IS_MAC else "win",
            "audio_q": AUDIO_Q, "video_q": VIDEO_Q,
        }

    def set_theme(self, theme):
        self._cfg["theme"] = "classic" if theme == "classic" else "night"
        self._save()

    def set_mode(self, mode):
        self._cfg["mode"] = "video" if mode == "video" else "audio"
        self._save()

    # ---- helpers for the page
    def paste(self):
        try:
            return _clipboard_text().strip()
        except Exception:  # noqa: BLE001
            return ""

    def pick_folder(self, current):
        import webview
        res = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=current or "")
        return res[0] if res else None

    def open_folder(self, path):
        p = Path(path)
        target = p if p.is_dir() else p.parent
        target.mkdir(parents=True, exist_ok=True)
        if IS_WIN:
            os.startfile(target)
        else:
            subprocess.Popen(["open", str(target)])

    def reveal(self, path):
        if not Path(path).exists():
            return self.open_folder(path)
        if IS_WIN:
            subprocess.Popen(["explorer", f"/select,{path}"])
        else:
            subprocess.Popen(["open", "-R", path])

    def open_file(self, path):
        if Path(path).exists():
            if IS_WIN:
                os.startfile(path)
            else:
                subprocess.Popen(["open", path])

    def clear_history(self):
        self._history = []
        self._save()

    def exit_app(self):
        self._exit_ok = True
        self._window.destroy()

    # ---- download
    def start(self, url, mode, quality, playlist, outdir):
        url = (url or "").strip()
        if not url.startswith("http"):
            return {"ok": False, "error": "bad_url"}
        with self._lock:
            if self._job.get("state") == "running":
                return {"ok": False, "error": "busy"}
            video = mode == "video"
            out = Path(outdir)
            try:
                out.mkdir(parents=True, exist_ok=True)
            except OSError as ex:
                return {"ok": False, "error": f"Папка недоступна: {ex}"}
            self._cfg["dir_video" if video else "dir_audio"] = str(out)
            self._save()
            self._cancel = False
            self._job = {"state": "running", "pct": 0.0, "stage": "connect", "detail": "",
                         "title": "", "mode": mode, "started": time.time()}
        threading.Thread(target=self._work, args=(url, out, video, quality, bool(playlist)), daemon=True).start()
        return {"ok": True}

    def cancel(self):
        self._cancel = True

    def poll(self):
        j = dict(self._job)
        if j.get("state") != "running":
            self._job = {"state": "idle"} if j.get("state") in ("done", "error", "cancelled") else self._job
        return j

    def _set(self, **kw):
        self._job.update(kw)

    def _work(self, url, outdir, video, quality, playlist):
        def hook(d):
            if self._cancel:
                raise yt_dlp.utils.DownloadCancelled()
            info = d.get("info_dict") or {}
            idx, n = info.get("playlist_index") or 1, info.get("n_entries") or 1
            if d["status"] == "downloading":
                tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                p = (d["downloaded_bytes"] / tot) if tot else 0.0
                self._set(pct=((idx - 1) + p) / n, stage="download", title=info.get("title") or self._job.get("title", ""),
                          detail=(f"{idx} из {n}" if n > 1 else ""), speed=d.get("speed") or 0, eta=d.get("eta"))
            elif d["status"] == "finished":
                self._set(stage="convert", pct=idx / n, title=info.get("title") or self._job.get("title", ""))

        try:
            with yt_dlp.YoutubeDL(build_opts(video, quality, outdir, playlist, hook)) as y:
                info = y.extract_info(url, download=True)
            got = [(t, p) for t, p in _entries(info) if p]
            for t, p in got:
                self._history.insert(0, {"title": t or Path(p).stem, "path": p, "mode": "video" if video else "audio",
                                         "size": Path(p).stat().st_size if Path(p).exists() else 0, "ts": int(time.time())})
            self._save()
            self._job = {"state": "done", "count": len(got), "title": got[0][0] if got else "",
                         "path": got[0][1] if got else str(outdir), "mode": "video" if video else "audio",
                         "history": [h for h in self._history if Path(h["path"]).exists()]}
        except yt_dlp.utils.DownloadCancelled:
            self._job = {"state": "cancelled"}
        except Exception as ex:  # noqa: BLE001 - shown to the user
            if self._cancel:
                self._job = {"state": "cancelled"}
            else:
                msg = ANSI.sub("", str(ex)).replace("ERROR: ", "").strip()
                self._job = {"state": "error", "error": msg[:400]}


BRIDGE_PORT = 47653


def start_bridge(api):
    """Local 127.0.0.1 endpoint for the Chrome extension (only chrome-extension:// origins are accepted)."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _origin_ok(self):
            return (self.headers.get("Origin") or "").startswith("chrome-extension://")

        def _send(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", ""))
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self._send(204 if self._origin_ok() else 403, {})

        def do_GET(self):
            if not self._origin_ok():
                return self._send(403, {"ok": False})
            self._send(200, {"ok": True, "app": "ytdl", "version": VERSION, "busy": self._busy()})

        def _busy(self):
            return api._job.get("state") == "running"

        def do_POST(self):
            if not self._origin_ok():
                return self._send(403, {"ok": False})
            try:
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except ValueError:
                return self._send(400, {"ok": False, "error": "bad_json"})
            url = str(data.get("url", ""))
            host = (urlparse(url).hostname or "").lower()
            if not (host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")):
                return self._send(400, {"ok": False, "error": "bad_url"})
            if self._busy():
                return self._send(200, {"ok": False, "error": "busy"})
            mode = "video" if data.get("mode") == "video" else "audio"
            try:
                api._window.evaluate_js(f"window.extDownload({json.dumps(url)}, {json.dumps(mode)})")
            except Exception:  # noqa: BLE001
                return self._send(200, {"ok": False, "error": "window"})
            self._send(200, {"ok": True})

    try:
        srv = ThreadingHTTPServer(("127.0.0.1", BRIDGE_PORT), H)
    except OSError:
        return
    threading.Thread(target=srv.serve_forever, daemon=True).start()


def _selftest_ffmpeg():
    r = subprocess.run([str(Path(ffmpeg_location()) / "ffmpeg.exe") if IS_WIN else ffmpeg_location(), "-version"],
                       capture_output=True, text=True)
    print(r.stdout.splitlines()[0] if r.stdout else r.stderr)
    return r.returncode


def _selftest():
    url = sys.argv[sys.argv.index("--selftest") + 1]
    video = "--video" in sys.argv
    out = Path(os.environ.get("TEMP", "/tmp")) / "ytdl_selftest"
    out.mkdir(exist_ok=True)
    with yt_dlp.YoutubeDL(build_opts(video, (VIDEO_Q if video else AUDIO_Q)[-1], out, False,
                                     lambda d: None)) as y:
        y.extract_info(url, download=True)
    (out / "selftest.ok").write_text("OK " + ",".join(p.name for p in out.iterdir()), encoding="utf-8")


def main():
    if "--selftest-ffmpeg" in sys.argv:
        sys.exit(_selftest_ffmpeg())
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    import webview

    api = Api()
    night = api._cfg.get("theme") != "classic"
    window = webview.create_window(
        TITLE, js_api=api,
        # macOS: a file:// URL keeps pywebview from starting a local HTTP server
        # (which triggers the "find devices on local networks" prompt).
        url=str(ROOT / "ui" / "index.html") if IS_WIN else (ROOT / "ui" / "index.html").as_uri(),
        width=1160, height=690 if IS_WIN else 740, min_size=(900, 560),
        # Windows at 225% DPI: pywebview centres off-screen, so pin the position.
        **({"x": 40, "y": 12} if IS_WIN else {}),
        background_color="#07060F" if night else "#F5F2FC", text_select=False,
    )
    api._window = window
    start_bridge(api)

    def on_closing():
        # Every close (X, Alt+F4, taskbar) asks "Выйти?" in the page first.
        if api._exit_ok:
            return True
        threading.Thread(target=lambda: window.evaluate_js("window.askExit && window.askExit()"), daemon=True).start()
        return False

    window.events.closing += on_closing
    def smoke():
        # CI check (YTDL_SMOKE=<file>): load the page, prove the JS bridge + fonts work, quit.
        time.sleep(8)
        try:
            res = window.evaluate_js(
                "JSON.stringify({api: !!window.pywebview, go: !!document.querySelector('#btnGo'),"
                " fonts: [...document.fonts].map(f => f.family + ':' + f.status)})")
        except Exception as ex:  # noqa: BLE001
            res = "ERR " + repr(ex)
        Path(os.environ["YTDL_SMOKE"]).write_text(str(res), encoding="utf-8")
        api._exit_ok = True
        window.destroy()

    webview.start(smoke if os.environ.get("YTDL_SMOKE") else None,
                  gui="edgechromium" if IS_WIN else None, debug="--debug" in sys.argv,
                  storage_path=str(APP_HOME / ".webview"), private_mode=False)


if __name__ == "__main__":
    main()
