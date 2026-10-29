# Checked reference inputs

Copied from the original local analysis under `insights/analysis/`, except `aoi_event_unions.parquet`, which came from `insights/data/`. These are preparatory July 2021 flood results for supplied mapped areas, not national totals or the final challenge answer. `MANIFEST.sha256` records byte integrity of the copied files.

| Files | Role | Raw source to revisit |
|---|---|---|
| `aoi_metrics.csv`, `activation_union_metrics.csv` | Exposure, area, population and overlap calculations | EMS product vectors, EFAS rasters, OBAT GeoPackages, GHS-POP 2020 |
| `aoi_event_unions.parquet` | Prepared AOI/water/event geometry for map regeneration | EMS product vectors |
| `ems_products.csv`, `event_observation_sources.csv` | Product identity, geography and source dates | EMS vectors and metadata |
| `ems_damage_grades.csv`, `graded_asset_audit.csv` | Graded records, distinct from exposure overlays | Supplied EMS GRA layers and summary workbooks |
| `raster_metadata.json`, `raster_value_audit.json`, `hazard_nesting_audit.json` | Raster dimensions, values and scenario checks | EFAS and GHS-POP GeoTIFFs |
| `obat_*_database_profile.json` | GeoPackage schema and counts | Country OBAT GeoPackages |
| `validation_report.json` | Checks performed in the original local analysis | Raw sources and derived tables |

The copied result table is only a starting point. Rerun a calculation from the raw source when it becomes a headline claim; record the script, source version, assumptions and check in `data-analysis/`. Annex 2, p. 3 warns that OBAT undercounts buildings in Belgian flood areas. The EMS AOIs are partial and different products may use different dates or coverage.
