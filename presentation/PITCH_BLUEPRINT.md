# Pitch blueprint: Johan's way out (5 minutes, 5 slides)

## Current visual implementation (30 October 2026)

This section supersedes the original dark-theme layout and delivery notes below.

- White background, navy Segoe UI text, restrained EU-blue emphasis, original-colour FARI/JRC artwork at bottom left, and numbered title tags at top right.
- Slide 1 has four builds: Johan without the house, his three questions, 29% not warned in Rhineland-Palatinate, then separate 85% and 46% grids among warned respondents across both states. These are independently normalised shares, not inferred overlapping groups of 60 and 33 people.
- Slide 2 uses open editorial columns with one-time connector/diagram reveals.
- Slide 3 uses the transparent 1244 by 894 road SVG and its fitted overlay coordinates. Road stress retains its source semantics. Trip times are labelled as free-flow model estimates; the closed-road check concerns the driving network.
- Slide 4 remains the teammate-owned demo. Its content and interaction logic have not been redesigned.
- Slide 5 uses restrained artwork, a light Europe map and a flat closing layout. Existing impact estimates retain their team-brief qualification.
- Motion uses short crossfades and small lifts. Static and reduced-motion modes show completed states without animation.
- `build_single.py` embeds the exact map named by `pitch-data.js` and both organiser logos. No external fonts or runtime dependencies are needed.

See README.md for build commands, QA_REPORT.md for final checks, and the source files for the current layouts. The sections below retain the original planning and evidence context.

## Original planning record

Checkpoint 1 of the 10-agent build. Wave 1 (agents 1-5: discovery) ran in the main session on 30 Oct 2026; its findings are below. Waves 2-3 (agents 6-10) build against the contract in sections 5-7. Story spine: `powerpoint/Pitch deck.pptx` (Johan). Policy brief: *The Missing Link: Mending the Flood Warning Chain* (team version of 29 Oct, pasted in chat). Not used: `deliverables/` (another deliverable).

## 1. Johan (agent 1, from `Pitch deck.pptx`)
- Johan is 11, fictional, in a yellow raincoat (his signature colour, so his route is EU gold). Say once that he stands for residents of flood-prone streets; give him no real historical experiences.
- Arc in the deck: Meet Johan → the night of 14-15 July 2021 → the warning chain broke → three questions (*Am I in danger? How serious is it? Where should I go?*) → NAVIGATE (tool) + PREPARE (drills) → "Next time, Johan knows what to do and where to go."
- Illustrations copied to `assets/johan/`: `johan-home.png` (by his house and the river), `johan-night.png` (house at night, rain), `johan-thinking.png`, `johan-phone.png` (reads the alert, relieved), `johan-shelter.png` (walks with his phone to a shelter on a hill). Alt texts are in the pptx.
- This deck places Johan in **Bad Neuenahr-Ahrweiler** because the map screenshot shows that town. `policy-tool/DEMO.md` puts him in Gemünd: align the spoken line before presenting.

## 2. The routing engine (agent 2, from git)
Latest pushes (fetched 30 Oct 11:15): `origin/team1-smart-shelter-map` f266dec (11:09), bundle last changed in **01abbb0** (10:56, generated 2026-10-30 09:46 UTC); `origin/feature/alert-route-message` 53a9406 (11:12, alert as plain 2G cell-broadcast text in iOS style).

How the Smart Shelter System routes (`ideas/05-smart-shelter-map/pipeline/research/20_tool_pipeline.py`, `lib/challenge/*.py`):
1. **Flood → closed roads.** A road is closed if it touches the mapped July 2021 flood (Copernicus EMS EMSR517, flood + traces) or lies under modelled water (EFAS 10/100/500-year).
2. **Residents → zones.** GHS-POP 2020 residents inside the flood (modelled estimate), on 500 m zones.
3. **Match.** Each zone is matched to candidate buildings from OpenStreetMap that still have room (capacity = floor area × usable share ÷ m² per person; set A: core public buildings, 5 m²; set B: core + extended, 3.5 m²), considering the 200 fastest within 1 h.
4. **Route.** Walk (4 km/h) to the nearest open road, then the fastest path on open roads (free-flow speed per road class). Every route is checked: no closed road.
5. **Road stress.** People on each road → vehicles per hour (80% by car, 2 per car, 2 h window) ÷ an assumed capacity per road class. **An indicator, not a forecast, and not fed back into the routes.**

