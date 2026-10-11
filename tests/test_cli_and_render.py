"""CLI contract and renderer selection (no Office needed), plus a real PowerPoint render when one is installed."""
import subprocess
import sys

import pytest
from conftest import SCRIPTS


def deck(*args):
    return subprocess.run([sys.executable, str(SCRIPTS / "deck.py"), *args], capture_output=True, text=True,
                          env={**__import__("os").environ, "DECK_NO_VENV": "1"})


def test_help_lists_every_command():
    out = deck("--help").stdout
    for cmd in ("doctor", "init", "brand", "build", "inspect", "edit", "taste"):
        assert cmd in out


def test_errors_are_one_line_unless_traced():
    plain = deck("validate", "missing.json")
    assert plain.returncode == 2
    assert "Traceback" not in plain.stderr
    traced = deck("validate", "missing.json", "--trace")  # accepted after the subcommand
    assert "Traceback" in traced.stderr


def test_fonts_fetch_defaults_to_project(monkeypatch, tmp_path):
    from deckkit import cli, fonts

    seen = {}
    monkeypatch.setattr(fonts, "fetch_google_font", lambda fam, weights, italic, out_dir: seen.setdefault("out", out_dir) and [])
    cli.main(["fonts", "fetch", "Inter", "-p", str(tmp_path)])
    assert seen["out"] == tmp_path.resolve() / "brand" / "fonts"


@pytest.mark.parametrize("platform,app,expected", [("darwin", True, "powerpoint-mac"), ("darwin", False, None), ("linux", False, None)])
def test_powerpoint_backend_by_platform(monkeypatch, tmp_path, platform, app, expected):
    from deckkit import render

    monkeypatch.setattr(render.sys, "platform", platform)
    monkeypatch.setattr(render, "_mac_app", lambda: tmp_path if app else None)
    assert render.powerpoint_backend() == expected


def test_baseline_cache_is_per_backend():
    from deckkit import calib

    assert calib.cache_path("powerpoint").name == "ppt-baselines.json"  # existing Windows caches keep working
    assert calib.cache_path("powerpoint-mac") != calib.cache_path("powerpoint")


def test_mac_qa_does_not_report_ignored_transitions(built, monkeypatch):
    """PowerPoint for Mac exports PDF only: no transition readback, so QA must not call them 'ignored'."""
    import json
    import shutil

    from deckkit.qa import run_qa

    project = built["project"]
    render_dir = project / "build" / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    for png in (project / "build" / "ref").glob("slide-*.png"):
        shutil.copy2(png, render_dir / png.name)
    (render_dir / "render.json").write_text(json.dumps({"engine": "powerpoint-mac", "slides": [
        {"index": s["index"]} for s in built["layout"]["slides"]], "errors": []}))
    r = run_qa(project)
    codes = {x["code"] for x in r["issues"]}
    assert "transition-ignored" not in codes and "animation-ignored" not in codes
    assert r["renderer"] == "powerpoint-mac"


@pytest.mark.powerpoint
def test_powerpoint_renders_every_slide(built, tmp_path):
    from deckkit.render import render

    info = render(built["pptx"], tmp_path / "render", engine="powerpoint")
    assert info["engine"].startswith("powerpoint")
    assert len(list((tmp_path / "render").glob("slide-*.png"))) == len(built["layout"]["slides"])


def test_finds_chromium_built_for_another_playwright(monkeypatch, tmp_path):
    """Cloud sandboxes ship one pinned Chromium and block `playwright install`: use what's on disk."""
    from deckkit import util
    for rel in ("chromium-1194/chrome-linux/chrome", "chromium-1208/chrome-linux/chrome",
                "chromium_headless_shell-1194/chrome-linux/headless_shell", "ffmpeg-1011/ffmpeg-linux"):
        exe = tmp_path / rel
        exe.parent.mkdir(parents=True)
        exe.write_text("")
    monkeypatch.setattr(util.shutil, "which", lambda name: None)
    # Playwright 1.63 expects build 1243, which isn't there; its folder is still where the others live
    chromium = type("Chromium", (), {"executable_path": str(tmp_path / "chromium-1243" / "chrome-linux64" / "chrome")})()
    pw = type("PW", (), {"chromium": chromium})()
    found = [p.relative_to(tmp_path).as_posix() for p in util.installed_chromiums(pw) if tmp_path in p.parents]
    assert found[0] == "chromium-1208/chrome-linux/chrome"  # newest build first
    assert "chromium_headless_shell-1194/chrome-linux/headless_shell" in found
    assert not any(f.startswith("ffmpeg") for f in found)


def test_launch_falls_back_to_chromium_on_disk(monkeypatch, tmp_path):
    from deckkit import util
    exe = tmp_path / "chrome"
    monkeypatch.setattr(util, "installed_chromiums", lambda pw: [exe])

    class Chromium:
        def launch(self, headless, channel=None, executable_path=None):
            if executable_path != str(exe):
                raise RuntimeError(f"Executable doesn't exist ({channel or 'bundled'})\nlog")
            return "browser"

    pw = type("PW", (), {"chromium": Chromium()})()
    assert util.launch_browser(pw) == "browser"
    monkeypatch.setattr(util, "installed_chromiums", lambda pw: [])
    with pytest.raises(RuntimeError, match="No Chromium browser available"):
        util.launch_browser(pw)
