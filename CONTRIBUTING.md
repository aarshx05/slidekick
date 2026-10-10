# Contributing

Thanks for helping make `/slidekick` better! Issues, ideas, new example decks and PRs are all welcome.

## Dev setup

```bash
git clone https://github.com/aarshx05/slidekick && cd slidekick
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r skills/slidekick/scripts/requirements.txt pytest ruff
python -m playwright install chromium                  # skip if Edge or Chrome is installed
python skills/slidekick/scripts/deck.py doctor
```

To test the skill inside your agent while you edit it, point the agent at this checkout. On macOS/Linux, `.claude/skills/slidekick` is already a symlink to `skills/slidekick`. On Windows, use a junction:
`New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\slidekick" -Target "<repo>\skills\slidekick"`.

## Checks

```bash
ruff check .
pytest            # tests marked `powerpoint` run only when PowerPoint is installed
```

CI runs both on Windows, macOS and Linux. If you have PowerPoint, please run `pytest` locally before opening a PR, because the hosted runners can't.

## Where things live

| Path | What |
|---|---|
| `skills/slidekick/SKILL.md` | what the agent follows: Create / Edit / Analyse |
| `skills/slidekick/references/` | step guides, design guide, review rubric, schemas |
| `skills/slidekick/scripts/deckkit/` | the pipeline (extract → compile → render → QA → taste) |
| `skills/slidekick/assets/canvas/` | base stylesheet and the starter deck (the canvas contract) |
| `examples/` | showcase decks, each one rebuildable from its own folder |
| `docs/` | the landing site (GitHub Pages) |

## Guidelines

- **Editable or it doesn't ship.** Never rasterise something that PowerPoint can represent natively.
- Changes to the agent's instructions (`SKILL.md`, `references/`) are product changes. Explain in the PR what behaviour changes and why.
- Keep the skill dependency-light. New Python dependencies go in `requirements.txt`, capped at the next major version.
- Example decks: use fictional brands and content you have the rights to. Clear the author metadata (`--author ""` is the default).
- Update `CHANGELOG.md` and bump `version` in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json` and `plugin.json` together.