So the engine routes around flooded (closed) roads and respects shelter capacity. It does **not** simulate traffic or reroute around jams; it flags overloaded roads.

## 3. The screenshot (agent 3)
`powerpoint/visualisation busy roates + flooded areas.png`: 1524 × 919 px (aspect 1.658), a Leaflet view of the tool's full-analysis map, Bad Neuenahr-Ahrweiler, July 2021 flood, set A. Legend from the page source: blue = mapped flood; black/white dashes = closed road; green/yellow/orange/dark red = stress < 0.5 / 0.5-1 / 1-1.5 / > 1.5; magenta = candidate buildings used (numbers = merged buildings); dashed violet = edge of the area mapped in 2021. Leaflet UI to hide: zoom buttons (x 28-70, y 18-100), "Legend" button and attribution (x 1380-1500, y 825-898); frame border: crop l 14, t 4, r 21, b 21.

Georeference (`fit_screenshot.py` → `georef.json`): px = (x − X0)·s, py = (Y0 − y)·s in EPSG:3857, s = 0.09998 px per metre (effective zoom 13.93). Check image `figures/generated/pitch/georef_check.png`: the bundle's 1-px roads land on the coloured roads. All overlay coordinates in `pitch-data.js` are in these PNG pixels. **A replacement SVG must show the same view at the same aspect ratio**, or rerun the fit on a PNG export of it.

## 4. Brand (agent 4)
The organiser is **FARI** (AI for the Common Good Institute, Brussels), not "FAIR". No FARI or JRC logo files exist in the repo or in the Annex 6 template. Official EC logos are not fetched from the web (use is restricted). The deck uses a typographic lockup and loads `assets/logos/fari.svg|png` and `assets/logos/jrc.svg|png` automatically if the organisers' files are dropped there. Colours: EU blue `#003399`, EU gold `#FFCC00`, slate night surfaces. `assets/europe.png` (2500 × 2166) is the Europe map from the Annex 6 template; the Ahr valley is at about (33.0 %, 58.9 %) of it, ±10 px.

## 5. Stack and file ownership (agent 5)
Plain HTML, CSS and JS, no build step and no CDN code, so it runs offline from `file://` (fonts: Inter and JetBrains Mono from Google Fonts with system fallbacks). Open `presentation/index.html`, press F for full screen.

| File | Owner | Notes |
|---|---|---|
| `index.html`, `css/deck.css`, `js/deck.js` | main (agent 5) | frozen in wave 2 |
| `pitch-data.js` | `build_pitch_data.py` | never hand-edit; `window.PITCH` |
| `css/brand.css`, `slides/s1-johan.js/.css`, `slides/s5-europe.js/.css` | agent 6 | |
| `slides/s2-pipeline.js/.css`, `slides/s3-map.js/.css` | agent 7 | |
| `slides/s4-policy.js/.css` | agent 8 | |
| `css/motion.css`, `js/motion.js`, any file | agent 9 | wave 3, alone |
| any file, `QA_REPORT.md` | agent 10 | wave 3, after 9 |

Slide API (`js/deck.js`): `Deck.register({id, order, steps, time:[start,end], notes, html, mount(el, P), step(el, n, dir), enter(el), leave(el)})`. The engine adds `.is-active` and cumulative classes `.s1 … .s6` (`.sK` while step ≥ K) and `data-step`. Any element with `data-b="K"` builds in at step K (`data-b-out="K"` leaves at K). Utilities: `Deck.tick(el, value, {decimals, suffix, duration})`, `Deck.draw(path, {duration, delay})`, `Deck.fmt(n, d)`, `Deck.onKey(fn)` (only while the slide is active), `Deck.mapSrc(img)` (base map: SVG first, PNG fallback), `Deck.SPRING`, `Deck.reduced`. Stage: 1920 × 1080, scaled to fit; safe margins 96 px left/right; brand lockup top-right (y 28-76); pace bar = bottom 4 px; source captions at y ≥ 1020 in `.src` (mono, 15 px).

