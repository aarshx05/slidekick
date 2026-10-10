import contextlib
import functools
import http.server
import json
import os
import pathlib
import socketserver
import sys
import threading

SKILL_DIR = pathlib.Path(__file__).resolve().parents[2]
CANVAS_W, CANVAS_H = 1280, 720
EMU_PER_PX = 9525  # 96 px per inch


def log(*a):
    print("[deck]", *a, file=sys.stderr, flush=True)


def cache_dir() -> pathlib.Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.join(pathlib.Path.home(), ".cache")
    d = pathlib.Path(base) / "slidekick"
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def hex6(c: str) -> str:
    c = c.strip().lstrip("#").upper()
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return c[:6]


def rgb_of(c: str):
    c = hex6(c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def luminance(c: str) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb_of(c)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


@contextlib.contextmanager
def serve_dir(root):
    """Serve `root` over http://127.0.0.1:<port>/ (fonts and images need a real origin, not file://)."""
    handler = functools.partial(_QuietHandler, directory=str(root))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def launch_browser(playwright):
    """Prefer an installed Edge/Chrome so no browser download is needed."""
    errors = []
    for kw in ({"channel": "msedge"}, {"channel": "chrome"}, {}):
        try:
            return playwright.chromium.launch(headless=True, **kw)
        except Exception as e:  # noqa: BLE001 - try next channel
            errors.append(f"{kw or 'bundled chromium'}: {str(e).splitlines()[0]}")
    raise RuntimeError("No Chromium browser available. Install Edge/Chrome or run "
                       "`python -m playwright install chromium`.\n" + "\n".join(errors))


def url_to_local(url: str, base_url: str, root: pathlib.Path):
    """Map a served URL back to the file on disk; None if it is remote."""
    from urllib.parse import unquote, urlparse
    if url.startswith(base_url + "/"):
        return (root / unquote(urlparse(url).path).lstrip("/")).resolve()
    if url.startswith("file:///"):
        p = unquote(urlparse(url).path)
        if os.name == "nt" and p.startswith("/") and len(p) > 2 and p[2] == ":":
            p = p[1:]
        return pathlib.Path(p)
    return None
