# Edit mode: Q3 review → Q4 review

`before.pptx` is an ordinary Office-theme "Q3 Business Review" for a fictional retailer. Slidekick's Edit mode turned it into `after.pptx`, the Q4 review, in place: it updated the numbers, the chart data and the tables, rewrote label headlines as takeaways, restyled the callout's accent to the theme's navy, duplicated the regional table slide into a channel slide, and imported two redesigned slides (built in `new-slides/` from the deck's own template). `inspect/` holds the outlines whose shape ids `edits.json` refers to.

Prompt: `/slidekick update before.pptx to Q4: new numbers, chart and table data, takeaway headlines, and add a channel breakdown slide.`

Rebuild: `python ../../skills/slidekick/scripts/deck.py edit before.pptx edits.json --out after.pptx` (to change the two imported slides, first run `python ../../skills/slidekick/scripts/deck.py build -p new-slides`).
