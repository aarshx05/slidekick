"""Source real visuals: screenshot a live product/site, or download an image with provenance."""
import datetime
import hashlib
import pathlib
import urllib.request

from .util import launch_browser, log

DISMISS = ["Accept all", "Accept All", "Accept", "I agree", "Agree", "Allow all", "Got it", "OK", "Close", "No thanks", "Reject all"]


def capture(url, out, width=1440, height=900, full_page=False, selector=None, scale=2, dark=False, wait_ms=1200, scroll=True):
    from playwright.sync_api import sync_playwright

    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        br = launch_browser(p)
        ctx = br.new_context(viewport={"width": width, "height": height}, device_scale_factor=scale,
                             color_scheme="dark" if dark else "light",
                             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:  # noqa: BLE001 - busy sites never go idle
            pass
        for label in DISMISS:
            try:
                btn = page.get_by_role("button", name=label, exact=True)
                if btn.count() and btn.first.is_visible():
                    btn.first.click(timeout=1500)
                    page.wait_for_timeout(400)
                    break
            except Exception:  # noqa: BLE001
                continue
        if scroll:  # trigger lazy-loaded / scroll-animated content, then return to top
            page.evaluate("""async () => { const h = document.body.scrollHeight;
                for (let y = 0; y < h; y += innerHeight * 0.8) { scrollTo(0, y); await new Promise(r => setTimeout(r, 150)); }
                scrollTo(0, 0); }""")
        page.wait_for_timeout(wait_ms)
        if selector:
            page.locator(selector).first.screenshot(path=str(out))
        else:
            page.screenshot(path=str(out), full_page=full_page)
        title = page.title()
        br.close()
    _record(out.parent, out.name, url, f"screenshot of {title!r}")
    return out


def fetch(url, out_dir, name=None, note=""):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 slidekick"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
        ctype = r.headers.get("Content-Type", "")
    if not (ctype.startswith("image/") or data[:4] in (b"\x89PNG", b"GIF8", b"RIFF") or data[:2] == b"\xff\xd8" or b"<svg" in data[:500]):
        raise RuntimeError(f"not an image ({ctype or 'unknown type'}): {url}")
    ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/svg+xml": ".svg", "image/gif": ".gif"}.get(
        ctype.split(";")[0], pathlib.Path(url.split("?")[0]).suffix or ".img")
    name = name or (hashlib.sha1(data).hexdigest()[:10] + ext)
    if not pathlib.Path(name).suffix:
        name += ext
    out = out_dir / name
    out.write_bytes(data)
    _record(out_dir, out.name, url, note)
    log(f"saved {out} ({len(data) // 1024} KB)")
    return out


def _record(folder, name, url, note):
    src = pathlib.Path(folder) / "SOURCES.md"
    line = f"- `{name}` ← {url} ({datetime.date.today().isoformat()}){' — ' + note if note else ''}\n"
    with open(src, "a", encoding="utf-8") as f:
        if src.stat().st_size == 0:
            f.write("# Image sources\n\nCheck usage rights before publishing. Prefer the brand's own imagery.\n\n")
        f.write(line)
