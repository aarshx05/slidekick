import argparse
import json
import pathlib
import shutil
import sys

from .util import SKILL_DIR, log, read_json

ASSETS = SKILL_DIR / "assets" / "canvas"
SCHEMAS = SKILL_DIR / "references" / "schemas"

DEFAULT_BRAND_CSS = """/* Neutral defaults. Run `deck.py brand <kit>` to replace with real brand tokens. */
:root {
  --brand-dk1: #111418; --brand-lt1: #FFFFFF; --brand-dk2: #1F2A44; --brand-lt2: #EEF2F7;
  --brand-accent1: #3B5BDB; --brand-accent2: #F08C00; --brand-accent3: #2B8A3E; --brand-accent4: #AE3EC9;
  --color-primary: #3B5BDB; --color-bg: #FFFFFF; --color-text: #111418; --color-dark: #1F2A44; --color-surface: #EEF2F7;
  --color-muted: #5C6370; --color-accent-1: #3B5BDB; --color-accent-2: #F08C00;
  --font-display: 'Segoe UI', Arial, sans-serif; --font-body: 'Segoe UI', Arial, sans-serif;
}
"""


def _p(args):
    return pathlib.Path(args.project).resolve()


def cmd_doctor(args):
    ok = True
    print(f"python      {sys.version.split()[0]}  ({sys.executable})")
    for mod in ("pptx", "lxml", "xlsxwriter", "playwright", "PIL", "numpy", "fontTools", "pymupdf", "jsonschema"):
        try:
            __import__(mod)
            print(f"  ok        {mod}")
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"  MISSING   {mod}: {e}")
    try:
        from playwright.sync_api import sync_playwright

        from .util import launch_browser
        with sync_playwright() as p:
            br = launch_browser(p)
            print(f"browser     ok ({br.browser_type.name} {br.version})")
            br.close()
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"browser     MISSING: {e}")
    from .render import find_soffice, powerpoint_backend
    ppt = powerpoint_backend()
    so = find_soffice()
    print(f"powerpoint  {'not available' if not ppt else 'ok (Windows, ground truth)' if ppt == 'powerpoint' else 'ok (Mac, ground truth; transitions/animations checked in XML only)'}")
    print(f"libreoffice {so or 'not found'}")
    print(f"QA backend  {'PowerPoint' if ppt else 'LibreOffice (approximation of PowerPoint)' if so else 'none'}")
    if not ppt and not so:
        ok = False
        print("  -> install PowerPoint or LibreOffice so QA can render the .pptx")
    from .fonts import FontIndex
    idx = FontIndex()
    print(f"fonts       {len(idx.faces)} installed faces indexed")
    return 0 if ok else 1


