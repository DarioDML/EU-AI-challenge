# Policy tool plan: "Smart Shelter System" (DRAFT, 2026-10-29)

## 0. Three profiles (user decision 2026-10-29 evening; supersedes the what-if and citizen-stretch parts below)
Scope: only the interactive map is worked on now. One page, one bundle, three profiles chosen by a switch in the header (`?profile=citizen|municipality|full`). Each profile shows only what its user needs; the numbers come from the same precomputed plans, so the three never disagree. MVP = proof of concept of the basic flow, not a finished product. Task items: `BACKLOG.md` B13-B34.

Read this plan with the build (note 2026-10-30): the page is static. It switches between precomputed results (flood level, closure rule, capacity set, population year); there is no live recompute and no click-to-close road or shelter. Sections 3, 4, 7 and 8 below are marked STALE where they still describe that; `README.md` describes what exists.

| | Citizen | Municipality | Full analysis (current page) |
|---|---|---|---|
| Question | Where do I go and how? What do I prepare now? | What happens to the people of the areas I am responsible for? | How was it computed, and how do assumptions move it? |
| Input | street name (search, offline) then a tap on the map near home; or tap directly | hover a municipality (highlight), click to pick, "Add" / "Remove" to build a list | all selectors (flood level, closure rule, capacity set, population year) |
| Output | building (OSM name, else street, else nearest named road), route as steps (walk to the open road, then street names), walk + drive time, up to 2 more buildings; a "prepare now" panel | for the list: residents in the flood (rounded, minimum), placed within 1 h, not placed, within 2 km, over 30 min, shelters used and how full, the largest destination municipalities with their share, people sent outside the two districts, people outside the 2021 map, closed roads touching the area | everything (cards, layers, legend, compare tables, CSV, messages) |
| Hidden | every selector, model terms, cards | closure rule, capacity set, population year (fixed and stated in one line), model terms | nothing |
| Fixed setting | observed 2021 flood, Set A, 2020 residents (one line says so); optional toggle "2021 flood / extreme (500-year model)" | flood level selector only; Set A, 2020, "closed if it touches the flood" | user chooses |

Data rules that hold in every profile (user decisions 2026-10-30):
- **Coverage of the July 2021 map.** The EMS map covers only the requested areas of interest; the Rhine banks between Remagen and Bad Breisig lie outside, while the river model floods them (people outside the 2021 map: 0 / 4,810 / 10,652 / 13,763 at 2021 / 10 / 100 / 500 years). Show every level in full, draw the edge of the 2021 mapped area at every level, and compare 2021 with the model only inside it. Wording outside it: citizen "Our July 2021 flood map does not cover this area yet. We are working on adding more data for it. Until then, follow official warnings." (plus "In a rare, large river flood (model), this area could flood." where the model floods it); municipality row "July 2021 data not yet available: we are working on it" with a † line naming the places, never 0; full analysis "not assessed in July 2021" and "N outside the 2021 map" on the People card. "Working on it" must stay true: a backlog item with leads (Länder flood hazard maps, other 2021 mappings), verified before use, and labelled "planned" in the brief. Same pattern for streams the river model misses (Kall): "the river model does not include this stream yet".
- **Shelter rule.** A building is used only if it is dry in EVERY flood map we have (2021 footprint not touching the flood or trace, centre dry at 10, 100 and 500 years; `DRY_IN_ALL_MAPS` in the pipeline). Reason: each map misses places the other floods (before the rule, the 2021 plan sent 1,234 people to buildings the 10-year model floods, the model plans about 2,600 to buildings flooded in 2021).