Keys: Space, →, PageDown, Enter = next; ←, PageUp, Backspace = back; Home/End; F full screen; N speaker notes and timer; T restart the 5-minute clock; on slide 4: 1-4 flood level, B shelter buildings. `#3.2` in the URL opens slide 3, step 2 (used for screenshots).

## 6. Design tokens (in `css/deck.css`)
Fonts `--font` (Inter, SF Pro Display, Segoe UI Variable Display, system-ui), headlines `letter-spacing: -0.03em`; `--mono` (JetBrains Mono, Cascadia Mono, Consolas). Surfaces `--bg #070B16`, `--surface #0A1020`, glass `--glass rgba(10,16,32,.66)` + 1 px `rgba(255,255,255,.12)` + blur 18 px. Ink `--ink #F5F7FB`, `--ink-2` 74 %, `--ink-3` 52 %. Johan and his route: `--gold #FFCC00`. Map semantics copied from the tool: `--flood #56B4E9`, `--flood-line #0072B2`, `--closed #111`, stress `#009E73 #F0E442 #D55E00 #7A0019`, buildings `#C2185B`. Chart (validated by the dataviz checker on `#0A1020`: lightness, chroma, CVD, contrast all pass): within 30 min `--ok #1E9C6E`, over 30 min `--slow #CF7F12`, no place `--none #E0455E`, always with text labels. Motion `--spring cubic-bezier(0.16, 1, 0.3, 1)`, 700 ms builds, 750 ms phone; only `transform` and `opacity` animate; `prefers-reduced-motion` shortens everything.
No purple or magenta gradients, no icon-card rows, no default browser sliders, ≤ 20 words visible per build (source captions excepted).

## 7. Storyboard (5:00)
Numbers come from `window.PITCH` (paths given); never type them by hand.

**Slide 1 · 0:00-0:45 · Meet Johan** (steps 3). 0: `johan-home.png`; "Meet Johan." / "11 · Bad Neuenahr-Ahrweiler · July 2021"; micro "Fictional character". 1: crossfade to `johan-night.png`; "The water came at night." / **85 %** "of those warned didn't expect severe flooding" / **46 %** "didn't know what to do"; src "Thieken et al. 2023, NHESS 23, 973-990 · online survey, n = 1,315, NRW and Rhineland-Palatinate". 2: `johan-thinking.png`; 01 "Am I in danger?" 02 "How serious is it?" 03 "Where should I go?" (03 in gold).
Say: "Johan doesn't need a generic alert. He needs to know where to go, and which road out is open."

**Slide 2 · 0:45-1:30 · How it works** (steps 3). Title "From flood map to one clear message." Three lenses on one line, joined by gold pulses: (1) **Flood + roads**: a circular crop of the screenshot around `P.callouts.flood.px`, sub "closed roads", src "Copernicus EMS · EFAS · OpenStreetMap"; (2) **Match + route**: homes → buildings with a capacity fill, sub "a shelter with room", src "GHS-POP · building capacity · open roads"; (3) **Johan's alert**: a phone with three lines 1-2-3, sub "three answers, plain text", src "Cell Broadcast · works on 2G". Footer micro: "Supports, and does not replace, official warnings and evacuation decisions." Never call the engine "AI", and never say it balances traffic.

**Slide 3 · 1:30-2:45 · The map** (steps 4). The screenshot at native size (no upscaling at 1080p), cropped, with an overlay SVG `viewBox="14 4 1489 894"`. Title "Streets close. Exits overload." 1: glass pins: flood at `P.callouts.flood.px`, "`closed_km_town` km of streets closed"; jam at `P.callouts.jam.px`, "3.8× road capacity", mono "Johannisstraße · model"; Johan at `P.callouts.home.px` (gold, pulsing). 2: route A (`P.johan.plans['obs2021|any|restrictive'].overlay.path`, white, dark casing, drawn in) leaves the frame at the bottom: label "Polch · 28 min"; HUD (3 tiles): *Johan's trip* 28.2 min · *Flooded roads on his route* 0 · *Town residents sent to other districts* `P.plans[key].town.outside` (8,645); chip "Core public buildings only". 3: route A fades to a ghost, route B (`…|generous`) draws in gold with a glow to the kindergarten pin (`overlay.shelter_px`); HUD ticks to 2.4 min · 0 · 0; chip "+ Extended buildings". src: "Smart Shelter System, bundle 2026-10-30 09:46 UTC (commit 01abbb0) · flood: Copernicus EMS EMSR517 · residents: GHS-POP 2020 estimate · roads © OpenStreetMap contributors · capacities, car share and speeds are assumptions; stress is an indicator, not a forecast".

