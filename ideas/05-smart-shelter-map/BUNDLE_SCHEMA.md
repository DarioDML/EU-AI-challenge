# Bundle contract: pipeline -> page (smart shelter system)

The pipeline (`research/r01/20_tool_pipeline.py`, local) writes ONE JSON object, `tool/data/bundle.json`. The page (`tool/src/app.html`) reads it from `window.BUNDLE` (injected by `tool/build.py` into a single self-contained `tool/dist/shelter_tool.html`). Coordinates are EPSG:4326 (lon, lat) everywhere. Ids are small integers. Every number is a MINIMUM or an ASSUMPTION-driven estimate; the page must say so (see `meta.disclaimer`).

```jsonc
{
  "meta": {
    "title": "Smart shelter system: planning aid",
    "area": "Eifel and Ahr valley, Germany",
    "generated_utc": "2026-10-29T15:00:00Z",
    "bounds": [6.30, 50.30, 7.45, 50.78],                 // w, s, e, n
    "disclaimer": "text shown permanently: planning aid, not live guidance ...",
    "data_notes": ["string", "..."],                      // bullet list for the 'About the data' panel
    "limits": ["string", "..."]                           // bullet list: what the tool cannot do
  },
  "assumptions": {                                        // shown in the 'Assumptions' panel; every value is an ASSUMPTION unless marked otherwise
    "capacity": {"restrictive": {"m2_per_person": 5.0, "usable_share": 0.4, "cap_max": 500, "tiers": "core"},
                 "generous":    {"m2_per_person": 3.5, "usable_share": 0.7, "cap_max": 1500, "tiers": "core + extended"}},
    "vehicles": {"car_share": 0.8, "persons_per_car": 2.0, "evacuation_window_h": 2.0},
    "road_capacity_veh_per_h": {"motorway": 3600, "primary": 1600, "secondary": 1200, "tertiary": 900, "residential": 400},
    "notes": ["string"]
  },
  "scenarios": [                                          // flood levels
    {"id": "obs2021", "label": "Observed July 2021 (EMS snapshot)", "kind": "observed", "note": "string",
     "closures": [{"id": "any", "label": "road closed if it touches the flood"}]},
    {"id": "rp100", "label": "100-year flood (EFAS model)", "kind": "modelled", "note": "string",
     "closures": [{"id": "wet", "label": "closed under any water"}, {"id": "d05", "label": "closed under more than 0.5 m"}]}
  ],
  "capacities": [{"id": "restrictive", "label": "Restrictive shelter capacity"}, {"id": "generous", "label": "Generous shelter capacity"}],
  "floods": {"obs2021": {"type": "FeatureCollection", "features": []}},     // observed flood polygons (simplified), may be empty in the mock
  "overlays": [{"scenario": "rp100", "png": "data:image/png;base64,...", "bounds": [[50.30, 6.30], [50.78, 7.45]],   // [[s, w], [n, e]]
                "legend": [{"label": "0 - 0.5 m", "color": "#9ecae1"}, {"label": "0.5 - 1 m", "color": "#4292c6"}, {"label": "more than 1 m", "color": "#08519c"}]}],
  "network": {"edges": [{"id": 12, "c": [[6.50, 50.55], [6.51, 50.56]], "h": "primary", "n": "B 266", "b": 0, "t": 0}]},   // c = polyline, h = highway class, n = name or ref, b/t = bridge/tunnel flags
  "zones": [{"id": 0, "lon": 6.49, "lat": 50.53, "muni": "Schleiden", "people": {"obs2021": 120, "rp10": 80, "rp100": 300, "rp500": 520}}],   // residents to place per flood level (minimum)
  "shelters": [{"id": 0, "lon": 6.47, "lat": 50.52, "type": "school", "kind": "education", "footprint_m2": 812, "muni": "Schleiden",
                "cap": {"restrictive": 80, "generous": 260},
                "flooded": {"obs2021": false, "rp10": false, "rp100": false, "rp500": true}}],         // flooded = not usable in that flood level
  "results": {                                            // key = "<scenario>|<closure>|<capacity>"
    "rp100|wet|restrictive": {
      "closed": [12, 15],                                 // network edge ids closed
      "assign": [[0, 3, 100, 540, 420, [12, 13, 14]]],    // [zone id, shelter id, people, travel time s, travel time s with no closures, edge ids of the route]
      "unassigned": {"2": 35},                            // zone id -> people who could not be placed
      "shelter_load": {"3": 100},                         // shelter id -> people assigned
      "load": {"13": 100},                                // edge id -> people on that edge (sum over routes)
      "summary": {"people_to_place": 135, "placed": 100, "unassigned": 35, "shelters_used": 1, "max_shelter_fill": 1.0,
                  "closed_edges": 2, "mean_time_min": 9.0, "mean_detour_min": 2.0, "worst_road_ratio": 1.4}
    }
  },
  "road_ratio_note": "worst_road_ratio and any road colour = people on the edge, turned into vehicles per hour, divided by an ASSUMED capacity: a stress indicator, not a traffic forecast"
}
```

## Additions since the first contract (2026-10-30; the pipeline writes them, the page reads them when present)

