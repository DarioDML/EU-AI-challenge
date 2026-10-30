# Smart shelter system: page (tool/)

A single self-contained HTML page (Leaflet inlined, no server, works from `file://`) that shows a flood-shelter planning aid from one JSON bundle. Planning aid only: not live guidance, shelters are OSM candidates, routes are not verified safe.

## Overview (state 2026-10-30, Team 1, European AI Challenge)
**What it answers.** For Kreis Euskirchen and Landkreis Ahrweiler (Germany only): if the July 2021 flood, or a modelled 10-, 100- or 500-year river flood, happened, where could the residents inside the flood shelter, and how would they get there?

**Three views** (header switch or `?profile=`):

| View | For | Shows |
|---|---|---|
| Citizen | a resident | Find your street or click your area. You get the building (OSM name, else street, else nearest road), route steps (walk to the open road, then drive), the time, and up to 2 more buildings. July 2021 flood, one building per area (at most 3 for a shared area). |
| Municipality | a local planner | Build a list of municipalities. You get: residents in the flood, placed within 1 h, without a place, within 2 km, over 30 min, the largest destinations, and people sent outside the two districts. The flood level is the only choice. |
| Full analysis | analysts and the jury | Every setting (flood level, road-closure rule, capacity set A/B, population 2020/2025), cards, layers, method, compare tables, CSV, draft messages. |

**Data rules that hold in every view** (design: `research/POLICY_TOOL_PLAN.md` section 0):
- **Coverage of the July 2021 map.** The satellite map (Copernicus EMS EMSR517) covers only the requested areas; the Rhine banks between Remagen and Bad Breisig lie outside, while the river model floods them. People inside the flood who live outside the 2021 map: 0 / 4,810 / 10,652 / 13,763 at 2021 / 10 / 100 / 500 years (claim C4.4).
  - The page draws the edge of the mapped area as a dashed violet line at every level.
  - Outside it the citizen and municipality views say "not covered yet; we are working on more data", never 0.
  - The full analysis shows "N outside the 2021 map".
- **Shelter rule.** A candidate building is used only if it is dry in every flood map we have (2021 and all three model levels).
- **Honesty.** Never "safe", never "your shelter"; candidate buildings, not designated shelters; counts are modelled minimums, rounded.

**Headline numbers** (Set A, 1 h by road; claims C4.2-C4.4 in `research/claims_register.md`):

| Level | People to place | Without a place |
|---|---|---|
| July 2021 | 25,559 | 0 (mean time 22.7 min) |
| 10-year | 15,091 | 0 |
| 100-year | 24,514 | 1,057 (0 with 2 h) |
| 500-year | 30,012 | 4,694 (1,179 with 2 h) |

One sentence (C4.3): for the July 2021 flood, under cautious assumptions, there is room for everyone within an hour by road, but not enough room close by: only about 9 % fit within 2 km.

**Map reading (full analysis).**
- Closed roads are black dashes (red is kept for stress and 'not placed').
- Below zoom 14, nearby shelters merge into numbered badges (magenta = used, grey = flooded); click one to zoom in.
- Flooded buildings have their own layer.
- A click on a blank spot steps back one selection.
- Notes close with ✕ or fade after 8 s.

**Regenerate the data, then the page** (about 5 min, from the project root):
```
.venv\Scripts\python.exe -B research\r01\20_tool_pipeline.py . results\runs\20261029-143924-5ec1\out results\runs\20261029-144102-f165\out research\r01\results\20261029-134745-b0be results\runs\20261029-101321-bf98\out results\runs\20261029-172655-2377\out research\r01\results\20261030-004137-9f38
.venv\Scripts\python.exe -B -I tool\build.py
.venv\Scripts\python.exe -B -I tool\verify\cdp_test.py        # headless Chrome, 161 checks
```
After every regenerate, rerun `research\r01\25_q3_compare_2021_2026.py` (arguments in its report) so the Q3 report's map numbers stay in step, and update claims C4.x.

**Test it locally over http** (as it will be hosted): `cd tool\dist` then `..\..\.venv\Scripts\python.exe -m http.server 8765`, and open `http://127.0.0.1:8765/shelter_tool.html?profile=full` (add `&basemap=1` for the OpenStreetMap background, which tile servers refuse to a `file://` page).

