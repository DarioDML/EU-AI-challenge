# Scripts

Run commands from the repository root.

| Script | Purpose |
|---|---|
| `data_access.py` | List public challenge bucket/local source folders and fetch one exact cloud file into ignored `data/raw/` |
| `query_obat.py` | Find a local country GeoPackage and run a read-only SQLite sample query |
| `check_data.py` | Verify bundled file hashes and arithmetic invariants in the AOI result table |
| `check_raw_sources.py` | Compare available raw raster metadata and OBAT layer counts with reference profiles |
| `generate_reference_figures.py` | Rebuild four charts, and optionally the fifth map, into `figures/generated/` |

Use environment variable `CHALLENGE_DATA_ROOT` for a local `working_data` path. `CHALLENGE_BUCKET_ROOT` defaults to the source in Annex 1. No credentials are stored in this repository. New scripts should accept paths or resolve them from the repository root and write only into documented output folders.
