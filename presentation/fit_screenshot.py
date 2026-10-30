"""Fit the map to Web Mercator so real routes can be drawn on it (writes georef.json).

Default input: the team's vector map assets/route-stress-map.svg (the Smart Shelter System map for July 2021,
assumption set A, 1244 x 894; derived from route-stress_bad-neuenahr-ahrweiler_july-2021_capacity-A.svg by
removing its white background rect). Its paths are read as geometry, not colour: the #111111 path is the
closed roads and the rgb(...) paths are the loaded roads (stress ramp). We rasterise those two sets, rasterise
the bundle's closed and loaded roads the same way, and find the zoom and offset that overlay them best
(FFT cross-correlation, coarse then fine).
Legacy input (--png): the old Leaflet screenshot, matched on its four stress colours.
Model: px = (x - X0) * s, py = (Y0 - y) * s, with x, y in EPSG:3857 metres.
Check: --check writes the map (rendered PNG given by --render, else white) with the bundle's roads drawn 1 px
thin on top: loaded roads magenta, closed roads orange. Look at it before trusting the fit.

    python powerpoint/pitch/fit_screenshot.py --render render.png --check figures/generated/pitch/georef_check.png
"""
import argparse
import json
import math
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / ".git").exists())  # repo root, wherever this folder sits
BUNDLE_PATH = "ideas/05-smart-shelter-map/data/bundle.json"
KEY = "obs2021|any|restrictive"
BOX = (6.90, 50.44, 7.35, 50.65)  # search window around Bad Neuenahr-Ahrweiler, lon/lat
COLOURS = {0: (0, 158, 115), 1: (240, 228, 66), 2: (213, 94, 0), 3: (122, 0, 25)}  # the page's STRESS colours
R = 6378137.0

ap = argparse.ArgumentParser()
ap.add_argument("--bundle", default=str(ROOT / BUNDLE_PATH))
ap.add_argument("--ref", default="origin/team1-smart-shelter-map")
ap.add_argument("--svg", default=str(HERE / "assets" / "route-stress-map.svg"))
ap.add_argument("--png", default="", help="legacy: fit the old Leaflet screenshot on its colours instead of the SVG geometry")
ap.add_argument("--render", default="", help="PNG render of the SVG, only used as the backdrop of --check")
ap.add_argument("--zoom", default="13.0,15.2", help="zoom range searched, lo,hi")
ap.add_argument("--out", default=str(HERE / "georef.json"))
ap.add_argument("--check", default="")
args = ap.parse_args()

src = Path(args.bundle)
raw = src.read_bytes() if src.exists() else subprocess.run(["git", "show", f"{args.ref}:{BUNDLE_PATH}"], cwd=ROOT, capture_output=True, check=True).stdout
B = json.loads(raw)
veh, cap = B["assumptions"]["vehicles"], B["assumptions"]["road_capacity_veh_per_h"]
E = {e["id"]: e for e in B["network"]["edges"]}
res = B["results"][KEY]


def merc(c):
    a = np.radians(np.asarray(c, float))
    return np.c_[R * a[:, 0], R * np.log(np.tan(np.pi / 4 + a[:, 1] / 2))]


def ratio(e, people):
    c = cap.get(E[e]["h"]) or cap.get(E[e]["h"].replace("_link", ""))
    return None if not c else people * veh["car_share"] / veh["persons_per_car"] / veh["evacuation_window_h"] / c


inbox = lambda c: any(BOX[0] <= p[0] <= BOX[2] and BOX[1] <= p[1] <= BOX[3] for p in c)
classes = {k: [] for k in COLOURS}
for k, v in res["load"].items():
    r = ratio(int(k), v)
    if r is not None and inbox(E[int(k)]["c"]):
        classes[0 if r < .5 else 1 if r < 1 else 2 if r < 1.5 else 3].append(merc(E[int(k)]["c"]))

def svg_masks(path):
    """Closed roads and loaded roads of the SVG as 0/255 masks at its own pixel size (geometry, not colour)."""
    txt = Path(path).read_text(encoding="utf-8")
    w, h = (int(float(v)) for v in re.search(r'<svg[^>]*width="([\d.]+)" height="([\d.]+)"', txt).groups())
    ims = {"closed": Image.new("L", (w, h), 0), "loaded": Image.new("L", (w, h), 0)}
    for attrs in re.findall(r"<path ([^>]*)/>", txt):
        stroke = re.search(r'stroke="([^"]*)"', attrs).group(1)
        kind = "closed" if stroke == "#111111" else "loaded" if stroke.startswith("rgb(") else None
        if kind:
            for sub in re.search(r'd="([^"]*)"', attrs).group(1).split("M")[1:]:
                pts = [tuple(float(v) for v in re.findall(r"-?[\d.]+", pair)) for pair in sub.split("L")]
                if len(pts) > 1:
                    ImageDraw.Draw(ims[kind]).line(pts, fill=255, width=3)
    return {k: np.asarray(v) for k, v in ims.items()}, w, h


