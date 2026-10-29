# Figures

`reference/` holds the five existing PNG/SVG pairs copied from the current local analysis. They are examples and comparison targets, not automatically approved submission graphics. Their numbers come from `data/reference/aoi_metrics.csv`; map 05 also uses `aoi_event_unions.parquet` and the supplied EFAS RP500 raster.

`generated/` is the default destination for new graphics. Run:

```powershell
python scripts/check_data.py
python scripts/generate_reference_figures.py
python scripts/generate_reference_figures.py --include-map
```

The first command checks the bundled table. The second creates charts 01–04 as PNG/SVG. The third also creates map 05 when the RP500 raster is available under `CHALLENGE_DATA_ROOT/cems-efas/` or `data/raw/working_data/cems-efas/`. New plotting scripts should read a named result table, save to `figures/generated/`, and write a short source and limitation note in `data-analysis/`. Preserve source labels and uncertainty when adapting a reference graphic.
