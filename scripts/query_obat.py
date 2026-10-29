"""Run a small read-only SQL query against one locally available OBAT GeoPackage."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
VALID_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def find_geopackage(country: str) -> Path:
    roots = []
    configured = os.environ.get("CHALLENGE_DATA_ROOT")
    if configured:
        roots.append(Path(configured).expanduser())
    roots.append(REPO / "data" / "raw" / "working_data")
    for root in roots:
        folder = root / f"obat_{country}"
        if folder.is_dir():
            matches = sorted(folder.rglob("*.gpkg"))
            if matches:
                return matches[0].resolve()
    raise SystemExit(
        f"No obat_{country} GeoPackage found. Set CHALLENGE_DATA_ROOT or fetch it into data/raw/working_data."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", choices=("be", "de", "nl"), required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--summary", action="store_true", help="Count records by use class; can take time")
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    path = find_geopackage(args.country)
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only = ON")
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM gpkg_contents WHERE data_type = 'features'"
            )
        ]
        if len(tables) != 1 or not VALID_IDENTIFIER.fullmatch(tables[0]):
            raise SystemExit(f"Expected one safe feature table; found {tables!r}")
        table = f'"{tables[0]}"'
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        wanted = ["fid", "id", "country", "use", "height", "epoch"]
        if not set(wanted).issubset(columns):
            raise SystemExit(f"Missing expected fields: {sorted(set(wanted) - columns)}")
        quoted = ", ".join(f'"{column}"' for column in wanted)
        cursor = connection.execute(f"SELECT {quoted} FROM {table} LIMIT ?", (args.limit,))
        print(f"Source: {path}")
        print(json.dumps([dict(zip(wanted, row)) for row in cursor], indent=2))
        if args.summary:
            summary = connection.execute(
                f'SELECT "use", COUNT(*) FROM {table} GROUP BY "use" ORDER BY "use"'
            )
            print("Counts by use:", dict(summary))


if __name__ == "__main__":
    main()
