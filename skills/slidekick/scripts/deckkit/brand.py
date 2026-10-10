"""Brand analysis: ingest a brand kit (template, logos, fonts, tokens, guideline PDFs) -> brand.json + brand.css + brand board."""
import colorsys
import json
import os
import pathlib
import re
import shutil
import zipfile

from lxml import etree

from .fonts import FontIndex, describe_font, to_ttf
from .util import contrast, hex6, log, luminance, read_json, rgb_of, write_json

A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
HEX_RE = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGB_RE = re.compile(r"rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})")
LOGO_WORDS = ("logo", "wordmark", "logotype", "brandmark", "lockup", "monogram", "symbol", "mark", "emblem")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
FONT_EXT = {".ttf", ".otf", ".woff", ".woff2", ".ttc"}


def _files(inputs):
    for inp in inputs:
        p = pathlib.Path(inp).resolve()
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and not any(part in SKIP_DIRS for part in f.parts):
                    yield f
        elif p.exists():
            yield p
        else:
            log(f"not found: {p}")


def saturation(hexv):
    r, g, b = (v / 255 for v in rgb_of(hexv))
    return colorsys.rgb_to_hls(r, g, b)[2]


def _norm_hex(s):
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return s.upper()


class Kit:
    def __init__(self, out_dir):
        self.out = pathlib.Path(out_dir)
        self.assets, self.fonts_dir, self.pages = self.out / "assets", self.out / "fonts", self.out / "pages"
        for d in (self.assets, self.fonts_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.colors = []  # (hex, weight, source, name)
        self.font_mentions = []  # (family, role, source)
        self.font_files = []
        self.logos, self.images, self.templates, self.guidelines = [], [], [], []
        self.theme = None

    def color(self, hexv, weight, source, name=""):
        self.colors.append({"hex": _norm_hex(hexv), "weight": weight, "source": source, "name": name})

    def copy(self, f, dst_dir):
        dst = dst_dir / f.name
        i = 1
        while dst.exists() and dst.read_bytes() != f.read_bytes():
            dst = dst_dir / f"{f.stem}-{i}{f.suffix}"
            i += 1
        if not dst.exists():
            shutil.copy2(f, dst)
        return dst


def _office(kit, f):
    with zipfile.ZipFile(f) as z:
        names = z.namelist()
        theme_name = next((n for n in names if re.match(r"(ppt/theme/theme\d+\.xml|theme/theme/theme\d+\.xml)$", n)), None)
        if theme_name:
            root = etree.fromstring(z.read(theme_name))
            slots = {}
            cs = root.find(f".//{A_NS}clrScheme")
            for el in (cs if cs is not None else []):
                slot = etree.QName(el).localname
                c = el[0] if len(el) else None
                if c is None:
                    continue
                val = c.get("val") if etree.QName(c).localname == "srgbClr" else c.get("lastClr")
                if val:
                    slots[slot] = _norm_hex(val)
                    kit.color(val, 6 if slot.startswith("accent") else 3, f"{f.name}:{slot}", slot)
            fonts = {}
            for tag, role in (("majorFont", "display"), ("minorFont", "body")):
                latin = root.find(f".//{A_NS}fontScheme/{A_NS}{tag}/{A_NS}latin")
                if latin is not None and latin.get("typeface"):
                    fonts[role] = latin.get("typeface")
                    kit.font_mentions.append((latin.get("typeface"), role, f"{f.name}:{tag}"))
            if kit.theme is None:
                kit.theme = {"slots": slots, "fonts": fonts, "source": str(f)}
        if f.suffix.lower() in (".pptx", ".potx"):
            kit.templates.append(str(f))
            master_media = set()
            for n in names:
                if re.match(r"ppt/(slideMasters|slideLayouts)/_rels/.*\.rels$", n):
                    for tgt in re.findall(r'Target="\.\./media/([^"]+)"', z.read(n).decode("utf-8", "replace")):
                        master_media.add("ppt/media/" + tgt)
            for n in sorted(master_media):
                if pathlib.Path(n).suffix.lower() in IMG_EXT | {".emf", ".wmf"} and n in names:
                    dst = kit.assets / f"{f.stem}-master-{pathlib.Path(n).name}"
                    dst.write_bytes(z.read(n))
                    if dst.suffix.lower() in IMG_EXT:
                        _image(kit, dst, from_master=True, copy=False)


def _svg_colors(text):
    cols = [m.group(1) for m in HEX_RE.finditer(text)]
    cols += ["%02X%02X%02X" % tuple(int(v) for v in m.groups()) for m in RGB_RE.finditer(text)]
    return [_norm_hex(c) for c in cols]


def _image(kit, f, from_master=False, copy=True):
    from PIL import Image

    dst = kit.copy(f, kit.assets) if copy else f
    name = f.stem.lower()
    info = {"path": str(dst), "name": f.name, "from_master": from_master}
    score = 3 if any(w in name for w in LOGO_WORDS) else 0
    if from_master:
        score += 2
    if f.suffix.lower() == ".svg":
        text = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', text)
        w, h = (float(m.group(1)), float(m.group(2))) if m else (0, 0)
        cols = _svg_colors(text)
        info.update(width=w, height=h, has_alpha=True, colors=list(dict.fromkeys(cols))[:6], vector=True)
        lum = [luminance(c) for c in cols] or [0.0]
        info["mean_luminance"] = sum(lum) / len(lum)
        score += 2
    else:
        try:
            im = Image.open(dst)
        except Exception:  # noqa: BLE001
            return
        w, h = im.size
        rgba = im.convert("RGBA")
        small = rgba.copy()
        small.thumbnail((128, 128))
        px = [p for p in small.getdata() if p[3] > 128]
        has_alpha = any(p[3] < 250 for p in small.getdata())
        q = small.convert("RGB").quantize(colors=6)
        pal = q.getpalette()[:18]
        counts = sorted(q.getcolors() or [], reverse=True)
        cols = ["%02X%02X%02X" % tuple(pal[i * 3:i * 3 + 3]) for _, i in counts if i < 6]
        info.update(width=w, height=h, has_alpha=has_alpha, colors=cols[:6], vector=False,
                    mean_luminance=(sum(0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2] for p in px) / max(1, len(px)) / 255) if px else 1.0)
        if has_alpha:
            score += 1
        if w * h > 1600 * 900 and not any(wd in name for wd in LOGO_WORDS):
            score -= 3
    ar = (info["width"] / info["height"]) if info.get("height") else 1
    info["shape"] = "wordmark" if ar > 2.2 else ("mark" if 0.7 < ar < 1.4 else "lockup")
    info["variant"] = "for-dark-backgrounds" if info.get("mean_luminance", 0) > 0.6 else "for-light-backgrounds"
    info["score"] = score
    if score >= 3:
        kit.logos.append(info)
        for c in info.get("colors", [])[:3]:
            if saturation(c) > 0.25:
                kit.color(c, 4, f"logo:{f.name}")
    else:
        kit.images.append(info)


