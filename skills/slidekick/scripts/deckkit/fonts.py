"""Installed-font index, CSS family -> PowerPoint typeface resolution, font install/fetch, EOT packing."""
import io
import json
import os
import pathlib
import re
import shutil
import struct
import sys
import urllib.request

from .util import cache_dir, log

FONT_EXT = {".ttf", ".otf", ".ttc", ".otc"}
GENERIC = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif",
           "ui-serif", "ui-monospace", "-apple-system", "blinkmacsystemfont", "emoji", "math"}
# Only used when Chromium didn't report the platform font it actually drew with.
# Segoe ships with Windows only; elsewhere fall back to faces that exist on both Mac and Windows.
_UI, _MONO, _HAND = ("Segoe UI", "Consolas", "Segoe Script") if sys.platform == "win32" else ("Arial", "Courier New", "Comic Sans MS")
GENERIC_MAP = {"serif": "Georgia", "sans-serif": "Arial", "monospace": _MONO, "system-ui": _UI,
               "ui-sans-serif": _UI, "-apple-system": _UI, "blinkmacsystemfont": _UI,
               "ui-monospace": _MONO, "ui-serif": "Georgia", "cursive": _HAND}


def font_dirs():
    if sys.platform == "win32":
        dirs = [pathlib.Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"]
        if os.environ.get("LOCALAPPDATA"):
            dirs.append(pathlib.Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts")
    elif sys.platform == "darwin":
        dirs = [pathlib.Path("/System/Library/Fonts"), pathlib.Path("/Library/Fonts"), pathlib.Path.home() / "Library/Fonts"]
    else:
        dirs = [pathlib.Path("/usr/share/fonts"), pathlib.Path("/usr/local/share/fonts"),
                pathlib.Path.home() / ".fonts", pathlib.Path.home() / ".local/share/fonts"]
    return [d for d in dirs if d.exists()]


def system_font_dir():
    return font_dirs()[0] if font_dirs() else None


def _name(tt, nid):
    n = tt["name"]
    for args in ((nid, 3, 1, 0x409), (nid, 1, 0, 0)):
        r = n.getName(*args)
        if r:
            return str(r)
    for r in n.names:
        if r.nameID == nid:
            try:
                return r.toUnicode()
            except Exception:  # noqa: BLE001
                pass
    return ""


def describe_font(path):
    """Return a list of face dicts for a font file (ttc -> several)."""
    from fontTools.ttLib import TTCollection, TTFont
    path = pathlib.Path(path)
    fonts = []
    try:
        if path.suffix.lower() in (".ttc", ".otc"):
            fonts = list(TTCollection(str(path), lazy=True).fonts)
        else:
            fonts = [TTFont(str(path), lazy=True, fontNumber=0)]
    except Exception:  # noqa: BLE001 - unreadable font, skip
        return []
    faces = []
    for i, tt in enumerate(fonts):
        try:
            os2 = tt["OS/2"] if "OS/2" in tt else None
            fam = _name(tt, 1)
            sub = _name(tt, 2)
            faces.append({
                "path": str(path), "index": i,
                "family": fam, "sub": sub,
                "typo": _name(tt, 16) or fam, "typo_sub": _name(tt, 17) or sub,
                "full": _name(tt, 4), "ps": _name(tt, 6),
                "weight": int(os2.usWeightClass) if os2 else (700 if "bold" in sub.lower() else 400),
                "italic": bool(os2 and (os2.fsSelection & 1)) or "italic" in sub.lower() or "oblique" in sub.lower(),
                "fsType": int(os2.fsType) if os2 else 0,
                "variable": "fvar" in tt,
            })
        except Exception:  # noqa: BLE001
            continue
    return faces


class FontIndex:
    def __init__(self, extra_files=()):
        self.cache_path = cache_dir() / "font-index.json"
        self.faces = []
        self._load(extra_files)

    def _load(self, extra_files):
        try:
            cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cache = {}
        new_cache, changed = {}, False
        files = []
        for d in font_dirs():
            for p in d.rglob("*"):
                if p.suffix.lower() in FONT_EXT:
                    files.append(p)
        files += [pathlib.Path(f) for f in extra_files]
        for p in files:
            try:
                st = p.stat()
            except OSError:
                continue
            key = f"{p}|{st.st_mtime_ns}|{st.st_size}"
            if key in cache:
                faces = cache[key]
            else:
                faces, changed = describe_font(p), True
            new_cache[key] = faces
            self.faces.extend(faces)
        if changed or len(new_cache) != len(cache):
            try:
                self.cache_path.write_text(json.dumps(new_cache), encoding="utf-8")
            except OSError:
                pass

    def families(self):
        return sorted({f["typo"] for f in self.faces} | {f["family"] for f in self.faces})

    def find(self, family):
        fam = family.strip().strip("'\"").lower()
        return [f for f in self.faces if f["typo"].lower() == fam or f["family"].lower() == fam
                or f["full"].lower() == fam or f["ps"].lower() == fam]

    def has(self, family):
        return bool(self.find(family))

    def resolve(self, family, weight=400, italic=False):
        """CSS (family, weight, italic) -> (typeface, bold, italic, face|None) as PowerPoint names fonts."""
        cands = self.find(family)
        if not cands:
            return family, weight >= 600, italic, None
        pool = [f for f in cands if f["italic"] == italic] or cands
        best = min(pool, key=lambda f: (abs(f["weight"] - weight), -f["weight"] if weight >= 500 else f["weight"]))
        if best["variable"]:
            return best["family"], weight >= 600, italic, best
        sub = best["sub"].lower()
        return best["family"], "bold" in sub, ("italic" in sub or "oblique" in sub) or (italic and not best["italic"]), best

    def faces_for_typeface(self, typeface):
        return [f for f in self.faces if f["family"].lower() == typeface.lower()]


def first_family(css_stack: str):
    for part in css_stack.split(","):
        name = part.strip().strip("'\"")
        if name:
            return name
    return "Arial"


def stack_families(css_stack: str):
    return [p.strip().strip("'\"") for p in css_stack.split(",") if p.strip()]


def install_fonts(paths):
    """Per-user install so Chromium and PowerPoint render the same glyphs (no admin needed)."""
    installed, records = [], []
    if sys.platform == "win32":
        import ctypes
        import winreg
        dst_dir = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"
        dst_dir.mkdir(parents=True, exist_ok=True)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts", 0,
                             winreg.KEY_SET_VALUE)
        for p in paths:
            p = pathlib.Path(p)
            faces = describe_font(p)
            if not faces:
                log(f"skip (not a font): {p}")
                continue
            dst = dst_dir / p.name
            shutil.copy2(p, dst)
            kind = "OpenType" if p.suffix.lower() == ".otf" else "TrueType"
            reg_name = f"{faces[0]['full'] or faces[0]['family']} ({kind})"
            winreg.SetValueEx(key, reg_name, 0, winreg.REG_SZ, str(dst))
            ctypes.windll.gdi32.AddFontResourceW(str(dst))
            installed.append(str(dst))
            records.append({"path": str(dst), "reg": reg_name})
        winreg.CloseKey(key)
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001D, 0, 0, 0x0002, 1000, None)
    else:
        dst_dir = (pathlib.Path.home() / "Library/Fonts") if sys.platform == "darwin" else (pathlib.Path.home() / ".local/share/fonts")
        dst_dir.mkdir(parents=True, exist_ok=True)
        for p in paths:
            dst = dst_dir / pathlib.Path(p).name
            shutil.copy2(p, dst)
            installed.append(str(dst))
            records.append({"path": str(dst)})
        if shutil.which("fc-cache"):
            os.system("fc-cache -f >/dev/null 2>&1")
    _record_installs(records)
    try:
        (cache_dir() / "font-index.json").unlink()
    except OSError:
        pass
    return installed