Design rules (honesty traps):
- Citizen location: street search works to street level, not house number (no geocoder offline; OSM street names keyed by name + municipality). A street lists the areas it crosses (`streets[].areas`, from all its edges): one area opens it, several are lettered on the map and in the list; a street wet in 2021 without residents says so.
- Outside every area inside the 2021 map: "This spot is not inside the 2021 flood in our data. This does not mean there is no risk: smaller streams are missing from our data. Follow official warnings." Outside the 2021 map: the coverage wording above. Never "safe".
- A shared area (at most 3 buildings): "Your area is shared over N buildings in this plan", building 1 = the largest share, the others with their share; never "reserved", never "go to the nearest one", never "your shelter"; "candidate building, not an officially designated shelter". A far building gets "Why so far? ... there is room within 1 hour by road, but not enough close by."
- People without a building in the citizen plan (`unassigned_reason` "plan_rule"): "This simple plan (one building per area) finds no building for about N residents of your area. The full analysis finds room for everyone within 1 hour by road; follow official instructions on the day." Never "no room".
- Prepare panel: a short example list labelled "example, to be checked against the official civil-protection checklist (BBK)"; logged as AI-drafted; a person verifies it before it is cited.
- Municipality: areas are official municipality boundaries (GISCO LAU 2024, simplified); a municipality with nobody in the flood shows "0 in the modelled flood" (model levels) or "0 in the mapped July 2021 flood" (2021, inside the mapped area only; outside it the coverage wording above), never "safe". In Rhineland-Palatinate an LAU is an Ortsgemeinde; the planning body may be the Verbandsgemeinde or the district: the competent actor is NOT named until verified (open).
- Every profile keeps one line: "Planning exercise, not live guidance. Counts are modelled minimums."

Data additions (pipeline `20_tool_pipeline.py`, one regenerate): `streets` (unique name + municipality from the full road graph, a few points each, UTF-8), `munis` (simplified LAU polygons of DEA28 + DEB12 with LAU id), `zones[].lau` (LAU id of the zone point). The 2020 numbers must stay unchanged and all pipeline checks pass.

Citizen v2 (user decision 2026-10-29, B25; replaces the tap-a-spot answer and the "split over N buildings" wording): every flooded area has ONE building and ONE route. Plan: a separate citizen plan of the July 2021 flood (Set A, 2020 residents) where each 250 m cell goes to exactly one candidate building (single-assignment, capacity-limited, minimum person-time, solved as a MILP with HiGHS; unassigned allowed at a penalty). Areas = connected 250 m cells with the same building AND the same first open-road node, so the road route is literally the same; the walk to that road is shown as a range. Cells that cannot go whole to one building within 1 h (12 cells, about 4,390 residents in the data; only 3 are larger than the largest building) are shared over at most 3 buildings and say so (B34, done in the data 2026-10-30; page wording written 2026-10-30 09:30, build NOT yet tested); in this simpler plan 969 of their residents get no named building after the shelter rule (767 before it; `unassigned_reason` "plan_rule"), while the main plan places everyone. The citizen hovers an area (highlight, tooltip with its building) and clicks it (building, route, time); street search selects the area it crosses or lists them. Layout: full-width map, floating card on the left (search, answer, map key, collapsed "Prepare now"). One story: the full analysis offers this plan as a second method ("one building per area") next to the optimised split plan (B23), and the municipality view states which plan the citizen view uses. Checks: tiny known-answer case, conservation, capacity, one building per cell, no route through a closed road, solver status and gap recorded, doubled candidate list.

Citizen, next step (B22, after the 2021 MVP; partly overtaken 2026-10-30: since the shelter rule every destination is dry in all maps by construction, so only parts (1) and (2) below remain, and the counts below are from before the rule): one answer for any flood, no scenario choice. Problem: the 2021 plan and the modelled plans differ (only 16 of 125 zones flooded in both keep the same main destination) and the model misses Kall and the Ahr (e.g. zone 55 Kall: 557 residents in 2021, 0 in every modelled map), so one narrow scenario is not enough for "where do I go". Design: (1) status of the home in plain words: "flooded in July 2021" / "could flood in a rare, very large flood (model)" / "not inside any flood in our data; this does not mean no risk"; (2) the plan of the largest flood that reaches the home (2021 if flooded then, else the 500-, 100-, 10-year model); (3) from that plan's destinations for the zone, the largest one whose building is dry in ALL flood maps (2021 and models), with its route and a "Why this building? It stayed dry in 2021 and in all modelled floods, and it has room in this plan" line. Feasibility (bundle check): 2,768 of 3,144 candidates are dry in all maps; for 313 of 341 flooded zones the main destination already is; 5 more have one among their other destinations; 5 zones (about 80 people) have none and 18 (about 2,700, mostly the 500-year model) have no place in the plan: those get an explicit "no building in this plan; follow official instructions" message. These feasibility counts are zone-based (2026-10-29) and are to recheck for areas. **Needs a pipeline step (updated 2026-10-30, was "page-only"):** since Citizen v2 the citizen view answers per area from `citizen_plan`, which exists only for the 2021 flood (`citizen_plan.key` = `obs2021|any|restrictive`), so a citizen plan per modelled level must be computed first. Acceptance (area terms): an area in Kall (zone 55) gives the same building as the 2021 answer (if dry in all maps); a Rhine area dry in 2021 but wet in the 500-year model gets the "could flood in a rare, very large flood" status and a building dry in all maps.

