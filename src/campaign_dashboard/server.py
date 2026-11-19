"""`campaign-dashboard --serve`: the same site, rendered on request from the current files.

A poller thread stats the inputs every POLL seconds. When a size or mtime changed it reloads the data
(session logs that did not change are not parsed again) and tells open pages over /events, so they
fetch themselves again and swap in what changed. Pages are rendered only when someone asks for them.
Binds to 127.0.0.1 only: the pages show your prompts.
"""

import hashlib
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .render import ASSETS, STATIC, Renderer, static_file

POLL = 2.0  # seconds between checks for changed files
PING = 15.0  # seconds between keep-alive comments on /events
TYPES = {".css": "text/css", ".js": "text/javascript", ".png": "image/png", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp"}


class Site:
    """The current Renderer, rebuilt by `poll()` when an input file changes."""

    def __init__(self, build, roots: list[tuple[Path, str]]):
        self._build = build  # (session_cache) -> Renderer
        self._roots = roots  # (folder, glob pattern) pairs whose files are watched
        self._sessions: dict = {}
        self.version = 0
        self.changed = threading.Condition()
        self._fingerprint = self._stat()
        self.renderer: Renderer = build(self._sessions)

    def _stat(self) -> str:
        h = hashlib.blake2b(digest_size=16)
        for root, pattern in self._roots:
            for f in sorted(root.glob(pattern)) if root.is_dir() else [root] if root.exists() else ():
                try:
                    st = f.stat()
                except OSError:
                    continue
                h.update(f"{f}\0{st.st_mtime_ns}\0{st.st_size}\n".encode())
        return h.hexdigest()

    def poll(self) -> bool:
        fp = self._stat()
        if fp == self._fingerprint:
            return False
        self._fingerprint = fp
        self.renderer = self._build(self._sessions)
        with self.changed:
            self.version += 1
            self.changed.notify_all()
        return True

    def watch(self) -> None:
        while True:
            time.sleep(POLL)
            try:
                self.poll()
            except Exception as e:  # a half-written file must not stop the poller
                print(f"reload failed: {type(e).__name__}: {e}")


def handler(site: Site, plans_dir: Path):
    plans_dir = plans_dir.resolve()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):  # one line per request is noise for a local dashboard
            pass

        def _send(self, body: bytes, ctype: str, cache: str = "no-store") -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            url = urlsplit(self.path)
            rel = unquote(url.path).lstrip("/")
            if rel == "search.html" and site.renderer.search_page:
                form = {k: v[0] for k, v in parse_qs(url.query).items()}
                return self._send(site.renderer.search_page(
                    form.get("q", ""), form.get("project", ""), form.get("role", "")).encode(), "text/html; charset=utf-8")
            if rel == "events":
                return self._events()
            if rel in STATIC:
                return self._send(static_file(rel).read_bytes(), TYPES[Path(rel).suffix],
                                  "max-age=86400" if rel.endswith(".js") else "no-cache")
            if not rel or rel.endswith("/"):
                rel += "index.html"
            if render := site.renderer.pages.get(rel):
                return self._send(render().encode(), "text/html; charset=utf-8")
            path = (plans_dir / rel).resolve()
            if (path.is_file() and path.is_relative_to(plans_dir) and ASSETS in path.relative_to(plans_dir).parts[1:2]
                    and path.suffix.lower() in TYPES):
                return self._send(path.read_bytes(), TYPES[path.suffix.lower()], "no-cache")
            self.send_error(HTTPStatus.NOT_FOUND)

        def _events(self) -> None:
            """Server-sent events: `data: <version>` whenever the site was rebuilt."""
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            seen = site.version
            try:
                while True:
                    with site.changed:
                        site.changed.wait_for(lambda: site.version != seen, timeout=PING)
                    msg = f"data: {site.version}\n\n" if site.version != seen else ": ping\n\n"
                    seen = site.version
                    self.wfile.write(msg.encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

    return Handler


def serve(site: Site, plans_dir: Path, port: int) -> ThreadingHTTPServer:
    threading.Thread(target=site.watch, daemon=True).start()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler(site, plans_dir))
    httpd.daemon_threads = True
    return httpd