def cmd_init(args):
    d = pathlib.Path(args.dir).resolve()
    for sub in ("brand", "assets", "canvas", "plan", "build", "qa"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    for name, dst in (("deck.css", d / "canvas" / "deck.css"), ("starter.html", d / "canvas" / "deck.html")):
        if args.force or not dst.exists():
            shutil.copy2(ASSETS / name, dst)
    if not (d / "canvas" / "brand.css").exists():
        (d / "canvas" / "brand.css").write_text(DEFAULT_BRAND_CSS, encoding="utf-8")
    print(f"initialized {d}")
    for sub in ("brand/", "assets/", "plan/", "canvas/deck.html", "canvas/deck.css", "canvas/brand.css"):
        print(f"  {sub}")
    return 0


def cmd_brand(args):
    from .brand import brand_board, ingest, write_tokens
    project = _p(args)
    out = project / "brand"
    b = ingest(args.inputs, out, name=args.name)
    css = write_tokens(out / "brand.json", project / "canvas" / "brand.css")
    board = brand_board(out / "brand.json", out / "brand-board.png")
    print(f"brand.json   {out / 'brand.json'}")
    print(f"brand.css    {css}")
    print(f"brand board  {board}   <- look at this to verify")
    print(f"template     {b.get('template') or '-'}")
    print("theme        " + " ".join(f"{k}=#{v}" for k, v in b["theme"].items()))
    f = b["fonts"]
    for role in ("display", "body"):
        if f.get(role):
            print(f"font {role:7s} {f[role]['family']}  installed={f[role]['installed']}  files={len(f[role]['files'])}")
    print(f"logos        {len(b['logos'])}: " + ", ".join(f"{l['name']} ({l['variant']})" for l in b["logos"][:6]))
    if b["guidelines"]:
        print(f"guidelines   {len(b['guidelines'])} PDF(s) -> text + page renders in brand/pages/")
    return 0


def cmd_tokens(args):
    from .brand import write_tokens
    project = _p(args)
    print(write_tokens(project / "brand" / "brand.json", project / "canvas" / "brand.css"))
    return 0


def cmd_board(args):
    from .brand import brand_board
    project = _p(args)
    print(brand_board(project / "brand" / "brand.json", project / "brand" / "brand-board.png"))
    return 0


def cmd_fonts(args):
    from . import fonts as F
    if args.action == "list":
        idx = F.FontIndex()
        fams = idx.families()
        if args.family:
            for f in idx.find(args.family):
                print(f"{f['family']!r:32} sub={f['sub']!r:16} weight={f['weight']} italic={f['italic']} {f['path']}")
            if not idx.find(args.family):
                print(f"not installed: {args.family}")
                return 1
        else:
            print("\n".join(fams))
        return 0
    if args.action == "install":
        for p in F.install_fonts(args.items):
            print(f"installed {p}")
        return 0
    if args.action == "fetch":
        out = pathlib.Path(args.out).resolve() if args.out else _p(args) / "brand" / "fonts"
        files = []
        for fam in args.items:
            files += F.fetch_google_font(fam, weights=[int(w) for w in args.weights.split(",")], italic=args.italic, out_dir=out)
        for f in files:
            print(f"downloaded {f}")
        if args.install:
            for p in F.install_fonts(files):
                print(f"installed {p}")
        return 0
    return 2


def cmd_capture(args):
    from .capture import capture
    print(capture(args.url, args.out, width=args.width, height=args.height, full_page=args.full, selector=args.selector,
                  dark=args.dark, scale=args.scale))
    return 0


def cmd_fetch(args):
    from .capture import fetch
    print(fetch(args.url, args.out or _p(args) / "assets", name=args.name, note=args.note or ""))
    return 0


def cmd_validate(args):
    import jsonschema
    path = pathlib.Path(args.file)
    kind = args.kind or ("narrative" if "narrative" in path.name else "slides")
    schema = json.loads((SCHEMAS / f"{kind}.schema.json").read_text(encoding="utf-8"))
    data = read_json(path)
    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    for e in errs:
        print(f"  {'/'.join(str(x) for x in e.path) or '<root>'}: {e.message}")
    extra = []
    if kind == "slides":
        ids = [s.get("id") for s in data.get("slides", [])]
        if len(ids) != len(set(ids)):
            extra.append("slide ids must be unique")
        for s in data.get("slides", []):
            if s.get("archetype") not in ("title", "section", "closing", "quote") and len(s.get("headline", "").split()) < 4:
                extra.append(f"{s.get('id')}: headline '{s.get('headline')}' is a label, not a takeaway")
    for x in extra:
        print(f"  {x}")
    print(f"{path.name}: {'OK' if not errs and not extra else f'{len(errs) + len(extra)} problem(s)'}")
    return 0 if not errs and not extra else 1


def cmd_extract(args):
    from .extract import extract
    d = extract(_p(args), html=args.html)
    n = sum(len(s["elements"]) for s in d["slides"])
    print(f"layout.json  {len(d['slides'])} slides, {n} top-level elements -> {_p(args) / 'build' / 'layout.json'}")
    for w in d["warnings"]:
        print(f"  [slide {w['slide']}] {w['code']}: {w['msg']} — {w['el']}")
    for c in d.get("console", []):
        print(f"  console {c}")
    return 0


def _kit_fonts(args, project):
    if getattr(args, "no_font_install", False):
        return
    from .fonts import ensure_kit_fonts
    for p in ensure_kit_fonts(project / "brand" / "brand.json"):
        print(f"font         installed brand font {pathlib.Path(p).name} (per-user, so renderers match; `deck.py uninstall --fonts` removes it)")


def cmd_compile(args):
    from .compile import compile_deck
    _kit_fonts(args, _p(args))
    r = compile_deck(_p(args), out=args.out, embed=args.embed_fonts, author=args.author)
    print(f"pptx         {r['output']}  ({len(r['slides'])} slides)")
    for fam, info in r["fonts"].items():
        state = "installed" if info.get("installed") else "NOT INSTALLED"
        print(f"  font {fam}: {state}{'' if info.get('system', True) else ' (non-system)'}")
    for w in r["warnings"]:
        print(f"  warning: {w}")
    return 0


def cmd_render(args):
    from .render import render
    project = _p(args)
    pptx = pathlib.Path(args.pptx) if args.pptx else project / "deck.pptx"
    info = render(pptx, project / "build" / "render", engine=args.engine)
    print(f"render       {info['engine']} {info.get('version', '')} -> {project / 'build' / 'render'} ({info['seconds']}s)")
    for e in info.get("errors", []):
        print(f"  error: {e}")
    return 0


def _print_qa(r, project):
    print(f"QA           {r['status'].upper()} — {r['errors']} error(s), {r['warnings']} warning(s), renderer={r['renderer']}")
    for s in r["slides"]:
        if s["diff"] is not None:
            print(f"  slide {s['slide']:2d}  diff {s['diff'] * 100:5.1f}%  words {s['words']}")
    shown = 0
    for x in sorted(r["issues"], key=lambda x: (x["severity"] != "error", x["slide"])):
        if shown >= 40:
            print(f"  ... see {project / 'qa' / 'report.md'}")
            break
        print(f"  {x['severity']:5s} [slide {x['slide'] or '-'}] {x['code']}: {x['msg']}" + (f" — {x['el']}" if x["el"] else ""))
        shown += 1
    print(f"report       {project / 'qa' / 'report.md'}")
    print(f"contact      {r['contact_sheet']}")


def cmd_qa(args):
    from .qa import run_qa
    project = _p(args)
    r = run_qa(project, diff_limit=args.diff_limit)
    _print_qa(r, project)
    return 1 if r["status"] == "fail" else 0


def cmd_build(args):
    from .compile import compile_deck
    from .extract import extract
    from .qa import run_qa
    from .render import render
    project = _p(args)
    _kit_fonts(args, project)
    d = extract(project, html=args.html)
    print(f"extract      {len(d['slides'])} slides, {len(d['warnings'])} warning(s)")
    r = compile_deck(project, out=args.out, embed=args.embed_fonts, author=args.author)
    print(f"pptx         {r['output']}")
    try:
        info = render(r["output"], project / "build" / "render", engine=args.engine)
        print(f"render       {info['engine']} ({info['seconds']}s)")
    except Exception as e:  # noqa: BLE001 - QA reports the missing render
        print(f"render       FAILED: {e}")
    q = run_qa(project, diff_limit=args.diff_limit)
    _print_qa(q, project)
    try:
        from .taste import run_taste
        _print_taste(run_taste(project=project, out_dir=project / "qa"))
    except Exception as e:  # noqa: BLE001 - taste lint is advisory; never block a build on it
        print(f"taste        skipped: {e}")
    return 1 if q["status"] == "fail" else 0


def cmd_inspect(args):
    from .reader import inspect_deck
    src = pathlib.Path(args.file).resolve()
    out = pathlib.Path(args.out).resolve() if args.out else src.parent / f"{src.stem}-inspect"
    inv = inspect_deck(src, out, render=not args.no_render, engine=args.engine, media=args.media)
    d = inv["deck"]
    print(f"inspected    {src.name}: {len(inv['slides'])} slides, renderer={inv['renderer'] or 'none'}")
    if d.get("pipeline"):
        print(f"  Slidekick build: {d['pipeline']}")
    for f, v in (d.get("fonts_used") or {}).items():
        print(f"  font {f}: {v['runs']} runs" + ("" if v.get("installed", True) else "  NOT INSTALLED"))
    errs = [x for x in inv["issues"] if x["severity"] == "error"]
    warns = [x for x in inv["issues"] if x["severity"] == "warn"]
    print(f"  issues: {len(errs)} error(s), {len(warns)} warning(s)")
    for x in (errs + warns)[:25]:
        print(f"  {x['severity']:5s} [slide {x['slide'] or '-'}] {x['code']}: {x['msg']}" + (f" — {x['el']}" if x["el"] else ""))
    print(f"outline      {out / 'outline.md'}   <- read this")
    print(f"inventory    {out / 'inventory.json'}  (shape ids/names for edits.json)")
    for s in inv["contact_sheets"]:
        print(f"contact      {s}   <- look at this")
    return 0


def cmd_edit(args):
    from .edit import apply_edits
    src = pathlib.Path(args.file).resolve()
    if args.in_place:
        out = src
    else:
        out = pathlib.Path(args.out).resolve() if args.out else src.with_name(f"{src.stem}-edited{src.suffix}")
    log_ = apply_edits(src, pathlib.Path(args.edits).resolve(), out, backup=args.in_place, author=args.author)
    for line in log_["log"]:
        print(f"  {line}")
    for w in log_["warnings"]:
        print(f"  warning: {w}")
    print(f"edited       {out}")
    print(f"next         deck.py inspect \"{out}\"  (render + overflow check), then review the changed slides")
    return 0


def cmd_taste(args):
    from .taste import run_taste
    if args.inventory:
        inv = pathlib.Path(args.inventory).resolve()
        r = run_taste(inventory=inv, out_dir=inv.parent)
    else:
        project = _p(args)
        r = run_taste(project=project, out_dir=project / "qa")
    _print_taste(r)
    return 0


def _print_taste(r):
    m = r["metrics"]
    print(f"taste        {len(r['findings'])} finding(s) — {m.get('compositions', '?')} distinct compositions in {m.get('slides')} slides, "
          f"{len(m.get('font_sizes', []))} text sizes, {len(m.get('families', []))} families")
    for f in r["findings"][:30]:
        print(f"  {f['severity']:6s} [slide {f['slide'] or '-'}] {f['code']}: {f['msg']}" + (f" — {f['el']}" if f.get("el") else ""))
    if len(r["findings"]) > 30:
        print(f"  ... see {r['report']}")
    print(f"taste report {r['report']}")


def cmd_preview(args):
    import time

    from .util import serve_dir
    project = _p(args)
    with serve_dir(project) as base:
        print(f"preview: {base}/{args.html}   (add ?debug or <body class=debug> to outline exported elements; Ctrl+C to stop)", flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0


def main(argv):
    ap = argparse.ArgumentParser(prog="deck.py", description="Editable, on-brand PPTX pipeline (HTML canvas -> Chromium geometry -> PPTX -> PowerPoint QA)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def proj(p):
        p.add_argument("-p", "--project", default=".", help="deck project folder (default: current dir)")
        return p

    sub.add_parser("doctor", help="check dependencies, browser, renderers, fonts").set_defaults(fn=cmd_doctor)
    p = sub.add_parser("init", help="scaffold a deck project folder")
    p.add_argument("dir")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)
    p = proj(sub.add_parser("brand", help="ingest a brand kit -> brand/brand.json, canvas/brand.css, brand board"))
    p.add_argument("inputs", nargs="+")
    p.add_argument("--name")
    p.set_defaults(fn=cmd_brand)
    proj(sub.add_parser("tokens", help="regenerate canvas/brand.css from brand/brand.json")).set_defaults(fn=cmd_tokens)
    proj(sub.add_parser("board", help="re-render brand/brand-board.png")).set_defaults(fn=cmd_board)
    p = proj(sub.add_parser("fonts", help="list | install <files> | fetch <Google family>"))
    p.add_argument("action", choices=["list", "install", "fetch"])
    p.add_argument("items", nargs="*")
    p.add_argument("--family")
    p.add_argument("--weights", default="400,600,700")
    p.add_argument("--italic", action="store_true")
    p.add_argument("--out", help="download folder (default: <project>/brand/fonts)")
    p.add_argument("--install", action="store_true")
    p.set_defaults(fn=cmd_fonts)
    p = sub.add_parser("capture", help="screenshot a live site/product")
    p.add_argument("url")
    p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=1440)
    p.add_argument("--height", type=int, default=900)
    p.add_argument("--scale", type=float, default=2)
    p.add_argument("--full", action="store_true")
    p.add_argument("--selector")
    p.add_argument("--dark", action="store_true")
    p.set_defaults(fn=cmd_capture)
    p = proj(sub.add_parser("fetch", help="download an image and record its source"))
    p.add_argument("url")
    p.add_argument("--out", help="folder (default: <project>/assets)")
    p.add_argument("--name")
    p.add_argument("--note")
    p.set_defaults(fn=cmd_fetch)
    p = sub.add_parser("validate", help="validate plan/narrative.json or plan/slides.json")
    p.add_argument("file")
    p.add_argument("--kind", choices=["narrative", "slides"])
    p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("inspect", help="read any deck (.pptx/.potx/.ppt/.odp/.pdf): outline, inventory, renders, issues")
    p.add_argument("file")
    p.add_argument("--out", help="output folder (default: <file>-inspect next to the file)")
    p.add_argument("--no-render", action="store_true", help="skip rendering (no pictures, overflow or contrast checks)")
    p.add_argument("--media", action="store_true", help="also save every picture to <out>/media/")
    p.add_argument("--engine", default="auto", choices=["auto", "powerpoint", "libreoffice"])
    p.set_defaults(fn=cmd_inspect)
    p = sub.add_parser("edit", help="apply edits.json to an existing .pptx in place (text, data, images, slides…)")
    p.add_argument("file")
    p.add_argument("edits")
    p.add_argument("--out", help="output .pptx (default: <file>-edited.pptx)")
    p.add_argument("--in-place", action="store_true", help="overwrite the input (a .bak copy is kept)")
    p.add_argument("--author", default="", help="'last modified by' to record (default: blank)")
    p.set_defaults(fn=cmd_edit)
    p = proj(sub.add_parser("taste", help="measurable design-taste lint -> qa/taste.md (or next to an inventory)"))
    p.add_argument("--inventory", help="inventory.json from `inspect` (lint an existing deck)")
    p.set_defaults(fn=cmd_taste)
    for name, fn, hlp in (("extract", cmd_extract, "HTML canvas -> build/layout.json + reference PNGs"),
                          ("compile", cmd_compile, "build/layout.json -> deck.pptx"),
                          ("render", cmd_render, "render deck.pptx with PowerPoint/LibreOffice"),
                          ("qa", cmd_qa, "diff + checks -> qa/report.md"),
                          ("build", cmd_build, "extract + compile + render + qa + taste lint"),
                          ("preview", cmd_preview, "serve the canvas for a live look")):
        p = proj(sub.add_parser(name, help=hlp))
        p.add_argument("--html", default="canvas/deck.html")
        p.add_argument("--out")
        p.add_argument("--pptx")
        p.add_argument("--engine", default="auto", choices=["auto", "powerpoint", "libreoffice"])
        p.add_argument("--embed-fonts", action="store_true", help="experimental: embed non-system fonts as EOT")
        p.add_argument("--diff-limit", type=float, default=0.012, help="share of mismatching pixels that fails a slide")
        p.add_argument("--author", default="", help="author to record in the .pptx (default: blank)")
        p.add_argument("--no-font-install", action="store_true", help="don't install the brand kit's fonts (renders will substitute them)")
        p.set_defaults(fn=fn)
    ap.add_argument("--trace", action="store_true", help="show the full Python traceback on errors (or set DECK_TRACE=1)")
    # accepted anywhere on the command line, not just before the subcommand
    trace = "--trace" in argv or bool(__import__("os").environ.get("DECK_TRACE"))
    args = ap.parse_args([a for a in argv if a != "--trace"])
    try:
        return args.fn(args)
    except Exception as e:  # noqa: BLE001 - one-line error for the agent, full trace on request
        if trace:
            raise
        log(f"error: {type(e).__name__}: {e}")
        return 2