Acceptance (current, Citizen v2): citizen: clicking an area, or picking a street that crosses one area, gives one building with its route and time from `citizen_plan`; a street that crosses several areas lists them to choose from; a place outside every area gives the "not inside the flood in our data" wording inside the 2021 map and the coverage wording outside it (test: a street in Remagen); a shared area shows no "reserved"; no "safe" anywhere. (History, MVP of 2026-10-29: "a known street + tap gives the zone's top destination from the bundle".) Municipality: selecting Kall sums its zones (1,847, shown about 1,800); Remagen at the 2021 level shows "July 2021 data not yet available" (never 0) and at the 100-year level the "outside the 2021 map" line; Add then Remove leaves an empty list. Full: all existing checks pass; the edge of the 2021 mapped area is drawn and in the legend at every level.

Status: a design proposal from the user's brainstorm plus AI additions and pushbacks. User decisions are dated where they appear (profiles 2026-10-29; coverage wording and shelter rule 2026-10-30); everything else, and every number, is to recheck against the live bundle. Every number that is an assumption is marked `ASSUMPTION`; a named actor is a placeholder until the Researchers verify its role from an official source. Cut features from the bottom of each list (cut line in section 4). Concept presentation is due end of Day 1; freeze about 11:30 on Day 2; deadline 13:30 (sent by the team).

## 1. Purpose in one sentence (2026-10-29 aim; what was built: section 0)
Let a crisis authority (and, as a stretch, a citizen) see, for a chosen flood level, **which area should go to which shelter, by which route, with shelter capacity, road closures and road load taken into account**, and turn the result into training scenarios and draft emergency messages.

The four format questions of Annex 4 (draft answers for the team to own; rewritten 2026-10-30 for the tool as built):
1. *Single action:* pick your area (citizen) or your municipality (municipality view) and read where people go, how long it takes and what happens to them; the full analysis exports the area-to-building table as CSV.
2. *What it does that a brief cannot:* it switches between precomputed flood levels (July 2021 and modelled 10-, 100-, 500-year floods), road-closure rules, capacity sets and population years and shows on the map how the answer moves for each area and building. It does not recompute live.
3. *Fit to the message (claim C4.3):* "For the July 2021 flood in Kreis Euskirchen and Landkreis Ahrweiler, under cautious assumptions, there is room for everyone within an hour by road, but not enough room close by: only about 9% fit within 2 km." (Still true after the shelter rule for "room for everyone within 1 h"; recheck the tool-side 2 km figures in C4.3 against the new bundle. Add one sentence on the coverage gap: at the 100-year level 43 % of the people live where the July 2021 map did not look.)
4. *Understood in under a minute:* three views for three users (citizen, municipality, full analysis); the citizen and municipality views show one map, one click and plain words, with the model settings hidden.

(History, 2026-10-29 draft: answer 2 said "it recomputes the plan when the flood level, a road or a shelter changes" and answer 4 "one map, one slider (flood level), one click"; neither was built.)

