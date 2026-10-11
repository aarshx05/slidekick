# Meet Slidekick

The 10-slide launch deck for Slidekick, built by Slidekick from the project's own brand kit (`../demo-brand-kit/`). Every image in it is the tool's own output: the Fernway example's slides, brand board, contact sheet and PowerPoint QA strip, the Edit-mode before/after, and real review scores.

Prompt: `/slidekick a 10-slide launch deck for Slidekick for people who make decks and doubt AI tools that export pictures. Use our brand kit and show real output as proof. End with the install command.`

Download: [deck.pptx](https://raw.githubusercontent.com/aarshx05/aarshx05/main/assets/slidekick/examples/demo-deck/deck.pptx). Decks, templates and PDFs are hosted in [aarshx05/aarshx05](https://github.com/aarshx05/aarshx05/tree/main/assets/slidekick/examples) so the plugin bundle stays text-only.

Rebuild (fetch the template first):

```bash
curl -L -o brand/deck-template.potx https://raw.githubusercontent.com/aarshx05/aarshx05/main/assets/slidekick/examples/demo-deck/brand/deck-template.potx
python ../../skills/slidekick/scripts/deck.py build -p .
```
