"""Design-taste lint: the measurable part of a design review.

Works on a Slidekick build (build/layout.json, exact Chromium geometry) or on any deck read by `inspect` (inventory.json).
It finds what a design director's eye catches first — near-miss alignments, headlines that jump between slides,
type-scale sprawl, runt lines, uneven rhythm, off-palette colours, sameness, the AI-deck tells — and reports them as
`major` or `polish` findings. It never judges whether the deck is *good*; that is the reviewer's job (taste.md)."""
import colorsys
import math
import pathlib
import re

from .util import CANVAS_W, hex6, luminance, read_json, write_json

W = CANVAS_W
WEIGHT_WORDS = re.compile(r"\s+(thin|hairline|extralight|extra light|ultralight|light|regular|book|normal|medium|semibold|semi bold|"
                          r"demibold|demi bold|bold|extrabold|extra bold|ultrabold|black|heavy|italic|oblique)\b.*$", re.I)
MONO = re.compile(r"mono|consolas|courier|menlo|monaco|code", re.I)


# ---------- normalisation ----------
class El:
    __slots__ = ("kind", "box", "label", "paras", "fill", "children", "image", "is_group", "caps", "spacing")

    def __init__(self, kind, box, label, paras=None, fill=None, image=None):
        self.kind, self.box, self.label = kind, box, label
        self.paras = paras or []  # [{runs:[{text,size,hex,weight,family,caps,spacing,mono}], align, lines, llr, baseline}]
        self.fill, self.image = fill, image
        self.children = []
        self.is_group = kind == "group"

    @property
    def text(self):
        return "\n".join("".join(r["text"] for r in p["runs"]) for p in self.paras)

    @property
    def size(self):
        return max((r["size"] for p in self.paras for r in p["runs"]), default=0)

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


def _family(css):
    first = (css or "").split(",")[0].strip().strip("'\"")
    return WEIGHT_WORDS.sub("", first).strip() or first


def _from_layout_el(e):
    kind = e["kind"]
    label = (e.get("name") or e.get("id") or "") + (f" {e['src']}" if e.get("src") else "")
    paras = []
    texts = [e["text"]] if e.get("text") else []
    if e.get("table"):
        texts += [c["text"] for c in e["table"]["cells"] if c.get("text")]
    for t in texts:
        for p in t["paragraphs"]:
            runs = [{"text": r["text"], "size": r["size"], "hex": hex6(r.get("hex", "000000")), "weight": r.get("weight", 400),
                     "family": _family(r.get("family")), "caps": r.get("caps", "none"), "spacing": r.get("spacing", 0),
                     "mono": bool(MONO.search(r.get("family") or ""))} for r in p["runs"] if not r.get("br") and r.get("text")]
            if runs:
                paras.append({"runs": runs, "align": p.get("align", "l"), "lines": p.get("lines"), "llr": p.get("last_line_ratio"),
                              "baseline": e["box"]["y"] + p["baseline_first"] if "baseline_first" in p and t is e.get("text") else None})
    fill = None
    sh = e.get("shape") or {}
    if (sh.get("fill") or {}).get("type") == "solid":
        fill = hex6(sh["fill"]["hex"])
    image = None
    if e.get("image") and e["image"].get("natural") and e["image"].get("kind") == "raster":
        nw, nh = e["image"]["natural"]
        c = e["image"].get("crop") or {}
        if nw and nh and e["box"]["w"] > 1 and e["box"]["h"] > 1:
            vw, vh = nw * (1 - c.get("l", 0) - c.get("r", 0)), nh * (1 - c.get("t", 0) - c.get("b", 0))
            image = {"ppx": min(vw / e["box"]["w"], vh / e["box"]["h"])}
    el = El(kind if kind != "shape" or not paras else "text", e["box"], label, paras, fill, image)
    el.children = [_from_layout_el(c) for c in e.get("children", [])]
    return el


