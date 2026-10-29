"""Check copied reference-file integrity and AOI result-table arithmetic."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
REFERENCE = REPO / "data" / "reference"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_manifest(source_insights: Path | None) -> int:
    lines = (REFERENCE / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    entries = {}
    for line in lines:
        hash_value, name = line.split("  ", 1)
        assert len(hash_value) == 64 and name not in entries
        entries[name] = hash_value
    actual = {p.name for p in REFERENCE.iterdir() if p.is_file()} - {"README.md", "MANIFEST.sha256"}
    assert set(entries) == actual, f"Manifest/file mismatch: {sorted(set(entries) ^ actual)}"
    for name, expected in entries.items():
        assert sha256(REFERENCE / name) == expected, f"Changed reference file: {name}"
        if source_insights:
            source = (
                source_insights / "data" / name
                if name == "aoi_event_unions.parquet"
                else source_insights / "analysis" / name
            )
            assert source.is_file(), f"Original source missing: {source}"
            assert sha256(source) == expected, f"Copy differs from source: {name}"
    return len(entries)


def number(row: dict[str, str], key: str) -> float:
    value = float(row[key])
    assert math.isfinite(value), f"{row['aoi_id']}: {key} is not finite"
    return value


def check_metrics() -> int:
    with (REFERENCE / "aoi_metrics.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 19, f"Expected 19 mapped AOIs, found {len(rows)}"
    assert len({row["aoi_id"] for row in rows}) == len(rows), "Duplicate AOI"
    for row in rows:
        aid = row["aoi_id"]
        event = number(row, "event_km2")
        water = number(row, "water_km2")
        assert event >= 0 and -1e-8 <= water <= event + 1e-8, aid
        assert number(row, "pop2020_fractional") <= number(row, "pop2020_all_touched") + 1e-6, aid
        assert number(row, "pop2020_fractional") >= 0, aid
        buildings = number(row, "buildings_event")
        residential = number(row, "residential_event")
        assert math.isclose(
            buildings,
            residential + number(row, "nonresidential_event") + number(row, "unclassified_use_event"),
        ), aid
        assert 0 <= number(row, "residential_water_only") <= residential <= buildings, aid
        for period in (10, 100, 500):
            prefix = f"rp{period}_"
            assert math.isclose(
                number(row, prefix + "positive_buildings")
                + number(row, prefix + "zero_buildings")
                + number(row, prefix + "nodata_buildings"),
                buildings,
            ), f"{aid}: {prefix} classes"
            assert 0 <= number(row, prefix + "positive_residential") <= residential, aid
            assert 0 <= number(row, prefix + "positive_fraction") <= 1 + 1e-8, aid
        assert number(row, "residential_buffer_-10m") <= residential <= number(row, "residential_buffer_10m"), aid
    report = json.loads((REFERENCE / "validation_report.json").read_text(encoding="utf-8"))
    assert report["all_passed"] is True, "Original validation report did not pass"
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-insights",
        type=Path,
        help="Optional path to the original insights folder; also compare copied bytes with source",
    )
    args = parser.parse_args()
    files = check_manifest(args.source_insights)
    areas = check_metrics()
    print(f"OK: {files} reference files match the manifest; {areas} AOIs pass arithmetic checks.")
    if args.source_insights:
        print("OK: copied reference files also match the original insights folder.")


if __name__ == "__main__":
    main()
