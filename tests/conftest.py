import argparse
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "slidekick" / "scripts"
sys.path.insert(0, str(SCRIPTS))

BRAND_KIT = ROOT / "examples" / "demo-brand-kit"


def pytest_collection_modifyitems(config, items):
    from deckkit.render import powerpoint_available
    if powerpoint_available():
        return
    skip = pytest.mark.skip(reason="needs Microsoft PowerPoint")
    for item in items:
        if "powerpoint" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    """The starter canvas, extracted and compiled once (no PowerPoint needed: calibration off)."""
    from deckkit.cli import cmd_init
    from deckkit.compile import compile_deck
    from deckkit.extract import extract

    project = tmp_path_factory.mktemp("deck") / "proj"
    cmd_init(argparse.Namespace(dir=str(project), force=False))
    layout = extract(project)
    report = compile_deck(project, calibrate=False)
    return {"project": project, "layout": layout, "report": report, "pptx": pathlib.Path(report["output"])}
