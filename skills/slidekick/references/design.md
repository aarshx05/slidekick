# Design guide

The goal is a deck that looks designed for this brand and this message, not a template filled with text. Restraint beats decoration.

## Make it distinctive: not AI-looking

A deck that is clean, consistent and on-brand can still look machine-made. The tells are sameness and safe defaults. Treat this section as binding, and check the finished contact sheet against it.

### Start with a design concept (Step 3, before any layout)

Write one sentence in `slides.json → design.concept` that gives the deck a point of view drawn from the product, brand or subject. Examples: "an annual report set by a printer", "a field manual", "a film title sequence", "a lab notebook". Then derive a **signature device** from it. It is one recurring, ownable element used on most slides, such as an oversized slide number, a ruled margin column, a cropped-bleed screenshot, a running index strip, or a distinctive headline treatment. Take it from the brand's own assets (its logo geometry, UI motifs, grid, tone of voice) rather than from a generic toolkit.

### The AI-look tells to avoid

- The same card grid on every slide: three or four equal rounded rectangles with a small label, a title and a paragraph. Use it at most once per deck.
- A mono, uppercase, letter-spaced kicker above every headline, a logo icon in the same corner of every slide, and numbered "01 / 02 / 03" labels as decoration.
- Soft radial glows or orbs, gradient blobs, glowing borders on screenshots, and pill-shaped chips used as labels.
- Every slide on one dark (or one white) ground with identical margins and an identical headline position. Vary the ground, density and composition within the brand's rules.
- Every headline centred in the same place at the same size, and every slide built from the same equal-width column split.
- Screenshots shrunk into a small centred box with three callout cards beside it, repeated for every screen.
- Filler copy shaped like a template (a short title plus one sentence for each of three items), and headlines with the "X, not Y" or "More than just…" cadence.
- Stock-looking symmetry. Unrelated slides that all share the same visual weight and rhythm.

### What to do instead

- **Vary the composition.** A deck of 12 slides should use at least 5 clearly different compositions. Change scale, alignment and density on purpose, with one quiet slide, one crowded slide, one slide that is only a number, and one full-bleed image.
- **Use scale and crop with intent.** Let a headline be huge, let a real screenshot bleed off the edge at full size, and crop tightly to the one element that proves the claim. Show the product large enough to read; a thumbnail is not evidence.
- **Break the grid in one place per slide.** Align to the grid, then let one element overlap a margin, run off the page or sit off-axis, so it looks composed rather than auto-laid-out.
- **Asymmetry and hierarchy.** One dominant element per slide, with the others clearly subordinate. Avoid equal weights.
- **Typography does the work.** Use the brand's display face at extreme and ordinary sizes in the same deck, with real tracking, weight and case decisions. Pair it with a measured text size. Ruled lines, numerals and captions are design material, so use them in place of boxes around everything.
- **Draw from the brand's world.** Reuse its logo geometry, colour ratios, illustration style and UI chrome. Use its colours at the ratios its guide gives, rather than splitting the palette across equal accent chips.
- **Write like a person.** Headlines are specific claims with real nouns and numbers from the source, in the brand's own voice, with varied sentence length. Cut anything that could appear unchanged in another company's deck.
- **Restraint with effects.** Use no glow or soft shadow unless the brand itself uses it. Use at most one gradient in the deck, and only where the brand defines it.

### Self-check before Step 5 ends

1. Cover the logo: could this deck belong to any other product? If yes, push the concept further.
2. Squint at `qa/contact-sheet.png`: are there at least 5 distinct layouts, and is the signature device visible on most slides?
3. Count identical-card slides, glow effects and mono kickers. If any appears on more than 3 slides, rework them.
4. Is any slide only there to fill a slot? Cut it or merge it.

## Finish: the details that make it look crafted

A design director spots these first, and the review in [taste.md](taste.md) checks for every one. Build them in from the start.

**Alignment**
- Every edge is either exactly on another edge or clearly off it. A 1–6 px near-miss reads as a mistake. Snap positions to the grid in CSS (`left: 72px`, not `left: 74px` "by eye").
- Side-by-side text shares a baseline: label and value, column heads, stat and caption.
- Headline position, margins and the content top are identical across slides of the same kind. Anything that moves visibly jumps when the presenter advances.
- Optical corrections: large numerals and display caps have side bearings, so nudge them left 2–4% of the font size to line up with the body text below.

**Spacing**
- Use one spacing scale (8 / 16 / 24 / 32 / 48 / 64). Equal relationships get equal gaps, and related things sit closer than unrelated ones.
- Keep the gap between headline and content consistent across the deck, and generous (≥ 32 px).
- After removing an item from a row, re-space the row. Never leave a hole.

**Typography**
- Balance headline breaks: no runt last line (one or two short words). Fix it with a `<br>` at the natural phrase break, or a narrower `max-width`. Don't use `text-wrap: balance`, because PowerPoint wraps greedily and can't reproduce it.
- Tighten big display type (−0.01 to −0.03 em) and open up small caps labels (+0.06 to +0.12 em). Leading: 1.0–1.15 for display, 1.4–1.5 for body.
- Use real typographic characters: “curly quotes” and ’apostrophes’, an em dash (—) or a spaced en dash ( – ), en dashes in ranges (10–20), × for multiples (3×, 1920×1080), the ellipsis (…), and non-breaking spaces (`&nbsp;`) between a number and its unit (40&nbsp;min) so they never split.
- Keep body lines to 45–75 characters. Never centre multi-line body text. Use sentence case, never long all-caps lines.
- Keep the type-scale steps clearly apart (≥ 1.2× between levels). Two sizes 1–2 px apart look like a mistake.

