"""Testing: visual diff (Chromium reference vs real render), deterministic checks, contact sheet, report."""
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .util import contrast, read_json, write_json

ERROR_CODES = {"overflow", "untagged-text", "untagged-media", "image-load", "image-src", "chart-json", "slide-size",
               "font-missing", "powerpoint-open", "transition-ignored", "animation-ignored", "visual-diff", "tiny-text"}


def _font(size):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _walk(elements):
    for e in elements:
        yield e
        yield from _walk(e.get("children", []))


def _runs(el):
    if el.get("text"):
        for p in el["text"]["paragraphs"]:
            for r in p["runs"]:
                if not r.get("br"):
                    yield p, r
    if el.get("table"):
        for c in el["table"]["cells"]:
            if c.get("text"):
                for p in c["text"]["paragraphs"]:
                    for r in p["runs"]:
                        if not r.get("br"):
                            yield p, r


# fonts every PowerPoint install has (Windows and Mac Office): missing locally is a render caveat, not a broken deck
OFFICE_FONTS = {"arial", "arial black", "calibri", "calibri light", "cambria", "candara", "consolas", "constantia", "corbel",
                "courier new", "georgia", "segoe ui", "segoe ui semibold", "segoe ui light", "tahoma", "times new roman",
                "trebuchet ms", "verdana", "aptos", "aptos display"}
TOLERANCE_PX = 2  # canvas px of positional jitter forgiven (glyph advance rounding differs between renderers)
# Calibrated on real decks: clean slides peak at ~25 connected 16px cells; a missing 2-line headline is ~150.
REGION_WARN_CELLS = 30
REGION_ERROR_CELLS = 60


