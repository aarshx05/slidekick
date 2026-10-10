"""Low-IR extraction: HTML/CSS canvas -> layout.json (+ reference PNGs), using Chromium as the layout engine."""
import base64
import hashlib
import pathlib
import shutil
import urllib.request

from .util import CANVAS_H, CANVAS_W, launch_browser, serve_dir, url_to_local, write_json

JS = (pathlib.Path(__file__).parent / "extract.js").read_text(encoding="utf-8")
FREEZE_CSS = """
*, *::before, *::after { animation: none !important; transition: none !important; caret-color: transparent !important; }
body.debug [data-pptx] { outline: none !important; }
"""


def _walk(elements):
    for e in elements:
        yield e
        yield from _walk(e.get("children", []))


def _platform_fonts(ctx, page):
    """tid -> primary platform font actually used by Chromium for that element's text."""
    cdp = ctx.new_cdp_session(page)
    cdp.send("DOM.enable")
    cdp.send("CSS.enable")
    root = cdp.send("DOM.getDocument", {"depth": -1})["root"]["nodeId"]
    ids = cdp.send("DOM.querySelectorAll", {"nodeId": root, "selector": "[data-deck-tid]"})["nodeIds"]
    out = {}
    for nid in ids:
        attrs = cdp.send("DOM.getAttributes", {"nodeId": nid})["attributes"]
        tid = dict(zip(attrs[::2], attrs[1::2])).get("data-deck-tid")
        try:
            fonts = cdp.send("CSS.getPlatformFontsForNode", {"nodeId": nid})["fonts"]
        except Exception:  # noqa: BLE001
            fonts = []
        if fonts:
            fonts.sort(key=lambda f: -f.get("glyphCount", 0))
            out[int(tid)] = {"family": fonts[0]["familyName"], "custom": fonts[0].get("isCustomFont", False),
                             "ps": fonts[0].get("postScriptName", ""), "all": [f["familyName"] for f in fonts]}
    cdp.detach()
    return out


def _materialize(src, base_url, root, media_dir):
    """Return a local file path for an image src (served file, data: URI or remote URL)."""
    local = url_to_local(src, base_url, root)
    if local and local.exists():
        return local
    media_dir.mkdir(parents=True, exist_ok=True)
    if src.startswith("data:"):
        head, data = src.split(",", 1)
        ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/svg+xml": ".svg", "image/webp": ".webp", "image/gif": ".gif"}.get(
            head[5:].split(";")[0], ".bin")
        raw = base64.b64decode(data) if ";base64" in head else urllib.request.unquote(data).encode("utf-8")
        p = media_dir / (hashlib.sha1(raw).hexdigest()[:16] + ext)
        p.write_bytes(raw)
        return p
    if src.startswith(("http://", "https://")):
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0 slidekick"})
        raw = urllib.request.urlopen(req, timeout=30).read()
        ext = pathlib.Path(src.split("?")[0]).suffix[:5] or ".img"
        p = media_dir / (hashlib.sha1(raw).hexdigest()[:16] + ext)
        p.write_bytes(raw)
        return p
    return None


def _rasterize_svgs(browser, items, media_dir):
    """Render each SVG standalone (transparent) at high DPI -> PNG fallback for the svgBlip."""
    if not items:
        return
    media_dir.mkdir(parents=True, exist_ok=True)
    page = browser.new_page(device_scale_factor=1)
    for el, svg_text in items:
        w, h = max(1, el["box"]["w"]), max(1, el["box"]["h"])
        scale = 4 if max(w, h) <= 600 else 2
        digest = hashlib.sha1((svg_text + f"{w}x{h}").encode("utf-8")).hexdigest()[:16]
        png = media_dir / f"svg-{digest}.png"
        svg_file = media_dir / f"svg-{digest}.svg"
        svg_file.write_text(svg_text, encoding="utf-8")
        if not png.exists():
            page.set_viewport_size({"width": int(w * scale) + 2, "height": int(h * scale) + 2})
            b64 = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
            page.set_content(f'<html><body style="margin:0;background:transparent">'
                             f'<img id="s" src="data:image/svg+xml;base64,{b64}" '
                             f'style="display:block;width:{w * scale}px;height:{h * scale}px"></body></html>')
            page.wait_for_function("document.getElementById('s').complete")
            page.locator("#s").screenshot(path=str(png), omit_background=True)
        el["image"]["png"] = str(png)
        el["image"]["svg_file"] = str(svg_file)
    page.close()


