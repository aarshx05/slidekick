"""DrawingML / PresentationML builders. XML shapes mirror what PowerPoint itself writes (probed via COM)."""
import itertools
import math

from lxml import etree
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.oxml.xmlchemy import OxmlElement

from .util import hex6

MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
P15 = "http://schemas.microsoft.com/office/powerpoint/2012/main"
P159 = "http://schemas.microsoft.com/office/powerpoint/2015/09/main"
SVG_EXT_URI = "{96DAC541-7B7A-43D3-8B79-37D633B846F1}"
ASVG = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"
RT_FONT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
FILL_TAGS = {qn(t) for t in ("a:noFill", "a:solidFill", "a:gradFill", "a:blipFill", "a:pattFill", "a:grpFill")}


def E(tag, attrs=None, children=()):
    e = OxmlElement(tag)
    for k, v in (attrs or {}).items():
        if v is None:
            continue
        e.set(qn(k) if ":" in k else k, str(v))
    for c in children:
        if c is not None:
            e.append(c)
    return e


def first(*els):
    for e in els:
        if e is not None:
            return e
    return None


# ---------- colors & fills ----------
def color(hexv, alpha=1.0, theme=None):
    hv = hex6(hexv)
    slot = (theme or {}).get(hv)
    c = E("a:schemeClr", {"val": slot}) if slot else E("a:srgbClr", {"val": hv})
    if alpha is not None and alpha < 0.999:
        c.append(E("a:alpha", {"val": int(round(max(0.0, alpha) * 100000))}))
    return c


def solid_fill(hexv, alpha=1.0, theme=None):
    return E("a:solidFill", children=[color(hexv, alpha, theme)])


def grad_fill(g, theme=None, alpha_mult=1.0):
    stops = sorted(g["stops"], key=lambda s: s["pos"])
    if len(stops) == 1:
        stops = stops + [dict(stops[0], pos=1.0)]
    gs = E("a:gsLst", children=[E("a:gs", {"pos": int(round(s["pos"] * 100000))}, [color(s["hex"], s["alpha"] * alpha_mult, theme)])
                                for s in stops])
    gf = E("a:gradFill", {"rotWithShape": "1"}, [gs])
    if g.get("kind", "linear") == "linear":
        ang = (g.get("angle", 180) - 90) % 360
        gf.append(E("a:lin", {"ang": int(round(ang * 60000)) % 21600000, "scaled": "0"}))
    else:
        cx, cy = g.get("cx", 50), g.get("cy", 50)
        gf.append(E("a:path", {"path": "circle"}, [E("a:fillToRect", {
            "l": int(cx * 1000), "t": int(cy * 1000), "r": int((100 - cx) * 1000), "b": int((100 - cy) * 1000)})]))
    return gf


def fill_el(fill, theme=None, alpha_mult=1.0):
    if not fill:
        return E("a:noFill")
    if fill["type"] == "gradient":
        return grad_fill(fill, theme, alpha_mult)
    return solid_fill(fill["hex"], fill.get("alpha", 1) * alpha_mult, theme)


def line_el(line, emu, theme=None, alpha_mult=1.0):
    if not line:
        return E("a:ln", children=[E("a:noFill")])
    ln = E("a:ln", {"w": max(1, emu(line["width"]))}, [solid_fill(line["hex"], line.get("alpha", 1) * alpha_mult, theme)])
    dash = {"dashed": "dash", "dotted": "sysDot"}.get(line.get("dash"))
    if dash:
        ln.append(E("a:prstDash", {"val": dash}))
    return ln


def shadow_el(sh, emu, w, h, theme=None, alpha_mult=1.0):
    if not sh:
        return None
    dist = math.hypot(sh["x"], sh["y"])
    direction = (math.degrees(math.atan2(sh["y"], sh["x"])) % 360) if dist else 0
    attrs = {"blurRad": emu(sh.get("blur", 0)), "dist": emu(dist), "dir": int(direction * 60000), "algn": "ctr", "rotWithShape": "0"}
    spread = sh.get("spread", 0)
    if spread and w and h:
        attrs["sx"] = int((1 + 2 * spread / w) * 100000)
        attrs["sy"] = int((1 + 2 * spread / h) * 100000)
    return E("a:effectLst", children=[E("a:outerShdw", attrs, [color(sh["hex"], sh.get("alpha", 1) * alpha_mult, theme)])])


