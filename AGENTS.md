# Repository instructions for coding assistants

Read `README.md`, `data-analysis/DATA_DICTIONARY.md`, and the README in the folder you change. Follow these rules:

1. Keep all paths relative to this repository. Resolve the repository root from `Path(__file__).resolve()`; do not point scripts into the older `EU AI challenge` folder.
2. Keep source downloads, credentials, caches and large intermediate files out of Git. Use `data/raw/` and environment variables. Never put a key, token, personal data or a whole dataset in a prompt or commit.
3. Every numeric claim needs a named source table/file, geography, dates, units, denominator, and a check. Put those details next to the result or figure.
4. Separate observed EMS flood evidence, EFAS scenario values, OBAT building points, and GHS-POP estimated residents. Preserve NoData and unmapped areas as unknown. Do not call exposure damage or a building point a household.
5. Save new figure files under `figures/generated/`; use the corresponding `data-analysis/` result table as input. Record the generation command and source paths in `figures/README.md` before promoting a figure.
6. Work in the assigned `ideas/` lane and a task branch. Coordinate edits to shared scripts and result tables through review.
7. Run `python scripts/check_data.py` when changing reference results or related plots. State any check that you could not run.
