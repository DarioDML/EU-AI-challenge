# Data access and storage

The challenge source is the public, read-only bucket `gs://datasets_challenge/working_data`. The eight source folders are `cems-efas`, `ems_be`, `ems_de`, `ems_nl`, `ghs_pop`, `obat_be`, `obat_de`, and `obat_nl` (Annexes 1–2). There is no SQL server: OBAT is stored in GeoPackage files, which are SQLite databases. The other sources are vectors and GeoTIFF rasters.

## Use the local source copy

If you already have the original local extraction, point the script to its `working_data` directory:

```powershell
$env:CHALLENGE_DATA_ROOT = 'C:\Users\Louis\Desktop\EU AI challenge\insights\data\working_data'
python scripts/data_access.py list --source local
python scripts/query_obat.py --country be --limit 5
```

The current extraction may not contain every source folder. The original archive remains in the older folder; this new repository does not depend on it by default.

## Read from the bucket

```powershell
python -m pip install -r requirements.txt
python scripts/data_access.py list --source cloud
python scripts/data_access.py list --source cloud --path cems-efas
python scripts/data_access.py fetch cems-efas/Europe_RP500_filled_depth.tif
```

`fetch` writes into `data/raw/working_data/` and will not overwrite an existing file. Large source files are deliberately ignored by Git. Use the exact bucket-relative path returned by `list`. To query an OBAT country GeoPackage, fetch its `.gpkg` file and run `python scripts/query_obat.py --country be --limit 5`. This runs a read-only SQLite query. You can also use the supplied starter notebook's `gcsfs` and GDAL approach for windowed raster/vector reads without downloading complete files.

## Fact-check chain

`data/reference/` contains compact results and an integrity manifest. Start with `python scripts/check_data.py`; then trace an assertion to the source path listed in `data/reference/README.md` and Annex 2. The check script tests arithmetic and copied-file integrity. It cannot by itself prove that a raw source is complete or that an interpretation is valid.

With a local `working_data` directory available, run `python scripts/check_raw_sources.py` to compare available raster metadata and OBAT layer counts with the bundled profiles. It reports missing source files as skipped; a final claim still needs a check of its actual source features/cells and method.
