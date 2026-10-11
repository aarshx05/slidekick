# Changelog

## 1.1.3

**Changed**
- The example decks, the `.potx` templates and the demo kit's guidelines PDF moved to [aarshx05/aarshx05](https://github.com/aarshx05/aarshx05/tree/main/assets/slidekick/examples), so the plugin bundle holds only text, images and fonts. This clears the plugin directory's `BINARIES_NOT_INSPECTED` hold. Each example's README links its files and gives the `curl` lines to fetch them before a rebuild.
- Tests generate their own `.potx` instead of reading the kit's template.

## 1.1.2

**Fixed**
- The Chromium fallback from 1.1.1 no longer reads environment variables. It asks Playwright where its browsers folder is, so the module that also serves the local preview at `127.0.0.1` reads nothing from the environment. This clears a plugin-directory review hold that read the two together as a credential leaving the machine. Behaviour is unchanged.

## 1.1.1

**Fixed**
- **Works out of the box in cloud sandboxes such as Claude Code on the web.** When neither Edge, Chrome nor Playwright's own Chromium build is available, Slidekick now launches any Chromium already on disk: another Playwright version's build (in `PLAYWRIGHT_BROWSERS_PATH` or the Playwright cache, newest first) or a system `chromium`/`google-chrome`. Before, a sandbox that ships one pinned Chromium and blocks `playwright install` stopped with "No Chromium browser available".

**Plugin listing**
- The Claude plugin description now says that Slidekick runs a local Python pipeline that installs its own packages on first run, and `plugin.json` links the README's Privacy section as the privacy policy.

## 1.1.0

**New**
- **A brand without a kit:** `deck.py brand --colors "#F26B1D,#2B2B2B" --font Nunito` builds a complete brand from colours and a font (or `--display-font`/`--body-font`). The `brand.json` format is now documented in step-1-source.md.
- **On-brand chart colours, always:** when a kit has fewer than six colours, the theme accents are shades and tints of the brand's own colours, never Office blue and orange.
- **A readable brand colour for text:** when the primary colour fails WCAG AA on the background (bright orange on white, say), `brand` reports it and writes `--color-primary-text`, a darker shade to use for text while shapes keep the true colour.
- **Highlight a single bar:** per-series `point_colors` (`{"3": "#F26B1D"}`), plus `label_position` and `label_color` for chart data labels. No more zero-value series workarounds.
- **A quick path for small jobs:** decks of 10 slides or fewer whose content the user supplied skip `narrative.json` and the long reading list. A pure correction in Edit mode (numbers, wording, chart data, same layout) gets a proportionate check instead of the full scored review.

**Fixed**
- The taste lint no longer flags the deliberate optical nudge of big numerals (which the design guide recommends), the inner padding of a chart's box, or a backing card in a stacked-deck motif as "margin" or "near-miss" majors. Real misalignments are still caught. The launch deck went from 4 false majors to 0.
- A canvas rebuild in Edit mode keeps the previous `deck.pptx` as `deck-previous.pptx` when the user has already shared it.

## 1.0.1

**Fixed**
- **Mac and Linux without PowerPoint no longer report FAIL on a good deck.** "PowerPoint not installed" isn't an error any more. When LibreOffice does the rendering, pixel diffs are warnings, and the report says the check is approximate. A real PowerPoint render still fails on a real diff.
- `build` and `compile` install the brand kit's fonts per-user when they aren't installed, so renderers stop substituting them. Each install is logged, `deck.py uninstall --fonts` removes them, and `--no-font-install` turns this off. QA now flags a font that exists only in the kit.
- Fonts in a CSS stack resolve the way a browser picks them: the first family installed on this machine. A deck with no brand kit on Mac or Linux no longer asks for Segoe UI. A missing core Office font (Arial, Calibri, Segoe UI…) is a warning, because recipients' PowerPoint has it.
- The demo deck ships its OFL fonts (Manrope, Inter), so it rebuilds on any OS.
- Demo deck slide 1: the top card of the Morph stack now shows a real cover slide instead of an empty card.

**New**
- Install on Gemini CLI (`gemini-extension.json`) and Cursor (`.cursor-plugin/plugin.json`).
- README demo GIF, plus measured time and token numbers.
- GitHub Discussions for questions and ideas.

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
