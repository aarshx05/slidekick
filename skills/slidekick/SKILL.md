---
name: slidekick
description: Build, edit and review PowerPoint decks. Create a fully editable, on-brand .pptx (native text, shapes, pictures, tables, charts, transitions incl. Morph, animations) from a brief, documents, data, a code project or a website, using brand kits (logos, palettes, fonts, .potx/.pptx templates, tokens, guideline PDFs). Edit an existing deck in place (rewrite text, update numbers and charts, swap images, restyle, add/delete/reorder/redesign slides) while preserving its formatting. Read, summarise or critique any deck (.pptx/.ppt/.odp/.pdf). Every design is checked by a fresh-eyes design-taste review. Use when someone says "/slidekick" (or "/deck"), "make a deck / presentation / slides / pitch deck / PPT", "turn this into a presentation", "edit / update / fix this deck", "change slide N", "review / critique / analyse / summarise this presentation", or hands over a .pptx or a brand kit.
---

# Slidekick

Design the deck as an HTML/CSS canvas, let Chromium solve the layout, compile every element into a native PowerPoint object, then render the file with real PowerPoint and check it against the design. A fresh-eyes design review then judges whether it is *good*, not just correct. The output is an ordinary `.pptx` that anyone can edit.

## Modes — pick one first

| The user… | Mode | Follow |
|---|---|---|
| wants a new deck (brief, docs, data, project, URL) | **Create** | Steps 0–6 below |
| hands over an existing deck and wants it changed: wording, numbers, images, styling, slides added/removed/reordered/redesigned | **Edit** | [references/edit.md](references/edit.md). Don't regenerate their deck |
| hands over a deck to understand, summarise, extract from, or critique | **Analyse** | [references/analyse.md](references/analyse.md). Don't modify their file |

Mixed asks chain modes: "review this and fix it" is Analyse → Edit; "rebuild this old deck in our new brand" is Analyse (for content) → Create. If the user names a .pptx you built earlier in this project, it's Edit (`inspect` tells you whether it changed since the build).

```
Source ─► Semantic analysis (content · brand · audience)
       ─► High-IR  plan/narrative.json     (the story)
       ─► Mid-IR   plan/slides.json        (semantic slides)
       ─► Low-IR   canvas/deck.html ─► Chromium geometry ─► build/layout.json
       ─► Code gen deck.pptx  (python-pptx + OOXML patches: transitions, animations, SVG, theme)
       ─► Execute  PowerPoint render (LibreOffice fallback)
       ─► Test     pixel diff vs design + deterministic checks + your visual review
       ─► Optimize fix and rebuild (max 3 rounds)
       ─► Review   taste lint + fresh-eyes design review → fix (max 2 rounds)
```

## Invocation

`/slidekick [input] [options]` — options may also come as plain language.

| Option | Meaning | Default |
|---|---|---|
| `--brand <paths…>` | brand kit: folder or files (`.potx`/`.pptx` template, logos, fonts, `tokens.json`, CSS, guideline PDF) | look for one in the project, else derive |
| `--audience "<who>"` | who watches/reads it | inferred, stated in the brief |
| `--mode presented\|read` | presented = sparse slides + speaker notes; read = self-explanatory | presented |
| `--slides N` / `--minutes M` | length | from content (≈1 slide/min presented) |
| `--tone <preset or freeform>` | see [references/design.md](references/design.md) | inferred |
| `--transitions subtle\|dynamic\|none` | subtle = fade + Morph for continuity | subtle |
| `--animations on\|off` | builds on the slides that benefit | on (sparingly) |
| `--embed-fonts` | experimental EOT font embedding | off |
| `--out <dir>` | output folder | `deck-output/` (timestamped `deck-output-YYYY-MM-DD-HHmmss/` if it exists) |

Input can be a prompt/brief, documents (`.md .pdf .docx .txt`), data (`.csv .xlsx .json`), the current code project, or a URL. If there is nothing to build from, ask what the deck is about.

## Tooling

`<skill-dir>` is the folder containing this file (Claude Code prints it as "Base directory for this skill"). Every command is:

```bash
python "<skill-dir>/scripts/deck.py" <command> [-p <out-dir>] ...
```

(`python3` on macOS/Linux.) The first run creates a private environment and installs dependencies. Run `deck.py doctor` once per machine. It reports the browser, PowerPoint/LibreOffice and fonts available. PowerPoint gives ground-truth QA: Windows fully, Mac in beta (renders only; transitions and animations are checked in the XML). LibreOffice is an approximation. On a Mac, the first render may ask to let the terminal control PowerPoint. Say yes.

## Step 0 — Set up

```bash
python "<skill-dir>/scripts/deck.py" init <out-dir>
```

This creates `brand/ assets/ plan/ canvas/{deck.html,deck.css,brand.css} build/ qa/`. `canvas/deck.html` starts as a reference deck that shows the authoring contract; you replace its slides.

