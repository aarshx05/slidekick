"""Canvas -> layout.json -> .pptx: the deck that comes out is native, editable and carries no stray identity."""
import zipfile

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


def test_extract_is_clean(built):
    layout = built["layout"]
    assert len(layout["slides"]) >= 5
    assert layout["warnings"] == [], layout["warnings"]


def test_every_slide_compiles_to_native_objects(built):
    prs = Presentation(built["pptx"])
    assert len(prs.slides) == len(built["layout"]["slides"])
    for slide in prs.slides:
        assert len(slide.shapes) > 0
    texts = [sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
    assert any("writes itself" in t for t in texts), "headline should be real, editable text"


def test_chart_has_embedded_workbook(built):
    prs = Presentation(built["pptx"])
    charts = [sh for s in prs.slides for sh in s.shapes if sh.has_chart]
    if not charts:
        return
    assert charts[0].chart.part.chart_workbook.xlsx_part is not None


def test_groups_survive(built):
    prs = Presentation(built["pptx"])
    kinds = {sh.shape_type for s in prs.slides for sh in s.shapes}
    assert MSO_SHAPE_TYPE.GROUP in kinds


def test_transitions_written(built):
    with zipfile.ZipFile(built["pptx"]) as z:
        xml = b"".join(z.read(n) for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
    assert b"<p:transition" in xml
    assert b"morph" in xml


def test_core_properties_are_scrubbed(built):
    cp = Presentation(built["pptx"]).core_properties
    assert cp.author == ""
    assert cp.last_modified_by == ""  # python-pptx's default template says "Steve Canny"


def test_template_author_does_not_leak(tmp_path, built):
    from conftest import BRAND_KIT
    from deckkit.compile import open_template, reset_core_props

    prs = open_template(BRAND_KIT / "deck-template.potx")
    prs.core_properties.author = "Someone Else"
    reset_core_props(prs, "Deck Bot")
    out = tmp_path / "t.pptx"
    prs.save(out)
    cp = Presentation(out).core_properties
    assert (cp.author, cp.last_modified_by, cp.revision) == ("Deck Bot", "Deck Bot", 1)