def _font_file(kit, f):
    p = to_ttf(f, kit.fonts_dir) if f.suffix.lower() in (".woff", ".woff2") else kit.copy(f, kit.fonts_dir)
    for face in describe_font(p):
        kit.font_files.append({"file": str(p), "family": face["typo"], "legacy_family": face["family"],
                               "weight": face["weight"], "italic": face["italic"], "fsType": face["fsType"]})
        kit.font_mentions.append((face["typo"], "file", f.name))


CSS_VAR_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;}{]+)")


def _css(kit, f):
    text = f.read_text(encoding="utf-8", errors="replace")
    for name, val in CSS_VAR_RE.findall(text):
        for c in _svg_colors(val):
            w = 5 if re.search(r"primary|brand|accent", name) else 2
            kit.color(c, w, f"{f.name}:{name}", name.lstrip("-"))
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
        m = re.search(r"font-family\s*:\s*([^;]+)", body)
        if m:
            fam = m.group(1).split(",")[0].strip().strip("'\"")
            if fam.startswith("var(") or fam.lower() in ("inherit", "initial"):
                continue
            role = "display" if re.search(r"\bh[1-3]\b|title|heading|display|hero", sel) else "body"
            kit.font_mentions.append((fam, role, f"{f.name}:{sel.strip()[:30]}"))
    for fam in re.findall(r"fonts\.googleapis\.com/css2?\?family=([^&\"':]+)", text):
        kit.font_mentions.append((fam.replace("+", " "), "google", f.name))