def set_sppr(spPr, fill=None, ln=None, effects=None):
    """Replace fill/line/effects on an spPr while keeping schema order (xfrm, geom, fill, ln, effectLst...)."""
    for ch in list(spPr):
        if ch.tag in FILL_TAGS or ch.tag in (qn("a:ln"), qn("a:effectLst"), qn("a:effectDag")):
            spPr.remove(ch)
    anchor = first(spPr.find(qn("a:prstGeom")), spPr.find(qn("a:custGeom")), spPr.find(qn("a:xfrm")))
    idx = (list(spPr).index(anchor) + 1) if anchor is not None else 0
    for el in (fill, ln, effects):
        if el is not None:
            spPr.insert(idx, el)
            idx += 1


def set_geometry(spPr, prst, adj=None):
    geom = spPr.find(qn("a:prstGeom"))
    if geom is None:
        return
    geom.set("prst", prst)
    av = geom.find(qn("a:avLst"))
    if av is None:
        av = E("a:avLst")
        geom.append(av)
    for ch in list(av):
        av.remove(ch)
    if adj is not None:
        av.append(E("a:gd", {"name": "adj", "fmla": f"val {int(adj)}"}))


# ---------- text ----------
def rpr(run, fx, tag="a:rPr"):
    """fx: callable context with .pt(px), .emu(px), .font(run)->(typeface,b,i), .theme, .link_rid(url)."""
    typeface, bold, italic = fx.font(run)
    a = {"lang": fx.lang, "sz": max(100, min(400000, int(round(fx.pt(run["size"]) * 100)))),
         "b": "1" if bold else "0", "i": "1" if italic else "0", "kern": "0", "dirty": "0"}
    if run.get("underline"):
        a["u"] = "sng"
    if run.get("strike"):
        a["strike"] = "sngStrike"
    if run.get("caps") in ("all", "small"):
        a["cap"] = run["caps"]
    if run.get("spacing"):
        a["spc"] = int(round(fx.pt(run["spacing"]) * 100))
    if run.get("baseline"):
        a["baseline"] = int(run["baseline"] * 1000)
    r = E(tag, a)
    alpha = run.get("alpha", 1) * fx.alpha
    if run.get("gradient"):
        r.append(grad_fill(run["gradient"], fx.theme, fx.alpha))
    else:
        r.append(solid_fill(run["hex"], alpha, fx.theme))
    if run.get("shadow"):
        r.append(shadow_el(run["shadow"], fx.emu, 0, 0, fx.theme, fx.alpha))
    r.append(E("a:latin", {"typeface": fx.theme_font(typeface)}))
    r.append(E("a:cs", {"typeface": typeface}))
    if run.get("link") and tag == "a:rPr":
        r.append(E("a:hlinkClick", {"r:id": fx.link_rid(run["link"])}))
    return r


def paragraph(p, fx):
    attrs = {"algn": p.get("align", "l")}
    if p.get("mar_l"):
        attrs["marL"] = fx.emu(p["mar_l"])
    if p.get("mar_r"):
        attrs["marR"] = fx.emu(p["mar_r"])
    if p.get("indent"):
        attrs["indent"] = fx.emu(p["indent"])
    if p.get("level"):
        attrs["lvl"] = int(p["level"])
    ppr = E("a:pPr", attrs, [
        E("a:lnSpc", children=[E("a:spcPts", {"val": max(0, int(round(fx.pt(p["line_height"]) * 100)))})]),
        E("a:spcBef", children=[E("a:spcPts", {"val": max(0, int(round(fx.pt(p.get("space_before", 0)) * 100)))})]),
        E("a:spcAft", children=[E("a:spcPts", {"val": "0"})]),
    ])
    b = p.get("bullet")
    if b:
        ppr.append(E("a:buClr", children=[color(b["hex"], b.get("alpha", 1), fx.theme)]))
        first_size = next((r["size"] for r in p["runs"] if not r.get("br")), b.get("size", 16))
        ppr.append(E("a:buSzPct", {"val": int(max(25, min(400, 100 * b.get("size", first_size) / first_size)) * 1000)}))
        if b["type"] == "auto":
            ppr.append(E("a:buFont", {"typeface": "+mj-lt"}))
            ppr.append(E("a:buAutoNum", {"type": b["scheme"], "startAt": b.get("start", 1) if b.get("start", 1) != 1 else None}))
        else:
            ppr.append(E("a:buFont", {"typeface": "Arial", "panose": "020B0604020202020204", "pitchFamily": "34", "charset": "0"}))
            ppr.append(E("a:buChar", {"char": b["char"]}))
    else:
        ppr.append(E("a:buNone"))
    para = E("a:p", children=[ppr])
    last = None
    for run in p["runs"]:
        if run.get("br"):
            para.append(E("a:br", children=[rpr(run, fx)]))
            continue
        t = E("a:t")
        t.text = run["text"]
        para.append(E("a:r", children=[rpr(run, fx), t]))
        last = run
    if last is not None:
        para.append(rpr(last, fx, tag="a:endParaRPr"))
    return para


