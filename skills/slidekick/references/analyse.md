# Analyse mode — read, summarise or critique a deck

The user hands over a deck and wants to know what's in it, whether it works, or what to fix. Match the effort to the ask:

| The ask | Deliver |
|---|---|
| "what's in this deck?", "summarise it", "pull the numbers / the speaker notes" | §1 only: answer from `outline.md` |
| "extract the images / the data" | §1 with `--media`; tables and chart data are in `inventory.json` |
| "review it", "critique", "is it any good?", "how do I make it better?", "get it ready for…" | §1–§4: the full report |
| "fix it" | the full report, then Edit mode (`edit.md`) for the fixes the user picks. Ask before changing their file |

## 1. Read

```bash
python "<skill-dir>/scripts/deck.py" inspect <deck> --out <work>/inspect [--media]
```

It accepts `.pptx .potx .ppt .odp` (.ppt/.odp convert via LibreOffice) and **`.pdf`** exports. A PDF gives text, positions, sizes, colours and renders, but no shapes, notes or animations, and it can't be edited in place.

It produces:
- `outline.md` — the storyline (one title per slide), then each slide's shapes with ids, text, effective font/size/colour, tables, chart data and notes. **Read all of it.**
- `contact-sheet.png` (or `contact-sheet-NN.png`, 15 slides each) and `render/slide-NN.png` (rendered by PowerPoint when available). **Look at them.** For decks of 30 slides or fewer, open every slide. For longer ones, read the contact sheets, then open the flagged slides and one of each layout.
- `inventory.json` — the same data, machine-readable.
- Mechanical issues: PowerPoint-measured text `overflow`, `font-missing` (renders show a substitute: install the font first or say so), `low-res` and `stretched` images, `small-text`, `contrast`, `dense`, hidden slides, missing alt text, non-native objects.

## 2. Analyse the story

Work from the outline:
- **Headline test.** Read the titles top to bottom. Do they make a convincing paragraph? Are they takeaways ("Churn fell to 1.8%") or labels ("Churn")?
- **Arc.** Which arc is it (step-2-narrative.md)? Is the ask or answer where this audience needs it? Is anything missing (proof, the ask, objections), redundant or out of order?
- **Evidence.** Does every claim have a number, a source or real product proof? Flag invented-looking stats and unsourced numbers. Never "fix" them by inventing your own.
- **Density.** Count the words per slide against the mode: presented ≤ 40 body words, read ≤ 90. Note walls of text and slides with nothing to say.
- **Audience fit.** If the user said who it's for, judge against that. If not, infer it and state your assumption.

## 3. Review the design

```bash
python "<skill-dir>/scripts/deck.py" taste --inventory <work>/inspect/inventory.json
```

Then run the design review in `taste.md` (mode `analyse`, all slides), with fresh eyes via a subagent if available, and write `review.json`. For someone else's deck, judge it against good design and its own brand. Don't hold it to Slidekick's house style.

## 4. Report — `<work>/analysis.md`

```markdown
# <deck title> — analysis
**What it is:** one paragraph — topic, apparent audience, length, mode (presented/read), brand.
**Verdict:** one or two sentences — does it do its job? The single most important change.

## Storyline
The titles as a numbered list, then: arc, what works, what's missing/out of order, headline rewrites for weak titles.

## Design — scores
| hierarchy | composition | typography | alignment | colour | imagery | brand | copy |  (1–5, from review.json)
Top findings (blockers and majors), each: slide · what's wrong · the fix.

## Mechanics
Fonts (missing / non-portable), overflow, low-res images, small text, contrast, hidden slides, accessibility.

## Recommended changes, prioritised
1. … (mark each: **in place** = Edit-mode operations · **rebuild slide** · **redesign deck**)
```

In chat, give the user the verdict, the scores, the top 3–5 changes, and the path to `analysis.md`. Then offer to apply the in-place fixes (Edit mode) or rebuild the deck (Create mode, with this deck as source content).

Don't modify the user's file in Analyse mode.