def _tokens(kit, f):
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + [str(k)])
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + [str(i)])
        elif isinstance(o, str):
            key = ".".join(path)
            for c in _svg_colors(o):
                kit.color(c, 5 if re.search(r"primary|brand|accent", key, re.I) else 2, f"{f.name}:{key}", key)
            if re.search(r"font.?family|typeface", key, re.I) and not o.startswith(("{", "$")):
                kit.font_mentions.append((o.split(",")[0].strip().strip("'\""), "display" if re.search(r"head|display|title", key, re.I) else "body", f.name))
    walk(data, [])


def _pdf(kit, f):
    import pymupdf as fitz

    doc = fitz.open(f)
    kit.pages.mkdir(parents=True, exist_ok=True)
    text = []
    for i, page in enumerate(doc):
        text.append(page.get_text())
        if i < 16:
            pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2), alpha=False)
            out = kit.pages / f"{f.stem}-p{i + 1:02d}.png"
            pix.save(str(out))
    full = "\n".join(text)
    (kit.out / f"{f.stem}.txt").write_text(full, encoding="utf-8")
    kit.guidelines.append({"pdf": str(f), "text": str(kit.out / f"{f.stem}.txt"), "pages": len(doc)})
    for c in _svg_colors(full):
        kit.color(c, 3, f"{f.name}:text")
    for m in re.finditer(r"(?:typeface|font|typography)[^\n:]*[:\-–]\s*([A-Z][\w ]{2,30})", full):
        kit.font_mentions.append((m.group(1).strip(), "guideline", f.name))
    doc.close()


def _text(kit, f):
    text = f.read_text(encoding="utf-8", errors="replace")
    for c in _svg_colors(text):
        kit.color(c, 2, f.name)


def _pick_palette(kit):
    agg = {}
    for c in kit.colors:
        e = agg.setdefault(c["hex"], {"hex": c["hex"], "weight": 0, "sources": [], "names": set()})
        e["weight"] += c["weight"]
        e["sources"].append(c["source"])
        if c["name"]:
            e["names"].add(c["name"])
    cols = sorted(agg.values(), key=lambda e: -e["weight"])
    neutrals = [c for c in cols if saturation(c["hex"]) < 0.12 or luminance(c["hex"]) > 0.92 or luminance(c["hex"]) < 0.02]
    chroma = [c for c in cols if c not in neutrals]
    named = next((c for c in chroma if any(re.search(r"primary|brand|accent1", n) for n in c["names"])), None)
    primary = named or (chroma[0] if chroma else None)
    dark = min(cols, key=lambda c: luminance(c["hex"]))["hex"] if cols else "111111"
    light = max(cols, key=lambda c: luminance(c["hex"]))["hex"] if cols else "FFFFFF"
    if luminance(dark) > 0.1:
        dark = "111418"
    if luminance(light) < 0.85:
        light = "FFFFFF"
    accents = ([primary] if primary else []) + [c for c in chroma if c is not primary]
    distinct = []
    for c in accents:
        if all(_dist(c["hex"], d) > 40 for d in distinct):
            distinct.append(c["hex"])
    return cols, dark, light, distinct


def _dist(a, b):
    return sum(abs(x - y) for x, y in zip(rgb_of(a), rgb_of(b)))


def _mix(hexv, other, amt):
    a, b = rgb_of(hexv), rgb_of(other)
    return "%02X%02X%02X" % tuple(round(x + (y - x) * amt) for x, y in zip(a, b))


