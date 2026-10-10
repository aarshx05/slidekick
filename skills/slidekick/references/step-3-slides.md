# Step 3 — Mid-IR: semantic slides (`plan/slides.json`)

Lower each beat into slides. Each slide is described by **what it says and what each block does**, not by where things sit. Coordinates come in Step 4.

## First: deck-wide design decisions (`design`)

Decide these once, so all slides share one system (see [design.md](design.md)):
- `concept`: one sentence giving the deck a point of view, plus its `signature_device`, the recurring ownable element drawn from the brand or product (read "Make it distinctive" in design.md first). Also plan the layout for each slide so that at least 5 compositions appear in a 12-slide deck.
- `grid`: margins and columns, e.g. `"72px margins, 12 columns, 24px gutter"`.
- `type_scale`: the 5–6 text styles you will use (hero, slide title, lead, body, label/kicker, footnote), each with size, line-height and weight.
- `background_strategy`: e.g. "light slides, dark brand slide for title/section/closing".
- `transition_default` and `animation_policy` (see below).

## Then: one entry per slide

```json
{
  "id": "results",
  "beat": "b4",
  "archetype": "stats",
  "headline": "Ramp time fell 93% and satisfaction rose to 4.7/5",
  "blocks": [
    {"role": "kicker", "content": "Results after one quarter"},
    {"role": "stat", "content": {"value": "-93%", "label": "time to first merged PR"}, "source": "s2", "emphasis": 3},
    {"role": "stat", "content": {"value": "4.7/5", "label": "new-hire satisfaction"}, "source": "s2"},
    {"role": "stat", "content": {"value": "-61%", "label": "\"where is X?\" questions"}, "source": "s2"},
    {"role": "source", "content": "Internal onboarding telemetry, Q3 2026 (n = 412)"}
  ],
  "visual": "three equal stat cards; the first number in accent colour",
  "transition": "fade",
  "build": "cards float in one by one on click",
  "notes": "Lead with the 93% — that is the CFO's number. Pause after satisfaction."
}
```

## Archetypes

| Archetype | When | Shape |
|---|---|---|
| `title` | opening | logo, title, subtitle, presenter/date |
| `agenda` | > 8 slides | 3–5 items, the current one highlighted on section slides |
| `section` | chapter breaks | big number/label, one line |
| `statement` | a single strong claim | one sentence, large, maybe one supporting line |
| `bullets` | 3–5 parallel points | headline + list; prefer `two-column` or `process` if the points have structure |
| `two-column` | compare/contrast or text + visual | two balanced blocks |
| `image-full` | emotional or product moment | full-bleed image, short overlay text with a scrim for contrast |
| `image-split` / `product-shot` | show the product | real screenshot on one side, 2–3 callouts on the other |
| `stats` | 2–4 key numbers | big numbers + short labels + source |
| `chart` | trend/comparison in data | native chart + takeaway headline; highlight the series that matters |
| `table` | exact values across options | ≤ 6 rows × 5 columns; highlight the recommended row |
| `timeline` / `process` | sequence or plan | 3–6 steps, connected |
| `comparison` / `before-after` | choosing or contrasting | aligned columns, same attributes in the same order |
| `quote` | voice of customer/expert | quote, attribution, maybe a photo |
| `team` | who | photos, names, one-line credentials |
| `logo-wall` | customers/partners | real logos only, same visual weight |
| `cta` / `closing` | the ask | one clear action, contact |

## Headlines

- Use **action titles**: a full sentence stating the takeaway ("Weekly active teams tripled in twelve weeks"). Label titles ("Adoption") belong in the kicker.
- Exceptions: `title`, `section`, `quote`, `closing`.
- ≤ 2 lines at the slide-title size (roughly ≤ 70 characters).

## Word budgets

| Mode | Headline | Body text per slide | Bullets |
|---|---|---|---|
| presented | ≤ 12 words | ≤ 40 words | ≤ 5, ≤ 10 words each |
| read | ≤ 15 words | ≤ 90 words | ≤ 6, ≤ 15 words each |

Detail that doesn't fit goes into `notes` (presented) or an appendix slide.

## Transitions and builds

- **Default:** `fade` between unrelated slides; **`morph`** when consecutive slides share an element that should visibly move or resize (the same logo, card, chart frame, highlight shape). Morph matches objects by name, so give the shared element the same `data-name` starting with `!!` on both slides (see step-4).
- `push`/`wipe` (direction left) can signal a sequence, e.g. steps of a process. Use them sparingly.
- Dramatic transitions (`vortex`, `curtains`, `fracture`, `origami`…) only when the tone asks for it, and at most once.
- **Builds** (animations) only where revealing things one at a time helps the story: stat cards, process steps, a before/after. Use `float` or `fade`, on click, ≤ 5 per slide. Never animate titles or body paragraphs for decoration.

Then run:

```bash
python "<skill-dir>/scripts/deck.py" validate <out-dir>/plan/slides.json
```

It also flags label-style headlines and duplicate ids.
