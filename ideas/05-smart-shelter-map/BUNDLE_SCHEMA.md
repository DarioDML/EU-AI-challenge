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

Page rules (contract with the builder): (1) the disclaimer is always visible; (2) a scenario is labelled observed or modelled; (3) unassigned people are shown, never hidden; (4) shelters are 'candidate buildings from OpenStreetMap', never 'designated'; (5) everything works offline except the basemap, which is optional; (6) no personal data, no tracking, no calls to external services other than the pinned map library and basemap tiles.