def _record_installs(records):
    """Remember what we put in the user's font folder so `deck.py uninstall` can take it back out."""
    path = cache_dir().parent / "slidekick-installed-fonts.json"
    try:
        known = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        known = []
    seen = {r["path"] for r in records}
    path.write_text(json.dumps([r for r in known if r["path"] not in seen] + records, indent=1), encoding="utf-8")


def to_ttf(path, out_dir):
    """woff/woff2 -> ttf/otf so PowerPoint and the font index can use it."""
    from fontTools.ttLib import TTFont
    path = pathlib.Path(path)
    if path.suffix.lower() not in (".woff", ".woff2"):
        return path
    tt = TTFont(str(path))
    tt.flavor = None
    ext = ".otf" if "CFF " in tt else ".ttf"
    out = pathlib.Path(out_dir) / (path.stem + ext)
    tt.save(str(out))
    return out


def fetch_google_font(family, weights=(400, 700), italic=False, out_dir="."):
    """Download static TTFs from Google Fonts (open-licensed) for embedding/installing."""
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    axes = []
    for it in ([0, 1] if italic else [0]):
        for w in sorted(set(int(x) for x in weights)):
            axes.append(f"{it},{w}")
    q = family.replace(" ", "+") + ":ital,wght@" + ";".join(axes)
    req = urllib.request.Request(f"https://fonts.googleapis.com/css2?family={q}", headers={"User-Agent": "slidekick/1.0"})
    css = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    files = []
    for block in re.findall(r"@font-face\s*{(.*?)}", css, re.S):
        style = re.search(r"font-style:\s*(\w+)", block).group(1)
        weight = re.search(r"font-weight:\s*(\d+)", block).group(1)
        url = re.search(r"url\((https://[^)]+)\)", block).group(1)
        data = urllib.request.urlopen(url, timeout=60).read()
        ext = ".ttf" if data[:4] in (b"\x00\x01\x00\x00", b"true") else (".otf" if data[:4] == b"OTTO" else ".woff2")
        dst = out_dir / f"{family.replace(' ', '')}-{weight}{'Italic' if style == 'italic' else ''}{ext}"
        dst.write_bytes(data)
        files.append(str(to_ttf(dst, out_dir)))
    if not files:
        raise RuntimeError(f"Google Fonts returned no files for {family!r}")
    return files


