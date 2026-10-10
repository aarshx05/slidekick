# Changelog

## 1.0.0 — first public release

`/deck` is now **Slidekick** (`/slidekick`). Saying "/deck" still triggers it.

**New**
- **PowerPoint for Mac QA (beta).** On macOS, renders go through PowerPoint for Mac (AppleScript → PDF) instead of LibreOffice. Text baselines are calibrated and cached separately for Mac. Transitions and animations are checked in the XML only, because PDF export doesn't report them.
- `deck.py uninstall [--fonts]` removes the private environment and caches. With `--fonts` it also removes the fonts `/slidekick` installed.
- `--author` on `compile`, `build` and `edit` sets who the `.pptx` is attributed to.
- Install on Codex, opencode, Antigravity, Cursor and others: `npx skills add`, `.codex-plugin/`, and skill links under `.agents/`, `.opencode/` and `.claude/`.
- Test suite and CI on Windows, macOS and Linux.

**Fixed**
- Decks no longer inherit a template's author (or python-pptx's default "last modified by"). Edited decks keep the original author.
- `--trace` works after the subcommand (`deck.py build --trace`).
- `doctor` reports a missing Playwright instead of crashing, and names the QA backend it will use.
- `fonts fetch` saves into the project's `brand/fonts` (it follows `-p`), not the current folder.
- Importing the calibration module no longer creates folders.
- The private environment is isolated from system packages. Dependency versions are capped at the next major release.
- Off Windows, generic CSS families map to fonts that exist on Mac and Windows, instead of Segoe.
- `brand.json` stores paths relative to `brand/`, so projects can be moved and shared without exposing your folders. A brand template given by a relative path is no longer dropped silently, and a missing template now warns.
- Chart edits keep the chart's number format ("$0.0M") instead of resetting the axis to General.
- Images whose `object-position` is in px and whose aspect matches their box no longer crash compile (NaN).
- `fetch` follows `-p` and saves into the project's `assets/`.

## 0.2.0 (as /deck)

- Edit mode: change an existing deck in place with an atomic `edits.json` (text, find/replace, charts, tables, images, styling, delete/move/duplicate/import slides). Formatting is preserved.
- Analyse mode: `inspect` any `.pptx/.ppt/.odp/.pdf` to get an outline, inventory, renders and issues.
- Design review: `taste` lint, plus a fresh-eyes reviewer gate (no blocker, every dimension ≥ 4/5).

## 0.1.0 (as /deck)

- Create mode: brief + brand kit → HTML canvas → native, editable `.pptx`, followed by PowerPoint-rendered QA with baseline calibration.