def _fill_accents(given, dark):
    """Six theme accents from the brand's own colours: shades and tints of what the kit gave, never Office blue/orange."""
    out = list(given[:6]) or ["3B5BDB"]
    seeds = given or ["3B5BDB"]
    candidates = ([v for c in seeds for v in (_mix(c, "000000", 0.38), _mix(c, "FFFFFF", 0.42))] + [_mix(dark, "FFFFFF", 0.55)]
                  + [v for c in seeds for v in (_mix(c, "000000", 0.62), _mix(c, "FFFFFF", 0.7))]
                  + [_mix(dark, "FFFFFF", 0.3), _mix(dark, "FFFFFF", 0.8)])
    for v in candidates:
        if len(out) >= 6:
            break
        if all(_dist(v, d) > 40 for d in out):
            out.append(v)
    k = 1
    while len(out) < 6:
        out.append(_mix(seeds[0], "FFFFFF" if k % 2 else "000000", 0.15 * k))
        k += 1
    return out


def _text_safe(hexv, bg, target=4.5):
    """The nearest shade of a brand colour that is readable as text on bg (WCAG AA); unchanged if it already is."""
    toward = "000000" if luminance(bg) > 0.4 else "FFFFFF"
    for i in range(0, 21):
        v = _mix(hexv, toward, i * 0.04)
        if contrast(v, bg) >= target:
            return v
    return toward


def _tint(hexv, amt):
    r, g, b = rgb_of(hexv)
    return "%02X%02X%02X" % tuple(int(v + (255 - v) * amt) for v in (r, g, b))


def ingest(inputs, out_dir, name=None, colors=None, display_font=None, body_font=None):
    """inputs: kit files/folders (may be empty). colors/fonts: explicit choices, ranked above anything found in the kit."""
    kit = Kit(out_dir)
    for i, c in enumerate(colors or []):
        kit.color(c, 10_000 - i, "--colors", "primary" if i == 0 else f"brand-{i + 1}")
    for fam, role in ((display_font, "display"), (body_font, "body")):
        if fam:
            kit.font_mentions.insert(0, (fam, role, "--font"))
    for f in _files(inputs):
        ext = f.suffix.lower()
        try:
            if ext in (".pptx", ".potx", ".thmx"):
                _office(kit, f)
            elif ext in FONT_EXT:
                _font_file(kit, f)
            elif ext in IMG_EXT:
                _image(kit, f)
            elif ext in (".css", ".scss", ".html", ".htm"):
                _css(kit, f)
            elif ext == ".json":
                _tokens(kit, f)
            elif ext == ".pdf":
                _pdf(kit, f)
            elif ext in (".md", ".txt"):
                _text(kit, f)
        except Exception as e:  # noqa: BLE001 - keep ingesting other files
            log(f"could not read {f.name}: {e}")

    cols, dark, light, accents = _pick_palette(kit)
    if kit.theme and len(kit.theme.get("slots", {})) >= 10:
        slots = dict(kit.theme["slots"])
    else:
        acc = _fill_accents(accents, dark)
        slots = {"dk1": dark, "lt1": light, "dk2": accents[0] if accents and luminance(accents[0]) < 0.2 else _shade(dark),
                 "lt2": _tint(acc[0], 0.92), **{f"accent{i + 1}": c for i, c in enumerate(acc)}, "hlink": acc[0], "folHlink": acc[1]}
    index = FontIndex()  # system-installed only: kit files don't count until `deck.py fonts install`
    roles = {"display": None, "body": None}
    for fam, role, _ in kit.font_mentions:
        if role in roles and not roles[role]:
            roles[role] = fam
    families = list(dict.fromkeys(f for f, _, _ in kit.font_mentions))
    roles["display"] = roles["display"] or (kit.font_files[0]["family"] if kit.font_files else (families[0] if families else None))
    roles["body"] = roles["body"] or roles["display"]
    fonts = {}
    for role, fam in roles.items():
        if fam:
            files = [ff for ff in kit.font_files if ff["family"].lower() == fam.lower()]
            fonts[role] = {"family": fam, "installed": index.has(fam), "files": [ff["file"] for ff in files],
                           "fallback": "Georgia, serif" if role == "display" and "serif" in fam.lower() and "sans" not in fam.lower() else "Segoe UI, Arial, sans-serif"}
    fonts["files"] = sorted({ff["file"] for ff in kit.font_files})
    logos = sorted(kit.logos, key=lambda l: -l["score"])
    brand = {
        "name": name or (pathlib.Path(inputs[0]).stem if inputs else "Brand"),
        "theme": slots,
        "colors": {"primary": "#" + (accents[0] if accents else slots["accent1"]),
                   "primary_text": "#" + _text_safe(accents[0] if accents else slots["accent1"], slots["lt1"]),
                   "background": "#" + slots["lt1"],
                   "text": "#" + slots["dk1"], "dark": "#" + slots["dk2"], "surface": "#" + slots["lt2"],
                   "accents": ["#" + c for c in accents[:6]]},
        "fonts": fonts,
        "logos": [{k: v for k, v in l.items() if k != "score"} for l in logos],
        "template": kit.templates[0] if kit.templates else None,
        "imagery": [i["path"] for i in kit.images][:40],
        "guidelines": kit.guidelines,
        "rules": [],
        "review": {"note": "Auto-extracted. Check the brand board, fix roles/colors/logos here, then run `deck.py tokens`.",
                   "color_candidates": [{"hex": "#" + c["hex"], "weight": c["weight"], "names": sorted(c["names"]), "sources": c["sources"][:4]}
                                        for c in cols[:24]],
                   "font_candidates": [{"family": f, "role": r, "source": s} for f, r, s in kit.font_mentions][:30],
                   "font_files": kit.font_files},
    }
    write_json(kit.out / "brand.json", _relative_paths(brand, kit.out.resolve()))
    return brand