**On the web.** The same page is also prepared as a website, hosted with the team's policy tool once the team approves it: one static page that opens in any desktop browser, with nothing to install. It has the same three views and the same data, and it can show an OpenStreetMap background, which the local file cannot.

**Page size.** About 16 MB (one file with the data inlined). This is above the comfortable limit for email and Claude Artifacts. A web build with the data as a separate, compressed JSON is a later option.


## Build
```
.venv\Scripts\python.exe -B -I tool\build.py                              # default: tool\data\bundle.json if it exists, else the mock
.venv\Scripts\python.exe -B -I tool\build.py tool\data\bundle.json        # explicit real bundle
.venv\Scripts\python.exe -B -I tool\build.py tool\data\mock_bundle.json   # explicit synthetic bundle
.venv\Scripts\python.exe -B -I tool\mock\make_mock_bundle.py              # (re)writes the synthetic mock bundle
```
Run from the project root. `build.py` downloads Leaflet 1.9.4 (js, css) once from cdnjs into `vendor\` and prints the SHA-256; later runs reuse it. It prints the output size (real bundle on 2026-10-30: about 14.5 MB as printed, 15,174,043 bytes; it changes with every bundle). Open `dist\shelter_tool.html` directly.

## Replacing the mock with the real bundle
Write the pipeline output to `tool\data\bundle.json` (format of `BUNDLE_SCHEMA.md`) and run `build.py`. The page reads only `window.BUNDLE`; nothing is hard-coded except labels. Missing keys are listed in a "Data check" bar instead of crashing. The MOCK badge shows only when `meta.mock === true`.

## Files
- `BUNDLE_SCHEMA.md` the contract (not edited here)
- `src\app.html` the page (inline CSS and JS; markers `/*__LEAFLET_CSS__*/`, `/*__LEAFLET_JS__*/`, `/*__BUNDLE__*/null` are filled by build.py, so src alone does not run)
- `build.py` builder; `vendor\` pinned Leaflet; `data\bundle.json` real bundle; `data\mock_bundle.json` synthetic bundle; `mock\make_mock_bundle.py` its generator (own Dijkstra and greedy capacity-limited assignment, no lib imports)
- `dist\shelter_tool.html` the deliverable page; `verify\` screenshots (`r_*.png` real bundle, others mock) and helpers `shot.sh`, `shot_phone.sh`, `phone.html` (the phone helpers are history: the page is desktop only)

## URL hooks (for testing and demos)
`?scenario=rp100&closure=wet&capacity=generous&zone=26` or `&shelter=5`; `&layers=zones,shelters,allshelters,roads,closed,routes,stress,flood` sets which layers are on; `&basemap=0|1` (default: on when the browser reports online); `&scrollto=<element id>`; `&selftest=1` (console only: times a switch through all result keys, prints the CSV head and the clipboard result). A hash (`#zone=26`) works too. Default state without parameters: first observed scenario, its first closure rule, first capacity (real data: obs2021 / any / restrictive).

## Contract additions (all optional, nothing renamed or removed)
- `meta.mock` (bool): MOCK DATA badge only when exactly true.
- `results[key].assign[i][6]`: 7th element, edge ids of the route WITHOUT closures; drawn dotted next to the actual route so a detour is visible (the real bundle does not have it).
- `results[key].summary.unassigned_no_route` and `.unassigned_no_capacity` (sum to `summary.unassigned`): sub-line on the UNASSIGNED card; tooltip: no route = no reachable shelter by open roads within 1 h, no capacity = reachable shelters are full.
- Round 3 summary fields (shown in the summary bar): `unassigned_no_open_road`, `unassigned_no_shelter_reachable`, `unassigned_capacity_limited` (the old `unassigned_no_route` / `unassigned_no_capacity` pair is used only if the new ones are absent), `worst_road_class`, `stress_edges_over_1`, `mean_access_min`, `people_access_over_10min`. Headline time = `mean_time_min` (walk + road); the walk and the road detour are shown separately; `assign[i][4]` is the baseline time including the walk, so detour = [3] - [4] is not clipped.
- `meta` fields shown in the expandable disclaimer: `limits` (list; Python-style dicts inside a sentence are reformatted), `outside_hero_area` and `outside_road_network` ("not modelled"), `q1_totals_bbox`, `candidate_list_check.k` (the "200 fastest shelters" wording), `area` (in the permanent banner with the first two sentences of `disclaimer`).
- `results[key].access_s` ({zone id: seconds}): first leg ON FOOT from a zone inside the flood to the nearest open road (assumed passable before the water rises). The zone panel shows it and says the reported travel time already includes it.
- `assumptions.assignment` (object, free keys): shown in the Assumptions panel (which renders every key of `assumptions`).
- Page tolerances: people may be fractional (shown as whole numbers; under 0.5 shown as "<1" in panels and CSV); zones under 1 person are not drawn or listed; edge names 'nan' or 'None' count as unnamed; road classes `*_link` use the capacity of their base class.
- Road stress ratio = people x car_share / persons_per_car / evacuation_window_h / road_capacity_veh_per_h[class]; the page recomputes it from `load` and logs a console warning if it differs from `summary.worst_road_ratio` (no such warning appeared with the real bundle). Above 1 is labelled "over capacity under the assumptions", never a prediction.