def eot_bytes(font_path, index=0):
    """Wrap a TrueType/OpenType face as an uncompressed EOT (the .fntdata container PowerPoint uses)."""
    from fontTools.ttLib import TTCollection, TTFont
    p = str(font_path)
    tt = TTCollection(p).fonts[index] if p.lower().endswith((".ttc", ".otc")) else TTFont(p)
    buf = io.BytesIO()
    tt.save(buf)
    data = buf.getvalue()
    os2, head = tt["OS/2"], tt["head"]

    def utf16(s):
        b = s.encode("utf-16-le")
        return struct.pack("<H", len(b)) + b

    pn = os2.panose
    panose = bytes([pn.bFamilyType, pn.bSerifStyle, pn.bWeight, pn.bProportion, pn.bContrast,
                    pn.bStrokeVariation, pn.bArmStyle, pn.bLetterForm, pn.bMidline, pn.bXHeight])
    body = panose + struct.pack("<BBIHH", 1, 1 if os2.fsSelection & 1 else 0, os2.usWeightClass, os2.fsType, 0x504C)
    body += struct.pack("<IIII", os2.ulUnicodeRange1, os2.ulUnicodeRange2, os2.ulUnicodeRange3, os2.ulUnicodeRange4)
    body += struct.pack("<II", getattr(os2, "ulCodePageRange1", 0), getattr(os2, "ulCodePageRange2", 0))
    body += struct.pack("<I", head.checkSumAdjustment) + b"\0" * 16
    for nid in (1, 2, 5, 4):
        body += b"\0\0" + utf16(_name(tt, nid))
    body += b"\0\0" + struct.pack("<H", 0)
    body += struct.pack("<IIHHII", 0, 0, 0, 0, 0, 0)
    total = 16 + len(body) + len(data)
    return struct.pack("<IIII", total, len(data), 0x00020002, 0) + body + data


def embeddable(face):
    fs = face.get("fsType", 0)
    return not (fs & 0x0002) and not (fs & 0x0200)


def ensure_kit_fonts(brand_json):
    """Install brand-kit fonts whose families aren't installed yet, so PowerPoint/LibreOffice don't substitute them.

    Per-user, no admin; recorded for `deck.py uninstall --fonts`. Returns the installed paths."""
    brand_json = pathlib.Path(brand_json)
    if not brand_json.exists():
        return []
    files = (json.loads(brand_json.read_text(encoding="utf-8")).get("fonts") or {}).get("files") or []
    files = [p for p in (brand_json.parent / f for f in files) if p.exists() and p.suffix.lower() in FONT_EXT]
    if not files:
        return []
    idx = FontIndex()  # installed fonts only
    need = [p for p in files if any(not idx.has(face["typo"]) and not idx.has(face["family"]) for face in describe_font(p))]
    return install_fonts(need) if need else []

