# Edit mode — change an existing deck in place

The user hands over a deck: theirs, a colleague's, or one Slidekick built earlier. They want it changed, not remade. Keep everything they didn't ask to change: masters, layouts, untouched slides, animations, and the formatting of text you rewrite. The output must still look like *their* deck.

## 1. Read it first

```bash
python "<skill-dir>/scripts/deck.py" inspect <deck.pptx> --out <work>/inspect     # .pptx .potx .ppt .odp (.pdf is read-only)
```

Read `outline.md` (the storyline, then every slide's shapes with `#id "name"`, box, effective font, size and colour, notes and tables/charts with data) and **look at** `contact-sheet.png`. The ids in the outline are what your edits refer to.

Check the header line `Built by Slidekick:`:
- **unchanged since the last build** → the canvas is still the source of truth. Prefer editing `canvas/deck.html` / `plan/` and rebuilding (Create Step 5), so the project stays in sync. The rebuild replaces `deck.pptx`. If the user has already shared or delivered that file, copy it to `deck-previous.pptx` first and say so.
- **MODIFIED after the last build** → someone edited the .pptx in PowerPoint. Rebuilding would wipe out their changes. Edit in place, or ask before rebuilding.

Fix `font-missing` issues first (`deck.py fonts fetch …`). Renders with a substitute font will mislead you about fit.

## 2. Pick the right tool per change

| The ask | Do |
|---|---|
| reword, fix typos, update numbers, rename a product everywhere | `text`, `replace`, `table`, `chart`, `notes` |
| emphasise or restyle an element; nudge position or size | `style`, `geometry` |
| swap a screenshot or photo | `image` (cover-crops to the existing frame) |
| delete, reorder, hide, duplicate slides | `delete_slide`, `move_slide`, `hide_slide`, `duplicate` |
| **add a new slide, or redesign one slide** | build it with the canvas pipeline in a side project that uses *this deck* as the brand template, then `import` it (`replace` or `after`). See §4 |
| redesign or rebrand the whole deck | Create mode, with the inspected outline as the source content |
| change a SmartArt, OLE object, video or master/layout | not supported in place. Tell the user, or rebuild that slide via §4 |

## 3. Write `edits.json` and apply it

```bash
python "<skill-dir>/scripts/deck.py" edit <deck.pptx> <work>/edits.json --out <work>/<name>-edited.pptx
```

Never overwrite the user's file unless they ask (`--in-place` keeps a `.bak`). The operations apply in order, and **either all succeed or nothing is written**. A wrong id or an unmatched `find` stops with the list of valid shapes.

- **Slides** are referred to by their numbers in `outline.md` (the original deck), even after earlier ops delete or move slides. New slides are referred to by the label you give them with `"as"`.
- **Shapes** are referred to by `#id` (an integer, preferred) or exact name. `"@title"` means the title placeholder.
- **Units:** geometry in px on the 1280-wide canvas (as in the outline), font sizes in pt.
- **Colours:** `"#RRGGBB"` or a theme slot (`accent1`, `tx1`, `bg1`, …). Theme slots keep the deck recolourable.

```json
{"edits": [
  {"op": "text",    "slide": 3, "shape": 7, "text": "Revenue grew 42% in Q3"},
  {"op": "text",    "slide": 4, "shape": 5, "text": ["First bullet", {"text": "Sub-point", "level": 1}, "Third bullet"]},
  {"op": "text",    "slide": 5, "shape": 2, "text": [{"runs": [{"text": "Churn fell to "}, {"text": "1.8%", "bold": true, "color": "accent1"}]}]},
  {"op": "replace", "find": "Acme Cloud", "with": "Acme Platform"},
  {"op": "replace", "find": "FY(\\d\\d)", "with": "FY\\1/26", "regex": true, "slide": 2, "notes": true},
  {"op": "table",   "slide": 6, "shape": 4, "cells": [null, [null, "$4.2M", "$5.1M"]]},
  {"op": "chart",   "slide": 7, "shape": 3, "categories": ["Q1","Q2","Q3"], "series": [{"name": "Revenue", "values": [12, 18, 27]}]},
  {"op": "image",   "slide": 8, "shape": 6, "src": "assets/new-dashboard.png", "fit": "cover", "focus": [0.5, 0.2], "alt": "Dashboard, October"},
  {"op": "style",   "slide": 9, "shape": 4, "color": "accent2", "bold": true, "size_pt": 28, "paragraphs": [0]},
  {"op": "geometry","slide": 9, "shape": 4, "x": 72, "w": 640},
  {"op": "notes",   "slide": 9, "text": "Pause here."},
  {"op": "delete_shape", "slide": 10, "shape": "Stock photo 3"},
  {"op": "duplicate",    "slide": 4, "as": "q4-copy"},
  {"op": "text",         "slide": "q4-copy", "shape": 7, "text": "Q4 outlook"},
  {"op": "move_slide",   "slide": 12, "after": 2},
  {"op": "hide_slide",   "slide": 13},
  {"op": "delete_slide", "slide": 14},
  {"op": "import", "from": "<side-project>/deck.pptx", "slides": [1], "replace": 5, "as": "new-5"}
]}
```

| op | fields |
|---|---|
| `text` | `slide`, `shape`, `text`: a string (`\n` starts a new paragraph, `\v` is a line break) or a list of paragraphs, each a string or `{"text"\|"runs", "level"}`. Each paragraph keeps the formatting of the paragraph it replaces. Extra paragraphs copy the last one. A run may override `bold italic underline color size_pt font` |
| `replace` | `find`, `with`, optional `slide`, `regex`, `case` (default true), `notes`, `optional`. Works across run boundaries, in tables, groups and chart titles. Each run keeps its formatting |
| `table` | `cells`: a 2-D array with `null` = keep (or `row`, `col`, `text` for one cell). Adding rows or columns isn't supported, so rebuild via §4 |
| `chart` | `categories` + `series[{name, values}]` (or `points` for scatter), optional `number_format`. Formatting is kept |
| `image` | `src`, `fit` `cover`\|`contain`\|`stretch`, `focus [x, y]` (0–1, where the crop centres), `alt`. Raster only (convert an SVG to PNG at 2× display size) |
| `style` | any of `size_pt bold italic underline color font` (optionally only `paragraphs: [i…]`), `align`, `fill`, `line`, `autofit none\|shrink\|resize` |
| `geometry` | any of `x y w h` (top-level shapes; move a group as a whole) |
| `delete_shape` | also removes its animations |
| `duplicate` | copy placed after the original (or `after`/`before`/`at`), `as` a label |
| `move_slide` | `after` / `before` (a slide ref) or `at` (`"start"`, `"end"`, or a 1-based position) |
| `delete_slide`, `hide_slide` (`hidden: false` to unhide) | sections, custom shows and links to the slide are kept valid |
| `import` | `from` a .pptx, `slides` (default all), and `replace` (a slide ref), `after`/`before`/`at`, `as` labels, `layout` `blank`\|`match`. It carries pictures, charts with their data, links, transitions, animations and notes |

### Writing replacement text that fits

- Stay within about ±15% of the original length. Longer text overflows or rewraps, shorter text leaves a hole. If it must be longer, cut words first. After that, widen the box (`geometry`) on the deck's own grid. Shrink the type only to a size the deck already uses, never below its body size.
- Match the voice and pattern of the surrounding slides: sentence case or title case, the punctuation habits, and how numbers are formatted.
- Don't turn autofit on to hide overflow. It shrinks text off the deck's type scale.

## 4. New or redesigned slides — build, then import

1. Set up a side project and use the deck itself as the brand template:
   ```bash
   python "<skill-dir>/scripts/deck.py" init <work>/new
   python "<skill-dir>/scripts/deck.py" brand <deck.pptx> -p <work>/new
   ```
   The theme colours and fonts match, so imported text keeps theme-linked colours.
2. **Derive the deck's system from the inventory, don't invent one.** Take the headline box position and size, the margins, the body size, the accent usage and the background treatment from `inventory.json` on comparable slides, and write them into the side project's canvas CSS. A new slide must look like a sibling of its neighbours, not like a Slidekick slide. Exception: if the user asked for a redesign, Create mode's design guide applies to that slide.
3. Write only the needed slides in `canvas/deck.html`, then `deck.py build -p <work>/new` until QA is clean.
4. `import` them into the deck with `replace` or `after`.

The template's master graphics (logo, footer) are hidden on imported canvas slides, because the canvas draws everything. If the deck's other slides show a master logo or footer, reproduce it in the canvas at the same position.

## 5. Verify — always

```bash
python "<skill-dir>/scripts/deck.py" inspect <work>/<name>-edited.pptx --out <work>/after
python "<skill-dir>/scripts/deck.py" taste --inventory <work>/after/inventory.json
```

- `overflow` errors come from PowerPoint's own layout: rewritten text no longer fits. Fix them.
- Look at the render of every changed slide next to its "before" render (`<work>/inspect/render/` and `<work>/after/render/`). Did anything shift, rewrap, lose formatting or leave a hole?
- **A pure correction** (numbers, wording, chart or table data; no slide added, removed or re-laid-out; text within about 20% of its old length): QA or `inspect` must show no new overflow, collision or contrast issue, and the taste lint no new finding. Then a quick fresh-eyes look at only the changed slides answers one question: does anything look broken or out of place? That replaces the scored review. If it finds anything, run the full review below.
- **Anything else:** run the design review (`taste.md`, mode `edit`) on the changed slides and their neighbours. Judge consistency with the deck's own system, and don't impose Slidekick's style on someone else's deck. A deletion that leaves a `rhythm` hole, or a new slide that doesn't match, is a blocker.

## 6. Deliver

Give the user:
- the path to the edited file;
- the list of changes, slide by slide (the `edit` log);
- anything you couldn't do in place, and why;
- anything they should check: fonts, replaced numbers that need confirming, slides you rebuilt.

Offer to apply the review's remaining suggestions.