def body_pr(text, fx, wrap=True, insets=(0, 0, 0, 0), anchor="t"):
    l, t, r, b = insets
    return E("a:bodyPr", {"wrap": "square" if wrap else "none", "lIns": fx.emu(max(0, l)), "tIns": fx.emu(max(0, t)),
                          "rIns": fx.emu(max(0, r)), "bIns": fx.emu(max(0, b)), "anchor": anchor, "rtlCol": "0"},
             [E("a:noAutofit")])


def fill_txbody(txBody, text, fx, wrap, insets, anchor):
    for ch in list(txBody):
        txBody.remove(ch)
    txBody.append(body_pr(text, fx, wrap, insets, anchor))
    txBody.append(E("a:lstStyle"))
    for p in text["paragraphs"]:
        txBody.append(paragraph(p, fx))


# ---------- transitions ----------
_DIR = {"left": "l", "right": "r", "up": "u", "down": "d", "l": "l", "r": "r", "u": "u", "d": "d",
        "left-up": "lu", "right-up": "ru", "left-down": "ld", "right-down": "rd"}
TRANSITIONS = {
    "fade": ("", "<p:fade/>"), "fade-black": ("", '<p:fade thruBlk="1"/>'),
    "push": ("", '<p:push dir="{d4}"/>'), "wipe": ("", '<p:wipe dir="{d4}"/>'),
    "split": ("", '<p:split orient="horz" dir="out"/>'), "cover": ("", '<p:cover dir="{d8}"/>'),
    "uncover": ("", '<p:pull dir="{d8}"/>'), "cut": ("", "<p:cut/>"), "dissolve": ("", "<p:dissolve/>"),
    "morph": ("p159", '<p159:morph option="byObject"/>'), "morph-words": ("p159", '<p159:morph option="byWord"/>'),
    "morph-chars": ("p159", '<p159:morph option="byChar"/>'),
    "reveal": ("p14", '<p14:reveal dir="{dlr}"/>'), "pan": ("p14", '<p14:pan dir="{d4}"/>'),
    "gallery": ("p14", '<p14:gallery dir="{dlr}"/>'), "conveyor": ("p14", '<p14:conveyor dir="{dlr}"/>'),
    "doors": ("p14", '<p14:doors dir="vert"/>'), "vortex": ("p14", '<p14:vortex dir="{d4}"/>'),
    "flip": ("p14", '<p14:flip dir="{dlr}"/>'),
    "curtains": ("p15", '<p15:prstTrans prst="curtains"/>'), "fracture": ("p15", '<p15:prstTrans prst="fracture"/>'),
    "airplane": ("p15", '<p15:prstTrans prst="airplane"/>'), "origami": ("p15", '<p15:prstTrans prst="origami"/>'),
    "peel-off": ("p15", '<p15:prstTrans prst="peelOff"/>'), "page-curl": ("p15", '<p15:prstTrans prst="pageCurlDouble"/>'),
}
DEFAULT_DUR = {"morph": 1500, "morph-words": 1500, "morph-chars": 1500, "fade": 700, "cut": 0}
NSURI = {"p14": P14, "p15": P15, "p159": P159}