def visual_diff(ref_path, ren_path, masks, scale):
    a = Image.open(ref_path).convert("RGB")
    b = Image.open(ren_path).convert("RGB")
    if b.size != a.size:
        b = b.resize(a.size, Image.LANCZOS)
    # compare at canvas resolution; each pixel may match anything within ±TOLERANCE_PX
    cw, ch = round(a.width / scale), round(a.height / scale)
    A = np.asarray(a.resize((cw, ch), Image.BOX).filter(ImageFilter.GaussianBlur(0.8)), dtype=np.int16)
    B = np.asarray(b.resize((cw, ch), Image.BOX).filter(ImageFilter.GaussianBlur(0.8)), dtype=np.int16)
    d = None
    for dy in range(-TOLERANCE_PX, TOLERANCE_PX + 1):
        for dx in range(-TOLERANCE_PX, TOLERANCE_PX + 1):
            e = np.abs(A - np.roll(B, (dy, dx), axis=(0, 1))).max(axis=2)
            d = e if d is None else np.minimum(d, e)
    for (x, y, w, h) in masks:
        d[int(y):int(y + h), int(x):int(x + w)] = 0
    bad_small = d > 56
    ratio = float(bad_small.mean())
    bad = np.asarray(Image.fromarray((bad_small * 255).astype(np.uint8)).resize(a.size, Image.NEAREST)) > 0
    H, W = bad.shape
    cell = max(8, int(16 * scale))
    gh, gw = H // cell, W // cell
    grid = bad[:gh * cell, :gw * cell].reshape(gh, cell, gw, cell).mean(axis=(1, 3)) > 0.12
    regions, seen = [], np.zeros_like(grid)
    for gy in range(gh):
        for gx in range(gw):
            if grid[gy, gx] and not seen[gy, gx]:
                stack, cells = [(gy, gx)], []
                seen[gy, gx] = True
                while stack:
                    cy, cx = stack.pop()
                    cells.append((cy, cx))
                    for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                        if 0 <= ny < gh and 0 <= nx < gw and grid[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
                ys, xs = [c[0] for c in cells], [c[1] for c in cells]
                regions.append({"x": min(xs) * cell / scale, "y": min(ys) * cell / scale,
                                "w": (max(xs) - min(xs) + 1) * cell / scale, "h": (max(ys) - min(ys) + 1) * cell / scale,
                                "area": len(cells)})
    regions.sort(key=lambda r: -r["area"])
    heat = b.copy()
    ov = np.zeros((H, W, 4), dtype=np.uint8)
    ov[bad] = (255, 0, 80, 170)
    overlay = Image.fromarray(ov, "RGBA")
    heat = Image.alpha_composite(heat.convert("RGBA"), overlay).convert("RGB")
    return ratio, regions[:8], a, b, heat


def _compare_image(a, b, heat, label, path):
    w, h = a.width // 2, a.height // 2
    out = Image.new("RGB", (w * 3 + 40, h + 44), (24, 24, 27))
    dr = ImageDraw.Draw(out)
    f = _font(18)
    for i, (im, cap) in enumerate(((a, "HTML reference (Chromium)"), (b, "PPTX render"), (heat, "diff"))):
        out.paste(im.resize((w, h), Image.LANCZOS), (10 + i * (w + 10), 34))
        dr.text((10 + i * (w + 10), 8), cap, fill=(230, 230, 230), font=f)
    dr.text((out.width - 260, 8), label, fill=(255, 120, 150), font=f)
    out.save(path)


def contact_sheet(images, path, cols=3, thumb=(640, 360)):
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (thumb[0] + 12) + 12, rows * (thumb[1] + 40) + 12), (24, 24, 27))
    dr = ImageDraw.Draw(sheet)
    f = _font(20)
    for i, (label, p) in enumerate(images):
        x, y = 12 + (i % cols) * (thumb[0] + 12), 12 + (i // cols) * (thumb[1] + 40)
        im = Image.open(p).convert("RGB").resize(thumb, Image.LANCZOS)
        sheet.paste(im, (x, y + 28))
        dr.text((x, y + 2), label, fill=(235, 235, 235), font=f)
    sheet.save(path)


def _bg_color(img, box, scale, text_hex):
    x0, y0 = max(0, int(box["x"] * scale)), max(0, int(box["y"] * scale))
    x1, y1 = min(img.width, int((box["x"] + box["w"]) * scale)), min(img.height, int((box["y"] + box["h"]) * scale))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    px = np.asarray(img.crop((x0, y0, x1, y1)).convert("RGB")).reshape(-1, 3).astype(np.int16)
    t = np.array([int(text_hex[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.int16)
    far = px[np.abs(px - t).sum(axis=1) > 90]
    if len(far) < max(20, 0.15 * len(px)):
        return None
    q = (far // 16) * 16 + 8
    vals, counts = np.unique(q, axis=0, return_counts=True)
    c = vals[counts.argmax()]
    return "".join(f"{int(v):02X}" for v in c)


def run_qa(project, build="build", out="qa", diff_limit=0.012):
    project = pathlib.Path(project).resolve()
    bdir, qdir = project / build, project / out
    qdir.mkdir(parents=True, exist_ok=True)
    for old in qdir.glob("compare-*.png"):
        old.unlink()
    L = read_json(bdir / "layout.json")
    R = read_json(bdir / "render" / "render.json") if (bdir / "render" / "render.json").exists() else {}
    C = read_json(bdir / "compile.json") if (bdir / "compile.json").exists() else {}
    scale = L.get("reference_scale", 1.5)
    issues = []

    def add(slide, code, msg, el="", severity=None):
        issues.append({"slide": slide, "severity": severity or ("error" if code in ERROR_CODES else "warn"), "code": code, "msg": msg, "el": el})

    for w in L.get("warnings", []):
        add(w["slide"], w["code"], w["msg"], w.get("el", ""))
    for c in L.get("console", []):
        add(0, "console", c, severity="warn")
    ground_truth = str(R.get("engine") or "").startswith("powerpoint")
    for e in R.get("errors", []):
        # "not installed" is a fact about the machine, not the deck; a PowerPoint that failed while another
        # renderer succeeded is worth a look but doesn't make the deck wrong
        if e.startswith("powerpoint") and "not installed" not in e:
            add(0, "powerpoint-open", e, severity=None if ground_truth or not R.get("engine") else "warn")
    if R and R.get("engine") == "powerpoint-mac":
        add(0, "renderer", "rendered with PowerPoint for Mac — transitions/animations are checked in XML only", severity="warn")
    elif R and R.get("engine") != "powerpoint":
        add(0, "renderer", f"rendered with {R.get('engine')}, an approximation of PowerPoint: pixel diffs are advisory, not failures "
                           "(install PowerPoint for ground-truth QA)", severity="warn")
    if not R:
        add(0, "renderer", "no render found (run `deck.py render`) — visual diff skipped", severity="warn")
    for fam, info in (C.get("fonts") or {}).items():
        if not info.get("installed") and fam.lower() in OFFICE_FONTS:
            add(0, "font-local", f"'{fam}' isn't installed on this machine, so the local render substitutes it. "
                                 "PowerPoint ships it, so recipients see it correctly", severity="warn")
        elif not info.get("installed"):
            add(0, "font-missing", f"font '{fam}' is not installed — PowerPoint will substitute it. "
                                   f"Install it (`deck.py fonts install <files>` / `deck.py fonts fetch \"{fam}\"`) or switch fonts.")
        elif info.get("kit_only"):
            add(0, "font-not-installed", f"'{fam}' is only in the brand kit, so renderers substitute it and the diff is unreliable. "
                                         f"Install it: `deck.py fonts install brand/fonts/*` (build does this unless --no-font-install)",
                severity="warn")
        elif not info.get("system"):
            add(0, "font-portability", f"'{fam}' is a non-system font: recipients need it installed (or build with --embed-fonts, experimental)",
                severity="warn")
    for w in C.get("warnings", []):
        add(0, "compile", w, severity="warn")

    rslides = {s["index"]: s for s in R.get("slides", [])}
    per_slide = []
    sheet_imgs = []
    for s in L["slides"]:
        i = s["index"]
        ref = bdir / "ref" / f"slide-{i:02d}.png"
        ren = bdir / "render" / f"slide-{i:02d}.png"
        row = {"slide": i, "diff": None, "words": 0}
        flat = list(_walk(s["elements"]))
        # transitions / animations recognized by PowerPoint
        rs = rslides.get(i)
        if R.get("engine") == "powerpoint" and rs:
            if s.get("transition") and s["transition"].get("type") not in (None, "", "none") and rs.get("entry_effect", 0) == 0:
                add(i, "transition-ignored", f"PowerPoint did not recognize transition '{s['transition']['type']}'")
            want = sum(1 for e in flat if e.get("anim"))
            effs = rs.get("effects")
            if effs is not None and want != len(effs):
                add(i, "animation-ignored", f"expected {want} animations, PowerPoint parsed {len(effs)}")
        # visual diff
        if ref.exists() and ren.exists():
            masks = [(e["box"]["x"], e["box"]["y"], e["box"]["w"], e["box"]["h"]) for e in flat if e["kind"] == "chart"]
            ratio, regions, a, b, heat = visual_diff(ref, ren, masks, scale)
            row["diff"] = round(ratio, 4)
            _compare_image(a, b, heat, f"slide {i}: {ratio * 100:.1f}% differs", qdir / f"compare-{i:02d}.png")
            for rg in regions[:4]:
                hits = [e for e in flat if e["kind"] != "group" and e["box"]["x"] < rg["x"] + rg["w"] and rg["x"] < e["box"]["x"] + e["box"]["w"]
                        and e["box"]["y"] < rg["y"] + rg["h"] and rg["y"] < e["box"]["y"] + e["box"]["h"]]
                hits.sort(key=lambda e: e["box"]["w"] * e["box"]["h"])
                rg["elements"] = [f"{e['id']} {e.get('src', '')}" for e in hits[:2]]
            row["regions"] = regions[:4]
            biggest = regions[0]["area"] if regions else 0  # 16x16-px cells in one connected mismatch
            where = "; ".join(f"({int(r['x'])},{int(r['y'])} {int(r['w'])}x{int(r['h'])}) {', '.join(r.get('elements', [])) or 'background'}"
                              for r in regions[:3])
            if ratio > diff_limit or biggest >= REGION_ERROR_CELLS:
                # LibreOffice is an approximation of PowerPoint: report the drift, but only ground truth fails a build
                add(i, "visual-diff", f"{ratio * 100:.1f}% of pixels differ, largest mismatch {biggest} cells — {where}. "
                                      f"See qa/compare-{i:02d}.png" + ("" if ground_truth else " (approximate renderer: check it by eye)"),
                    severity=None if ground_truth else "warn")
            elif ratio > diff_limit * 2 / 3 or biggest >= REGION_WARN_CELLS:
                add(i, "visual-drift", f"{ratio * 100:.1f}% differ, largest mismatch {biggest} cells — {where}. See qa/compare-{i:02d}.png",
                    severity="warn")
        sheet_imgs.append((f"{i}", ren if ren.exists() else ref))
        # deterministic checks
        ref_img = Image.open(ref) if ref.exists() else None
        words = 0
        for e in flat:
            b_ = e["box"]
            if (e.get("text") or e.get("table") or e.get("chart")) and (
                    b_["x"] < -2 or b_["y"] < -2 or b_["x"] + b_["w"] > 1282 or b_["y"] + b_["h"] > 722):
                add(i, "off-slide", "content extends past the slide edge and will be cut off", e.get("src", ""))
            checked = False
            for p, r in _runs(e):
                words += len(r["text"].split())
                if r["size"] < 10.67:
                    add(i, "tiny-text", f"{r['size'] * 0.75:.1f}pt text is unreadable when presented", e.get("src", ""))
                elif r["size"] < 13.33:
                    add(i, "small-text", f"{r['size'] * 0.75:.1f}pt text is small for a presented slide", e.get("src", ""))
                if not checked and ref_img is not None and not r.get("gradient") and e["kind"] == "text":
                    checked = True
                    bg = _bg_color(ref_img, b_, scale, r["hex"])
                    if bg:
                        cr = contrast(r["hex"], bg)
                        large = r["size"] >= 24 or (r["size"] >= 18.66 and r.get("weight", 400) >= 700)
                        need = 3.0 if large else 4.5
                        if cr < need:
                            add(i, "contrast", f"contrast {cr:.2f}:1 (#{r['hex']} on ~#{bg}) below {need}:1", e.get("src", ""),
                                severity="error" if cr < need - 1.2 else "warn")
        row["words"] = words
        if words > 90:
            add(i, "dense", f"{words} words on one slide — split it or move detail to speaker notes", severity="warn")
        per_slide.append(row)

    if sheet_imgs:
        contact_sheet(sheet_imgs, qdir / "contact-sheet.png")
    errors = [x for x in issues if x["severity"] == "error"]
    status = "fail" if errors else ("pass-with-warnings" if issues else "pass")
    report = {"status": status, "errors": len(errors), "warnings": len(issues) - len(errors), "renderer": R.get("engine"),
              "slides": per_slide, "issues": issues, "contact_sheet": str(qdir / "contact-sheet.png")}
    write_json(qdir / "report.json", report)
    lines = [f"# Deck QA — {status.upper()}", "", f"renderer: {R.get('engine', 'none')} · errors: {len(errors)} · warnings: {len(issues) - len(errors)}",
             "", "| slide | diff | words | issues |", "|---|---|---|---|"]
    for row in per_slide:
        n = [x for x in issues if x["slide"] == row["slide"]]
        diff = "" if row["diff"] is None else "%.1f%%" % (row["diff"] * 100)
        codes = ", ".join(sorted({x["code"] for x in n})) or "—"
        lines.append(f"| {row['slide']} | {diff} | {row['words']} | {codes} |")
    lines += ["", "## Issues", ""]
    for x in sorted(issues, key=lambda x: (x["severity"] != "error", x["slide"])):
        lines.append(f"- **{x['severity']}** [slide {x['slide'] or '-'}] `{x['code']}` {x['msg']}" + (f" — {x['el']}" if x["el"] else ""))
    (qdir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