def _relative_paths(node, base):
    """Store paths relative to brand/ so a project can be moved or shared without exposing the author's folders."""
    if isinstance(node, dict):
        return {k: _relative_paths(v, base) for k, v in node.items()}
    if isinstance(node, list):
        return [_relative_paths(v, base) for v in node]
    if isinstance(node, str) and len(node) > 3 and pathlib.Path(node).is_absolute():
        try:
            return pathlib.Path(os.path.relpath(node, base)).as_posix()
        except ValueError:  # another drive on Windows: nothing relative to point at
            return node
    return node


def _shade(hexv):
    r, g, b = rgb_of(hexv)
    return "%02X%02X%02X" % (int(r * 0.85), int(g * 0.85), int(b * 0.85))


def write_tokens(brand_json, css_out):
    """brand.json -> canvas/brand.css (CSS variables + @font-face for kit fonts)."""
    brand_json = pathlib.Path(brand_json).resolve()
    css_out = pathlib.Path(css_out).resolve()
    b = read_json(brand_json)
    t = b.get("theme", {})
    lines = ["/* Generated from brand/brand.json by `deck.py tokens` — edit brand.json, not this file. */"]
    seen = set()
    for ff in b.get("review", {}).get("font_files", []):
        p = pathlib.Path(ff["file"])
        if not p.is_absolute():
            p = brand_json.parent / p
        key = (ff["family"], ff["weight"], ff["italic"])
        if key in seen or not p.exists():
            continue
        seen.add(key)
        rel = _rel(p, css_out.parent)
        lines.append(f"@font-face {{ font-family: '{ff['family']}'; src: url('{rel}'); font-weight: {ff['weight']}; "
                     f"font-style: {'italic' if ff['italic'] else 'normal'}; font-display: block; }}")
    fonts = b.get("fonts", {})
    disp = fonts.get("display") or {}
    body = fonts.get("body") or {}
    lines.append(":root {")
    for slot in ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6"):
        if slot in t:
            lines.append(f"  --brand-{slot}: #{hex6(t[slot])};")
    c = b.get("colors", {})
    for k_, v in (("primary", c.get("primary")), ("primary-text", c.get("primary_text") or c.get("primary")), ("bg", c.get("background")), ("text", c.get("text")), ("dark", c.get("dark")),
                  ("surface", c.get("surface"))):
        if v:
            lines.append(f"  --color-{k_}: {v};")
    for i, v in enumerate(c.get("accents", []), 1):
        lines.append(f"  --color-accent-{i}: {v};")
    if c.get("text") and c.get("background"):
        lines.append(f"  --color-muted: color-mix(in srgb, {c['text']} 62%, {c['background']});")
    if disp:
        lines.append(f"  --font-display: '{disp['family']}', {disp.get('fallback', 'sans-serif')};")
    if body:
        lines.append(f"  --font-body: '{body['family']}', {body.get('fallback', 'sans-serif')};")
    for i, logo in enumerate(b.get("logos", [])[:6]):
        p = pathlib.Path(logo["path"])
        if not p.is_absolute():
            p = brand_json.parent / p
        lines.append(f"  --logo-{i + 1}: url('{_rel(p, css_out.parent)}');")
    lines.append("}")
    css_out.parent.mkdir(parents=True, exist_ok=True)
    css_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return css_out