## 2. Users and named actor
- **Primary: the planning and exercise officer of a crisis staff** (zone-to-shelter planning, training scenarios). Named actor: `[crisis-management authority of the chosen area, to be verified from an official source]`.
- **Secondary (stretch): a citizen** looks up their zone and gets shelter, route and a short message.
- Push back: a citizen-facing tool implies operational advice. Our data are a 2021 snapshot, OSM of 2026 and unverified assumptions, so the tool must say "planning aid, not live guidance" on every screen. Authority-first is the defensible position; citizen view stays a demo mode.

## 3. What the user sees (flow) [STALE: see section 0; item 5 what-if was not built]
1. **Map** (pan, zoom) with a **flood-level selector**: observed 2021 (EMS), 10-, 100-, 500-year (EFAS modelled depth), plus a depth threshold for "road not passable" (ASSUMPTION, to verify).
2. **Layers:** population (our ~1 km grid and dasymetric building dots, shaded by residents exposed at that flood level); shelters as typed symbols sized by capacity (school, sports hall, community or civic, other; colour = safe, flooded, full); road network with closed roads in red; chosen routes; road load in green-yellow-red.
3. **Click a zone** -> side panel: residents to place, assigned shelter(s), route, travel time, a warning if the main road is closed, and the detour cost in minutes.
4. **Click a shelter** -> capacity, load (% full), zones assigned, status (candidate, not officially designated).
5. **What-if (training mode):** close a road, close a shelter, change the flood level; the plan recomputes.
6. **Message panel:** a fixed-template draft message per zone in German, French, Dutch and English (cell-broadcast style, short), to be reviewed by a person; exportable table (CSV) for the exercise.

## 4. Features, with a cut line (MoSCoW) [STALE: see section 0; click-to-close what-if was not built]
**Must (the demo fails without these)**
- Flood-level selector with at least 2 levels (observed 2021 and one EFAS return period); the exposed population changes with it.
- Shelters (typed, with an assumed capacity), population shading, closed-road display.
- Zone -> shelter assignment that respects capacity, with a route per zone that avoids closed roads.
- Honest legend: assumptions, "not live", date of the data.

**Should**
- All four flood levels; the 'details' panel with the assumptions and their swing (Q3 reach curve).
- Road load as a stress indicator (people per road segment turned into vehicles, compared with an assumed road capacity).
- Draft messages from templates; CSV export; click-to-close road or shelter (what-if).

**Could (cut first)**
- Citizen address lookup; walking versus driving split; evacuation time curve over hours; hospital and care-home special flags with transport; vertical evacuation layer (tall buildings); multi-language polish beyond German and English; PDF export.

**Won't (say so in the brief)**
- A real traffic simulation, live data, and any statement that a shelter is officially designated or safe.

## 5. Data: what we have, what we need
| Need | Have now | Gap and action |
|---|---|---|
| Flood levels | EMS 2021 extent and trace (all AOIs); EFAS depth for RP10, 100, 500 in the bucket (`lib/challenge/efas.py` reads windows) | EFAS is modelled, empty cells mean "not modelled" (small rivers are missing) and the 500-year map is a ceiling that 2021 exceeded in places; never treat empty as dry. The two maps cover different places: EMS only its areas of interest (Rhine banks outside), EFAS only its river network (Kall streams outside); see the data rules in section 0 (`meta.ems_coverage`, `zones[].in_ems_area`). |
| Population | GHS-POP ~1 km cells; dasymetric per building; exposed per scenario computable with existing code | Recompute exposed residents per EFAS level (existing functions). A true "raster" is the 1 km grid: say so. |
| Shelters | OSM candidates (German extracts retrieved; Belgian and Dutch extracts also in the card) with footprint; assumed capacity (Q3 method) | Names and shelter status are not in the data; names of public buildings are public facts but "designated shelter" must come from an official list (backlog B9). Re-extract names for display. |
| Roads | OSM extracts contain the road ways | **Main technical risk.** Our `road_graph()` (YunAI `network.py`) builds nodes only at line endpoints, so side streets meeting a through road mid-way are not connected. Fix: split ways at shared vertices before building the graph (a small, testable step); keep bridges and tunnels from connecting where they cross. Also read `oneway`, `maxspeed`, `bridge`, `tunnel` from the tags. |
| Closed roads | EMS or EFAS flood polygons | A road is closed if it intersects the flood (EMS) or lies under depth above the threshold (EFAS). The threshold is an ASSUMPTION. |
| Traffic capacity | none | ASSUMPTION per road class (vehicles per hour), occupancy (people per car) and share going by car; all to be verified or clearly marked. Output is a stress indicator, not a forecast. |
| Messages | none | Templates written by the Communicator; the AI drafts, a person reviews each language. |