def transition_el(t):
    typ = (t.get("type") or "").lower()
    if typ in ("", "none"):
        return None
    if typ not in TRANSITIONS:
        raise ValueError(f"unknown transition {typ!r}; choose from {', '.join(sorted(TRANSITIONS))}")
    ns, tpl = TRANSITIONS[typ]
    d = _DIR.get((t.get("dir") or "").lower(), "")
    inner = tpl.format(d4=d if d in ("l", "r", "u", "d") else "l", d8=d or "l", dlr=d if d in ("l", "r") else "l")
    dur = int(t.get("duration") or DEFAULT_DUR.get(typ, 1000))
    spd = "fast" if dur <= 500 else "med" if dur <= 750 else "slow"
    adv = f' advTm="{int(t["advance"])}"' if t.get("advance") else ""
    if ns:
        choice = (f'<mc:Choice xmlns:{ns}="{NSURI[ns]}" Requires="{ns}"><p:transition spd="{spd}" xmlns:p14="{P14}" '
                  f'p14:dur="{dur}"{adv}>{inner}</p:transition></mc:Choice>')
        fallback = "<p:fade/>"
    else:
        choice = (f'<mc:Choice xmlns:p14="{P14}" Requires="p14"><p:transition spd="{spd}" p14:dur="{dur}"{adv}>{inner}'
                  f"</p:transition></mc:Choice>")
        fallback = inner
    xml = (f'<mc:AlternateContent xmlns:mc="{MC}" {nsdecls("p", "a", "r")}>{choice}<mc:Fallback>'
           f'<p:transition spd="{spd}"{adv}>{fallback}</p:transition></mc:Fallback></mc:AlternateContent>')
    return parse_xml(xml)


def _insert_after_clrmap(sld, el):
    anchor = first(sld.find(qn("p:clrMapOvr")), sld.find(qn("p:cSld")))
    sld.insert(list(sld).index(anchor) + 1, el)


def set_transition(slide, t):
    el = transition_el(t)
    if el is not None:
        _insert_after_clrmap(slide._element, el)


# ---------- animations ----------
ANIM_DEFAULT_DUR = {"appear": 1, "fade": 500, "float": 1000, "fly": 500, "wipe": 500, "zoom": 500}
_SIDE = {"left": ("8", "wipe(left)", ("0-#ppt_w/2", "#ppt_y")), "right": ("2", "wipe(right)", ("1+#ppt_w/2", "#ppt_y")),
         "top": ("1", "wipe(up)", ("#ppt_x", "0-#ppt_h/2")), "bottom": ("4", "wipe(down)", ("#ppt_x", "1+#ppt_h/2"))}
ANIMATIONS = ["appear", "fade", "float", "zoom", "fly", "fly-left", "fly-right", "fly-top", "fly-bottom",
              "wipe", "wipe-left", "wipe-right", "wipe-top", "wipe-bottom"]


def _anim_family(effect):
    e = effect.lower()
    if e not in ANIMATIONS:
        raise ValueError(f"unknown animation {effect!r}; choose from {', '.join(ANIMATIONS)}")
    fam, _, side = e.partition("-")
    return fam, side or "bottom"


