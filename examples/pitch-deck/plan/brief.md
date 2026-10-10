# Brief: Fernway, seed pitch

## Ask
An 11-slide seed pitch for Fernway, a **fictional** startup that builds and runs rooftop greenhouses on top of the grocery stores that sell the produce. It is a Slidekick gallery example, so it has to show native charts (revenue growth, unit economics, market size), a native table, a meaningful Morph transition, tasteful builds, and a strong title and close. Every number is invented but internally consistent, and the deck says so on the closing slide.

## Audience
Seed investors (generalist and climate/food-tech partners) in a 20-minute first meeting, presented on a screen. They know venture maths and have seen vertical-farm decks that burned cash on electricity and warehouses. They care about unit economics, capital intensity, a believable path to scale, and market size.

Objections, and where each is answered:
- "Vertical farms all failed on energy costs." → slide 9, comparison table (sunlight first, LED top-up, no warehouse lease).
- "Will grocers let you on their roof?" → slide 4 (we lease the roof; the grocer pays nothing) and slide 10 (a second chain signs in 2027).
- "Does one roof make money?" → slide 7, unit economics chart.
- "Is the market big enough?" → slide 8, market chart.

Mode: presented (sparse slides; the story lives in the speaker notes).

## The one thing
A grocery roof is profitable farmland: one Fernway roof earns $124k a year and pays back in 26 months, so $6M builds a 20-roof business.

## Facts (all illustrative, invented for this fictional company)
- Leafy greens travel ~1,800 miles and spend ~6 days in transit before the shelf: Fernway market research (illustrative)
- 1 in 7 (14%) leafy greens is thrown away unsold at the store: pilot grocer shrink data (illustrative)
- Typical supermarket roof: 40,000 sq ft, flat, structurally rated, unused: Fernway roof surveys (illustrative)
- Pilot: 3 roofs live on 3 stores of one regional grocer; median harvest-to-shelf time 38 minutes: Fernway ops logs (illustrative)
- Shrink on Fernway greens in pilot stores: 4%, against 14% for trucked greens: pilot grocer data (illustrative)
- Quarterly revenue: Q3 2025 $38k, Q4 $71k, Q1 2026 $118k, Q2 $196k, Q3 $262k → 6.9× in a year; run rate $262k × 4 = $1.05M: Fernway finance (illustrative)
- Per roof per year: 140,000 lb at $2.95/lb = $413k revenue; growing inputs and energy $121k; labour $132k; roof lease and upkeep $36k; contribution $124k (30%): Fernway per-roof model (illustrative)
- Build cost per roof $270k → payback 270 / 124 = 2.18 years ≈ 26 months: Fernway per-roof model (illustrative)
- Market: US grocery spend on leafy greens and herbs $14.8B (TAM); 9,400 suitable roofs in the top 50 metros × $413k = $3.9B (SAM); 2030 target 400 roofs × $413k = $165M: Fernway market analysis (illustrative)
- Plan: 3 roofs (2026) → 9 (2027) → 20 (end of 2028); 20 × $413k = $8.3M run rate: Fernway operating plan (illustrative)
- Raise: $6M seed. Use of funds: roof builds $3.5M (58%), growing team and operations $1.6M (27%), climate-control software $0.9M (15%): Fernway operating plan (illustrative)

## Product in use
Harvest at dawn on the roof → packed in the rooftop pack room → down the store's freight lift → on the shelf 38 minutes later. Shown as a time-stamped process on slide 4 and with the greenhouse photo on slide 5.

## Brand
The Fernway kit in `brand/` was made for this example. Forest #1E3D2C (brand colour, dark grounds, primary data), Paper #F6F0E4 (default ground), Sand #E9DFCC (secondary surface), Terracotta #C2593A (one highlight per slide; text ≥ 24 px or shapes only, because it is 3.9:1 on Paper), Sage #7F9C7A (muted data). Fraunces (display, 600/400) and DM Sans (body, 400/500/700) are both SIL OFL; the files are in `brand/fonts/` with their licences and are installed. The logo is a gable-and-leaf mark plus a Fraunces wordmark converted to paths: the dark lockup goes on Paper, the light lockup on Forest. No template.

## Assets
- `assets/greenhouse-gable.jpg` (slides 1 and 11, cropped by the gable) and `assets/greenhouse-leaves.jpg` (slide 5, tight crop of the leaves): both cut from one photo of a greenhouse interior with rows of lettuce by wei (@chanwei_snap) on Unsplash, Unsplash License. Stand-in imagery for the fictional company (see `plan/SOURCES.md`).
- `brand/assets/*.svg`: Fernway logos, drawn for this example.

## Rubric
- What is it? Rooftop greenhouses run on grocery stores; the produce is sold one floor down.
- Who is it for? Seed investors, first meeting.
- What must they believe? A single roof is profitable, and the model scales without warehouses or grocer capex.
- Strongest evidence? 26-month payback per roof, 6.9× revenue growth, 38 minutes from harvest to shelf.
- Visual hook? The gable: the logo's roof shape crops the photo on the title, and returns as the roofline rule on content slides.
- Real UI or data? Native charts of revenue, per-roof economics and market; a native comparison table.
- Brand rules? Terracotta once per slide and large only; Forest for dark slides; two families.
- What would make them say no? Vertical-farm energy scars and capital intensity, answered on slides 7 and 9.

## Open questions
None for the example. A real deck would add team bios and a cap table.
