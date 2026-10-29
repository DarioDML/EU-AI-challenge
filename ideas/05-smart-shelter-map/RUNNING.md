# Smart Shelter System: interactive map (Team 1 policy tool, draft)

Planning aid for the Eifel (Kreis Euskirchen) and Ahr valley (Landkreis Ahrweiler), Germany only. It shows which area (500 m cell of residents inside the flood) is assigned to which shelter building, by which route, for the observed July 2021 flood and the EFAS 10-, 100- and 500-year floods, with closed roads, detours and an indicative road-load stress layer.

**Status: draft, work in progress.** It is a planning aid, not live guidance and not an official evacuation plan. Shelters are candidate OpenStreetMap buildings, not designated shelters. Capacities, walking and driving assumptions are unverified and listed in the page ("Full disclaimer, limits, not modelled").

## Run it (nothing to install)
Open `dist/shelter_tool.html` in a browser (about 9 MB, one self-contained file: page, map library and data inlined; it makes no network requests by default and works offline). The OpenStreetMap background map is off by default because OSM's public tile servers block pages opened as local files.

URL options: `?scenario=obs2021|rp10|rp100|rp500&closure=any|mapped|wet|d05&capacity=restrictive|generous&zone=N&shelter=N`.

## Rebuild the page from the data
`python build.py` (Python 3, standard library only) inlines `vendor/leaflet.*` and `data/bundle.json` into `src/app.html` and writes `dist/shelter_tool.html`. `python build.py data/mock_bundle.json` builds with the small mock bundle. The data contract is in `BUNDLE_SCHEMA.md`; more in `README.md`.

## Where the data come from
`data/bundle.json` is produced by `pipeline/research/20_tool_pipeline.py` from three earlier runs (roads: `18_tool_roads.py`, residents in the flood per scenario: `19_tool_scenarios.py`; run ids are in `meta.provenance` inside the bundle). The pipeline reads the challenge's cloud datasets (EMS flood layers, EFAS depth, GHS-POP and GHS-OBAT) and OpenStreetMap extracts, so it is NOT runnable from this repository alone; it is here for review and reproducibility. `pipeline/lib/` holds the road-graph and shelter-assignment code with unit tests (`python -m unittest` from `pipeline/lib`, needs numpy, scipy, pandas) and `pipeline/tool_pipeline_checks.json` the checks of the last run.

## Method in one paragraph
Residents: GHS-POP 2020 (1 km grid, modelled) is spread over GHS-OBAT building points by footprint; the buildings inside the flood (observed: mapped flood or flood trace; modelled: EFAS depth above 0) are summed into 250 m nodes and then 500 m zones. Roads: OSM roads of the main classes, closed where they touch the flood. Residents inside the flood walk (assumed 4 km/h, at most 2 km) to the nearest open road, then each zone's 200 fastest reachable shelters within 1 hour are the options; a transport optimisation fills shelters up to their assumed capacity minimising total person-time. The road stress layer turns the routed people into vehicles per hour against an ASSUMED capacity per road class: an indicator, not a traffic forecast.

## Licences and attribution
Contains OpenStreetMap data (c) OpenStreetMap contributors, ODbL (Geofabrik extracts of 29 Oct 2026). Copernicus EMS rapid mapping, EFAS (Copernicus Emergency Management Service) and JRC GHSL (GHS-POP, GHS-OBAT) are challenge-provided datasets; check their terms before reuse. Leaflet 1.9.4 (BSD 2-Clause) is bundled in `vendor/`.
