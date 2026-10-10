# Step 5 — Build, render, test, optimize

```bash
python "<skill-dir>/scripts/deck.py" build -p <out-dir>
```

`build` runs four stages plus the taste lint, which you can also run one at a time:

| Stage | Command | Produces |
|---|---|---|
| Low-IR | `extract` | `build/layout.json` (geometry, styles, runs, fonts actually used by Chromium), `build/ref/slide-NN.png` (the design) |
| Code gen | `compile [--embed-fonts]` | `deck.pptx`, `build/compile.json` (font resolution, calibration, warnings) |
| Execute | `render [--engine powerpoint\|libreoffice]` | `build/render/slide-NN.png`, `build/render/render.json` (what PowerPoint parsed: transitions, animations, notes, fonts) |
| Test | `qa [--diff-limit 0.012]` | `qa/report.md`, `qa/report.json`, `qa/contact-sheet.png`, `qa/compare-NN.png` |
| Taste | `taste` | `qa/taste.md`, `qa/taste.json`: measured design signals for the review in Step 5b ([taste.md](taste.md)) |

The first compile on a machine with PowerPoint **calibrates text baselines**. It renders tiny probes for each text style the deck uses and caches where PowerPoint actually places them, so text lands where the design put it. Later builds reuse the cache.

## 1. Read the QA report

`build` prints the status, per-slide diff and issues. Codes:

| Code | Severity | Meaning → fix |
|---|---|---|
| `untagged-text`, `untagged-media` | error | visible content not exported → tag it (`data-pptx`) or remove it |
| `untagged-box` | warn | a background/border/shadow outside any tagged element → tag it as `shape` or drop it |
| `overflow` | error | text overflows its box in the design → shorten, enlarge the box, or reduce size |
| `visual-diff` | error | design and PowerPoint render disagree: > 1.2% of pixels, or one connected mismatch ≥ 60 cells (16 px each). Open `qa/compare-NN.png`; the message names the elements in each region |
| `visual-drift` | warn | smaller disagreement (> 0.8%, or a region ≥ 30 cells); check the compare image |
| `font-missing` | error | PowerPoint would substitute the font → install it (`deck.py fonts install …` / `fonts fetch …`) and rebuild |
| `font-portability` | warn | non-system font: recipients need it installed. Tell the user (or try `--embed-fonts`, experimental) |
| `contrast` | warn/error | text below WCAG AA against what's behind it → darken/lighten text, or add a scrim behind text on photos |
| `tiny-text` / `small-text` | error/warn | < 8pt / < 10pt → enlarge, or move to notes |
| `dense` | warn | > 90 words → split the slide or move detail to notes |
| `off-slide` | warn | content past the slide edge would be cut off |
| `transition-ignored`, `animation-ignored` | error | PowerPoint didn't parse it → check the attribute value against step-4 |
| `powerpoint-open` | error | PowerPoint refused the file → report the message (this is a bug in the pipeline) |
| `row-layout-text`, `pseudo-content`, `inline-bg`, `inline-image` | warn | authoring-contract violation → restructure as described in the message |
| `radius`, `multi-gradient`, `gradient`, `scale` | warn | CSS feature approximated → simplify the CSS if the result looks wrong |
| `renderer` | warn | rendered with LibreOffice, so fidelity checks are approximate; or with PowerPoint for Mac, so transitions/animations weren't read back |

## 2. Visual and semantic review — look at the pictures

QA checks mechanics; you check whether the deck is *good*. View `qa/contact-sheet.png` (all slides as rendered by PowerPoint) and every flagged `qa/compare-NN.png` (design | PPTX | diff). Check:

**Visual**
- Nothing clipped, colliding or crowding the edges; consistent margins and alignment across slides.
- Clear hierarchy: the eye goes to the headline first, then the key visual or number.
- Brand: correct logo variant on light/dark, brand colours only, brand fonts rendered (not a fallback face).
- Images are sharp, sensibly cropped (no cut-off faces or UI), and consistent in treatment.
- Charts: the highlighted series is the one the headline talks about; labels are legible.
- Distinctive, not AI-looking: run the self-check in design.md ("Make it distinctive"). At least 5 distinct compositions in a 12-slide deck, the signature device visible on most slides, no identical-card grid, glow or mono-kicker repeated on more than 3 slides. If it fails, rework the canvas before shipping; it counts as a fix round.
- Clear the `major` items in `qa/taste.md` you agree with now (near-misses, headline jumps, runts, rhythm holes). They are cheap to fix and would otherwise use up the reviewer's attention.

**Semantic**
- The headlines alone tell the story (the headline test from Step 2).
- Each slide's body proves its headline, with no orphan facts.
- Every number matches its source in the brief.
- The audience's objections from the brief are answered somewhere.
- The final slide makes the ask from the narrative objective.

## 3. Optimize (≤ 3 rounds)

For each problem, fix it at the right level:
- **Layout or styling** → edit `canvas/deck.html`.
- **A slide in the wrong place or with the wrong message** → edit `plan/slides.json` (and the narrative if the story changed), then update the canvas.
- **Brand wrong** → edit `brand/brand.json`, run `deck.py tokens`.

Rebuild after each round. Stop after 3 rounds even if minor warnings remain, and list them for the user.

Once QA is clean, go to **Step 5b, the design review** ([taste.md](taste.md)). It has its own budget of 2 rounds.

## Notes on fidelity

- The diff forgives ±2 px of positional jitter (renderers round glyph advances differently), so clean slides score 0.0–0.5%. A missing or rewrapped headline, a shifted block or a wrong colour fails.
- **Fonts are the main source of drift.** If Chromium and PowerPoint use different fonts, everything shifts, so install fonts first.
- LibreOffice renders approximate text metrics and some effects differently. With LibreOffice, treat small diffs as noise and review visually.
- The PPTX is the source of truth for the user. Never "fix" a diff by flattening content into an image.