def timing_el(items):
    """items: dicts with spid, is_sp, effect, trigger(click|with|after), delay, duration (ms). Order = play order."""
    if not items:
        return None
    ids = itertools.count(3)

    def tgt(spid):
        return f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'

    def set_vis(spid):
        return (f'<p:set><p:cBhvr><p:cTn id="{next(ids)}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
                f'</p:cTn>{tgt(spid)}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
                f'<p:to><p:strVal val="visible"/></p:to></p:set>')

    def fade(spid, d, filt="fade"):
        return (f'<p:animEffect transition="in" filter="{filt}"><p:cBhvr><p:cTn id="{next(ids)}" dur="{d}"/>{tgt(spid)}'
                f'</p:cBhvr></p:animEffect>')

    def anim(spid, attr, v0, v1, d, additive=False):
        def val(v):
            return f'<p:fltVal val="{v}"/>' if isinstance(v, (int, float)) else f'<p:strVal val="{v}"/>'
        add = ' additive="base"' if additive else ""
        return (f'<p:anim calcmode="lin" valueType="num"><p:cBhvr{add}><p:cTn id="{next(ids)}" dur="{d}" fill="hold"/>{tgt(spid)}'
                f'<p:attrNameLst><p:attrName>{attr}</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst><p:tav tm="0"><p:val>{val(v0)}'
                f'</p:val></p:tav><p:tav tm="100000"><p:val>{val(v1)}</p:val></p:tav></p:tavLst></p:anim>')

    def effect(it, node_type):
        fam, side = _anim_family(it["effect"])
        d = int(it.get("duration") or ANIM_DEFAULT_DUR[fam])
        sp = it["spid"]
        cid = next(ids)
        grp = ' grpId="0"' if it["is_sp"] else ""
        if fam == "appear":
            pid, sub, body = 1, "0", set_vis(sp)
        elif fam == "fade":
            pid, sub = 10, "0"
            body = set_vis(sp) + fade(sp, d)
        elif fam == "float":
            pid, sub = 42, "0"
            body = set_vis(sp) + fade(sp, d) + anim(sp, "ppt_x", "#ppt_x", "#ppt_x", d) + anim(sp, "ppt_y", "#ppt_y+.1", "#ppt_y", d)
        elif fam == "zoom":
            pid, sub = 53, "16"
            body = set_vis(sp) + anim(sp, "ppt_w", 0, "#ppt_w", d) + anim(sp, "ppt_h", 0, "#ppt_h", d) + fade(sp, d)
        elif fam == "fly":
            sub, _, (x0, y0) = _SIDE[side]
            pid = 2
            body = set_vis(sp) + anim(sp, "ppt_x", x0, "#ppt_x", d, True) + anim(sp, "ppt_y", y0, "#ppt_y", d, True)
        else:  # wipe
            sub, filt, _ = _SIDE[side]
            pid = 22
            body = set_vis(sp) + fade(sp, d, filt)
        xml = (f'<p:par><p:cTn id="{cid}" presetID="{pid}" presetClass="entr" presetSubtype="{sub}" fill="hold"{grp} '
               f'nodeType="{node_type}"><p:stCondLst><p:cond delay="{int(it.get("delay") or 0)}"/></p:stCondLst>'
               f'<p:childTnLst>{body}</p:childTnLst></p:cTn></p:par>')
        return xml, int(it.get("delay") or 0) + d

    groups = []
    for it in items:
        trig = it.get("trigger", "click")
        if trig == "click" or not groups:
            nt = "clickEffect" if trig == "click" else ("withEffect" if trig == "with" else "afterEffect")
            groups.append({"auto": trig != "click", "pars": [{"items": [(it, nt)]}]})
        elif trig == "with":
            groups[-1]["pars"][-1]["items"].append((it, "withEffect"))
        else:
            groups[-1]["pars"].append({"items": [(it, "afterEffect")]})

    out = []
    for gi, g in enumerate(groups):
        gid = next(ids)
        cond = '<p:cond delay="indefinite"/>'
        if g["auto"] and gi == 0:
            cond += '<p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond>'
        pars, offset = [], 0
        for par in g["pars"]:
            pid = next(ids)
            effs, end = [], 0
            for it, nt in par["items"]:
                x, e_end = effect(it, nt)
                effs.append(x)
                end = max(end, e_end)
            pars.append(f'<p:par><p:cTn id="{pid}" fill="hold"><p:stCondLst><p:cond delay="{offset}"/></p:stCondLst>'
                        f'<p:childTnLst>{"".join(effs)}</p:childTnLst></p:cTn></p:par>')
            offset += end
        out.append(f'<p:par><p:cTn id="{gid}" fill="hold"><p:stCondLst>{cond}</p:stCondLst><p:childTnLst>{"".join(pars)}'
                   f'</p:childTnLst></p:cTn></p:par>')
    bld = "".join(f'<p:bldP spid="{it["spid"]}" grpId="0" animBg="1"/>' for it in items if it["is_sp"])
    xml = (f'<p:timing {nsdecls("p")}><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
           f'<p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
           f'{"".join(out)}</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl>'
           f'</p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
           f'</p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>'
           f'{"<p:bldLst>" + bld + "</p:bldLst>" if bld else ""}</p:timing>')
    return parse_xml(xml)


def set_timing(slide, items):
    el = timing_el(items)
    if el is None:
        return
    sld = slide._element
    trans = [c for c in sld if c.tag in (qn("p:transition"), "{%s}AlternateContent" % MC)]
    anchor = trans[-1] if trans else first(sld.find(qn("p:clrMapOvr")), sld.find(qn("p:cSld")))
    sld.insert(list(sld).index(anchor) + 1, el)


