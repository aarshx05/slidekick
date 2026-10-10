# Design review — the taste pass

QA proves the file is *correct*. This pass decides whether it is *good*: would a design director at a top studio let it go to a client? The author cannot judge that reliably. After hours inside the canvas, your own defaults look right to you. So the review is done by **fresh eyes**, with the output in front of them and the HTML out of sight, against a fixed rubric. The result is a short list of exact fixes, not a mood.

Run it:
- **Create** — after the first build with no QA errors (Step 5), and again on the changed slides after fixing. At most 2 review rounds.
- **Edit** — on the changed slides plus one neighbour on each side, judged against *the deck's own system*.
- **Analyse** — on the whole deck, as part of the report.

## 1. Gather the evidence

```bash
python "<skill-dir>/scripts/deck.py" taste -p <out-dir>                          # Create: after build (build runs it too)
python "<skill-dir>/scripts/deck.py" taste --inventory <inspect-dir>/inventory.json   # Edit / Analyse
```

`taste` measures the things an eye catches but a model misses. It writes `qa/taste.md` (or `<inspect-dir>/taste.md`):

| Code | What it measured |
|---|---|
| `near-miss`, `baseline` | edges or baselines 1–6 px apart: reads as a mistake, not a choice |
| `headline-jump`, `margin` | the headline or left margin moves between slides, so it visibly jumps when presenting |
| `edge`, `tight` | content within 24 px of the slide edge; < 10 px between neighbours |
| `rhythm` | unequal gaps in a row of equal items (often a hole after a deletion) |
| `runt`, `widow`, `long-headline` | a headline ending in a short last line; a lone last word; 3+ line headlines |
| `measure`, `centred-body`, `all-caps` | body lines > 90 characters; centred paragraphs; long all-caps text |
| `typography` | straight quotes, hyphens as dashes, `...`, `3x` for 3×, `10-20` for 10–20, double spaces |
| `type-scale`, `families`, `weights` | too many sizes, sizes too close to read as different levels, > 2 families, > 3 weights |
| `off-palette`, `accents` | colours that aren't brand colours or tints of them; > 2 accent hues on a slide |
| `sameness`, `card-grid`, `kicker`, `corner-mark` | few distinct compositions, runs of look-alike slides, and the AI-deck tells from design.md |
| `soft-image` | a picture shown larger than its pixels |

The lint can be wrong (an offset may be deliberate). The reviewer confirms or dismisses each `major`.

## 2. Run the reviewer

