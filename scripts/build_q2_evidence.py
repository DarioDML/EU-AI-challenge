"""Validate the Researchers' Q2 evidence table and write it as policy-tool data."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlparse


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "policy-tool" / "q2_evidence.csv"
TARGET = REPO / "policy-tool" / "data" / "q2_evidence.js"
AREAS = {"region", "be_01", "nl_01", "de_08", "de_09", "de_10", "de_18"}
THEMES = {"defences", "rebuilding", "land_use", "evacuation_shelter", "critical_infra", "awareness"}
STATUSES = {"verified", "claimed", "unknown"}
FIELDS = ("area_id", "theme", "status", "finding", "source", "url", "checked", "lead")


def is_web_link(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def main() -> None:
    rows: list[dict[str, str]] = []
    problems: list[str] = []
    seen: dict[tuple[str, str], int] = {}
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        for number, raw in enumerate(csv.DictReader(handle), start=2):
            row = {field: (raw.get(field) or "").strip() for field in FIELDS}
            if row["area_id"] not in AREAS:
                problems.append(f"line {number}: unknown area_id {row['area_id']!r}")
            if row["theme"] not in THEMES:
                problems.append(f"line {number}: unknown theme {row['theme']!r}")
            if row["status"] not in STATUSES:
                problems.append(f"line {number}: status must be one of {sorted(STATUSES)}")
            if row["status"] != "unknown" and not (row["finding"] and row["source"]):
                problems.append(f"line {number}: a {row['status']} row needs a finding and a source")
            if row["url"] and not all(is_web_link(link.strip()) for link in row["url"].split(" | ")):
                problems.append(f"line {number}: each url (separate several with ' | ') must start with http:// or https://")
            key = (row["area_id"], row["theme"])
            if key in seen:
                problems.append(f"line {number}: {key[0]}/{key[1]} already on line {seen[key]}; edit that row instead")
            seen[key] = number
            rows.append(row)
    if problems:
        raise SystemExit("Fix q2_evidence.csv:\n" + "\n".join(problems))
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text("window.Q2_EVIDENCE = " + json.dumps(rows, ensure_ascii=False) + ";\n", encoding="utf-8")
    counts = {status: sum(row["status"] == status for row in rows) for status in sorted(STATUSES)}
    print(f"Wrote {TARGET} ({len(rows)} rows: {counts})")


if __name__ == "__main__":
    main()
