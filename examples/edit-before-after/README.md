# Edit mode: Q3 review → Q4 review

`before.pptx` is an ordinary Office-theme "Q3 Business Review" for a fictional retailer. Slidekick's Edit mode turned it into `after.pptx`, the Q4 review, in place: it updated the numbers, the chart data and the tables, rewrote label headlines as takeaways, restyled the callout's accent to the theme's navy, duplicated the regional table slide into a channel slide, and imported two redesigned slides (built in `new-slides/` from the deck's own template). `inspect/` holds the outlines whose shape ids `edits.json` refers to.

Prompt: `/slidekick update before.pptx to Q4: new numbers, chart and table data, takeaway headlines, and add a channel breakdown slide.`

Download: [before.pptx](https://raw.githubusercontent.com/aarshx05/aarshx05/main/assets/slidekick/examples/edit-before-after/before.pptx), [after.pptx](https://raw.githubusercontent.com/aarshx05/aarshx05/main/assets/slidekick/examples/edit-before-after/after.pptx) and the imported slides, [new-slides/deck.pptx](https://raw.githubusercontent.com/aarshx05/aarshx05/main/assets/slidekick/examples/edit-before-after/new-slides/deck.pptx). Decks are hosted in [aarshx05/aarshx05](https://github.com/aarshx05/aarshx05/tree/main/assets/slidekick/examples) so the plugin bundle stays text-only.

Rebuild (fetch the inputs first):

```bash
curl -L -o before.pptx https://raw.githubusercontent.com/aarshx05/aarshx05/main/assets/slidekick/examples/edit-before-after/before.pptx
curl -L -o new-slides/deck.pptx https://raw.githubusercontent.com/aarshx05/aarshx05/main/assets/slidekick/examples/edit-before-after/new-slides/deck.pptx
python ../../skills/slidekick/scripts/deck.py edit before.pptx edits.json --out after.pptx
```

To change the two imported slides, run `python ../../skills/slidekick/scripts/deck.py build -p new-slides` before the edit.
