"""Inline the policy-tool data into one HTML file for submission (Leaflet and map tiles still load online)."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "policy-tool"
DATA_TAG = re.compile(r'<script src="(data/[A-Za-z0-9_]+\.js)"></script>')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPO / "deliverables" / "shelter-alert-tool.html")
    args = parser.parse_args()
    page = (TOOL / "index.html").read_text(encoding="utf-8")
    match = DATA_TAG.search(page)
    if match is None:
        raise SystemExit("No data <script> tag found in policy-tool/index.html")
    data = (TOOL / match.group(1)).read_text(encoding="utf-8").replace("</script", "<\\/script")
    bundled = page[: match.start()] + f"<script>\n{data}</script>" + page[match.end() :]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(bundled, encoding="utf-8")
    print(f"Wrote {args.output} ({args.output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
