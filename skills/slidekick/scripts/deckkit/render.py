"""Execution: render the .pptx with the real engine (PowerPoint via COM) or LibreOffice, and read back what it parsed."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

from .util import log, write_json

PPT_SCRIPT = r'''
import json, sys, pythoncom, win32com.client
pptx, out_dir, W, H = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
bounds = len(sys.argv) > 5 and sys.argv[5] == "bounds"


def overflow(shapes, out):
    """Text that PowerPoint lays out beyond its shape (points past the edge), recursing into groups."""
    for k in range(1, shapes.Count + 1):
        sh = shapes.Item(k)
        try:
            if sh.Type == 6:
                overflow(sh.GroupItems, out)
                continue
            if sh.Rotation or not sh.HasTextFrame or not sh.TextFrame.HasText:
                continue
            tr = sh.TextFrame.TextRange
            dy = max(tr.BoundTop + tr.BoundHeight - (sh.Top + sh.Height), sh.Top - tr.BoundTop)
            dx = max(tr.BoundLeft + tr.BoundWidth - (sh.Left + sh.Width), sh.Left - tr.BoundLeft)
            if max(dx, dy) > 2:
                out.append({"id": int(sh.Id), "name": sh.Name, "over_y": round(dy, 1), "over_x": round(dx, 1)})
        except Exception:
            pass


pythoncom.CoInitialize()
app = win32com.client.Dispatch("PowerPoint.Application")
pre_count, pre_visible = app.Presentations.Count, bool(app.Visible)
info = {"version": app.Version, "slides": [], "slide_size": None}
pres = app.Presentations.Open(pptx, True, False, False)
try:
    info["slide_size"] = [float(pres.PageSetup.SlideWidth), float(pres.PageSetup.SlideHeight)]
    for s in pres.Slides:
        i = s.SlideIndex
        s.Export(f"{out_dir}\\slide-{i:02d}.png", "PNG", W, H)
        t = s.SlideShowTransition
        effects = []
        try:
            seq = s.TimeLine.MainSequence
            for k in range(1, seq.Count + 1):
                e = seq.Item(k)
                try:
                    name = e.Shape.Name
                except Exception:
                    name = "?"
                effects.append({"type": int(e.EffectType), "shape": name, "trigger": int(e.Timing.TriggerType),
                                "duration": float(e.Timing.Duration), "delay": float(e.Timing.TriggerDelayTime)})
        except Exception:
            effects = None
        try:
            notes = s.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text[:80]
        except Exception:
            notes = ""
        row = {"index": i, "entry_effect": int(t.EntryEffect), "duration": float(t.Duration),
               "shapes": int(s.Shapes.Count), "effects": effects, "notes": notes, "hidden": bool(t.Hidden)}
        if bounds:
            row["overflow"] = []
            overflow(s.Shapes, row["overflow"])
        info["slides"].append(row)
    fonts = []
    try:
        for k in range(1, pres.Fonts.Count + 1):
            f = pres.Fonts.Item(k)
            fonts.append({"name": f.Name, "embedded": bool(f.Embedded)})
    except Exception:
        pass
    info["fonts"] = fonts
finally:
    pres.Close()
    if pre_count == 0 and not pre_visible:
        app.Quit()
print(json.dumps(info))
'''


def _ppt_pids():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq POWERPNT.EXE", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    except OSError:
        return set()
    return {int(line.split('","')[1]) for line in out.strip().splitlines() if line.startswith('"POWERPNT')}


MAC_APP_NAME = "Microsoft PowerPoint"
# PowerPoint for Mac is sandboxed: it can read/write its own container without a "Grant File Access" dialog
MAC_CONTAINER = pathlib.Path.home() / "Library" / "Containers" / "com.microsoft.Powerpoint" / "Data"

MAC_SCRIPT = '''
on run argv
    set src to POSIX file (item 1 of argv)
    set pdf to POSIX file (item 2 of argv)
    tell application "Microsoft PowerPoint"
        set v to version
        open src
        set p to active presentation
        save p in pdf as save as PDF
        close p saving no
    end tell
    return v
end run
'''


def _mac_app():
    for base in (pathlib.Path("/Applications"), pathlib.Path.home() / "Applications"):
        app = base / f"{MAC_APP_NAME}.app"
        if app.exists():
            return app
    return None


def _mac_running():
    return subprocess.run(["pgrep", "-x", MAC_APP_NAME], capture_output=True).returncode == 0


def powerpoint_backend():
    """'powerpoint' (Windows COM), 'powerpoint-mac' (AppleScript) or None."""
    if sys.platform == "darwin":
        return "powerpoint-mac" if _mac_app() else None
    return "powerpoint" if _win_powerpoint() else None


def powerpoint_available():
    return powerpoint_backend() is not None


def _win_powerpoint():
    if sys.platform != "win32":
        return False
    try:
        import winreg
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"PowerPoint.Application\CLSID").Close()
        return True
    except OSError:
        return False


def find_soffice():
    for c in (shutil.which("soffice"), shutil.which("libreoffice"),
              r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
              "/Applications/LibreOffice.app/Contents/MacOS/soffice", "/usr/bin/soffice"):
        if c and pathlib.Path(c).exists():
            return c
    return None


def _rasterize_pdf(pdf, out_dir, width):
    import pymupdf as fitz

    doc = fitz.open(pdf)
    for i, page in enumerate(doc, 1):
        zoom = width / page.rect.width
        page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False).save(str(pathlib.Path(out_dir) / f"slide-{i:02d}.png"))
    n = len(doc)
    doc.close()
    return n


def render_powerpoint_mac(pptx, out_dir, width, height, timeout):
    """PowerPoint for Mac via AppleScript: stage in its sandbox, save as PDF, rasterize. No transition/animation readback."""
    was_running = _mac_running()
    MAC_CONTAINER.mkdir(parents=True, exist_ok=True)
    stage = pathlib.Path(tempfile.mkdtemp(prefix="deck-qa-", dir=MAC_CONTAINER))
    try:
        src, pdf = stage / "deck.pptx", stage / "deck.pdf"
        shutil.copy2(pptx, src)
        try:
            p = subprocess.run(["osascript", "-e", MAC_SCRIPT, str(src), str(pdf)], capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            if not was_running:  # only an instance we started
                subprocess.run(["pkill", "-x", MAC_APP_NAME], capture_output=True)
            raise RuntimeError("PowerPoint timed out (a dialog may have blocked it — often a 'repair' or file-access prompt)") from None
        if p.returncode != 0:
            err = (p.stderr or "").strip()
            if "-1743" in err:
                raise RuntimeError("macOS blocked automation: allow your terminal to control Microsoft PowerPoint in "
                                   "System Settings > Privacy & Security > Automation, then retry")
            raise RuntimeError(f"PowerPoint could not open/render the file: {err.splitlines()[-1] if err else 'unknown error'}")
        if not pdf.exists():
            raise RuntimeError("PowerPoint did not write the PDF export")
        n = _rasterize_pdf(pdf, out_dir, width)
        if not was_running:
            subprocess.run(["osascript", "-e", f'tell application "{MAC_APP_NAME}" to quit'], capture_output=True, timeout=30)
        return {"version": p.stdout.strip(), "slides": [{"index": i} for i in range(1, n + 1)]}
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def render_powerpoint(pptx, out_dir, width, height, timeout, text_bounds=False):
    if sys.platform == "darwin":
        return render_powerpoint_mac(pptx, out_dir, width, height, timeout)
    before = _ppt_pids()
    proc = subprocess.Popen([sys.executable, "-c", PPT_SCRIPT, str(pptx), str(out_dir), str(width), str(height),
                             "bounds" if text_bounds else "-"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        for pid in _ppt_pids() - before:  # only instances we started
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        raise RuntimeError("PowerPoint timed out (a dialog may have blocked it — often an invalid file 'repair' prompt)") from None
    if proc.returncode != 0:
        msg = (err or "").strip().splitlines()[-1:] or ["unknown error"]
        raise RuntimeError(f"PowerPoint could not open/render the file: {msg[0]}")
    return json.loads(out.strip().splitlines()[-1])


def render_libreoffice(pptx, out_dir, width, height, timeout):
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError("LibreOffice not found")
    with tempfile.TemporaryDirectory() as tmp:
        profile = pathlib.Path(tmp, "profile").as_uri()
        subprocess.run([soffice, f"-env:UserInstallation={profile}", "--headless", "--norestore", "--convert-to", "pdf",
                        "--outdir", tmp, str(pptx)], capture_output=True, timeout=timeout, check=True)
        n = _rasterize_pdf(next(pathlib.Path(tmp).glob("*.pdf")), out_dir, width)
    return {"slides": [{"index": i} for i in range(1, n + 1)]}


def render(pptx, out_dir, engine="auto", width=1920, height=1080, timeout=300, text_bounds=False):
    """Render every slide to PNG. text_bounds=True (PowerPoint only) also reports text overflowing its shape."""
    pptx = pathlib.Path(pptx).resolve()
    out_dir = pathlib.Path(out_dir).resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    engines = ["powerpoint", "libreoffice"] if engine == "auto" else [engine]
    errors = []
    for eng in engines:
        if eng == "powerpoint" and not powerpoint_available():
            errors.append("powerpoint: not installed")
            continue
        try:
            t0 = time.time()
            if eng == "powerpoint":
                info = render_powerpoint(pptx, out_dir, width, height, timeout, text_bounds)
            else:
                info = render_libreoffice(pptx, out_dir, width, height, timeout)
            if eng == "powerpoint":
                eng = powerpoint_backend()
            info.update({"engine": eng, "seconds": round(time.time() - t0, 1), "pptx": str(pptx), "errors": errors})
            write_json(out_dir / "render.json", info)
            return info
        except Exception as e:  # noqa: BLE001 - fall through to next engine
            errors.append(f"{eng}: {e}")
            log(f"render with {eng} failed: {e}")
    raise RuntimeError("no renderer succeeded:\n" + "\n".join(errors))