## Step 1 — Source and semantic analysis

**Read:** [references/step-1-source.md](references/step-1-source.md)

Gather content, brand and audience. Ingest the brand kit with `deck.py brand <kit…> -p <out-dir>`, **look at `brand/brand-board.png`**, correct `brand/brand.json`, then run `deck.py tokens`. Collect real imagery into `assets/`.
Write `plan/brief.md`.

**Gate:** the brief answers every rubric question; the brand board shows the right logo, colours and fonts (fonts installed — see Step 1); every image you plan to use is in `assets/` with its source noted.

## Step 2 — High-IR: narrative

**Read:** [references/step-2-narrative.md](references/step-2-narrative.md)

Write `plan/narrative.json` and validate it with `deck.py validate <out-dir>/plan/narrative.json`.

**Gate:** it validates, and the beat messages read alone tell the whole story to the stated audience.

## Step 3 — Mid-IR: semantic slides

**Read:** [references/step-3-slides.md](references/step-3-slides.md) and [references/design.md](references/design.md)

Write `plan/slides.json`: the deck-wide design decisions first, then one entry per slide (archetype, action headline, content blocks, visual, transition, build, notes). Validate it.

**Gate:** it validates; headlines read as a storyline; every slide is within its word budget.

## Step 4 — Low-IR: the canvas

**Read:** [references/step-4-canvas.md](references/step-4-canvas.md) — the authoring contract. Follow it exactly.

Write `canvas/deck.html`: one `<section class="slide">` (1280×720) per slide, styled with the brand tokens in `canvas/brand.css`. Tag every exported element with `data-pptx`. Then run `deck.py extract -p <out-dir>` and fix every warning it prints.

**Gate:** extract prints no `untagged-*`, `overflow`, `pseudo-content`, `inline-*` or `row-layout-text` warnings.

## Step 5 — Build, render, test, optimize

**Read:** [references/step-5-build.md](references/step-5-build.md)

```bash
python "<skill-dir>/scripts/deck.py" build -p <out-dir>
```

`build` runs extract → compile → render → QA → taste lint. Then **look at** `qa/contact-sheet.png` and every `qa/compare-NN.png` that QA flags, and do the visual and semantic review in step-5. Fix in the canvas (or the plan) and rebuild. Stop after **3** fix rounds; report anything still open.

**Gate:** QA status is not `FAIL`; no slide's visual diff is above the limit; your review finds no clipped, colliding, off-brand or unreadable slide.

## Step 5b — Design review (taste)

**Read:** [references/taste.md](references/taste.md)

Correct is not the same as good. Once QA is clean, hand the rendered deck and `qa/taste.md` to a **fresh-eyes reviewer**: a subagent with the prompt in taste.md, or a separate pass of your own if you can't spawn one. It scores 8 dimensions against a studio-level bar and returns `qa/review.json` with exact fixes. Apply them, rebuild, and re-review the changed slides. Stop after **2** review rounds.

**Gate:** no blocker, every dimension ≥ 4, at most 3 open majors (listed for the user).

## Step 6 — Deliver

Give the user:
- the path to `deck.pptx` (and `qa/contact-sheet.png` as a preview);
- one sentence on the storyline and design direction, plus the review scores and verdict;
- anything they must know: fonts recipients need installed, image sources to clear (`assets/SOURCES.md`), and QA items you could not resolve;
- an offer to re-cut length, change tone, or rework specific slides.

## Laws

- **Editable or it doesn't ship.** Every visible thing is a native object: text in text boxes, data in native charts and tables. Never flatten a slide into a picture.
- **One idea per slide.** The headline states the takeaway, and the body proves it.
- **Show the real thing.** Use real product UI, real data and real brand assets. Never use abstract filler or invented numbers.
- **On brand.** Use only brand colours, fonts and logos, with the logo used as the brand guide says.
- **Distinctive, never generic.** The deck must not look machine-made. Before laying out slides, set a design concept and a signature device (`slides.json → design.concept`), vary the composition across slides, and avoid the AI-look tells listed in [references/design.md](references/design.md) ("Make it distinctive"). Run its self-check on the contact sheet in Step 5.
- **Reviewed by fresh eyes.** The author never signs off their own design. Every deck you create or change passes the design review in [references/taste.md](references/taste.md) before it ships.
- **Their deck, their system.** When editing someone's deck, change only what was asked, keep their formatting, and make new slides look like siblings of their slides. Never overwrite their file unless asked.
- **Readable when presented.** Body text ≥ 18px, and no text below 14px except source footnotes. Text needs WCAG AA contrast.
- **Nothing secret leaves Step 1.** Keep credentials, internal URLs, customer names and personal data out of slides and notes; substitute fictional stand-ins and say so.