if args.png:
    img = np.asarray(Image.open(args.png).convert("RGB")).astype(int)
    H, W = img.shape[:2]
    masks = {k: (np.abs(img - np.array(rgb)).sum(axis=2) < 40).astype(np.uint8) * 255 for k, rgb in COLOURS.items()}
    backdrop = args.png
else:
    masks, W, H = svg_masks(args.svg)
    classes = {"loaded": [m for k in (0, 1, 2, 3) for m in classes[k]], "closed": []}
    for e in res["closed"]:
        if inbox(E[e]["c"]):
            classes["closed"].append(merc(E[e]["c"]))
    backdrop = args.render
(X0, Y0), (X1, Y1) = merc([(BOX[0], BOX[3]), (BOX[2], BOX[1])])


def raster(s, lines, width, ox=0.0, oy=0.0, size=None):
    w, h = size or (int((X1 - X0) * s) + 1, int((Y0 - Y1) * s) + 1)
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for xy in lines:
        d.line([(float((x - X0) * s - ox), float((Y0 - y) * s - oy)) for x, y in xy], fill=255, width=width)
    return im


def blurred(im, r):
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255


def corr(big, t):
    shape = (big.shape[0] + t.shape[0], big.shape[1] + t.shape[1])
    return np.fft.irfft2(np.fft.rfft2(big, shape) * np.conj(np.fft.rfft2(t, shape)), shape)[: big.shape[0], : big.shape[1]]


def scale(z):
    return 256 * 2 ** z / (2 * math.pi * R)


# coarse: whole window at a quarter of the resolution, zoom 13 to 15.2
ds = 4
small = {k: blurred(Image.fromarray(m).resize((W // ds, H // ds), Image.BILINEAR), 1) for k, m in masks.items()}
best = None
zlo, zhi = (float(v) for v in args.zoom.split(","))
for z in np.arange(zlo, zhi + 0.01, 0.05):
    tot = sum(corr(blurred(raster(scale(z) / ds, classes[k], 2), 1), small[k]) for k in classes)
    iy, ix = np.unravel_index(np.argmax(tot), tot.shape)
    if best is None or tot[iy, ix] > best[0]:
        best = (float(tot[iy, ix]), float(z), int(ix) * ds, int(iy) * ds)
_, zc, oxc, oyc = best

# fine: full resolution in a +-120 px window around the coarse offset
M, best = 120, None
full = {k: blurred(Image.fromarray(m), 1.5) for k, m in masks.items()}
for z in np.arange(zc - 0.06, zc + 0.0601, 0.004):
    f = scale(z) / scale(zc)
    ox, oy = oxc * f - M, oyc * f - M
    tot = sum(corr(blurred(raster(scale(z), classes[k], 4, ox, oy, (W + 2 * M, H + 2 * M)), 1.5), full[k]) for k in classes)[: 2 * M, : 2 * M]
    iy, ix = np.unravel_index(np.argmax(tot), tot.shape)
    if best is None or tot[iy, ix] > best[0]:
        best = (float(tot[iy, ix]), float(z), ox + ix, oy + iy)
_, z, ox, oy = best
s = scale(z)
fit = {"key": KEY, "zoom_eff": round(z, 4), "s_px_per_merc_m": s, "X0": float(X0 + ox / s), "Y0": float(Y0 - oy / s), "W": W, "H": H}
Path(args.out).write_text(json.dumps(fit, indent=1))
print("fit", fit)

if args.check:
    ov = Image.open(backdrop).convert("RGB") if backdrop else Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(ov)
    P = lambda xy: [(float((x - fit["X0"]) * s), float((fit["Y0"] - y) * s)) for x, y in xy]
    for name, lines in classes.items():
        for xy in lines:
            d.line(P(xy), fill=(255, 140, 0) if name == "closed" else (255, 0, 255), width=1)
    if args.png:
        for e in res["closed"]:
            if inbox(E[e]["c"]):
                d.line(P(merc(E[e]["c"])), fill=(255, 140, 0), width=1)
    Path(args.check).parent.mkdir(parents=True, exist_ok=True)
    ov.save(args.check)
    print("check image", args.check)
