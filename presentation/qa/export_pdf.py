#!/usr/bin/env python3
"""PDF backup of the pitch: every build state (?static screenshots from audit.py) as one page.

    python powerpoint/pitch/qa/export_pdf.py            # uses the last audit screenshots (shots/), runs audit.py if none
    python powerpoint/pitch/qa/export_pdf.py --refresh  # re-shoot first
Writes powerpoint/pitch/johan-pitch-backup.pdf (1920x1080 pages, JPEG q88); if over 10 MB, 1280x720 pages instead.
"""
import argparse, io, re, subprocess, sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
PITCH = HERE.parent
sys.path.insert(0, str(HERE))
import audit  # default_out()


def pdf(files, out, size, q):
    pages = []
    for f in files:
        im = Image.open(f).convert("RGB")
        if im.size != size:
            im = im.resize(size, Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=q); buf.seek(0)
        pages.append(Image.open(buf).convert("RGB"))
    pages[0].save(out, "PDF", save_all=True, append_images=pages[1:], resolution=96.0)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--out", default=str(PITCH / "johan-pitch-backup.pdf")); ap.add_argument("--quality", type=int, default=88)
    ap.add_argument("--shots", default=str(audit.default_out()))
    a = ap.parse_args()
    shots = Path(a.shots) / "shots"
    if a.refresh or not list(shots.glob("*.png")):
        subprocess.run([sys.executable, str(HERE / "audit.py"), "--out", a.shots], stdout=subprocess.DEVNULL, check=False)
    key = lambda p: tuple(int(x) for x in re.match(r"(\d+)\.(\d+)_", p.name).groups())
    files = sorted((p for p in shots.glob("*.png") if re.match(r"\d+\.\d+_", p.name) and not p.name.startswith("0.")), key=key)
    if not files:
        sys.exit("no screenshots found")
    out = Path(a.out)
    pdf(files, out, (1920, 1080), a.quality)
    mb = out.stat().st_size / 1e6
    if mb > 10:
        pdf(files, out, (1280, 720), a.quality)
        mb = out.stat().st_size / 1e6
        print("over 10 MB at 1920x1080: rendered at 1280x720 (compact)")
    print(f"{out}  {len(files)} pages  {mb:.1f} MB")


if __name__ == "__main__":
    main()
