# Deck QA — PASS-WITH-WARNINGS

renderer: powerpoint · errors: 0 · warnings: 6

| slide | diff | words | issues |
|---|---|---|---|
| 1 | 0.0% | 17 | — |
| 2 | 0.3% | 28 | visual-drift |
| 3 | 0.5% | 42 | — |
| 4 | 0.3% | 39 | — |
| 5 | 0.2% | 30 | — |
| 6 | 0.3% | 43 | — |
| 7 | 0.4% | 33 | — |
| 8 | 0.3% | 51 | — |
| 9 | 0.2% | 78 | — |
| 10 | 0.9% | 10 | visual-drift |

## Issues

- **warn** [slide -] `font-portability` 'Manrope ExtraBold' is a non-system font: recipients need it installed (or build with --embed-fonts, experimental)
- **warn** [slide -] `font-portability` 'Inter' is a non-system font: recipients need it installed (or build with --embed-fonts, experimental)
- **warn** [slide -] `font-portability` 'Inter SemiBold' is a non-system font: recipients need it installed (or build with --embed-fonts, experimental)
- **warn** [slide -] `font-portability` 'Manrope' is a non-system font: recipients need it installed (or build with --embed-fonts, experimental)
- **warn** [slide 2] `visual-drift` 0.3% differ, largest mismatch 31 cells — (224,240 240x48) e7 h2.abs.stmt[data-name="Statement"] "Decks still take a day, and most AI tool"; (192,272 16x16) e7 h2.abs.stmt[data-name="Statement"] "Decks still take a day, and most AI tool". See qa/compare-02.png
- **warn** [slide 10] `visual-drift` 0.9% differ, largest mismatch 41 cells — (432,192 208x80) e94 h2.abs.hero[data-name="Headline"] "Try it on your next deck"; (304,192 112x64) e94 h2.abs.hero[data-name="Headline"] "Try it on your next deck"; (224,176 64x80) e94 h2.abs.hero[data-name="Headline"] "Try it on your next deck". See qa/compare-10.png
