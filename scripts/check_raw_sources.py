"""Compare available local rasters and OBAT GeoPackages with reference metadata."""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
REFERENCE = REPO / "data" / "reference"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(
            os.environ.get("CHALLENGE_DATA_ROOT", REPO / "data" / "raw" / "working_data")
        ),
        help="Local working_data directory",
    )
    args = parser.parse_args()
    root = args.data_root.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Source folder missing: {root}")
    checked = 0
    skipped = []
    metadata = json.loads((REFERENCE / "raster_metadata.json").read_text(encoding="utf-8"))
    for record in metadata:
        parts = Path(record["file"]).parts
        assert parts[0] == "working_data"
        path = root.joinpath(*parts[1:])
        if not path.is_file():
            skipped.append(str(path.relative_to(root)))
            continue
        import rasterio

        with rasterio.open(path) as raster:
            assert str(raster.crs) == record["crs"], path
            assert raster.width == record["width"] and raster.height == record["height"], path
            assert raster.nodata == record["nodata"], path
            assert all(
                math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10)
                for a, b in zip(tuple(raster.transform), record["transform"])
            ), path
        checked += 1
        print(f"OK raster metadata: {path.relative_to(root)}")

    for country in ("be", "de", "nl"):
        folder = root / f"obat_{country}"
        files = sorted(folder.rglob("*.gpkg")) if folder.is_dir() else []
        if not files:
            skipped.append(f"obat_{country}/*.gpkg")
            continue
        assert len(files) == 1, f"Expected one GeoPackage under {folder}"
        profile = json.loads(
            (REFERENCE / f"obat_{country}_database_profile.json").read_text(encoding="utf-8")
        )
        with sqlite3.connect(files[0].resolve().as_uri() + "?mode=ro", uri=True) as connection:
            connection.execute("PRAGMA query_only = ON")
            rows = connection.execute(
                "SELECT table_name, feature_count FROM gpkg_ogr_contents"
            ).fetchall()
        assert len(rows) == 1, f"Expected one OBAT layer: {files[0]}"
        assert rows[0][0] == profile["contents"][0][0], files[0]
        assert rows[0][1] == profile["national_summary"]["n"], files[0]
        checked += 1
        print(f"OK OBAT layer/count: {files[0].relative_to(root)}")

    if not checked:
        raise SystemExit("No matching source files found; set CHALLENGE_DATA_ROOT first")
    print(f"Checked {checked} available raw sources; {len(skipped)} absent locally.")
    for item in skipped:
        print(f"  skipped: {item}")


if __name__ == "__main__":
    main()
