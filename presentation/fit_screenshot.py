"""Fit the map screenshot to Web Mercator so real routes can be drawn on it (writes georef.json).

The screenshot 'powerpoint/visualisation busy roates + flooded areas.png' is the Smart Shelter System map
(July 2021 flood, assumption set A). Its coloured roads are the tool's road-stress classes, so we rasterise the
bundle's loaded roads per class and find the zoom and offset that overlay them best (FFT cross-correlation,
coarse then fine). Model: px = (x - X0) * s, py = (Y0 - y) * s, with x, y in EPSG:3857 metres.
Check: --check writes the screenshot with the bundle's roads drawn 1 px thin on top; look at it.

    python powerpoint/pitch/fit_screenshot.py --check figures/generated/pitch_georef_check.png
"""
import argparse
import json
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / ".git").exists())  # repo root, wherever this folder sits
BUNDLE_PATH = "ideas/05-smart-shelter-map/data/bundle.json"
KEY = "obs2021|any|restrictive"
BOX = (6.95, 50.47, 7.30, 50.62)  # search window around Bad Neuenahr-Ahrweiler, lon/lat
COLOURS = {0: (0, 158, 115), 1: (240, 228, 66), 2: (213, 94, 0), 3: (122, 0, 25)}  # the page's STRESS colours
R = 6378137.0

ap = argparse.ArgumentParser()
ap.add_argument("--bundle", default=str(ROOT / BUNDLE_PATH))
ap.add_argument("--ref", default="origin/team1-smart-shelter-map")
ap.add_argument("--png", default=str(ROOT / "powerpoint" / "visualisation busy roates + flooded areas.png"))
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

img = np.asarray(Image.open(args.png).convert("RGB")).astype(int)
H, W = img.shape[:2]
masks = {k: (np.abs(img - np.array(rgb)).sum(axis=2) < 40).astype(np.uint8) * 255 for k, rgb in COLOURS.items()}
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
for z in np.arange(13.0, 15.21, 0.05):
    tot = sum(corr(blurred(raster(scale(z) / ds, classes[k], 2), 1), small[k]) for k in COLOURS)
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
    tot = sum(corr(blurred(raster(scale(z), classes[k], 4, ox, oy, (W + 2 * M, H + 2 * M)), 1.5), full[k]) for k in COLOURS)[: 2 * M, : 2 * M]
    iy, ix = np.unravel_index(np.argmax(tot), tot.shape)
    if best is None or tot[iy, ix] > best[0]:
        best = (float(tot[iy, ix]), float(z), ox + ix, oy + iy)
_, z, ox, oy = best
s = scale(z)
fit = {"key": KEY, "zoom_eff": round(z, 4), "s_px_per_merc_m": s, "X0": float(X0 + ox / s), "Y0": float(Y0 - oy / s), "W": W, "H": H}
Path(args.out).write_text(json.dumps(fit, indent=1))
print("fit", fit)

if args.check:
    ov = Image.open(args.png).convert("RGB")
    d = ImageDraw.Draw(ov)
    P = lambda xy: [(float((x - fit["X0"]) * s), float((fit["Y0"] - y) * s)) for x, y in xy]
    for lines in classes.values():
        for xy in lines:
            d.line(P(xy), fill=(255, 0, 255), width=1)
    for e in res["closed"]:
        if inbox(E[e]["c"]):
            d.line(P(merc(E[e]["c"])), fill=(255, 140, 0), width=1)
    Path(args.check).parent.mkdir(parents=True, exist_ok=True)
    ov.save(args.check)
    print("check image", args.check)
