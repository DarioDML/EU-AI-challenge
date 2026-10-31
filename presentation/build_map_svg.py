"""Rebuild the pitch's route-stress map as a high-precision transparent vector (assets/route-stress-map-hd.svg).

Same picture as the Smart Shelter System full-analysis map for July 2021 (assumption set A, key obs2021|any|restrictive),
same pixel space as assets/route-stress-map.svg (1244 x 894; px = (x - X0) * s, py = (Y0 - y) * s in EPSG:3857 metres, from georef.json),
but drawn from the bundle's own geometry with 2-decimal coordinates instead of whole pixels.
Style, layer order, stress ramp (24 steps, 6 pieces per road), badge merging (44 px, busiest first) and label rules are copied from
ideas/05-smart-shelter-map/src/app.html (drawRoads, drawRoadResults, drawFlood, drawShelters, placeClustered, drawMuniLabels).
Only what lies within the viewBox plus a 40 px margin is drawn; no background, no clip rectangle.

    python powerpoint/pitch/build_map_svg.py
    python powerpoint/pitch/build_map_svg.py --bundle path/to/bundle.json
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").is_file())
BUNDLE_PATH = "ideas/05-smart-shelter-map/data/bundle.json"
BUNDLE_BLOB = "92c3d36692b7a17d34fec8c90d9f8c59c728d91c"
KEY = "obs2021|any|restrictive"
R = 6378137.0
MARGIN = 40.0
CLUSTER_PX = 44
STRESS_STOPS = [(0, (26, 152, 80)), (0.75, (240, 210, 40)), (1.25, (215, 48, 39)), (2, (122, 0, 25))]
STRESS_MAX, STRESS_STEPS, PIECES = 2, 24, 6
LABELS = ["Bad Neuenahr-Ahrweiler", "Grafschaft"]  # the two names the reference shows in this frame

ap = argparse.ArgumentParser()
ap.add_argument("--bundle", default=str(ROOT / BUNDLE_PATH))
ap.add_argument("--ref", default="origin/team1-smart-shelter-map", help="git ref used when --bundle does not exist")
ap.add_argument("--georef", default=str(HERE / "georef.json"))
ap.add_argument("--out", default=str(HERE / "assets" / "route-stress-map-hd.svg"))
args = ap.parse_args()

src = Path(args.bundle)
raw = src.read_bytes() if src.exists() else subprocess.run(["git", "show", f"{args.ref}:{BUNDLE_PATH}"], cwd=ROOT, capture_output=True, check=True).stdout
blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
if blob != BUNDLE_BLOB:
    raise SystemExit(f"Bundle changed: expected pinned blob {BUNDLE_BLOB}, got {blob}; no output written")
B = json.loads(raw.decode("utf-8"))
G = json.loads(Path(args.georef).read_text(encoding="utf-8"))
W, H = G["W"], G["H"]
E = {e["id"]: e for e in B["network"]["edges"]}
res = B["results"][KEY]
veh, cap = B["assumptions"]["vehicles"], B["assumptions"]["road_capacity_veh_per_h"]


def px(lon, lat):
    x = R * math.radians(lon)
    y = R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return ((x - G["X0"]) * G["s_px_per_merc_m"], (G["Y0"] - y) * G["s_px_per_merc_m"])


def f2(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def hits(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return max(xs) >= -MARGIN and min(xs) <= W + MARGIN and max(ys) >= -MARGIN and min(ys) <= H + MARGIN


def d_lines(lines):
    """Several polylines -> one path 'd' (one subpath each), 2 decimals, consecutive duplicates dropped."""
    out = []
    for pts in lines:
        q = []
        for p in pts:
            t = (f2(p[0]), f2(p[1]))
            if not q or t != q[-1]:
                q.append(t)
        if len(q) == 1:
            q.append(q[0])  # a dot: round caps draw it, as the canvas does
        out.append("M" + "L".join(f"{a} {b}" for a, b in q))
    return "".join(out)


def path(d, **a):
    if not d:
        return ""
    return "<path d=\"" + d + "\" " + " ".join(f"{k.replace('_', '-')}=\"{v}\"" for k, v in a.items()) + "/>"


LINE = dict(fill="none", stroke_linecap="round", stroke_linejoin="round")
EP = {i: [px(*p) for p in e["c"]] for i, e in E.items()}
EP_in = {i: pts for i, pts in EP.items() if hits(pts)}

# ---- roads, grouped as the tool does (drawRoads): major = motorway/primary, mid = secondary/tertiary, rest = minor (links included)
groups = {"major": [], "mid": [], "minor": []}
for i, e in E.items():
    if i in EP_in:
        groups["major" if e["h"] in ("motorway", "primary") else "mid" if e["h"] in ("secondary", "tertiary") else "minor"].append(EP_in[i])
svg = [path(d_lines(groups["minor"]), stroke="#9aa0a8", stroke_width=1, stroke_opacity=0.6, **LINE),
       path(d_lines(groups["mid"]), stroke="#7c828a", stroke_width=1.6, stroke_opacity=0.7, **LINE),
       path(d_lines(groups["major"]), stroke="#7c828a", stroke_width=2.6, stroke_opacity=0.85, **LINE)]

# ---- closed roads: solid black
closed = [EP_in[i] for i in res["closed"] if i in EP_in]
svg.append(path(d_lines(closed), stroke="#111111", stroke_width=2.4, stroke_opacity=1, **LINE))


# ---- flood polygons (every feature, bundle order), even-odd, clipped to the margin box (Sutherland-Hodgman)
def clip_ring(ring):
    lo, hi = (-MARGIN, -MARGIN), (W + MARGIN, H + MARGIN)
    for axis in (0, 1):
        for keep_lo in (True, False):
            lim = lo[axis] if keep_lo else hi[axis]
            ins = (lambda p: p[axis] >= lim) if keep_lo else (lambda p: p[axis] <= lim)
            nxt = []
            for a, b in zip(ring, ring[1:] + ring[:1]):
                ia, ib = ins(a), ins(b)
                if ia != ib:
                    t = (lim - a[axis]) / (b[axis] - a[axis])
                    nxt.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
                if ib:
                    nxt.append(b)
            ring = nxt
            if not ring:
                return []
    return ring


for ft in B["floods"]["obs2021"]["features"]:
    g = ft["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    d = []
    for poly in polys:
        for ring in poly:
            pts = [px(*p[:2]) for p in ring]
            if pts[0] == pts[-1]:
                pts = pts[:-1]
            if len(pts) < 3 or not hits(pts):
                continue
            c = clip_ring(pts)
            if len(c) >= 3:
                d.append("M" + "L".join(f"{f2(a)} {f2(b)}" for a, b in c) + "Z")
    svg.append(path("".join(d), fill="#56B4E9", fill_opacity=0.35, fill_rule="evenodd", stroke="#0072B2", stroke_width=1.5,
                    stroke_opacity=1, stroke_linecap="round", stroke_linejoin="round"))


# ---- used roads (blue underlay) and stress ramp
def stress_rgb(r):
    x = max(0, min(STRESS_MAX, r))
    for k in range(1, len(STRESS_STOPS)):
        x1, c1 = STRESS_STOPS[k]
        if x <= x1:
            x0, c0 = STRESS_STOPS[k - 1]
            f = (x - x0) / (x1 - x0)
            return "rgb(" + ",".join(str(math.floor(v + f * (c1[j] - v) + 0.5)) for j, v in enumerate(c0)) + ")"
    return "rgb(122,0,25)"


def ratio(eid, people):
    e = E[eid]
    c = cap.get(e["h"]) or cap.get(e["h"].replace("_link", ""))
    return None if not c else people * veh["car_share"] / veh["persons_per_car"] / veh["evacuation_window_h"] / c


load_ids = [int(k) for k in res["load"]]
svg.append(path(d_lines([EP_in[i] for i in load_ids if i in EP_in]), stroke="#0072B2", stroke_width=2.5, stroke_opacity=0.7, **LINE))

key = lambda p: f"{p[0]:.5f},{p[1]:.5f}"
rat, node = {}, {}
for i in load_ids:
    r = ratio(i, res["load"][str(i)])
    c = E[i]["c"]
    if r is None or len(c) < 2:
        continue
    rat[i] = r
    for q in (c[0], c[-1]):
        s = node.setdefault(key(q), [0.0, 0])
        s[0] += r
        s[1] += 1
node_r = lambda q: node[key(q)][0] / node[key(q)][1] if key(q) in node else None
buckets = [[] for _ in range(STRESS_STEPS + 1)]
for i, r in rat.items():
    c = E[i]["c"]
    a, b = node_r(c[0]), node_r(c[-1])
    r0 = (r + (r if a is None else a)) / 2
    r1 = (r + (r if b is None else b)) / 2
    P = EP[i]
    length, cum = 0.0, [0.0]
    for k in range(1, len(c)):
        length += math.hypot(c[k][0] - c[k - 1][0], c[k][1] - c[k - 1][1])
        cum.append(length)
    for k in range(PIECES):
        t0, t1 = k / PIECES, (k + 1) / PIECES
        pts = []
        for j in range(len(c) - 1):
            s0, s1 = (cum[j] / length, cum[j + 1] / length) if length else (0, 1)
            if s1 < t0 or s0 > t1:
                continue
            span = (s1 - s0) or 1
            f = lambda u: (P[j][0] + (P[j + 1][0] - P[j][0]) * u, P[j][1] + (P[j + 1][1] - P[j][1]) * u)
            if not pts:
                pts.append(f(max(0, (t0 - s0) / span)))
            pts.append(f(min(1, (t1 - s0) / span)))
        if len(pts) > 1 and hits(pts):
            rr = r0 + (r1 - r0) * (k + 0.5) / PIECES
            buckets[min(STRESS_STEPS, math.floor(max(0, rr) / STRESS_MAX * STRESS_STEPS))].append(pts)
for n, lines in enumerate(buckets):
    if lines:
        r = (n + 0.5) / STRESS_STEPS * STRESS_MAX
        svg.append(path(d_lines(lines), stroke=stress_rgb(r), stroke_width=f"{2.5 + 4 * min(1, max(0, r) / STRESS_MAX):.3f}",
                        stroke_opacity=0.95, **LINE))

# ---- shelter badges: used buildings (load >= 0.5), busiest first, each joins the first group within 44 px of its centre
S = {s["id"]: s for s in B["shelters"]}
used = sorted(((S[int(k)], v) for k, v in res["shelter_load"].items() if v >= 0.5 and int(k) in S), key=lambda x: -x[1])
clusters = []
for s, v in used:
    p = px(s["lon"], s["lat"])
    for c in clusters:
        if math.hypot(c["x"] - p[0], c["y"] - p[1]) < CLUSTER_PX:
            c["n"] += 1
            break
    else:
        clusters.append({"x": p[0], "y": p[1], "n": 1})
for c in clusters:
    x, y, n = c["x"], c["y"], c["n"]
    if not (-MARGIN <= x <= W + MARGIN and -MARGIN <= y <= H + MARGIN):
        continue
    size = 22 if n == 1 else round(min(40, 22 + 4 * math.log2(n)))
    r = size / 2
    svg.append(f'<circle cx="{f2(x)}" cy="{f2(y)}" r="{f2(r)}" fill="#C2185B" stroke="#ffffff" stroke-width="2"/>'
               f'<circle cx="{f2(x)}" cy="{f2(y)}" r="{f2(r - 1)}" fill="none" stroke="#12000A" stroke-width="2"/>'
               f'<text x="{f2(x)}" y="{f2(y)}" dy="0.35em" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" '
               f'font-weight="700" font-size="13" fill="#ffffff">{n}</text>')

# ---- municipality names at the centre of the outline's bounding box, white halo under dark text
for m in B["munis"]:
    if m["name"] not in LABELS:
        continue
    pts = []

    def walk(o):
        if isinstance(o[0], (int, float)):
            pts.append(o)
        else:
            for q in o:
                walk(q)
    walk(m["geometry"]["coordinates"])
    lon = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    lat = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    x, y = px(lon, lat)
    svg.append(f'<text x="{f2(x)}" y="{f2(y)}" dy="0.35em" text-anchor="middle" font-family="Segoe UI, Arial, Helvetica, sans-serif" '
               f'font-weight="700" font-size="14" fill="#111111" stroke="#ffffff" stroke-width="3.5" stroke-linejoin="round" '
               f'paint-order="stroke">{m["name"]}</text>')

out = Path(args.out)
out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
               + "".join(svg) + "</svg>", encoding="utf-8")
print(out, out.stat().st_size, "bytes;", len(clusters), "badges;", len(EP_in), "edges in frame")