```jsonc
{
  "zones":    [{"...": "as above", "lau": "DE_05366024", "people_pop2025": {"obs2021": 526.8, "rp10": 0.0, "rp100": 0.0, "rp500": 0.0}}],   // lau = GISCO LAU id of the zone; residents from the 2025 projection (zone 55, Kall)
  "shelters": [{"...": "as above",
                "name": "Rathaus Kall",              // OSM name tag, "" when OSM has none (1,696 of 3,144 shelters have one; run of 30_tool_building_names.py, same 29 Oct 2026 extract)
                "street": "Bahnhofstraße 9",         // OSM addr:street + addr:housenumber, "" when no addr:street (1,760 have one)
                "near_street": "Bahnhofstraße",      // nearest NAMED road of the road graph within 300 m (fallback label), else "" (only 5 shelters have none of the three)
                "in_area": true}],                   // inside Kreis Euskirchen or Landkreis Ahrweiler, by geometry (LAU polygon), never by name
  "results": {"obs2021|any|restrictive|pop2025": {"...": "same shape as the other results; residents of the 2025 projection"}},
  "populations": [{"id": "pop2020", "label": "2020 (default)", "year": 2020, "note": "string"},
                  {"id": "pop2025", "label": "2025 projection", "year": 2025, "note": "string", "window_residents": 0, "dropped_no_usable_building": 0, "file": "string", "file_generation": "string"}],
  "munis":    [{"id": "DE_05366028", "name": "Mechernich", "geometry": {"type": "Polygon"}}],   // every municipality of the two districts (GISCO LAU 2024, simplified 40 m)
  "streets":  [{"n": "Zum Fahrenbach", "m": "Kall",  // street name + municipality: one record per pair, from the FULL road graph (not only the display network)
                "p": [[50.55, 6.54]],                // [lat, lon] up to 6 points along the street PLUS the midpoint of every wet edge
                "wet": true,                         // any edge closed in July 2021 (closure 'any') or touching the observed flood or a flood trace
                "areas": [58, 60, 61]}],             // citizen_plan area ids that any of its edges crosses (use these, not the points, to open an area)
  "citizen_plan": {                                  // the citizen profile: July 2021, closure 'any', set A, 2020 residents
    "key": "obs2021|any|restrictive", "method": "string", "k": 200,
    "solver": {"status": 0, "message": "string", "gap": 0.0},        // step 1: one building per 250 m cell (HiGHS MILP)
    "solver_split": {"status": 0, "message": "string", "gap": 0.0},  // step 2: cells that cannot go whole to one building, at most 3 buildings each
    "max_buildings_per_split_cell": 3,
    "summary": {"people": 25559, "placed": 24792, "unassigned": 767, "mean_time_min": 22.9, "areas": 375, "buildings_used": 274, "split_cells": 12, "split_people": 4390, "placed_one_building": 22961},
    "main_plan_summary": {"...": "summary of results[key], for comparison"},
    "areas": [{"id": 0, "cells": 1, "people": 19.5, "muni": "Schleiden", "lau": "DE_05366036",
               "split": false,                       // true = shared over up to 3 buildings (dest has 1-3 entries)
               "no_open_road": false, "walk_s": [33, 33],             // walk to the first open road, min and max over the cells, seconds
               "unassigned": 0.0,                    // people of this area without a building in THIS plan
               "unassigned_reason": "",              // "" | "plan_rule" (the at-most-3-buildings rule; buildings in reach are full; the main plan places everyone) | "no_road" | "none_in_1h"
               "dest": [{"s": 1959, "people": 19.5, "road_s": 108, "route": [64806, 64807]}],   // shelter id, people sent, road time s (without the walk), edge ids
               "backup": {"s": 1787, "road_s": 315, "has_room": true, "route": [64806]},        // only for one-building areas: fastest other building, has_room = room for the whole area after the plan
               "geometry": {"type": "Polygon"}}]}
}
```
Optional `people_ranges` (written into the bundle by `pipeline/research/21_tool_people_ranges.py`, standalone, 2020 residents only):
```jsonc
"people_ranges": {
  "label": "range across methods", "rules": {"footprint": "footprint share (tool's rule)", "...": "..."}, "direction": "string", "plan_method": "string",
  "levels": {"rp100": {"base": 24514, "low": 11200, "high": 41300,      // base = sum of zones[].people; low/high rounded down/up to 100 (run of 2026-10-30)
                       "low_rule": "edge_in", "high_rule": "edge_out", "plan_rules": ["edge_in", "edge_out"], "spreading": [22079, 25170], "edge": [11258, 41277],
                       "variants": {"footprint": 24440, "equal": 24097, "floor_area": 24456, "cell_area": 25170, "cell_centre": 22079, "edge_in": 11258, "edge_out": 41277}}},
  "plans": {"rp100|wet|restrictive": {"base": {...}, "low": {...}, "high": {...}}},   // each: people, places_per_resident, shelters_full, shelters_used, unplaced_at_most
  "checks": {"rp100_base_matches_bundle": {"pass": true, "ours": 24440, "bundle": 24514, "relative_difference": -0.003}}
}
```
The plans at both ends (2020 keys only) use the lowest and highest building-based variant (`plan_rules`) and are `results[key]` with every zone's residents scaled to the low or high count, not re-optimised, so `unplaced_at_most` is an upper estimate. The page shows the range only for 2020 residents and never calls it a confidence interval.

Citizen plan numbers are a simpler plan than `results[key]`: it keeps each 250 m cell together, so it leaves some people without a named building (`unassigned_reason` "plan_rule") although the main plan finds room for everyone within 1 h. The page must not word those people as "no room".

Page rules (contract with the builder): (1) the disclaimer is always visible; (2) a scenario is labelled observed or modelled; (3) unassigned people are shown, never hidden; (4) shelters are 'candidate buildings from OpenStreetMap', never 'designated'; (5) everything works offline except the basemap, which is optional; (6) no personal data, no tracking, no calls to external services other than the pinned map library and basemap tiles.