Scope question that drives everything: **one hero area, built to be repeatable.** See section 10.

## 6. Method (offline pipeline; the web page only displays and filters)
1. **Scenarios:** for each flood level, flood polygons (and depth) -> demand nodes (exposed residents per 250 m node or 1 km cell), closed roads; shelters wet in ANY flood map removed at every level (shelter rule, section 0).
2. **Graph:** road graph with split ways; closed edges removed per scenario; travel time = length / speed (class defaults are an ASSUMPTION).
3. **Assignment:** a transport problem: each demand node may go to its k nearest reachable safe shelters (travel time on the open graph); minimise total person-time subject to shelter capacity; people who cannot be placed are reported as "unassigned", never hidden. Solved with the sparse LP already available (scipy HiGHS); no new installs.
4. **Routes and load:** shortest path per assigned pair; sum people along each road segment; load ratio against assumed capacity. Detour = time with closures minus time without.
5. **Output:** a compact bundle (GeoJSON and JSON, simplified) per scenario; the page loads the bundle for the selected level.
6. **Messages:** template text filled with zone, shelter, route description and closed roads to avoid; a person reviews before use.

## 7. Acceptance tests (known-answer, before the demo) [STALE: see section 0; the live checks are `research/r01/outputs/tool_pipeline_checks.json` and `tool/verify/cdp_test.py`]
- Shelter load never exceeds its capacity; people assigned plus unassigned equal people to place (conservation).
- No route uses a closed road; every route length is at least the straight-line distance.
- A tiny hand-made network with a known detour and a known overload gives the expected answer (as for `lib/challenge/shelter.py`).
- Roads built by splitting ways: a T-junction is connected, a bridge crossing is not.
- Independent recompute of one scenario by a second method (as the Q3 review did); every exported map and the page itself inspected visually; the page checked at projector width.

## 8. Architecture and packaging [STALE: see section 0 and `tool/README.md`]
- One self-contained HTML page (MapLibre or Leaflet from a pinned CDN version, data bundle embedded or alongside) that runs offline except for the basemap; **fallback: no basemap**, vector layers only, so a dead network does not kill the demo.
- Size budget (2026-10-29 plan): a few MB. Actual: the built page is about 15.5 MB (build of 2026-10-30 09:30, bundle 15.9 MB), too close to the 16 MB Artifact limit and possibly too large for some mail servers (to check). Hosting decided 2026-10-30 (user): the built page as `policy-tool/shelter/index.html` on branch `team1-smart-shelter-map` of the team repo, so the team's Vercel project builds a preview link; `main` untouched, no pull request. Later option: a web build with the data as a separate JSON (served compressed, about 2-3 MB) and an OSM basemap over http(s).
- The pipeline stays in `research/` with scripts, runs and the claims register; the page only shows numbers that exist in the register (one story for tool, brief and demo).