**If you can spawn a subagent (Claude Code's Agent tool), do.** Use a general-purpose agent with no access to your reasoning. Paste the prompt below with the paths filled in, and the reviewer writes the JSON file. **If you can't**, do the review yourself as a separate pass. Re-read this file, open only the images and the lint report (not the HTML), and follow the same method and output format.

```text
You are the design director reviewing a presentation before it goes to the client. You did not make it.
Judge only what is on screen. Be exacting and concrete; praise is only useful in "keep".

Read first: <skill-dir>/references/taste.md (sections 3–5: method, rubric, output) and <skill-dir>/references/design.md.
Context: <one paragraph: audience, setting, mode (presented/read), brand, design concept + signature device if any>.
Review mode: <create | edit (judge consistency with the deck's own system; don't impose Slidekick's style) | analyse>.
Slides to review: <all | list of numbers> (look at neighbours for consistency).

Evidence (open every image at full size — the contact sheet alone hides detail):
- contact sheet(s): <paths>
- slide renders: <dir>/slide-NN.png
- measured signals: <path to taste.md>
- brand board / guideline rules: <path or "none">

Write your review as JSON to <out path> exactly in the format of taste.md section 5, then reply with the verdict and
the blocker/major count. No vague notes ("make it pop", "improve spacing"): every finding names the slide, the element,
what is wrong, and the exact change (sizes, positions, words).
```

## 3. Method (the reviewer's checklist)

**Deck pass, on the contact sheet**
1. *Rhythm.* Does the sequence breathe, mixing quiet and dense, big type and evidence? Or is every slide the same weight?
2. *System.* Do the headline position, margins, type steps and colour roles hold from slide to slide? Does anything jump?
3. *Concept.* Is there a point of view, and is the signature device present? Cover the logo: could this be any company's deck?
4. *Tells.* Look for repeated card grids, a kicker on every slide, glows and orbs, a logo in every corner, and screenshots shrunk into boxes.

**Slide pass, on each full-size render**
1. *Three-second test.* Where does the eye land first, second and third? It should be the headline, then the one piece of evidence. If it lands on decoration, a logo or a label, hierarchy has failed.
2. *Squint test.* Blur your eyes. Is there one dominant mass? Is the balance deliberate, or is the space left over?
3. *Edges.* Trace the vertical lines. Count the distinct left edges (2–3 is typical; 5 is chaos). Note anything a few px off, uneven margins, or content hugging an edge.
4. *Space.* Related things sit closer than unrelated ones. Equal relationships get equal gaps. The headline has air under it. Look for trapped white space (an awkward pocket enclosed by elements) against open space that frames the content.
5. *Type.* Are the steps clearly distinct? Is the rag even, with no runts or widows? Body lines should run 45–75 characters. Check tracking on caps and big display type, numerals, curly quotes and real dashes, and that nothing below 18 px is anything but a footnote.
6. *Colour.* The accent marks the one thing that matters. The same colour means the same thing on every slide. Contrast must hold. Tints should be clean, not muddy greys on coloured grounds.
7. *Images and data.* Crop tight to the proof, keep images sharp, and treat them the same way throughout. Charts are labelled directly, the highlighted series is the one the headline names, and there's no chart junk.
8. *Remove one thing.* What could go with no loss? It usually should.

## 4. Rubric — score each 1–5

The bar is the best presentation design you know: Apple keynotes for restraint and scale, Stripe and Linear for typographic precision, Pentagram and Collins brand decks for concept, and the FT and The Economist for charts. A **3** is a competent template, and **3 does not ship.**

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| **Hierarchy & focus** | eye wanders; everything is medium | headline reads first, but evidence competes with decoration | one dominant element per slide; the order of reading is designed |
| **Composition & pacing** | one layout repeated; slides interchangeable | some variety, predictable rhythm | each slide composed for its message; deliberate quiet/loud rhythm; scale used boldly |
| **Typography** | many sizes, runts, straight quotes, cramped leading | consistent scale, a few rough breaks | distinct steps, balanced breaks, tuned tracking and leading, typographic details right |
| **Alignment & spacing** | near-misses, uneven gaps, edge-huggers | grid mostly holds | every edge on purpose; spacing scale and proximity are exact; nothing jumps between slides |
| **Colour & contrast** | palette spread evenly; accents everywhere | on-brand, accent slightly overused | brand ratios respected; one accent carries meaning; contrast effortless |
| **Imagery & data** | thumbnails, stretched or soft images, chart junk | real assets, generic crops | evidence large and tightly cropped; charts say the headline at a glance |
| **Brand & distinctiveness** | generic or AI-looking; could be anyone's | on-brand but templated | unmistakably this brand, with a concept and a signature device used with restraint |
| **Copy-design fit** | walls of text; label headlines | action headlines, slightly wordy | every word earns its space; headlines and layout make one argument |

**Severity** of a finding:
- **blocker** — the audience would notice and think less of it: clipped or unreadable text, broken hierarchy, an off-brand element, an obvious misalignment, a hole, an AI-looking slide.
- **major** — a design director would send it back before a client sees it.
- **polish** — finish details: quotes, a widow, a 2 px nudge.

**Ship bar:**
- no blockers;
- every dimension ≥ 4;
- at most 3 open majors, each one listed for the user.

## 5. Output — `review.json`

```json
{
  "mode": "create",
  "slides_reviewed": [1, 2, 3],
  "scores": {"hierarchy": 4, "composition": 3, "typography": 4, "alignment": 5, "colour": 4, "imagery": 4, "brand": 3, "copy": 4},
  "verdict": "revise",
  "findings": [
    {"slide": 3, "severity": "major", "dimension": "composition", "element": "the five step cards (Step 1–5)",
     "problem": "Same equal-card row as slide 6; the process reads as a template, and step 05's dark card pulls the eye before the headline.",
     "fix": "Make it a horizontal timeline: one 2px rule at y=360 across the content width, numbers 64px on the rule, labels below; drop the card fills; keep step 05 as the only accent.",
     "lint": "card-grid"}
  ],
  "keep": ["the full-bleed orb on the title, continued by Morph to slide 2", "tight crop of the compare image on slide 5"],
  "summary": "Systematic and on-brand, but templated: kickers and card rows on most slides flatten the rhythm."
}
```

- At most **12 findings**, ordered by severity, then by how visible they are. Merge repeats into one deck-level finding (`"slide": 0`) that lists the slides.
- `fix` is executable: give coordinates, sizes, copy edits or a named structural change. If a fix trades off against another, say which wins.
- `keep` protects what works from being "fixed" away.

## 6. Apply and re-check (the author)

1. Fix every blocker and major. Fix polish findings when they're cheap. Change the canvas, or the plan if a finding questions the slide's message. In Edit mode, use edit operations, or rebuild and `import` the slide.
2. Rebuild, then look at the changed slides yourself before re-review. Fixes break neighbours: check the slides on either side.
3. Second round: re-run the reviewer on the changed slides plus the contact sheet, with the first review attached ("check these fixes landed; flag regressions").
4. Stop after 2 rounds. If the ship bar still isn't met, deliver and tell the user what remains and why.

When you disagree with a finding, you may dismiss it, but write down why in one line in `review.json → "dismissed"`. "I prefer it" is not a reason. "The brand guide requires a kicker on every content slide (p. 12)" is.
