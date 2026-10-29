# Data analyse

Use this folder to turn source files into claims the team can inspect. Begin with [the data dictionary](DATA_DICTIONARY.md), then consult Annex 2 and the source file itself. Put a small CSV/Parquet result and a short Markdown note here for each proposed finding. Keep full downloads and large intermediates in `data/raw/` or an ignored local working directory.

For each result, record:

- Question and intended decision;
- Source file/bucket path, product or release, observation date, geography and coordinate system;
- Unit, numerator, denominator, missing-value treatment and deduplication rule;
- Exact command or script and output path;
- Independent check against source records or an alternative calculation;
- Limitations that would change the claim.

Run `python scripts/check_data.py` before using the bundled reference table. The reference checks confirm internal consistency and file integrity. They do not replace a source-level check for a new conclusion. Use [FINDING_TEMPLATE.md](FINDING_TEMPLATE.md) for each proposed result.

If the local source files are present, run `python scripts/check_raw_sources.py` to compare raster metadata and OBAT layer counts with the profiles in `data/reference/`. Record which sources were skipped.

## Current source-to-claim route

`data/reference/aoi_metrics.csv` → `scripts/check_data.py` → `scripts/generate_reference_figures.py` → `figures/generated/`. Its event definition is the union of supplied water and flood-trace observations, clipped to mapped EMS areas of interest. This union combines observations across dates; it is not a simultaneous flood snapshot.
