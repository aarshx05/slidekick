#!/usr/bin/env python3
"""deck — editable, on-brand PPTX pipeline. Run `python deck.py --help`."""
import hashlib
import os
import pathlib
import subprocess
import sys

if sys.version_info < (3, 10):
    sys.exit(f"[deck] Python 3.10+ is required (this is {sys.version.split()[0]}). Install a newer Python and re-run.")

HERE = pathlib.Path(__file__).resolve().parent
REQ = HERE / "requirements.txt"


def _venv_dir() -> pathlib.Path:
    if os.environ.get("DECK_VENV"):
        return pathlib.Path(os.environ["DECK_VENV"])
    base = os.environ.get("LOCALAPPDATA") or os.path.join(pathlib.Path.home(), ".cache")
    return pathlib.Path(base) / "slidekick" / f"venv-py{sys.version_info.major}{sys.version_info.minor}"


def _uninstall(argv) -> int:
    """Remove the private venv + caches and, with --fonts, the fonts deck installed. Stdlib only: runs outside the venv."""
    import json
    import shutil
    base = pathlib.Path(os.environ.get("LOCALAPPDATA") or os.path.join(pathlib.Path.home(), ".cache"))
    cache = base / "slidekick"
    manifest = base / "slidekick-installed-fonts.json"
    fonts = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []
    if cache.exists():
        shutil.rmtree(cache, ignore_errors=True)
        print(f"removed {cache}")
    if "--fonts" not in argv:
        for f in fonts:
            print(f"kept font {f['path']}")
        if fonts:
            print("run `deck.py uninstall --fonts` to remove these too")
        return 0
    key = None
    if os.name == "nt" and fonts:
        import ctypes
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts", 0, winreg.KEY_SET_VALUE)
    for f in fonts:
        if key is not None:
            ctypes.windll.gdi32.RemoveFontResourceW(f["path"])
            try:
                winreg.DeleteValue(key, f.get("reg", ""))
            except OSError:
                pass
        try:
            pathlib.Path(f["path"]).unlink()
            print(f"removed font {f['path']}")
        except OSError as e:
            print(f"could not remove {f['path']} ({e}); close apps using it and delete it by hand")
    if key is not None:
        winreg.CloseKey(key)
    manifest.unlink(missing_ok=True)
    return 0


def _ensure_env() -> None:
    """Re-exec inside a private, isolated venv that has requirements.txt installed."""
    if os.environ.get("DECK_IN_VENV") == "1" or os.environ.get("DECK_NO_VENV") == "1":
        return
    vd = _venv_dir()
    py = vd / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    want = hashlib.sha256(REQ.read_bytes()).hexdigest()
    stamp = vd / ".requirements.sha256"
    if not py.exists():
        print(f"[deck] creating environment at {vd} (first run only)", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "venv", str(vd)])
    if not stamp.exists() or stamp.read_text().strip() != want:
        print("[deck] installing dependencies (first run only)", file=sys.stderr)
        subprocess.check_call([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", str(REQ)])
        stamp.write_text(want)
    env = dict(os.environ, DECK_IN_VENV="1", PYTHONIOENCODING="utf-8")
    sys.exit(subprocess.call([str(py), str(HERE / "deck.py"), *sys.argv[1:]], env=env))


if __name__ == "__main__":
    if sys.argv[1:2] == ["uninstall"]:
        sys.exit(_uninstall(sys.argv[2:]))
    _ensure_env()
    sys.path.insert(0, str(HERE))
    from deckkit.cli import main

    sys.exit(main(sys.argv[1:]))