**Slide 4 · 2:45-4:15 · Decide before the night** (steps 2). Left 60 %: two custom sliders, *Flood level* (2021 mapped · 10-yr · 100-yr · 500-yr model) and *Shelter buildings* (Core public · + Extended); KPI "% reach a shelter within 30 min" = `within30 / to_place`; one stacked bar (within 30 min / over 30 min / no place), scaled to the largest `to_place`, 2 px gaps, legend with numbers; mono telemetry "roads over capacity · mean trip · no place". Right 40 %: at step 1 the iPhone slides in (`translate3d(120%,0,0)` → 0, 750 ms spring) with Johan's alert in the team's iOS cell-broadcast style (2G, "Demo message, not a real alert"), plus an ETA chip (total, walk, drive). Plans: `P.plans[level|closure|set]`, Johan: `P.johan.plans[…]`.
Alert copy: "Flood danger: {as in July 2021 | a 1-in-10/100/500-year flood}. {street} is in the flood area." / "Leave now. Go to: {shelter title}, {where}{, town if not Bad Neuenahr-Ahrweiler}." / "Walk {walk} min to the nearest open road, then {drive} min by car via {via without his street, max 2}." / "This route avoids flooded roads."
Key numbers: 2021 A → B: within 30 min 77.9 % → 99.4 %, Johan 28.2 → 2.4 min; 500-year A → B: no place 4,694 → 3, Johan 60.9 → 3.2 min.

**Slide 5 · 4:15-5:00 · Every valley in Europe** (steps 3). 0: `johan-shelter.png`, "Next time, Johan knows where to go." 1: zoom out to `europe.png` (tinted for the dark stage), gold pin at the Ahr; three numbers from the team brief: "~230 lives lost" and "€32-53 bn damage" (July 2021, BE·DE·NL; brief refs [2], [9], [20]) and "~10× return on early warning" (WMO 2022, ref [24]); line "Built only on open EU-wide data: Copernicus EMS · EFAS · GHSL · OpenStreetMap". 2: "To crisis authorities in BE · DE · NL:" 1 "Designate and publish flood shelters." 2 "Make every alert answer three questions." 3 "Drill the route at school." Then the large lockup.

## 8. Claims
May say (source → check): 25,559 residents inside the 2021 flood in Kreis Euskirchen + Landkreis Ahrweiler, all placed within 1 h in both sets; over 30 min 5,639 (A) vs 159 (B); 500-year: no place 4,694 (A) vs 3 (B); Bad Neuenahr-Ahrweiler: 14,842 residents in the 2021 flood, 8,645 sent to other districts under A, 0 under B; 71 km of its roads touch the 2021 flood; Johannisstraße carries 3,830 routed people = 3.8× an assumed 200 vehicles/h; Johan: Polch school 28.2 min / 37 km (A) vs kindergarten Vehner Weg 7, 2.4 min / 0.5 km (B), no closed road on either route. All from the bundle via `build_pitch_data.py` (52 checks). Thieken et al. 2023 figures checked against the abstract on 30 Oct.
Must not say: live or real-time data; traffic simulation; routing around jams; "AI engine"; designated, official or verified-safe shelters or routes; set A and B as lower and upper bounds (they are alternative assumption sets); that Johan is real. Taken from the team brief and not re-checked here: ~230 deaths, €32-53 bn, ×10 return, Japan's shelter law.

## 9. Open before presenting
1. Johan's town: Bad Neuenahr-Ahrweiler here, Gemünd in `policy-tool/DEMO.md`.
2. Drop official FARI and JRC logo files into `assets/logos/` if the organisers provided them.
3. The brief names no single public actor; slide 5 addresses "crisis authorities in BE · DE · NL".
4. Rebuild after a new bundle: `python presentation/build_pitch_data.py` (and `fit_screenshot.py` if the screenshot changes).