def _rel(p, base):
    import os
    return pathlib.Path(os.path.relpath(p, base)).as_posix()


BOARD_HTML = """<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="{css}">
<style>body{{margin:0;font-family:var(--font-body);background:#F4F4F5;color:#111;width:1400px}}
.wrap{{padding:32px}} h2{{font:600 14px/1 Segoe UI,Arial;letter-spacing:.08em;text-transform:uppercase;color:#71717A;margin:28px 0 12px}}
.sw{{display:flex;gap:12px;flex-wrap:wrap}} .s{{width:150px;border-radius:10px;overflow:hidden;background:#fff;box-shadow:0 1px 3px #0002;font:12px Segoe UI}}
.s div{{height:80px}} .s p{{margin:8px 10px}} .logos{{display:flex;gap:16px;flex-wrap:wrap}}
.lg{{width:300px;height:150px;display:flex;align-items:center;justify-content:center;border-radius:10px;padding:20px;box-sizing:border-box}}
.lg img{{max-width:100%;max-height:100%}} .cap{{font:12px Segoe UI;color:#555;width:300px;margin-top:4px;word-break:break-all}}
.type p{{margin:6px 0}}</style></head><body><div class="wrap">
<h1 style="font-family:var(--font-display);font-size:44px;margin:0">{name} — brand board</h1>
<h2>Theme colors</h2><div class="sw">{swatches}</div>
<h2>Logos (on light and dark)</h2><div class="logos">{logos}</div>
<h2>Type</h2><div class="type"><p style="font-family:var(--font-display);font-size:56px;font-weight:700">Display — {disp}</p>
<p style="font-family:var(--font-display);font-size:32px;font-weight:600">The quick brown fox jumps over the lazy dog</p>
<p style="font-family:var(--font-body);font-size:22px">Body — {body}. Pack my box with five dozen liquor jugs. 0123456789</p></div>
</div></body></html>"""


def brand_board(brand_json, out_png):
    from playwright.sync_api import sync_playwright

    from .util import launch_browser, serve_dir

    brand_json = pathlib.Path(brand_json).resolve()
    root = brand_json.parent
    write_tokens(brand_json, root / "_board" / "brand.css")
    b = read_json(brand_json)
    t = b.get("theme", {})
    sw = "".join(f'<div class="s"><div style="background:#{hex6(v)}"></div><p><b>{k}</b> #{hex6(v)}</p></div>' for k, v in t.items())
    logos = ""
    for logo in b.get("logos", [])[:6]:
        p = pathlib.Path(logo["path"])
        p = p if p.is_absolute() else root / p
        rel = _rel(p, root / "_board")
        for bg in ("#FFFFFF", "#" + hex6(t.get("dk1", "111111"))):
            logos += f'<div><div class="lg" style="background:{bg}"><img src="{rel}"></div><div class="cap">{logo["name"]} · {logo.get("variant")}</div></div>'
    html = BOARD_HTML.format(css="brand.css", name=b.get("name", "Brand"), swatches=sw, logos=logos or "<p>No logo found</p>",
                             disp=(b.get("fonts", {}).get("display") or {}).get("family", "?"),
                             body=(b.get("fonts", {}).get("body") or {}).get("family", "?"))
    (root / "_board" / "index.html").write_text(html, encoding="utf-8")
    with serve_dir(root) as base, sync_playwright() as p:
        br = launch_browser(p)
        page = br.new_page(viewport={"width": 1400, "height": 900})
        page.goto(f"{base}/_board/index.html", wait_until="networkidle")
        page.evaluate("document.fonts.ready.then(() => true)")
        page.screenshot(path=str(out_png), full_page=True)
        br.close()
    shutil.rmtree(root / "_board", ignore_errors=True)
    return out_png
