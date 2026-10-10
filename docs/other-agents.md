# Using /slidekick with other agents

`/slidekick` is a standard [Agent Skill](https://agentskills.io): a folder containing a `SKILL.md`, plus references and scripts. Any agent that can read files and run Python can use it.

## Agents that discover skills automatically

| Agent | Where it looks |
|---|---|
| Claude Code | the plugin (`/plugin install slidekick@slidekick`), or `.claude/skills/slidekick/` / `~/.claude/skills/slidekick/` |
| Codex CLI | the plugin (`codex plugin add slidekick@slidekick`), or `.agents/skills/slidekick/` |
| opencode | `.opencode/skills/slidekick/` |
| Google Antigravity | `.agents/skills/slidekick/` in a project, or `~/.gemini/config/skills/slidekick/` |
| Cursor, Copilot, Gemini CLI and more | `npx skills add https://github.com/aarshx05/slidekick --skill slidekick` |

## Anything else

Copy `skills/slidekick/` somewhere permanent, then add this to the agent's custom instructions or rules file:

> When asked to make, edit, review or summarise a presentation / slides / deck / .pptx, read and follow `<path>/deck/SKILL.md`. Run its tools with `python "<path>/deck/scripts/deck.py" …`.

## Requirements

- Python 3.10+. The first run sets up a private environment automatically.
- Edge, Chrome or Playwright's Chromium.
- For QA: PowerPoint (Windows, or Mac in beta) for ground-truth renders, or LibreOffice as an approximation.
- The design review step (Step 5b) uses a fresh-eyes subagent. If your agent can't spawn subagents, it does the review itself in a fresh pass over the rendered contact sheet.