# ---------- pictures ----------
def add_svg_blip(pic, svg_bytes, slide_part, cache):
    import hashlib

    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.opc.package import Part

    key = hashlib.sha1(svg_bytes).hexdigest()
    part = cache.get(key)
    if part is None:
        pkg = slide_part.package
        part = Part(pkg.next_image_partname("svg"), "image/svg+xml", pkg, svg_bytes)
        cache[key] = part
    rid = slide_part.relate_to(part, RT.IMAGE)
    blip = pic._element.blipFill.find(qn("a:blip"))
    ext = parse_xml(f'<a:extLst {nsdecls("a", "r")}><a:ext uri="{SVG_EXT_URI}"><asvg:svgBlip xmlns:asvg="{ASVG}" '
                    f'r:embed="{rid}"/></a:ext></a:extLst>')
    old = blip.find(qn("a:extLst"))
    if old is not None:
        blip.remove(old)
    blip.append(ext)


def set_picture_alpha(pic, alpha):
    if alpha >= 0.999:
        return
    blip = pic._element.blipFill.find(qn("a:blip"))
    blip.insert(0, E("a:alphaModFix", {"amt": int(round(alpha * 100000))}))


def set_background(slide, fill=None, blip_rid=None, crop=None, theme=None):
    cSld = slide._element.cSld
    old = cSld.find(qn("p:bg"))
    if old is not None:
        cSld.remove(old)
    if blip_rid:
        src = E("a:srcRect", {k: int(round(v * 100000)) for k, v in (crop or {}).items() if abs(v) > 1e-5})
        f = E("a:blipFill", {"dpi": "0", "rotWithShape": "1"}, [E("a:blip", {"r:embed": blip_rid}), src,
                                                                E("a:stretch", children=[E("a:fillRect")])])
    elif fill:
        f = fill_el(fill, theme)
    else:
        return
    cSld.insert(0, E("p:bg", children=[E("p:bgPr", children=[f, E("a:effectLst")])]))


# ---------- theme / fonts ----------
SLOTS = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"]


def patch_theme(prs, slots=None, major=None, minor=None, name=None):
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    for master in prs.slide_masters:
        part = master.part.part_related_by(RT.THEME)
        root = etree.fromstring(part.blob)
        A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        if name:
            root.set("name", name)
        cs = root.find(f".//{A}clrScheme")
        if cs is not None and slots:
            if name:
                cs.set("name", name)
            for slot in SLOTS:
                if slot in slots:
                    el = cs.find(A + slot)
                    if el is None:
                        continue
                    for ch in list(el):
                        el.remove(ch)
                    etree.SubElement(el, A + "srgbClr", val=hex6(slots[slot]))
        fs = root.find(f".//{A}fontScheme")
        if fs is not None:
            if name:
                fs.set("name", name)
            for tag, face in (("majorFont", major), ("minorFont", minor)):
                if face:
                    latin = fs.find(f"{A}{tag}/{A}latin")
                    if latin is not None:
                        latin.set("typeface", face)
                        for k in ("panose", "pitchFamily", "charset"):
                            latin.attrib.pop(k, None)
        blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        if hasattr(part, "_element"):
            part._element = parse_xml(blob)
        else:
            part._blob = blob


def embed_fonts(prs, fonts):
    """fonts: {typeface: {'regular': path, 'bold': path, 'italic': path, 'boldItalic': path}} -> EOT parts (experimental)."""
    from pptx.opc.package import Part
    from pptx.opc.packuri import PackURI

    from .fonts import eot_bytes

    if not fonts:
        return []
    pres_el = prs.part._element
    pkg = prs.part.package
    lst = pres_el.find(qn("p:embeddedFontLst"))
    if lst is None:
        lst = E("p:embeddedFontLst")
        anchor = first(pres_el.find(qn("p:smartTags")), pres_el.find(qn("p:notesSz")))
        pres_el.insert(list(pres_el).index(anchor) + 1, lst)
    n = 0
    done = []
    for typeface, styles in fonts.items():
        ef = E("p:embeddedFont", children=[E("p:font", {"typeface": typeface, "pitchFamily": "2", "charset": "0"})])
        for style in ("regular", "bold", "italic", "boldItalic"):
            if style not in styles:
                continue
            n += 1
            part = Part(PackURI(f"/ppt/fonts/font{n}.fntdata"), "application/x-fontdata", pkg, eot_bytes(styles[style]))
            rid = prs.part.relate_to(part, RT_FONT)
            ef.append(E(f"p:{style}", {"r:id": rid}))
        lst.append(ef)
        done.append(typeface)
    pres_el.set("embedTrueTypeFonts", "1")
    return done