def extract(project, html="canvas/deck.html", out="build", scale=1.5, screenshots=True):
    from playwright.sync_api import sync_playwright

    project = pathlib.Path(project).resolve()
    out_dir = project / out
    ref_dir = out_dir / "ref"
    media_dir = out_dir / "media"
    if ref_dir.exists():
        shutil.rmtree(ref_dir)
    ref_dir.mkdir(parents=True, exist_ok=True)
    html_path = (project / html).resolve()
    if not html_path.exists():
        raise FileNotFoundError(html_path)
    rel = html_path.relative_to(project).as_posix()

    with serve_dir(project) as base, sync_playwright() as p:
        browser = launch_browser(p)
        ctx = browser.new_context(viewport={"width": CANVAS_W, "height": CANVAS_H}, device_scale_factor=scale)
        page = ctx.new_page()
        console = []
        page.on("console", lambda m: console.append(f"{m.type}: {m.text}")
                if m.type in ("error", "warning") and "Failed to load resource" not in m.text else None)
        page.on("requestfailed", lambda r: console.append(f"request failed: {r.url}"))
        page.on("response", lambda r: console.append(f"HTTP {r.status}: {r.url}")
                if r.status >= 400 and not r.url.endswith("favicon.ico") else None)
        page.goto(f"{base}/{rel}", wait_until="networkidle")
        page.add_style_tag(content=FREEZE_CSS)
        page.evaluate("document.fonts.ready.then(() => true)")
        page.wait_for_function("Array.from(document.images).every(i => i.complete)", timeout=30000)
        data = page.evaluate(JS)
        if data.get("error"):
            raise RuntimeError(data["error"])
        fonts = _platform_fonts(ctx, page)

        svg_jobs = []
        for s in data["slides"]:
            imgs = [e for e in _walk(s["elements"]) if e.get("image")]
            if s["background"].get("image"):
                imgs.append(s["background"]["image"])
            for e in imgs:
                im = e["image"]
                if im["kind"] == "svg-inline":
                    svg_jobs.append((e, im.pop("svg")))
                    continue
                path = _materialize(im["src"], base, project, media_dir)
                if not path:
                    data["warnings"].append({"slide": s["index"], "code": "image-src", "msg": f"cannot resolve {im['src'][:80]}", "el": e.get("src", "")})
                    continue
                im["path"] = str(path)
                if im["kind"] == "svg":
                    svg_jobs.append((e, path.read_text(encoding="utf-8", errors="replace")))
        _rasterize_svgs(browser, svg_jobs, media_dir)

        if screenshots:
            loc = page.locator("section.slide")
            for i in range(loc.count()):
                loc.nth(i).screenshot(path=str(ref_dir / f"slide-{i + 1:02d}.png"), animations="disabled")
        browser.close()

    used = {}
    for s in data["slides"]:
        for e in _walk(s["elements"]):
            runs = []
            if e.get("text"):
                runs = [r for p_ in e["text"]["paragraphs"] for r in p_["runs"]]
            if e.get("table"):
                runs = [r for c in e["table"]["cells"] if c.get("text") for p_ in c["text"]["paragraphs"] for r in p_["runs"]]
            if e.get("chart"):
                runs = [e["chart"]["font"]]
            for r in runs:
                pf = fonts.get(r.get("tid"))
                if pf:
                    r["platform_font"] = pf["family"]
                    r["platform_custom"] = pf["custom"]
                    used.setdefault(pf["family"], {"custom": pf["custom"], "count": 0})["count"] += 1
    data["fonts_used"] = used
    data["console"] = console[:50]
    data["source"] = rel
    data["reference_scale"] = scale
    write_json(out_dir / "layout.json", data)
    return data
