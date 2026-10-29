# EU AI Challenge

A small, reviewable workspace for the four coders preparing the July 2021 flood challenge. The challenge question may change; treat the included results as checked starting points, not as a final answer.

Intended GitHub repository name: `EU-AI-challenge`.

## Start here

1. Read [the annexes](annexes/README.md), especially Annex 2 (data catalogue), Annex 3 (AI use), and Annex 4 (submission and evaluation).
2. Read [the data dictionary](data-analysis/DATA_DICTIONARY.md) before using EMS, EFAS, OBAT or POP.
3. Run `python scripts/check_data.py` to check the compact reference results.
4. Set up [source access](data/README.md), then work in one of the [idea lanes](ideas/README.md).
5. Put reusable code in `scripts/`, reviewable result tables in `data-analysis/`, and generated graphics in `figures/generated/`.

## Structure

| Path | Purpose |
|---|---|
| `annexes/` | Seven original challenge annexes and a short index |
| `data/reference/` | Compact, precomputed tables, audits and prepared event geometry from the current local analysis |
| `data/raw/` | Local/cloud-fetched source files; ignored by Git |
| `data/processed/` | Large local intermediates; ignored by Git |
| `data-analysis/` | Dataset definitions, fact checks, and future analysis notes |
| `ideas/01-...04-.../` | Independent work areas for four coders; assign an owner in each README |
| `scripts/` | Data access, checks and figure generation |
| `figures/reference/` | Five existing PNG/SVG figure pairs, for comparison |
| `figures/generated/` | New figure output; ignored until a reviewed figure is deliberately moved into a tracked location |
| `deliverables/` | Working submissions; output files ignored until reviewed |

## Work together

Use one branch per task, e.g. `coder-1/ems-event-definition`. Each coder owns an idea lane and may add a script or table under the shared folders. Avoid editing another coder's files in the same branch. A pull request should state the source file or bucket path, geography and dates, units, method, validation command, and any limitation that affects the claim. Review data claims and figure labels before merging. Update the AI usage sheet in Annex 7 as work proceeds.

An idea should move through `ideas/<lane>/README.md` → `scripts/<descriptive-name>.py` → `data-analysis/<descriptive-result>.csv` → `figures/generated/<descriptive-name>.png`. Keep raw downloads in `data/raw/`. If a figure is chosen for the brief, move a reviewed copy to a named folder in `figures/` and record its source table and script in `figures/README.md`.

## Reproduce the existing graphics

```powershell
python -m pip install -r requirements.txt
python scripts/check_data.py
python scripts/generate_reference_figures.py
```

The first four reference charts are regenerated as PNG and SVG in `figures/generated/`. For the fifth map, obtain the EFAS RP500 raster (instructions in `data/README.md`), set `CHALLENGE_DATA_ROOT` to its `working_data` parent if needed, then run `python scripts/generate_reference_figures.py --include-map`. The map also uses the tracked prepared AOI geometry. New graphics should follow the same input/output pattern.

## Scope and provenance

The seven annexes and reference assets were copied from the original local `EU AI challenge` folder. The large `datasets_challenge.zip`, full raw rasters/GeoPackages, brainstorming, guides, audio, and local full-dataset copies are not part of this workspace. The original folder was left intact. The challenge bucket `gs://datasets_challenge/working_data` is the source of raw data; it is read-only and the starter notebook uses anonymous access. Local `data/reference/` files are derived results, with source and limitations documented there.