## 9. Pushbacks and risks (with the answer I propose)
1. **"Traffic load" is not traffic simulation.** Show a stress indicator from assignment flows and assumed capacities, and label it so. A real simulation is out of reach in two days and would invite false precision.
2. **Safe route** means "avoids mapped flooded roads", not "verified safe": unmapped or not-assessed areas are not dry, EFAS misses small rivers, and flood depth on a road changes fast.
3. **Flood levels are scenarios.** 2021 observed is one satellite snapshot per area, 14-20 July 2021, not the peak, and only in the requested areas; EFAS RP10 to RP500 are modelled envelopes of river floods (not one event), and the 500-year map is a ceiling. Say which one is on screen, and never compare them outside the area both cover (the review of 2026-10-29 missed this; the user caught it on 2026-10-30).
4. **Capacity and reach are assumptions** (Q3 showed reach swings the answer by about 40 points). The details panel must show the assumption and let the reader change it; every unverified parameter is labelled.
5. **Shelter designation:** our shelters are candidates from OSM, in the state of 29 Oct 2026. Never write "designated" or "available" unless an official list says so.
6. **Cross-border:** Anna's mandate covers Belgium, the Netherlands and the German Region Aachen. Our Q3 numbers are German-only; the Ahr and Erft areas are mostly outside the mandate. The demo must not imply a cross-border system it does not have (section 10).
7. **Messages:** AI drafts, people approve. Wrong evacuation text is harmful, so templates are fixed and reviewed; no free text generated at run time.
8. **Time:** the road graph and the assignment are the long poles; the page can be built in parallel on mock data. If the graph slips, fall back to straight-line reach with an explicit label (Q3 result) and keep the interface.
9. **Responsible AI (jury criterion 4):** log every AI step in `deliverables/ai_log.md`; algorithms are deterministic and tested; the AI sheet states where AI was wrong (for example the flood-trace flags and the capacity cap in Q3).

## 10. Decisions (user, 2026-10-29) and what was left open
- **Hero area: yes to option (a)** Schleiden / Kall (Eifel, inside the wide Region Aachen under H1, unverified) as the working case, with the Ahr valley (Altenahr to Sinzig, Bad Neuenahr-Ahrweiler) as the data-rich comparison.
- **Germany only** for the demo, stated on screen.
- **Audience:** left to the AI: authority first (planner and exercise officer), citizen lookup as a stretch.
- **Roles:** not needed (it is an interactive tool, one builder); section 10 item on roles dropped.

## 10a. The options that were on the table

1. **Hero area** (needs data and relevance to Anna): (a) Schleiden / Kall (Eifel, inside the wide Region Aachen under H1, Q3 shows no shelter within 2 km) with the Ahr valley as the data-rich comparison; (b) the Maas corridor Maastricht - Roermond - Venlo (Dutch, inside the mandate); (c) Liège / Vesdre (Belgian, but the 2021 flood extent missed the Vesdre, so only EFAS levels would work there). Recommendation: (a) as the working case, because the pipeline already has its demand, shelters and gaps; (b) only if the team wants a cross-border story and accepts a new data pass.
2. **Authority first, citizen as stretch** (recommended) or both equally.
3. **Cross-border:** keep German-only for the demo and say so, or add one Belgian or Dutch zone (costs a second OSM and road pass).
4. **Who builds what:** Coder: scenarios, graph, assignment, bundle. Communicator: screen flow, templates, language review. Researchers: verify the assumptions (space per person, passable depth, road capacity), the actor and its role, and the official shelter lists.

## 11. Build order (time-boxed blocks, not clock times; Day 1 end time still unknown)
- **A. Scenarios and demand per flood level** (reuse Q1 and EFAS code) - first, because the page needs it.
- **B. Road graph with split ways + tests** - the main risk; start in parallel with A.
- **C. Assignment, routes, load, bundle** - needs A and B.
- **D. Page on mock data first, then real bundle** - parallel from the start (Communicator can lead the design).
- **E. Messages and training mode.**
- **F. Verification pass (independent reviewers) and visual inspection**, then the brief and AI sheet text drawn from the same claims register.
- Freeze 11:30 on Day 2; export about 12:30; the team sends by 13:15 for the 13:30 deadline. Anything not in the page by the freeze is cut.

## 12. How this serves the four jury criteria
- **Evidence and soundness:** tested algorithms, assumptions visible and movable, limits stated on the screen.
- **Policy usefulness:** a named actor, a concrete use (zone-to-shelter planning and exercises), what happens next; no invented costs or legal powers.
- **Clarity:** one map per view (citizen, municipality, full analysis), one click, plain words; the same numbers as the brief (claim C4.3).
- **Responsible AI:** deterministic, tested code; AI drafts reviewed by people; the AI log and the AI sheet show where AI helped and where it was wrong.
