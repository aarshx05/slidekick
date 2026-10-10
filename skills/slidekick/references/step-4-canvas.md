# Step 4 — Low-IR: the canvas contract (`canvas/deck.html`)

You write normal HTML/CSS. Chromium lays it out; the extractor reads the computed geometry and style of every element tagged `data-pptx` and turns it into a native PowerPoint object. **Anything not tagged is not exported.** `canvas/deck.html` from `init` is a working example of everything below.

## Page skeleton

```html
<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="stylesheet" href="deck.css">   <!-- slide frame + resets (do not edit) -->
<link rel="stylesheet" href="brand.css">  <!-- generated brand tokens + @font-face -->
<style> /* your deck design system: type scale, components */ </style>
</head><body>
  <section class="slide" data-transition="fade"> … </section>
  …
</body></html>
```

- Each `<section class="slide">` is exactly **1280×720 CSS px** (1 px = 1/96 in, so px → pt is exact).
- Slide background = the section's `background` (colour, gradient, or `url()` image, optionally under a gradient overlay).
- Use brand tokens (`var(--color-primary)`, `var(--font-display)`, `var(--brand-accent2)` …) instead of raw values. `brand.css` lists them.
- Position top-level blocks absolutely (`class="abs"` + `left/top/width`); this gives the most faithful result. Normal flow inside a box is fine.
- `<body class="debug">` (or `deck.html?debug` with the starter's one-line script) outlines what will be exported (red = text/shape, blue = group, green = image). `deck.py preview -p <out-dir>` serves the canvas for a live look.

## Element kinds — `data-pptx="…"`

| Kind | Put it on | Becomes |
|---|---|---|
| `text` | any block holding text (`h1`, `p`, `ul`, `div`) | a text box, or a shape with text if it has a background/border/radius/shadow |
| `shape` | a decorative box (may be empty) | rectangle / rounded rectangle / ellipse with fill, gradient, border, shadow |
| `image` | `<img>`, inline `<svg>`, a wrapper around one (for clipping/rounding), or an element with `background-image: url()` | a picture (SVG stays vector in PowerPoint 365, with a PNG fallback) |
| `table` | a `<table>` | a native table (merged cells, fills, borders, padding) |
| `chart` | a `<div>` with `data-chart='{…}'` | a native, editable chart with its data in an embedded workbook |
| `group` | a container of other tagged elements | a PowerPoint group that moves and animates as one |
| `ignore` | preview-only helpers | nothing (and not audited) |

Tagged elements nested inside a `text`/`shape` (e.g. an icon inside a card) are exported as separate objects on top of it. Inside a `group`, they become group members.

### Text

Supported per run (`<span>`, `<b>`, `<em>`, `<a>`…): font family, size, weight, italic, colour (incl. alpha), letter-spacing, `text-transform: uppercase` (kept editable as All Caps), small-caps, underline, line-through, links, super/subscript, `text-shadow`, and **gradient text** (`background-clip: text`).
Supported per paragraph: `text-align` (left/center/right/justify), `line-height`, spacing between blocks, left/right margins, `text-indent`, lists (`ul`/`ol` with disc/circle/square/custom-string/decimal/alpha/roman markers, `::marker` colour, nesting).
Vertical position is preserved exactly: top/middle/bottom placement within the box is detected from the layout (use flex centering or padding as you like).

Rules:
- **Always set an explicit `line-height`** (px or unitless) on text. `normal` is estimated.
- One text element = one text box. If text sits side by side (columns, label + value in a row), make each piece its own `data-pptx="text"` element. Flex or grid *rows* inside one text element will stack.
- Don't put meaning in `::before`/`::after` content, CSS counters or inline `<img>`/`<svg>` inside text. Use real elements; they are not exported otherwise.
- Inline backgrounds (badges/highlights inside a sentence) are lost. Make the badge its own `text` element.
- Single-line text is exported with wrapping off (it can never rewrap). Multi-line text is exported with a width that reproduces Chromium's exact line breaks.
- Don't let text overflow its box. Extract flags it, and the PPTX would overflow too.

### Shapes

`background-color`, `linear-gradient`/`radial-gradient` (top layer only, multiple stops, alpha), uniform `border` (solid/dashed/dotted), **per-side borders** (each side becomes its own thin bar, e.g. an accent bar on the left), `border-radius` (one radius per box; `50%` or a pill → ellipse/rounded), `box-shadow` (first outer shadow), `opacity`, `transform: rotate()`. `scale()`/skew and filters are not exported.

### Images

- `<img src="../assets/x.jpg" alt="…">` with `object-fit: cover|contain|fill` and `object-position` → cropped exactly. `alt` becomes the picture's alt text.
- **Rounded or circular images:** set `border-radius` on the `<img>`, or on a wrapper with `overflow:hidden` tagged `data-pptx="image"`.
- `background-image: url(…)` + `background-size: cover|contain|<len>` + `background-position` on a `data-pptx="image"` element works the same way.
- SVG (file or inline) stays vector. Inline SVG must be self-styled (attributes / inline style or `currentColor`). Classes from the page stylesheet are inlined from computed style.
- Large photos are downscaled to ~2× their displayed size; EXIF rotation is applied.
- Store images in `<out-dir>/assets/` and reference them relatively (`../assets/...`).

### Tables

A real `<table data-pptx="table">` with `<tr>`/`<td>`/`<th>`, `colspan`/`rowspan`, cell `background`, per-side cell borders, padding, `vertical-align`, and rich text in cells. Column widths and row heights come from the layout. Keep `border-collapse: collapse`.

### Charts

```html
<div data-pptx="chart" class="abs" style="left:72px; top:200px; width:1136px; height:420px; font:400 16px var(--font-body); color:var(--color-muted)"
     data-chart='{"type":"column","categories":["Q1","Q2","Q3"],"series":[{"name":"Revenue","values":[12,18,27]}],
                  "labels":true,"number_format":"$#,##0\"M\"","gridlines":false,"value_axis":false}'></div>
```

`type`: `column, stacked-column, percent-column, bar, stacked-bar, percent-bar, line, line-markers, area, stacked-area, pie, doughnut, scatter` (scatter series use `"points": [[x,y],…]`).
Options: `colors` (defaults to the brand accents), per-series `color`, `labels`, `label_format`, `number_format`, `legend` (`bottom|top|right|left|none`), `gridlines`, `grid_color`, `value_axis` (show), `min`, `max`, `gap`, `hole` (doughnut %), `line_width`, `smooth`, `title`, `font_size`, `text_color`.
The element's font and colour style the chart text. The inner markup is only a layout placeholder; QA masks charts out of the pixel diff.
**Highlight what matters:** to emphasise one series, colour it with the primary colour and the rest with a muted tone via `colors`.

### Groups

```html
<div data-pptx="group" data-name="Stat 1" class="abs card" style="left:72px; top:250px; width:352px; height:300px; padding:36px" data-anim="float">
  <p data-pptx="text" class="stat-value">-93%</p>
  <p data-pptx="text" class="stat-label">time to first merged PR</p>
</div>
```

The group's own background/border/shadow becomes its first member. Groups make cards move, resize and animate as one object.

## Slide attributes

| Attribute | Values |
|---|---|
| `data-transition` | `fade, fade-black, push, wipe, split, cover, uncover, cut, dissolve, morph, morph-words, morph-chars, reveal, pan, gallery, conveyor, doors, vortex, flip, curtains, fracture, airplane, origami, peel-off, page-curl, none` |
| `data-transition-dir` | `left, right, up, down` (push/wipe/cover/uncover/pan/vortex), `left, right` (reveal/gallery/conveyor/flip) |
| `data-transition-duration` | milliseconds (default 700; Morph 1500) |
| `data-advance` | auto-advance after N ms |
| `<aside class="notes">…</aside>` | speaker notes (hidden in the canvas) |

Every transition is written as PowerPoint writes it (with fallbacks for older versions), and QA verifies that PowerPoint recognised it.

### Morph

Morph animates objects that appear on consecutive slides. Give the shared object the **same `data-name` starting with `!!`** on both slides (e.g. `data-name="!!hero-card"`), and put `data-transition="morph"` on the *second* slide. Change its position, size, colour or rotation between the slides and PowerPoint tweens it. Text with the same content morphs too (`morph-words` / `morph-chars` animate text changes).

## Element animations (builds)

| Attribute | Values |
|---|---|
| `data-anim` | `appear, fade, float, zoom, fly, fly-left, fly-right, fly-top, fly-bottom, wipe, wipe-left, wipe-right, wipe-top, wipe-bottom` (entrance effects, exactly as PowerPoint authors them) |
| `data-anim-trigger` | `click` (default), `with` (with previous), `after` (after previous) |
| `data-anim-delay` | ms |
| `data-anim-duration` | ms (defaults: fade/fly/wipe/zoom 500, float 1000) |
| `data-anim-order` | integer play order (default: document order) |

The first effect on a slide with trigger `with`/`after` plays automatically when the slide appears. Animate groups rather than their parts.

## Names

`data-name="…"` sets the object name shown in PowerPoint's Selection Pane. Name the things a person would look for ("Title", "Logo", "Chart – adoption", "Stat 1"). Use `!!` names for Morph.

## Self-check before extract

- [ ] Every visible piece of text sits inside a `data-pptx="text"` (or `shape`/`table`/`chart`).
- [ ] Every image, logo and icon is `data-pptx="image"`.
- [ ] Explicit `line-height` everywhere; no text overflowing its box.
- [ ] Side-by-side text is in separate elements; no `::before` content, no inline badges.
- [ ] Only brand fonts and tokens are used; fonts are installed (`deck.py fonts list --family "<name>"`).
- [ ] Morph partners share `!!` names; builds are purposeful.
- [ ] Finish details from design.md: positions on the grid (no 1–6 px near-misses), balanced headline breaks via `<br>` (not `text-wrap: balance`), real quotes and dashes, `&nbsp;` between numbers and units.

```bash
python "<skill-dir>/scripts/deck.py" extract -p <out-dir>
```

Fix every warning it prints, then go to Step 5.
