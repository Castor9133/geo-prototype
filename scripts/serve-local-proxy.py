#!/usr/bin/env python3
"""本机一体：静态 dist + 反代 /api -> uvicorn（不依赖 Docker）。"""
from __future__ import annotations

import argparse
import http.server
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def _html_fallback_path(url_path: str) -> str:
    """Extensionless paths -> .html or directory index.html under dist/."""
    parts = urlsplit(url_path)
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") or "/"

    name = Path(path).name
    if name and "." in name:
        return url_path

    rel = path.lstrip("/")
    if rel:
        html_file = DIST / f"{rel}.html"
        if html_file.is_file():
            new_path = f"/{rel}.html"
            return urlunsplit(("", "", new_path, parts.query, parts.fragment))

        index_file = DIST / rel / "index.html"
        if index_file.is_file():
            new_path = f"/{rel}/index.html"
            return urlunsplit(("", "", new_path, parts.query, parts.fragment))
    else:
        index_file = DIST / "index.html"
        if index_file.is_file():
            return urlunsplit(("", "", "/index.html", parts.query, parts.fragment))

    return url_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve dist/ and proxy /api to FastAPI")
    parser.add_argument("--port", type=int, default=3009)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args()

    if not DIST.is_dir():
        raise SystemExit(f"dist not found: {DIST}")

    api_base = args.api.rstrip("/")

    class ProxyHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(DIST), **k)

        def do_GET(self):  # noqa: N802
            if self.path.startswith("/api/") or self.path.startswith("/api?"):
                return self._proxy()
            self.path = _html_fallback_path(self.path)
            return super().do_GET()

        def do_HEAD(self):  # noqa: N802
            if self.path.startswith("/api/") or self.path.startswith("/api?"):
                return self._proxy()
            self.path = _html_fallback_path(self.path)
            return super().do_HEAD()

        def do_POST(self):  # noqa: N802
            if self.path.startswith("/api/"):
                return self._proxy()
            self.send_error(405)

        def do_PUT(self):  # noqa: N802
            if self.path.startswith("/api/"):
                return self._proxy()
            self.send_error(405)

        def do_PATCH(self):  # noqa: N802
            if self.path.startswith("/api/"):
                return self._proxy()
            self.send_error(405)

        def do_DELETE(self):  # noqa: N802
            if self.path.startswith("/api/"):
                return self._proxy()
            self.send_error(405)

        def do_OPTIONS(self):  # noqa: N802
            if self.path.startswith("/api/"):
                return self._proxy()
            self.send_error(405)

        def _proxy(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            url = api_base + self.path
            req = Request(url, data=body, method=self.command)
            for key in ("Content-Type", "Authorization", "Accept", "X-Request-Id"):
                if key in self.headers:
                    req.add_header(key, self.headers[key])
            try:
                with urlopen(req, timeout=120) as resp:
                    data = resp.read()
                    self.send_response(resp.status)
                    for k, v in resp.headers.items():
                        if k.lower() not in {"transfer-encoding", "connection", "content-encoding"}:
                            self.send_header(k, v)
                    self.end_headers()
                    self.wfile.write(data)
            except HTTPError as exc:
                data = exc.read()
                self.send_response(exc.code)
                ctype = exc.headers.get("Content-Type") if exc.headers else None
                if ctype:
                    self.send_header("Content-Type", ctype)
                self.end_headers()
                self.wfile.write(data)
            except URLError as exc:
                self.send_error(502, str(exc.reason))

        def log_message(self, fmt, *a):
            print("[%s] %s" % (self.log_date_time_string(), fmt % a))

    server = http.server.ThreadingHTTPServer((args.bind, args.port), ProxyHandler)
    print(f"Serving {DIST} on http://{args.bind}:{args.port}/ (api -> {api_base})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
