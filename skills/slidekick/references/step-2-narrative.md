# Step 2 — High-IR: the narrative (`plan/narrative.json`)

The narrative is the deck with no slides in it: a sequence of **beats**, where each beat is one message stated as a full sentence. Get the story right here — rearranging beats is cheap, while rearranging finished slides is not.

## Choose the arc

| Arc | Use for | Beats |
|---|---|---|
| Situation → Complication → Resolution | exec updates, decisions, strategy | context · problem/stakes · insight · solution · proof · plan · ask |
| Problem → Solution → Proof → Ask | pitches, sales, funding | hook · problem · solution · how-it-works · proof · comparison · team · ask |
| What → So what → Now what | results reviews, research readouts | headline result · drivers · implications · next steps |
| Before → After → Bridge | product launches, change programmes | today's pain · the new world · how we get there · close |
| Tutorial | teaching, onboarding | agenda · concept · demo · practice · recap |

Adapt the arc to the audience you recorded in the brief:
- **Executives**: lead with the answer (the ask or result in beat 1–2), then support it. Keep it to 3 key points.
- **Investors**: hook, market, traction proof early. Every claim needs a number.
- **Practitioners**: show how it works in detail, use real UI and real data, and pre-empt the objections they'll raise.
- **Mixed / unknown**: plain language, one idea per beat, a recap at the end.

## Beat rules

- `message` is a **sentence with a verb**, written as a takeaway: "Onboarding fell from 9 days to 40 minutes", not "Onboarding results".
- Each beat must earn its place: it answers a question the audience will have at that moment, or one of their recorded objections.
- Each beat needs `evidence` (refs into `sources`/brief facts) unless it is a hook, section or close.
- Size: presented decks ≈ 1 slide per minute. Give each beat `slides: 1` unless it truly needs a sequence (a demo flow, a build-up).
- The **headline test**: read only the beat messages top to bottom. They must form a convincing paragraph. If not, reorder, merge or cut.

## Schema

`references/schemas/narrative.schema.json`. Example:

```json
{
  "title": "Self-serve onboarding: results and rollout",
  "objective": "Leadership approves a company-wide rollout in Q4",
  "audience": {"who": "VP Eng, CFO, Head of People", "knowledge": "mixed", "context": "quarterly business review, 15 min slot",
               "cares_about": ["cost", "time-to-productivity"], "objections": ["Is it worth $180k?", "Will non-engineers use it?"]},
  "mode": "presented",
  "tone": "polished, confident",
  "big_idea": "Self-serve onboarding pays for itself in one quarter, so we should give it to everyone.",
  "arc": "situation-complication-resolution",
  "length": {"slides": 8, "minutes": 12},
  "beats": [
    {"id": "b1", "purpose": "hook", "message": "New hires now ship their first change in 40 minutes, not 9 days."},
    {"id": "b2", "purpose": "problem", "message": "Before, new hires spent their first week searching instead of building.", "evidence": ["s1"]},
    {"id": "b3", "purpose": "solution", "message": "Three moves made onboarding self-serve.", "slides": 1},
    {"id": "b4", "purpose": "proof", "message": "Ramp time fell 93% and satisfaction rose to 4.7/5.", "evidence": ["s2"]},
    {"id": "b5", "purpose": "ask", "message": "A company-wide rollout costs $180k and pays back in one quarter.", "evidence": ["s3"]}
  ],
  "sources": [{"id": "s1", "ref": "survey-2026-03.pdf p.4"}, {"id": "s2", "ref": "telemetry.csv"}, {"id": "s3", "ref": "budget.xlsx"}]
}
```

Then run:

```bash
python "<skill-dir>/scripts/deck.py" validate <out-dir>/plan/narrative.json
```