## Profiles and display (2026-10-30)
- Three views: full analysis (default when no parameter is given), `?profile=citizen` and `?profile=municipality`; the switch in the header rewrites the parameter. Desktop only; always light with a white background.
- Residents: town chips with rounded sums when zoomed out, exact 500 m cells from zoom 12 (round 6, below). Kall (zone 55) is preselected.
- Citizen view: one building and one route per area from `citizen_plan` (July 2021 flood only). Bundle fields added on 2026-10-30 (`shelters[].name/street/near_street/in_area`, `streets[].wet/areas`, `citizen_plan.areas[].unassigned_reason`) are documented in `BUNDLE_SCHEMA.md`; whether the page reads them: to check after the page stage.

## Known limits
- Message drafts exist in German and English only, from fixed templates, with the (up to) two largest destinations; unknown shelter types are shown as given.
- "Closed roads to avoid" in a message = closed roads within about 800 m of the zone or its routes (heuristic; the bundle has no per-route list).
- No what-if editing (click-to-close a road or shelter); closure rule and capacity switch between precomputed results.
- Map shapes (cells, chips, shelter badges) are not keyboard tab stops (`keyboard: false`, so hundreds of markers do not become tab stops); in the full analysis use the "Pick from a list" selects. Keyboard use of the citizen and municipality views: to check. The shelter pick-list holds only shelters used in the current plan.
- Map declutter: by default only shelters used in the plan and flooded ones (small crossed marks) are drawn; "All candidate shelters" adds the rest as small dots. Roads are dimmed so routes and closed roads stay readable.
- Basemap (OSM raster): OFF by default and disabled when the page is opened from a local file (OSM blocks file pages); offered only over http(s) with `&basemap=1` (see "Test it locally" above). After 3 failed tiles the page says so and continues with vector layers.
- Clipboard: `navigator.clipboard` with an `execCommand` fallback; verified with a real click and a read-back in headless Chrome (permission granted by the test harness, focus emulated); a user in a normal window may still be asked for permission.
- File size: the real bundle makes a page of about 15.2 MB (15,174,043 bytes on 2026-10-30). Compact JSON per key on 2026-10-30: results 7.7 MB (including the 2025 population results), network 4.1 MB, shelters 1.1 MB, streets 0.8 MB, citizen_plan 0.5 MB. (Day 1: 14.8 MB page with network 4.6 MB and results 4.3 MB; zlib would then give about 2.2 MB; the zlib size now is to check.) A smaller encoding (integer-delta edge coordinates, gzip+base64 inflated with DecompressionStream) could cut the page to about 3 MB; that would change the contract and is NOT done.
- Real-input test: `.venv\Scripts\python.exe -B -I tool\verify\cdp_test.py` drives headless Chrome over the DevTools protocol (real mouse clicks, real key presses on the selects, a real CSV download, clipboard read-back) and compares the page with `dataundle.json` (161 passed, 0 failed on 2026-10-30 at the data stage). Screenshots land in `verify\t_*.png`.
- History (round 5; since round 6 the default is town chips and 500 m cells, see the round 6 line; `residents=rings` still works): population (round 5) is drawn as hollow brown rings over the flood (radius ~ sqrt(people), 5 to 22 px; outline = placement status: solid = all placed, dashed black = partly, dashed red = not placed; rounded counts from zoom 14); "Residents shown as" switches to translucent 500 m squares or off. Residents are shown rounded on screen ("about 300", "fewer than 10"); the CSV keeps whole numbers in `people_estimate` / `zone_total_estimate` with a "not a headcount" comment row. Shelter buildings are round badges with a house glyph (magenta usable, grey crossed flooded, violet dashed full, white dashed not counted; size = capacity). The two never share a colour or shape. Residents are "inside the flood, assumed to need shelter", not people who must leave.
- Round 4 bundle fields used: `meta.zone_bounds` (initial view), `meta.total_places`, `meta.provenance`, `meta.limit_check`, `summary.people_over_30min`, `shelters_at_capacity`, `free_places_total`, `shelters[].flooded.obs2021_mapped` (used when closure = mapped; the flood layer then draws only features with `properties.kind == "mapped flood"`), `assumptions.population` (rendered as "How residents are counted", with a "How counted?" link on the People card). Optional `shelters[].osm_id` adds a column to the CSV.
- CSV (round 4): first row is a comment with the disclaimer (quoted), then columns scenario, closure_rule, capacity_set (Set A/B), bundle_generated_utc, zone, municipality, zone_total, shelter_id, [shelter_osm_id], shelter_lat, shelter_lon, shelter_type, shelter_municipality, people_sent, minutes, detour_minutes, unassigned. File name uses SetA/SetB.
- `build.py --check` exits 1 if `dist/shelter_tool.html` is older than `src/app.html` or the default bundle.
- Round 6 (town chips + cells): `zones[].cell` (optional) holds the four WGS84 corners [lat, lon] (SW, SE, NE, NW) of the zone's 500 m EPSG:3035 grid cell; the page draws that polygon once it is at least 13 px wide (else a minimum-size box around the zone point). Default `residents=cells`: zoomed out (below zoom 12) one chip per municipality with the rounded sum of its cells, from zoom 12 unfilled cell outlines; counts from zoom 13 (largest first, overlapping labels skipped, "<10" from zoom 14). `residents=rings|squares|off` still work. Pipeline check `zone_point_inside_its_500m_cell`.
- Round 7 (population year): optional `populations` [{id, label, year, note}] (first = default, 2020); for other ids, results use the key `scenario|closure|capacity|<id>` and zones carry `people_<id>` (e.g. `people_pop2025`). The page shows a "Population year" select (hidden if only one), a 2020-vs-other table under the flood-level comparison, and a `population_year` CSV column. URL hook `&pop=pop2025`.
- URL hook added: `&view=lat,lon,zoom`; invalid link parameters (unknown scenario, closure, capacity, zone, shelter) show a visible note.

