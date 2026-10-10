# Step 1 — Source and semantic analysis

Three analyses run side by side: **content** (what is true and worth saying), **brand** (how it must look), and **audience** (who it's for and what they need). Write the results to `plan/brief.md`.

## 1. Content

Read what you were given, in this priority order:

| Input | Read |
|---|---|
| Prompt / brief | the ask, constraints, deadline, any required slides |
| Documents (`.md .pdf .docx .txt`) | claims, numbers, quotes, structure; note page/section for every fact you use |
| Data (`.csv .xlsx .json`) | compute the numbers yourself (python/pandas); keep the series you will chart |
| Code project | README, landing page, routes and key components; find the product **in use**: entry → key action → result |
| Website URL | `deck.py capture <url> --out assets/site.png` (headless browser, dismisses cookie banners, triggers lazy content); read the page copy and meta tags |

Rules:
- Every number on a slide must trace to a source. Record it in the brief as `claim — source`.
- Never invent statistics, quotes, customer logos or testimonials. If the story needs a number you don't have, say so in the brief and leave it out, or ask.
- Don't read or carry secrets (`.env`, keys, tokens, internal hostnames, real customer or personal data). If real UI shows such data, plan to use fictional stand-ins.

## 2. Brand

### Ingest the kit

```bash
python "<skill-dir>/scripts/deck.py" brand <kit-folder-or-files…> -p <out-dir> [--name "Acme"]
```

| Kit item | What is extracted |
|---|---|
| `.potx` / `.pptx` template | theme colour slots (dk1, lt1, dk2, lt2, accent1–6), theme fonts (major/minor), logos and images on the slide masters/layouts. The template becomes the deck's base: its theme travels into the PPTX, and its master graphics are hidden so your canvas controls every pixel |
| `.thmx` theme | colours and fonts |
| Logos (`.svg .png .jpg .webp`) | colours, aspect (wordmark / mark / lockup), light-or-dark variant, transparency |
| Fonts (`.ttf .otf .woff .woff2`) | family, weight, italic, embedding permission; woff/woff2 converted to ttf |
| `tokens.json` / Figma / Style Dictionary | colour and font tokens by name (`primary`, `brand`, `accent` get priority) |
| `.css` / `.html` | CSS custom properties, heading vs body `font-family`, Google Fonts links |
| Guideline PDF | full text in `brand/<name>.txt`, page renders in `brand/pages/`, hex codes, typeface mentions |

Outputs: `brand/brand.json`, `canvas/brand.css` (CSS variables plus `@font-face` for kit fonts), and `brand/brand-board.png`.

### Review — this is your job, not the script's

1. **Look at `brand/brand-board.png`.** Check the right logo, the right primary colour, legible type, and that light/dark logo variants are labelled correctly.
2. If there is a guideline PDF, **read `brand/<name>.txt` and look at the key pages** in `brand/pages/` (colour, logo usage, typography). Record its rules in `brand.json → "rules"`: logo clear space and minimum size, colours that must not be combined, required colour ratios, tone of voice.
3. Fix `brand/brand.json` where the guess is wrong: `theme` slots, `colors.primary`, `fonts.display` / `fonts.body`, logo order. `review.color_candidates` and `review.font_candidates` list everything that was found.
4. Run `deck.py tokens -p <out-dir>` to regenerate `canvas/brand.css`, and `deck.py board -p <out-dir>` to check the board again.

`theme` slots map to PowerPoint's theme. dk1 = main text, lt1 = main background, dk2/lt2 = secondary dark/light, accent1 = primary brand colour, and accent2–6 = supporting colours in order of importance. Colours that exactly match a slot are written as theme colours, so recolouring the theme in PowerPoint recolours the deck.

### Fonts — get them installed

PowerPoint can only render a font that is installed (embedding is experimental). After ingest, `brand.json → fonts.*.installed` tells you:

- **Kit includes the font files** → `deck.py fonts install brand/fonts/*.ttf` (per-user install, no admin).
- **Font is on Google Fonts** → `deck.py fonts fetch "Inter" --weights 400,600,700 --out brand/fonts --install`. This downloads the static TTFs, installs them, and `tokens` then adds `@font-face`.
- **Licensed font you don't have** → tell the user. Choose the closest installed or Google font with them, and record the substitution in `brand.json → rules`.

After installing, run `deck.py tokens` again. QA fails on any font PowerPoint would substitute.

### No brand kit?

- **Project or website** → use its own identity: colours from its CSS custom properties, fonts from its stylesheet, logo from `public/` / `assets/` or the site header. Feed those files to `deck.py brand`.
- **Nothing at all** → pick a restrained palette (one strong accent plus neutrals) and a font pair every recipient has (`Arial` / `Georgia`; `Segoe UI` only if the audience is all-Windows), or a Google pair you fetch with `deck.py fonts fetch "<family>" --install` (then `--embed-fonts` or tell them to install it). Write it into `brand/brand.json` by hand in the same shape, then run `tokens`.

## 3. Audience

Decide and write down:
- **Who** (role, seniority), **what they already know** (novice / practitioner / expert), and **the setting** (board meeting, investor pitch, conference talk, sales call, async read).
- **What they care about** and **their likely objections**. Each objection should be answered on some slide.
- **Mode**: *presented* (sparse slides, the story lives in speaker notes) or *read* (self-explanatory, denser, no notes needed).
- **The one thing** they should think or do afterwards.

## 4. Imagery — show the real thing

In order of preference:
1. **Brand kit / project assets.** Product screenshots, photos and icons the user owns.
2. **Live product.** `deck.py capture <url> --out assets/<name>.png [--width 1440 --height 900] [--selector ".hero"] [--full] [--dark]`. Use `--selector` to grab one component; a 2× scale is the default.
3. **Running the project locally.** Start its dev server and capture the screens that show entry → key action → result.
4. **Licensed external images** (Unsplash/Pexels-style free licences, or the company's press kit): `deck.py fetch <image-url> --out assets --name <name>.jpg --note "<licence>"`. Every fetch and capture is logged to `assets/SOURCES.md`.

Never use an image you can't attribute. Don't use AI-generated people or fake product UI presented as real.

## Write `plan/brief.md`

```markdown
# Brief: <deck title>
## Ask            — what was requested, constraints, length, deadline
## Audience       — who, knowledge, setting, cares about, objections, mode
## The one thing  — what they should think/do afterwards
## Facts          — `claim — source` lines (numbers, quotes, product facts)
## Product in use — entry → key action → result, with the asset for each
## Brand          — palette roles, fonts (installed?), logo choice + usage rules, template?
## Assets         — every image in assets/ with what it shows and where it came from
## Open questions — anything missing that would change the story
```

**Rubric (all must be answered):** What is it? Who is it for? What do they need to believe? What's the strongest evidence? What's the visual hook? What real UI or data will be shown? Which brand rules constrain the design? What would make this audience say no?