def _from_inv_el(e):
    label = f"#{e['id']} {e['name']}"
    paras = []
    for p in (e.get("text") or {}).get("paragraphs", []):
        runs = [{"text": r["text"], "size": r["size"], "hex": r["hex"], "weight": r["weight"], "family": _family(r["family"]),
                 "caps": r.get("caps", "none"), "spacing": r.get("spacing", 0), "mono": bool(MONO.search(r["family"] or ""))}
                for r in p["runs"] if not r.get("br")]
        if runs:
            paras.append({"runs": runs, "align": p.get("align", "l"), "lines": p.get("lines"), "llr": p.get("last_line_ratio"),
                          "baseline": None})
    if e.get("table"):
        pass  # table text sizes are not resolved for inventories; skip
    fill = e.get("fill") if e.get("fill") not in (None, "image", "gradient") else None
    kind = {"line": "shape", "media": "image", "other": "shape"}.get(e["kind"], e["kind"])
    el = El(kind, e["box"], label, paras, fill, None)
    el.children = [_from_inv_el(c) for c in e.get("children", [])]
    return el


def _bg_dark(bg):
    if isinstance(bg, dict):
        f = bg.get("fill") or {}
        if f.get("type") == "solid":
            return luminance(f["hex"]) < 0.18
        if bg.get("image"):
            return None
        if f.get("type") == "gradient" and f.get("stops"):
            return luminance(f["stops"][0]["hex"]) < 0.18
        return False
    if isinstance(bg, str) and bg.startswith("#"):
        return luminance(bg[1:]) < 0.18
    return None


def load(project=None, inventory=None):
    if inventory:
        inv = read_json(inventory)
        H = (inv["deck"].get("canvas") or [W, 720])[1]
        slides = [{"index": s["index"], "dark": _bg_dark(s.get("background")), "units": [_from_inv_el(e) for e in s["elements"]]}
                  for s in inv["slides"] if not s.get("hidden")]
        palette = list((inv["deck"].get("theme") or {}).get("colors", {}).values())
        return slides, palette, H, "inventory"
    L = read_json(pathlib.Path(project) / "build" / "layout.json")
    slides = [{"index": s["index"], "dark": _bg_dark(s.get("background")), "units": [_from_layout_el(e) for e in s["elements"]]}
              for s in L["slides"]]
    palette = []
    bj = pathlib.Path(project) / "brand" / "brand.json"
    if bj.exists():
        b = read_json(bj)
        palette = list((b.get("theme") or {}).values())
        for v in (b.get("colors") or {}).values():
            if isinstance(v, str) and re.fullmatch(r"#?[0-9A-Fa-f]{6}", v.strip()):
                palette.append(v)
    return slides, [hex6(p) for p in palette if isinstance(p, str)], 720, "layout"


# ---------- geometry helpers ----------
def _bleeds(b, H):
    return b["x"] < -0.5 or b["y"] < -0.5 or b["x"] + b["w"] > W + 0.5 or b["y"] + b["h"] > H + 0.5


def _background_like(e, H):
    b = e.box
    return b["w"] * b["h"] >= 0.6 * W * H or (e.kind == "image" and (b["w"] >= 0.9 * W or b["h"] >= 0.9 * H))


def _content_units(s, H):
    return [u for u in s["units"] if not _background_like(u, H) and not _bleeds(u.box, H) and u.box["w"] > 1 and u.box["h"] > 1]


def _overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


# ---------- colour helpers ----------
def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hls(h):
    r, g, b = (v / 255 for v in _rgb(h))
    return colorsys.rgb_to_hls(r, g, b)


def _on_palette(h, palette):
    _, l, s = _hls(h)
    if s < 0.12 or l < 0.06 or l > 0.97:
        return True  # neutrals are always allowed
    c = _rgb(h)
    for p in palette:
        pr = _rgb(p)
        for t in range(0, 21):
            f = t / 20
            for tgt in ((255, 255, 255), (0, 0, 0)):
                m = tuple(pr[i] * (1 - f) + tgt[i] * f for i in range(3))
                if math.dist(m, c) < 22:
                    return True
    return False