## Data behind the page (added 2026-10-29 by the data review; other statements in this file may be stale, see `reference/DATA_REGISTER.md` section 3)
| Dataset | Reference period / valid for | Retrieved | Used in the page for | Known gaps |
|---|---|---|---|---|
| EMS flood extent and traces (EMSR517 Germany) | satellite passes 14-20 July 2021; one snapshot per area, **not the peak** | read 2026-10-29 | the observed 2021 level and road closures | requested areas only; Germany's traces make its definition more inclusive |
| EFAS RP10/100/500 | modelled return periods, not an event; version v3.1.1 inferred | windows read 2026-10-29 | the modelled levels, closures, overlays | **not pinned or hashed**; empty means 'dry or not modelled'; misses small rivers (nothing at Kall) |
| GHS-POP epoch 2020 | modelled residents of 2020 | read 2026-10-29 | people in zones | about 930 x 600 m cells; 2025 epoch is a projection (sensitivity only) |
| GHS-OBAT R2024A | 2020 thematic; heights and use 2018; footprints 2024 release | read 2026-10-29 | places the residents on buildings (rule use 1 or 2: **non-residential buildings receive about 10%**) | Belgium undercounted (Germany only here); 2.7% of window residents have no usable building |
| OpenStreetMap Geofabrik, 29 Oct 2026 | map state of 29 Oct 2026 (files modified 04:59-05:00 GMT) | downloaded 2026-10-29 | roads, shelter candidates | no official shelter list; floors tagged on 12.7% of outlines; speeds are class defaults |
| GISCO LAU 2024 | boundaries of 1 Jan 2024 | 2026-10-29 | municipality names and borders | 2.5 years after the flood; join on `GISCO_ID` |
The page's permanent banner should carry the dates (backlog B32); at present they appear only after expanding the disclaimer.
