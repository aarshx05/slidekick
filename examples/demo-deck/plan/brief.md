# Brief: Meet Slidekick

## Ask
A 10-slide launch deck for Slidekick, the open-source Claude Code skill (`/slidekick`) that turns a brief plus a brand kit into an editable, on-brand PowerPoint deck, edits existing decks in place, and reviews decks. It doubles as the public launch deck and the gallery example for the project's own brand kit (`examples/demo-brand-kit/`). It replaces an earlier internal team demo.

## Audience
People who make decks for a living or close to it: founders, PMs, marketers, consultants. They know PowerPoint well and are not developers. They are sceptical of AI deck tools, because the ones they've tried "just export pictures": slides that look fine until you need to change a word. Setting: launch page, README gallery, short talks; presented or read on screen.

Objections, and where each is answered:
- "It's pictures of slides, isn't it?" → slide 4 (every element is a native object, with the counts from a real deck).
- "It won't look like our brand." → slide 5 (it builds from your template, logos, colours, fonts and rules).
- "It'll look different in PowerPoint." → slides 6–7 (every build is rendered by PowerPoint and diffed; baseline calibration).
- "I already have a deck." → slide 8 (Edit mode changes it in place).
- "AI design looks generic." → slide 9 (a separate fresh-eyes design review against a studio bar).

Mode: presented, with speaker notes, but readable on its own.

## The one thing
Slidekick gives you a real PowerPoint deck: native, on your brand, and checked in PowerPoint before you see it. Install it with `/plugin install slidekick@slidekick`.

## Facts (each traced to a source)
- Text baselines are calibrated against PowerPoint: 175 text styles (5 font/weight combinations × 5 sizes × 7 line-heights), maximum residual baseline error 0 px at 1/3 px precision (before calibration: up to 8 px): calibration run on PowerPoint 16, Windows 11, recorded in the earlier demo brief (October 2026)
- 25 slide transitions including Morph (by object, word and character), each one parsed by PowerPoint 16 on read-back: same source
- 14 entrance animations (appear, fade, float, zoom, five fly and five wipe directions), all parsed with the right triggers: same source
- QA forgives ±2 px of positional jitter; a missing or rewrapped headline, a shifted block or a wrong colour fails: `skills/slidekick/references/step-5-build.md`, "Notes on fidelity"
- The Fernway example (`examples/pitch-deck/`): 11 slides, rendered by PowerPoint for QA in 2.3 s; object counts from `deck.py inspect` of its `deck.pptx` (see slide 4)
- The Fernway design-review scores on slide 9 come from `examples/pitch-deck/qa/review.json`
- The Edit example (`examples/edit-before-after/`) turned a Q3 review into Q4 with one `edits.json`
- Install: `/plugin install slidekick@slidekick`; source: github.com/aarshx05/slidekick

## Product in use
Brief + brand kit (Fernway brief and brand board) → deck.pptx (Fernway contact sheet) → PowerPoint render diffed against the design (Fernway QA compare) → design review scores (Fernway review.json). Edit mode shown with the Halden Q3 → Q4 before/after renders. Every image is the tool's own output.

## Brand
The Slidekick kit in `examples/demo-brand-kit/`: Signal Violet #5B4BFF (hero colour), Coral #FF6B4A (one highlight per slide; shapes, or text on Ink only, never on Violet), Ink #14122B (text and dark slides), Mist #F3F2FF (light surface). Manrope (display, 800/700) and Inter (body, 400/600), both installed. Template `deck-template.potx` (copied into `brand/`). Logo: dark wordmark on light, light wordmark on Ink or Violet; clear space = mark height; minimum 24 px tall. The mark is three stacked, offset rounded cards (Coral, Violet, Ink), which is the deck's signature device.

## Assets
All in `assets/`, all produced by Slidekick itself in this repo (see `plan/SOURCES.md`): the Fernway brand board, contact sheet, title-slide and economics-slide renders, a QA compare strip, and the Halden before/after renders.

## Rubric
- What is it? A Claude Code skill that makes, edits and reviews real PowerPoint decks.
- Who is it for? People who make decks and distrust AI deck tools.
- What must they believe? The output is native, on-brand and checked in PowerPoint.
- Strongest evidence? A real 11-slide deck it made, its object counts, its PowerPoint diff, 0 px baseline error.
- Visual hook? The logo's three stacked cards: they Morph from the title into the frame behind the product images, then into brief → brand → deck.
- Real UI or data? The tool's own outputs: contact sheet, brand board, QA compare, edit before/after, review scores.
- Brand rules? Coral once per slide and never on Violet; Ink for dark slides; light wordmark on dark.
- What would make them say no? "It's pictures", "it's off-brand", "it's generic". Each answered with proof.

## Open questions
None.
