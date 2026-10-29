"""Inline all policy-tool data files into one HTML file for submission (Leaflet and map tiles still load online)."""

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
    if not DATA_TAG.search(page):
        raise SystemExit("No data <script> tag found in policy-tool/index.html")

    def inline(match: re.Match[str]) -> str:
        source = TOOL / match.group(1)
        if not source.exists():
            print(f"Skipping missing {match.group(1)}; build it with scripts/build_shelter_alert_data.py")
            return ""
        data = source.read_text(encoding="utf-8").replace("</script", "<\\/script")
        return f"<script>\n{data}</script>"

    bundled = DATA_TAG.sub(inline, page)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(bundled, encoding="utf-8")
    print(f"Wrote {args.output} ({args.output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
