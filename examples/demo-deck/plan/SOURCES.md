# Sources

Every image in this deck is an output of Slidekick itself, produced in this repository on 2026-10-10. No stock imagery.

## Images (`assets/`)
- `fernway-slide-grid.jpg`: the 11 PowerPoint renders of the Fernway deck (`examples/pitch-deck/build/render/slide-NN.png`, from `deck.py build`), laid out 3 × 4 on Ink with Pillow so the grid sits flush in its panel.
- `fernway-brand-board.png`: `examples/pitch-deck/brand/brand-board.png`, made by `deck.py brand` / `deck.py board` from the Fernway kit (resized to 1400 px).
- `fernway-slide-01.jpg` (slides 5 and 10), `fernway-slide-07.png` (slides 2 and 4): `examples/pitch-deck/build/render/slide-01.png` and `slide-07.png`, the Fernway title and unit-economics slides as rendered by PowerPoint 16 (resized to 1600 px).
- `fernway-qa-compare.png`: `examples/pitch-deck/qa/compare-02.png`, the QA strip (design | PowerPoint render | pixel difference) for Fernway slide 2, with the tool's small caption strip cropped off and the third (difference) panel faded to 25% so an empty diff reads as empty (resized to 2400 px).
- `halden-before-03.png`, `halden-after-03.png`: slide 3 of `examples/edit-before-after/before.pptx` and `after.pptx`, rendered by PowerPoint via `deck.py inspect`.
- The outlines and tags on slide 4 are drawn natively on top of the Fernway render, at the positions of the real objects in that slide's canvas (`examples/pitch-deck/canvas/deck.html`).

## Numbers
- 124 objects, 69 text boxes, 3 charts, 1 table: `deck.py inspect examples/pitch-deck/deck.pptx --no-render` (inventory element kinds, groups' members included).
- 0 px baseline error across 175 calibrated text styles; 25 transitions incl. Morph; 14 entrance animations: measurements recorded in the earlier internal demo brief (PowerPoint 16, Windows 11, October 2026).
- ±2 px QA tolerance: `skills/slidekick/references/step-5-build.md`, "Notes on fidelity".
- Review scores (slide 9): `examples/pitch-deck/qa/review.json`, rounds 1 and 2.

## Brand
- `brand/assets/*.svg`, `brand/deck-template.potx`: copied from `examples/demo-brand-kit/`. `brand/brand-guidelines.txt` is the text of `examples/demo-brand-kit/brand-guidelines.pdf`.
