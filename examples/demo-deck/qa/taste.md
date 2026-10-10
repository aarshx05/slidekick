# Taste lint

Measured signals only — the design review (references/taste.md) judges the rest. `major` = a design director would send it back; `polish` = finish details.

| signal | value |
|---|---|
| slides | 10 |
| distinct compositions | 10 |
| text sizes (px) | 14, 20, 22, 28, 44, 56, 96, 280 |
| type families | Inter, Manrope |
| off-palette colours | — |
| kicker-above-headline slides | — |
| card-grid slides | — |

## Deck

- **polish** `type-scale` 20px and 22px are too close to read as different levels — merge them

## Slide 2

- **polish** `long-headline` 4-line headline — cut it to ≤ 2 lines — Statement h2.abs.stmt[data-name="Statement"] "Decks still take a day, and most AI tool"

## Slide 4

- **major** `margin` left margin 48px vs 64px on most slides
- **polish** `baseline` side-by-side text baselines 3px apart — share one baseline — e34 p.abs.tag "Chart · data in Excel" / e38 p.abs.body "native objects in the 11-slide Fernway d"
- **polish** `tight` only 8px between these — group them tighter on purpose or give them air — Outline – headline div.abs.sel[data-name="Outline – headline"] / e36 p.abs.tag "Text box"

## Slide 5

- **major** `margin` left margin 48px vs 64px on most slides

## Slide 7

- **major** `margin` left margin 47px vs 64px on most slides

## Slide 8

- **polish** `tight` only 8px between these — group them tighter on purpose or give them air — e74 p.abs.label.muted "Before: the Q3 review" / e75 div.abs

## Slide 9

- **major** `margin` left margin 55px vs 64px on most slides
- **polish** `tight` only 8px between these — group them tighter on purpose or give them air — e83 div.abs / e84 p.abs.foot "Round 1"
- **polish** `tight` only 8px between these — group them tighter on purpose or give them air — e85 div.abs / e86 p.abs.foot "Round 2, after the fixes"