**Colour and image**
- The accent marks one thing per slide, and the same colour means the same thing on every slide.
- Use tints of brand colours (mixed with white or black), never unrelated greys or near-misses of a brand colour.
- Images are never shown larger than their pixels. Every screenshot gets the same frame treatment.

## Tone presets

Presets are defaults. Freeform direction ("calm like an annual report", "launch-keynote energy") refines or overrides them.

| Tone | Feel | Type & colour | Motion |
|---|---|---|---|
| `corporate` (default for business) | clear, confident, calm | brand primary as accent only, generous white space, sentence-case titles | fade; Morph for continuity; builds only on key slides |
| `keynote` | bold, few words, big visuals | huge type, full-bleed imagery, dark backgrounds | Morph between related slides, float-in builds |
| `editorial` | thoughtful, report-like | serif display face, long-form leads, thin rules | fade only |
| `startup-pitch` | energetic, numbers-forward | big stats, strong accent colour, product shots | push for sequences, zoom on the key number |
| `minimal` | quiet, precise | one accent, monochrome images, lots of space | fade, no builds |
| `playful` | warm, human | rounded shapes, secondary palette, illustrations | float/zoom builds, a single dramatic transition at most |

## Type scale (1280×720 canvas)

Pick one scale and use only its steps. Example (corporate):

| Style | Size / line-height | Weight | Use |
|---|---|---|---|
| hero | 72–88 / 1.05–1.1 | 700–800 | title, statement, closing |
| title | 40–48 / 1.15–1.2 | 700 | slide headline (≤ 2 lines) |
| lead | 24–28 / 1.4 | 400 | subtitle, intro sentence |
| body | 20–24 / 1.4–1.5 | 400 | paragraphs, bullets |
| label | 14–16 / 1.25, uppercase, +0.1em tracking | 600 | kicker, axis labels, tags |
| footnote | 13–14 / 1.35 | 400 | sources only |
| stat | 64–96 / 1.0–1.1 | 800 | big numbers |

Use the brand's display font for hero/title/stat and the body font for the rest. Never use more than two families.

## Grid and spacing

- Margins: 64–80 px left/right, 56–72 px top. Keep the same margin on every slide.
- Use a 12-column grid with 24 px gutters inside the margins. Align block edges to columns.
- Space with a 8 px base: 8 / 16 / 24 / 32 / 48 / 64.
- Keep the kicker, title and content top positions identical across slides of the same archetype, so the eye doesn't jump between slides.
- Leave at least 15% of the slide empty.

## Colour

- Use the brand palette only. Neutrals: text = dk1, background = lt1, muted text ≈ 60% text mixed into the background (`--color-muted`).
- Use one accent per slide for the thing that matters (the key number, the highlighted series, the recommended option).
- Dark brand slides (dk2 or primary background) mark title, section and closing slides; other slides stay light. Don't alternate randomly.
- Text contrast must meet WCAG AA: ≥ 4.5:1 for body, ≥ 3:1 for ≥ 24 px or bold ≥ 18.7 px. On photos, add a gradient scrim (e.g. `linear-gradient(90deg, rgba(0,0,0,.65), transparent 60%)` as the slide background over the image).
- Follow guideline rules (forbidden combinations, logo-on-colour rules) recorded in `brand.json → rules`.

## Logo

- Use the variant built for the background (`for-light-backgrounds` / `for-dark-backgrounds` in `brand.json`).
- Respect clear space and minimum size from the guidelines (default: clear space = logo height, min height 24 px).
- Put it on the title and closing slides; on content slides only if the brand guide asks (small, same corner every time).
- Never recolour, stretch, crop or add effects to the logo.

## Imagery

- Real product UI beats stock photos. Present screenshots in a simple frame (rounded corners 12–24 px, soft shadow, or a device-free browser bar), consistently.
- Crop to the part that proves the headline; enlarge it if needed. Add callouts as separate `text` + `shape` elements, not baked into the image.
- Photos: one style across the deck (all colour or all duotone, similar lighting); full-bleed or a clean half-split.
- Icons: one family, one stroke weight, inline SVG with `currentColor`.

## Data

- One message per chart, stated in the headline. Remove gridlines and axis lines that don't help, and label values directly.
- Highlight the series or bar the headline is about; mute the rest.
- Tables: right-align numbers, use the same decimals, highlight the recommended row, and keep to ≤ 6 rows.

## Patterns that look polished

These are starting points, not a template. Don't use the same pattern on more than a third of the slides, and adapt each to the deck's design concept (see "Make it distinctive").

- **Kicker + action title + one visual.** The default content-slide pattern.
- **Stat cards.** 2–4 equal cards, big number in the accent colour, label below, source in the footnote.
- **Product shot + 3 callouts.** Screenshot on the right 55–60%, three numbered callouts on the left.
- **Statement slide.** One sentence at hero size, one word in the accent colour, nothing else.
- **Morph continuity.** A brand shape or card that travels between slides (`!!` names) ties the deck together.

## Avoid

- Clip-art, gradients on everything, drop shadows on text, more than 2 fonts, centred body paragraphs.
- Bullet lists longer than 5, sentences in ALL CAPS, decorative builds on every slide.
- Generic SaaS phrasing ("streamline your workflow", "unlock synergies"). Use the source's real claims.
- Slides with no visual anchor (a wall of text) and slides with nothing to say (a picture with a label).