def _accent(h):
    hue, l, s = _hls(h)
    return s >= 0.35 and 0.15 <= l <= 0.85, hue


# ---------- checks ----------
def run_taste(project=None, inventory=None, out_dir=None):
    slides, palette, H, source = load(project, inventory)
    F = []

    def add(sev, code, slide, msg, el=""):
        F.append({"severity": sev, "code": code, "slide": slide, "msg": msg, "el": el})

    n = len(slides)
    sizes, fams, colours = {}, {}, {}
    heads, margins, kicker_slides, card_slides, corner_marks = [], [], [], [], {}

    for s in slides:
        i = s["index"]
        units = _content_units(s, H)
        allel = [e for u in s["units"] for e in u.walk()]
        texts = [e for e in allel if e.paras]

        # -- type, families, colours
        for e in texts:
            for p in e.paras:
                for r in p["runs"]:
                    k = round(r["size"] * 2) / 2
                    sizes[k] = sizes.get(k, 0) + len(r["text"])
                    if not r["mono"]:
                        fams.setdefault(r["family"], set()).add(r["weight"])
                    colours.setdefault(r["hex"].upper(), set()).add(i)
        for e in allel:
            if e.fill:
                colours.setdefault(e.fill.upper(), set()).add(i)

        # -- headline of this slide
        cands = [e for e in texts if e.box["y"] < 0.45 * H and len(e.text.split()) >= 3]
        head = max(cands, key=lambda e: (round(e.size), -e.box["y"]), default=None)
        if head:
            base = head.paras[0]["baseline"]
            heads.append({"slide": i, "x": head.box["x"], "y": base if base is not None else head.box["y"], "size": head.size,
                          "align": head.paras[0]["align"], "label": head.label})

        # -- margins
        xs = [u.box["x"] for u in units if u.box["x"] > 2]
        if xs:
            margins.append((i, min(xs)))

        # -- near-miss alignment (left/right edges of everything; tops/bottoms of non-text; baselines of text)
        def near_miss(group, where):
            seen = 0
            for a_i, a in enumerate(group):
                for b in group[a_i + 1:]:
                    for edge, fa, fb in (("left", a.box["x"], b.box["x"]),
                                         ("right", a.box["x"] + a.box["w"], b.box["x"] + b.box["w"])):
                        if edge == "right" and (a.paras or b.paras):
                            continue  # ragged text boxes don't define a right edge
                        d = abs(fa - fb)
                        if 0.75 < d <= 6 and seen < 3:
                            seen += 1
                            add("major", "near-miss", i, f"{edge} edges {d:.0f}px apart{where} — align them exactly or offset on purpose",
                                f"{a.label} / {b.label}")
                    if not a.paras and not b.paras:
                        for edge, fa, fb in (("top", a.box["y"], b.box["y"]),
                                             ("bottom", a.box["y"] + a.box["h"], b.box["y"] + b.box["h"])):
                            d = abs(fa - fb)
                            if 0.75 < d <= 6 and seen < 3 and _overlap(a.box["x"], a.box["x"] + a.box["w"], b.box["x"], b.box["x"] + b.box["w"]) == 0:
                                seen += 1
                                add("major", "near-miss", i, f"{edge} edges {d:.0f}px apart{where}", f"{a.label} / {b.label}")
                    ba = a.paras[0]["baseline"] if a.paras else None
                    bb = b.paras[0]["baseline"] if b.paras else None
                    if ba is not None and bb is not None and 0.75 < abs(ba - bb) <= 5 and seen < 3 and \
                            _overlap(a.box["x"], a.box["x"] + a.box["w"], b.box["x"], b.box["x"] + b.box["w"]) == 0:
                        seen += 1
                        add("polish", "baseline", i, f"side-by-side text baselines {abs(ba - bb):.0f}px apart — share one baseline",
                            f"{a.label} / {b.label}")
        near_miss(units, "")
        for u in s["units"]:
            if u.children:
                near_miss([c for c in u.children if not _background_like(c, H) and c.box["w"] > 1], f" inside {u.label}")

        # -- edge crowding
        for u in units:
            b = u.box
            gaps = {"left": b["x"], "top": b["y"], "right": W - b["x"] - b["w"], "bottom": H - b["y"] - b["h"]}
            tight = {k: v for k, v in gaps.items() if 0.5 < v < 24}
            if tight:
                k, v = min(tight.items(), key=lambda kv: kv[1])
                add("major", "edge", i, f"{v:.0f}px from the {k} edge — keep the margin or bleed it off deliberately", u.label)

        # -- crowding between units
        for a_i, a in enumerate(units):
            for b in units[a_i + 1:]:
                if a.paras and b.paras:
                    continue  # text boxes carry half-leading; their box gaps are not visual gaps
                ox = _overlap(a.box["x"], a.box["x"] + a.box["w"], b.box["x"], b.box["x"] + b.box["w"])
                oy = _overlap(a.box["y"], a.box["y"] + a.box["h"], b.box["y"], b.box["y"] + b.box["h"])
                if ox > 0 and oy > 0:
                    continue
                if ox > 0.3 * min(a.box["w"], b.box["w"]):
                    g = max(b.box["y"] - a.box["y"] - a.box["h"], a.box["y"] - b.box["y"] - b.box["h"])
                elif oy > 0.3 * min(a.box["h"], b.box["h"]):
                    g = max(b.box["x"] - a.box["x"] - a.box["w"], a.box["x"] - b.box["x"] - b.box["w"])
                else:
                    continue
                if 0 < g < 10:
                    add("polish", "tight", i, f"only {g:.0f}px between these — group them tighter on purpose or give them air",
                        f"{a.label} / {b.label}")

        # -- rows of similar items: card grids and rhythm
        boxy = [u for u in units if u.kind in ("group", "shape", "image") or (u.paras and u.fill)]
        rows = {}
        for u in boxy:
            key = next((k for k in rows if abs(k[0] - u.box["y"]) <= 6 and abs(k[1] - u.box["w"]) <= 0.05 * k[1]
                        and abs(k[2] - u.box["h"]) <= 0.05 * k[2]), None)
            rows.setdefault(key or (u.box["y"], u.box["w"], u.box["h"]), []).append(u)
        for key, row in rows.items():
            if len(row) < 3 or key[1] > 0.45 * W:
                continue
            row.sort(key=lambda u: u.box["x"])
            gaps = [b.box["x"] - a.box["x"] - a.box["w"] for a, b in zip(row, row[1:])]
            if any(c.children or c.paras for c in row) and i not in card_slides:
                card_slides.append(i)
            if max(gaps) - min(gaps) > 4:
                add("major", "rhythm", i, f"uneven gaps in a row of {len(row)} items: {', '.join(f'{g:.0f}' for g in gaps)}px "
                                          f"— equal gaps (or close the hole)", row[0].label)

        # -- kicker above the headline
        if head:
            for e in texts:
                if e is head or e.size > 18 or not e.paras:
                    continue
                runs = [r for p in e.paras for r in p["runs"]]
                caps = all(r["caps"] == "all" or (r["text"].upper() == r["text"] and any(c.isalpha() for c in r["text"])) for r in runs)
                below = head.box["y"] - (e.box["y"] + e.box["h"])
                if caps and -6 <= below <= 60 and abs(e.box["x"] - head.box["x"]) < 40:
                    kicker_slides.append(i)
                    break

        # -- small images in corners (logo-in-every-corner tell)
        for u in s["units"]:
            b = u.box
            if u.kind == "image" and b["w"] * b["h"] < 0.03 * W * H:
                cx = "l" if b["x"] < 160 else ("r" if b["x"] + b["w"] > W - 160 else None)
                cy = "t" if b["y"] < 120 else ("b" if b["y"] + b["h"] > H - 120 else None)
                if cx and cy:
                    corner_marks.setdefault(cy + cx, set()).add(i)

        # -- text craft
        for e in texts:
            for p in e.paras:
                size = max(r["size"] for r in p["runs"])
                txt = "".join(r["text"] for r in p["runs"])
                lines, llr = p.get("lines"), p.get("llr")
                if lines and llr is not None and lines >= 2:
                    tail = " ".join(txt.split()[-2:])
                    if size >= 28 and llr < 0.34:
                        add("major", "runt", i, f"headline ends in a short last line (“…{tail}”) — rebalance with a <br> or a narrower box, or edit the copy", e.label)
                    elif size < 28 and llr < 0.15 and lines >= 2:
                        add("polish", "widow", i, f"paragraph ends with a lone word (“…{tail}”)", e.label)
                if lines and size >= 28 and lines >= 3:
                    add("polish", "long-headline", i, f"{lines}-line headline — cut it to ≤ 2 lines", e.label)
                if size < 28 and not any(r["mono"] for r in p["runs"]):
                    if lines and lines >= 2 and p["align"] in ("l", "just") and len(txt) / lines > 90:
                        add("polish", "measure", i, f"~{len(txt) / lines:.0f} characters per line; 45–75 reads best — narrow the column", e.label)
                    if p["align"] == "ctr" and ((lines or 0) >= 3 or (lines is None and len(txt) > 160)):
                        add("polish", "centred-body", i, "centred multi-line body text is hard to read — left-align it", e.label)
                words = len(txt.split())
                if words >= 7 and all(r["caps"] == "all" or r["text"].upper() == r["text"] for r in p["runs"]) and any(c.isalpha() for c in txt):
                    add("polish", "all-caps", i, "a long all-caps line reads slowly — sentence case", e.label)
        glyphs = {}
        for e in texts:
            for p in e.paras:
                txt = "".join(r["text"] for r in p["runs"] if not r["mono"])
                for code, rx, fix in GLYPH_RULES:
                    m = rx.search(txt)
                    if m and code not in glyphs:
                        glyphs[code] = (fix, txt[max(0, m.start() - 12):m.end() + 12].strip(), e.label)
        for code, (fix, ctx, lab) in glyphs.items():
            add("polish", "typography", i, f"{fix} (“{ctx}”)", lab)

        # -- accents per slide
        hues = []
        for e in allel:
            for h in [r["hex"] for p in e.paras for r in p["runs"]] + ([e.fill] if e.fill else []):
                ok, hue = _accent(h)
                if ok and not any(min(abs(hue - x), 1 - abs(hue - x)) < 0.055 for x in hues):
                    hues.append(hue)
        if len(hues) > 2:
            add("polish", "accents", i, f"{len(hues)} accent hues on one slide — one accent should carry the meaning")

        # -- image resolution (layout only: inventories report low-res in their own issues)
        for e in allel:
            if e.image and e.image["ppx"] < 1.2:
                add("major", "soft-image", i, f"image is shown at {1 / e.image['ppx']:.1f}× its pixels — soft on a 1080p projector; use a larger source", e.label)

    # ---------- deck-level ----------
    # headlines jumping between slides
    content_heads = []
    if heads:
        med = sorted(h["size"] for h in heads)[len(heads) // 2]
        content_heads = [h for h in heads if 0.8 * med <= h["size"] <= 1.25 * med]
    for axis in ("x", "y"):
        vals = {}
        for h in content_heads:
            vals.setdefault(round(h[axis]), []).append(h)
        if not vals:
            continue
        mode, members = max(vals.items(), key=lambda kv: len(kv[1]))
        if len(members) >= 3:
            for h in content_heads:
                d = abs(h[axis] - mode)
                if 1 < d <= 24:
                    add("major", "headline-jump", h["slide"],
                        f"headline {'starts' if axis == 'x' else 'baseline sits'} {d:.0f}px off where it is on slides "
                        f"{', '.join(str(m['slide']) for m in members[:5])} — it visibly jumps when advancing; lock its position", h["label"])
    # margin drift
    mv = {}
    for i, x in margins:
        mv.setdefault(round(x), []).append(i)
    if mv:
        mode, members = max(mv.items(), key=lambda kv: len(kv[1]))
        if len(members) >= 3:
            for i, x in margins:
                if 1 < abs(x - mode) <= 24:
                    add("major", "margin", i, f"left margin {x:.0f}px vs {mode}px on most slides")
    # type scale
    used = sorted(k for k, v in sizes.items() if v >= 3)
    if len(used) > 8:
        add("major", "type-scale", 0, f"{len(used)} text sizes ({', '.join(f'{u:g}' for u in used)} px) — a deck needs 5–7 steps; snap to the scale")
    for a, b in zip(used, used[1:]):
        if a >= 13 and b / a < 1.13:
            add("polish", "type-scale", 0, f"{a:g}px and {b:g}px are too close to read as different levels — merge them")
    real_fams = sorted(fams)
    if len(real_fams) > 2:
        add("major", "families", 0, f"{len(real_fams)} type families ({', '.join(real_fams)}) — use at most two (display + body)")
    for f, ws in fams.items():
        if len(ws) > 3:
            add("polish", "weights", 0, f"{f} in {len(ws)} weights ({', '.join(map(str, sorted(ws)))}) — 2–3 weights read as a system")
    # palette
    off = {h: sl for h, sl in colours.items() if palette and not _on_palette(h, palette)}
    for h, sl in sorted(off.items(), key=lambda kv: -len(kv[1]))[:6]:
        add("major" if len(sl) >= 3 else "polish", "off-palette", 0,
            f"#{h} is not a brand colour or a tint of one (slides {', '.join(map(str, sorted(sl)))})")
    # sameness
    sigs = [(s["index"], _signature(s, H), s["dark"]) for s in slides]
    clusters = []
    cluster_of = {}
    for i, sig, dark in sigs:
        for c in clusters:
            if c["dark"] == dark and _jacc(c["sig"], sig) >= 0.75:
                c["members"].append(i)
                cluster_of[i] = id(c)
                break
        else:
            c = {"sig": sig, "dark": dark, "members": [i]}
            clusters.append(c)
            cluster_of[i] = id(c)
    comps = len(clusters)
    if n >= 6 and comps < min(5, math.ceil(0.4 * n)):
        add("major", "sameness", 0, f"only {comps} distinct compositions across {n} slides — vary scale, density and layout (design.md)")
    run = [sigs[0][0]] if sigs else []
    for (pi, _, _), (ci, _, _) in zip(sigs, sigs[1:]):
        if cluster_of[ci] == cluster_of[pi]:
            run.append(ci)
        else:
            if len(run) >= 3:
                add("major", "sameness", run[0], f"slides {run[0]}–{run[-1]} share one composition — break the run")
            run = [ci]
    if len(run) >= 3:
        add("major", "sameness", run[0], f"slides {run[0]}–{run[-1]} share one composition — break the run")
    if len(card_slides) > 1:
        add("major", "card-grid", 0, f"row-of-equal-cards layout on slides {', '.join(map(str, card_slides))} — use it at most once (AI-deck tell)")
    if len(kicker_slides) > 3:
        add("major", "kicker", 0, f"small uppercase kicker above the headline on {len(kicker_slides)} slides "
                                  f"({', '.join(map(str, kicker_slides))}) — an AI-deck tell; keep it where it earns its place")
    for corner, sl in corner_marks.items():
        if len(sl) >= 4 and len(sl) >= 0.6 * n:
            add("polish", "corner-mark", 0, f"small image in the same corner on {len(sl)} slides — logos belong on title/closing unless the brand asks")

    order = {"major": 0, "polish": 1}
    F.sort(key=lambda f: (order[f["severity"]], f["slide"] or 0))
    metrics = {"source": source, "slides": n, "compositions": comps, "font_sizes": used, "families": real_fams,
               "off_palette": sorted(off), "kicker_slides": kicker_slides, "card_grid_slides": card_slides,
               "headline_positions": {h["slide"]: [round(h["x"]), round(h["y"])] for h in heads}}
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {"metrics": metrics, "findings": F, "report": str(out_dir / "taste.md")}
    write_json(out_dir / "taste.json", result)
    (out_dir / "taste.md").write_text(_markdown(metrics, F), encoding="utf-8")
    return result


GLYPH_RULES = [
    ("quotes", re.compile(r"\"|(?<=\w)'(?=\w)|(?<=\s)'(?=\w)"), "straight quotes/apostrophes — use “ ” ‘ ’"),
    ("dash", re.compile(r"\s-\s|--"), "hyphen used as a dash — use an em dash (—) or spaced en dash (–)"),
    ("ellipsis", re.compile(r"\.\.\."), "three dots — use the ellipsis character (…)"),
    ("times", re.compile(r"\b\d+(?:\.\d+)?\s?x\b(?![-\w])|\b\d+\s?x\s?\d+\b"), "letter x as a multiplier — use × (3×, 1920×1080)"),
    ("range", re.compile(r"(?<![\d-])\d{1,4}-\d{1,4}(?![\d-])"), "hyphen in a number range — use an en dash (10–20)"),
    ("spaces", re.compile(r"\S  +\S"), "double space"),
]


def _signature(s, H):
    cells = set()
    cw, ch = W / 8, H / 4
    for u in s["units"]:
        b = u.box
        if _background_like(u, H) and u.kind != "image":
            continue
        for gx in range(8):
            for gy in range(4):
                ox = _overlap(b["x"], b["x"] + b["w"], gx * cw, (gx + 1) * cw)
                oy = _overlap(b["y"], b["y"] + b["h"], gy * ch, (gy + 1) * ch)
                if ox * oy >= 0.25 * cw * ch:
                    cells.add((gx, gy, "i" if u.kind == "image" else "t" if u.paras and not u.children else "b"))
    return cells


def _jacc(a, b):
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


def _markdown(m, F):
    lines = ["# Taste lint", "",
             "Measured signals only — the design review (references/taste.md) judges the rest. "
             "`major` = a design director would send it back; `polish` = finish details.", "",
             "| signal | value |", "|---|---|",
             f"| slides | {m['slides']} |",
             f"| distinct compositions | {m['compositions']} |",
             f"| text sizes (px) | {', '.join(f'{s:g}' for s in m['font_sizes'])} |",
             f"| type families | {', '.join(m['families'])} |",
             f"| off-palette colours | {', '.join('#' + h for h in m['off_palette']) or '—'} |",
             f"| kicker-above-headline slides | {', '.join(map(str, m['kicker_slides'])) or '—'} |",
             f"| card-grid slides | {', '.join(map(str, m['card_grid_slides'])) or '—'} |", ""]
    deck = [f for f in F if not f["slide"]]
    if deck:
        lines += ["## Deck", ""] + [f"- **{f['severity']}** `{f['code']}` {f['msg']}" for f in deck] + [""]
    by = {}
    for f in F:
        if f["slide"]:
            by.setdefault(f["slide"], []).append(f)
    for i in sorted(by):
        lines += [f"## Slide {i}", ""] + [f"- **{f['severity']}** `{f['code']}` {f['msg']}" + (f" — {f['el']}" if f["el"] else "")
                                          for f in by[i]] + [""]
    if not F:
        lines.append("No measurable findings. That does not mean the design is good — run the review.")
    return "\n".join(lines) + "\n"
