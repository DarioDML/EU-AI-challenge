# Challenge data dictionary

Definitions below follow the supplied Annex 2, its referenced data manuals, and the local source audits in `data/reference/`. Always inspect the actual file metadata before analysing a new product.

| Short name | Source folder | What a record/cell means | Best use | Critical limit |
|---|---|---|---|---|
| EMS | `ems_be/`, `ems_de/`, `ems_nl/` | Analyst-interpreted flood/vector product from satellite imagery during July 2021 | Observed water, flood traces, mapped assets and product context | Only mapped AOIs and acquisition dates; water visible on a pass is not the event peak |
| EFAS | `cems-efas/` | Modelled river-flood water depth for RP10, RP100 and RP500 scenarios | Compare recorded event evidence with positive scenario cells | It is a scenario, not an observation or a 2021 forecast; blank/NoData is not proof of safety |
| OBAT | `obat_be/`, `obat_de/`, `obat_nl/` | One point per building with use and inferred attributes, reference year 2020 | Count building points intersecting a specified geometry | Point is not a footprint, home, household or measured damage; Belgian inventory has a documented undercount warning |
| POP | `ghs_pop/` | Estimated residents in a grid cell; E2020 and projected E2025 supplied | Estimate residents within a mapped area with an explicit cell allocation rule | Residents per cell, not people known to be flooded, evacuated or present at a specific hour |

## EMS: observed evidence

The supplied activations are EMSR517 (Germany), EMSR518 (Belgium), and EMSR520 (Netherlands). Product type and source time matter. DEL products show delineation; some GRA products classify asset damage. Check the individual product and layer before asserting a grade. A union across products collects evidence from different dates and changing AOI boundaries, so do not describe it as one peak-time footprint. Outside a mapped AOI is unmapped, not observed dry. See `data/reference/ems_products.csv` and `event_observation_sources.csv`.

## EFAS: scenario water depth

The supplied GeoTIFFs are `Europe_RP10_filled_depth.tif`, `Europe_RP100_filled_depth.tif`, and `Europe_RP500_filled_depth.tif`. RP10, RP100 and RP500 describe annual exceedance probabilities of about 10%, 1%, and 0.2% under the model; they do not mean a flood occurs on a schedule. The catalogue notes missing small rivers and model assumptions. The local audit found positive values and NoData but no zero-depth values in the examined AOI windows. Phrase a comparison as “outside positive values in the supplied RP500 raster,” and preserve NoData separately. See `raster_value_audit.json` and `hazard_nesting_audit.json`.

## OBAT: building points

The supplied R2024A, E2020 files are country GeoPackages (SQLite). A feature has point geometry and fields including `fid`, `id`, `country`, `adm1`, `height`, `shapefactor`, `use`, `epoch`, `area` and `perimeter` in the inspected database profiles. The local manual reading gives `use=0` outside the built-up classification domain, `use=1` residential/mixed, and `use=2` non-residential. Verify coding in the supplied manual and file when using another release. `area` is an attribute, while geometry is a point: the point overlay cannot measure flooded footprint area. Count unique `(country, source fid)` when AOIs overlap. Country source folder does not by itself prove the point is within a same-country AOI.

## POP: estimated residents

The supplied R2023A global rasters have E2020 and E2025 versions. Use E2020 for a historical 2021 comparison; E2025 is a projection sensitivity. Values are people per cell, so do not multiply them by cell area. A partial-cell estimate should state its allocation rule; the current reference uses the fraction of each cell's metric area intersecting the event geometry, assuming residents are uniform inside a cell. “All touched cells” is a sensitivity comparison and often much larger. POP and OBAT are not independent measures because both use built-environment information.

## Common checks before a figure

Use a projected metric CRS (the prepared spatial analysis uses EPSG:3035) for areas and buffers. Keep source raster values on their native grid for calculation. Record whether the denominator is mapped AOI, event area, exposed points or population cells. Check product dates and coverage, units, NoData, duplicate AOIs and whether a quantity describes exposure or classified damage. Treat percentages from different denominators as different questions.

Primary local source: [Annex 2](../annexes/Annex%202.%20Data%20catalogue.pdf). The supplied catalogue links to [Copernicus Emergency Mapping](https://mapping.emergency.copernicus.eu/), [EFAS flood hazard data](https://data.jrc.ec.europa.eu/collection/id-0054), [GHS-OBAT](https://data.jrc.ec.europa.eu/dataset/f41a22f1-5741-4c41-86eb-6384654f6927), and [GHS-POP](https://data.jrc.ec.europa.eu/dataset/2ff68a52-5b5b-4a22-8f40-c41da8332cfe).
