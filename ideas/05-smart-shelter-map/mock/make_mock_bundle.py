"""Writes tool/data/mock_bundle.json: a SYNTHETIC bundle in the BUNDLE_SCHEMA.md format.

What it is: a made-up ~3.5 x 3.3 km area (lon 6.45-6.50, lat 50.52-50.55), a distorted road grid with a
meandering river valley, four flood levels, 2 shelter-capacity assumptions, ~40 zones, 25 shelters.
Nothing here is a real street, building or flood. It only exists so the page can be built and checked
before the real pipeline bundle exists.

Results are computed here with a tiny self-contained method (no imports from lib/):
  - closed roads = edges touching water (rule "wet") or water deeper than 0.5 m (rule "d05")
  - Dijkstra on the open graph from each zone, travel time = length / assumed class speed
  - greedy capacity-limited assignment: all (zone, shelter) pairs sorted by travel time, people are
    placed into the nearest shelter with free room; the rest are UNASSIGNED (never dropped)
Run:  .venv\\Scripts\\python.exe -B -I tool\\mock\\make_mock_bundle.py
"""
import base64
import heapq
import json
import math
import os
import random
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "data", "mock_bundle.json"))
random.seed(2026)

LON0, LON1, LAT0, LAT1 = 6.45, 6.50, 50.52, 50.55
LAT_M = 111200.0
LON_M = 111200.0 * math.cos(math.radians(50.535))
W = (LON1 - LON0) * LON_M
H = (LAT1 - LAT0) * LAT_M


def lonlat(x, y):
    return [round(LON0 + x / LON_M, 5), round(LAT0 + y / LAT_M, 5)]


# ---------------------------------------------------------------- river and flood model
def river_y(x):
    return H * 0.5 + 260 * math.sin(x / 800 + 0.6) + 90 * math.sin(x / 310)


def river_slope(x):
    return 260 / 800 * math.cos(x / 800 + 0.6) + 90 / 310 * math.cos(x / 310)


# half width (m) of the flooded strip and maximum depth (m) per flood level
LEVEL = {"obs2021": (380, 1.0), "rp10": (170, 1.0), "rp100": (330, 2.0), "rp500": (480, 3.0)}
SCEN_IDS = ["obs2021", "rp10", "rp100", "rp500"]


def half_width(sc, x):
    return LEVEL[sc][0] * (0.85 + 0.15 * math.sin(x / 260))


def river_dist(x, y):
    """Approximate perpendicular distance to the river centre line (m)."""
    return abs(y - river_y(x)) / math.sqrt(1 + river_slope(x) ** 2)


def depth(sc, x, y):
    w = half_width(sc, x)
    d = river_dist(x, y)
    return 0.0 if d >= w else LEVEL[sc][1] * (1 - d / w)


# ---------------------------------------------------------------- road network
NX, NY = 16, 13
ROW_CLASS = {5: ("primary", "B 266"), 2: ("secondary", "L 115"), 10: ("secondary", "L 98")}
COL_CLASS = {3: ("tertiary", "K 42"), 8: ("primary", "B 477"), 12: ("tertiary", "K 55")}
STREETS = ["Bachweg", "Muehlenweg", "Am Hang", "Feldstrasse", "Kirchgasse", "Lindenallee",
           "Schulstrasse", "Bergstrasse", "Wiesenweg", "Gartenstrasse", "Talweg", "Birkenweg",
           "Rosenweg", "Am Wald", "Dorfstrasse", "Heideweg"]
SPEED = {"primary": 80 / 3.6, "secondary": 50 / 3.6, "tertiary": 40 / 3.6, "residential": 16 / 3.6}

nodes = []  # (x, y)
for j in range(NY):
    for i in range(NX):
        x = i * W / (NX - 1)
        y = j * H / (NY - 1)
        inner = 0 < i < NX - 1 and 0 < j < NY - 1
        if inner:
            x += 70 * math.sin(y / 650 + i * 0.1) + random.uniform(-35, 35)
            y += 90 * math.sin(x / 900) + random.uniform(-35, 35)
        nodes.append((min(max(x, 0), W), min(max(y, 0), H)))


def nid(i, j):
    return j * NX + i


raw_edges = []  # (a, b, cls, name)
row_names = {j: STREETS[j % len(STREETS)] for j in range(NY)}
col_names = {i: STREETS[(i + 5) % len(STREETS)] for i in range(NX)}
for j in range(NY):
    for i in range(NX - 1):
        cls, name = ROW_CLASS.get(j, ("residential", row_names[j]))
        raw_edges.append((nid(i, j), nid(i + 1, j), cls, name))
for i in range(NX):
    for j in range(NY - 1):
        cls, name = COL_CLASS.get(i, ("residential", col_names[i]))
        raw_edges.append((nid(i, j), nid(i, j + 1), cls, name))
for _ in range(14):  # a few diagonals so it is not a perfect grid
    i, j = random.randrange(1, NX - 2), random.randrange(1, NY - 2)
    raw_edges.append((nid(i, j), nid(i + 1, j + 1), "residential", "Verbindungsweg"))

edges = []
for eid, (a, b, cls, name) in enumerate(raw_edges):
    (xa, ya), (xb, yb) = nodes[a], nodes[b]
    # one bend in the middle so lines are not ruler straight
    mx, my = (xa + xb) / 2, (ya + yb) / 2
    L = math.hypot(xb - xa, yb - ya) or 1
    off = random.uniform(-14, 14)
    mx += -(yb - ya) / L * off
    my += (xb - xa) / L * off
    pts = [(xa, ya), (mx, my), (xb, yb)]
    length = sum(math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) for k in range(2))
    side_a = ya - river_y(xa) > 0
    side_b = yb - river_y(xb) > 0
    edges.append({"id": eid, "a": a, "b": b, "pts": pts, "len": length, "cls": cls, "name": name,
                  "bridge": 1 if side_a != side_b else 0})

adj = {n: [] for n in range(len(nodes))}
for e in edges:
    adj[e["a"]].append((e["b"], e["id"]))
    adj[e["b"]].append((e["a"], e["id"]))


def edge_depth(sc, e):
    """Max depth along an edge, sampled at 5 points (a road is wet if any part is wet)."""
    p = e["pts"]
    samples = [p[0], ((p[0][0] + p[1][0]) / 2, (p[0][1] + p[1][1]) / 2), p[1],
               ((p[1][0] + p[2][0]) / 2, (p[1][1] + p[2][1]) / 2), p[2]]
    return max(depth(sc, x, y) for x, y in samples)


EDGE_DEPTH = {sc: [edge_depth(sc, e) for e in edges] for sc in SCEN_IDS}
CLOSURE_RULES = {
    "obs2021": [("any", "road closed if it touches the flood", 0.0)],
    "rp10": [("wet", "closed under any water", 0.0), ("d05", "closed under more than 0.5 m", 0.5)],
    "rp100": [("wet", "closed under any water", 0.0), ("d05", "closed under more than 0.5 m", 0.5)],
    "rp500": [("wet", "closed under any water", 0.0), ("d05", "closed under more than 0.5 m", 0.5)],
}

# ---------------------------------------------------------------- zones and shelters
MUNIS = ["Musterdorf-West", "Beispielhausen", "Testingen-Ost"]


def muni_at(x):
    return MUNIS[min(2, int(x / (W / 3)))]


near_river = [n for n, (x, y) in enumerate(nodes) if river_dist(x, y) <= 750]
random.shuffle(near_river)
zone_nodes = near_river[:40]
used_nodes = set(zone_nodes)
zones = []
for zid, n in enumerate(zone_nodes):
    x, y = nodes[n]
    pop = int(min(3000, max(150, math.exp(random.gauss(5.3, 0.6)))))
    people = {}
    for sc in SCEN_IDS:
        share = max(0.0, 1 - river_dist(x, y) / (half_width(sc, x) * 1.6))
        people[sc] = int(round(pop * share))
    lon, lat = lonlat(x, y)
    zones.append({"id": zid, "lon": lon, "lat": lat, "muni": muni_at(x), "people": people, "_node": n})

TYPES = [("school", "education", (900, 3000)), ("sports_hall", "sport", (1200, 2800)),
         ("community_centre", "community", (400, 1200)), ("civic", "civic", (500, 1800)),
         ("church", "religious", (250, 900)), ("hotel", "accommodation", (800, 2500))]
TYPE_SEQ = ["school", "sports_hall", "community_centre", "civic", "church", "school", "church",
            "sports_hall", "hotel", "community_centre", "school", "civic", "church", "hotel",
            "sports_hall", "school", "community_centre", "church", "civic", "school", "church",
            "sports_hall", "community_centre", "school", "civic"]
CORE = {"school", "sports_hall", "community_centre", "civic"}
CAPACITY = {"restrictive": {"m2_per_person": 5.0, "usable_share": 0.4, "cap_max": 500, "tiers": "core"},
            "generous": {"m2_per_person": 3.5, "usable_share": 0.7, "cap_max": 1500, "tiers": "core + extended"}}

cand = [n for n in range(len(nodes)) if n not in used_nodes]
wet_cand = [n for n in cand if river_dist(*nodes[n]) <= 600]
dry_cand = [n for n in cand if river_dist(*nodes[n]) > 600]
random.shuffle(wet_cand)
random.shuffle(dry_cand)
shelter_nodes = wet_cand[:8] + dry_cand[:17]
random.shuffle(shelter_nodes)
shelters = []
for sid, n in enumerate(shelter_nodes):
    t = TYPE_SEQ[sid]
    kind, (lo, hi) = next((k, r) for tt, k, r in TYPES if tt == t)
    fp = int(random.uniform(lo, hi) * 1.7)
    x, y = nodes[n]
    cap = {}
    for cid, a in CAPACITY.items():
        ok = (t in CORE) or a["tiers"] != "core"
        cap[cid] = int(min(a["cap_max"], fp * a["usable_share"] / a["m2_per_person"])) if ok else 0
    flooded = {sc: depth(sc, x, y) > 0 for sc in SCEN_IDS}
    lon, lat = lonlat(x + 12, y + 9)
    shelters.append({"id": sid, "lon": lon, "lat": lat, "type": t, "kind": kind, "footprint_m2": fp,
                     "muni": muni_at(x), "cap": cap, "flooded": flooded, "_node": n})

# ---------------------------------------------------------------- assumptions
VEH = {"car_share": 0.8, "persons_per_car": 2.0, "evacuation_window_h": 1.0}
ROAD_CAP = {"motorway": 3600, "primary": 1600, "secondary": 1200, "tertiary": 900, "residential": 400}
MAX_MIN = 20


def dijkstra(src, closed):
    dist = {src: 0.0}
    prev = {}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e18):
            continue
        for v, eid in adj[u]:
            if eid in closed:
                continue
            e = edges[eid]
            nd = d + e["len"] / SPEED[e["cls"]]
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = (u, eid)
                heapq.heappush(pq, (nd, v))
    return dist, prev


def path(prev, src, dst):
    out = []
    while dst != src:
        u, eid = prev[dst]
        out.append(eid)
        dst = u
    return out[::-1]


FREE_CACHE = {}


def free_from(n):
    """Dijkstra with no closures, cached per origin node."""
    if n not in FREE_CACHE:
        FREE_CACHE[n] = dijkstra(n, set())
    return FREE_CACHE[n]


def access_nodes(closed):
    """Zone -> access node. A zone whose own junction is cut off by closures is snapped to the nearest junction
    of the largest connected part of the open network (as a real pipeline would snap demand to the network)."""
    seen, best = set(), set()
    for n0 in adj:
        if n0 in seen:
            continue
        comp, stack = {n0}, [n0]
        while stack:
            u = stack.pop()
            for v, eid in adj[u]:
                if eid not in closed and v not in comp:
                    comp.add(v)
                    stack.append(v)
        seen |= comp
        if len(comp) > len(best):
            best = comp
    out = {}
    for z in zones:
        x, y = nodes[z["_node"]]
        out[z["id"]] = min(best, key=lambda m: (nodes[m][0] - x) ** 2 + (nodes[m][1] - y) ** 2)
    return out


def solve(sc, rule_thr, capid):
    closed = {e["id"] for e in edges if EDGE_DEPTH[sc][e["id"]] > rule_thr or (rule_thr == 0.0 and EDGE_DEPTH[sc][e["id"]] > 0)}
    usable = [s for s in shelters if not s["flooded"][sc] and s["cap"][capid] > 0]
    pairs = []
    routes = {}
    acc = access_nodes(closed)
    for z in zones:
        if z["people"][sc] <= 0:
            continue
        dist, prev = dijkstra(acc[z["id"]], closed)
        for s in usable:
            t = dist.get(s["_node"])
            if t is not None and t <= MAX_MIN * 60:
                pairs.append((t, z["id"], s["id"]))
                routes[(z["id"], s["id"])] = path(prev, acc[z["id"]], s["_node"])
    pairs.sort()
    remaining = {z["id"]: z["people"][sc] for z in zones if z["people"][sc] > 0}
    free = {s["id"]: s["cap"][capid] for s in usable}
    assign = []
    for t, zid, sid in pairs:
        n = min(remaining[zid], free[sid])
        if n <= 0:
            continue
        remaining[zid] -= n
        free[sid] -= n
        zn = acc[zid]
        fd, fprev = free_from(zn)
        tfree = fd[shelters[sid]["_node"]]
        fr = path(fprev, zn, shelters[sid]["_node"])
        assign.append([zid, sid, n, int(round(t)), int(round(tfree)), routes[(zid, sid)], fr])
    unassigned = {str(k): v for k, v in remaining.items() if v > 0}
    sload = {}
    eload = {}
    for zid, sid, n, t, tf, r, fr in assign:
        sload[str(sid)] = sload.get(str(sid), 0) + n
        for eid in r:
            eload[str(eid)] = eload.get(str(eid), 0) + n
    # checks (known-answer style, cheap)
    for zid, sid, n, t, tf, r, fr in assign:
        assert not (set(r) & closed), "route uses a closed edge"
    for sid, n in sload.items():
        assert n <= shelters[int(sid)]["cap"][capid]
    tot = sum(z["people"][sc] for z in zones)
    placed = sum(a[2] for a in assign)
    assert placed + sum(unassigned.values()) == tot
    ratios = []
    for k, v in eload.items():
        veh = v * VEH["car_share"] / VEH["persons_per_car"] / VEH["evacuation_window_h"]
        ratios.append(veh / ROAD_CAP[edges[int(k)]["cls"]])
    fills = [sload[str(s["id"])] / s["cap"][capid] for s in usable if str(s["id"]) in sload]
    summary = {
        "people_to_place": tot, "placed": placed, "unassigned": tot - placed,
        "shelters_used": len(sload), "max_shelter_fill": round(max(fills), 2) if fills else 0.0,
        "closed_edges": len(closed),
        "mean_time_min": round(sum(a[2] * a[3] for a in assign) / placed / 60, 1) if placed else 0.0,
        "mean_detour_min": round(sum(a[2] * (a[3] - a[4]) for a in assign) / placed / 60, 1) if placed else 0.0,
        "worst_road_ratio": round(max(ratios), 2) if ratios else 0.0,
    }
    return {"closed": sorted(closed), "assign": assign, "unassigned": unassigned,
            "shelter_load": sload, "load": eload, "summary": summary}


results = {}
for sc in SCEN_IDS:
    for cid, _, thr in CLOSURE_RULES[sc]:
        for capid in CAPACITY:
            results[f"{sc}|{cid}|{capid}"] = solve(sc, thr, capid)


# ---------------------------------------------------------------- flood polygon and overlay PNGs
def flood_polygon(sc):
    xs = [k * 100.0 for k in range(int(W / 100) + 2)]
    top, bot = [], []
    for x in xs:
        x = min(x, W)
        ry = river_y(x)
        off = half_width(sc, x) * math.sqrt(1 + river_slope(x) ** 2)
        top.append(lonlat(x, ry + off))
        bot.append(lonlat(x, ry - off))
    ring = top + bot[::-1]
    ring.append(ring[0])
    return {"type": "Feature", "properties": {"source": "synthetic mock"},
            "geometry": {"type": "Polygon", "coordinates": [ring]}}


def png_rgba(width, height, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def overlay(sc):
    pw, ph = 100, 80
    rows = []
    for py in range(ph):
        row = []
        for px in range(pw):
            x = (px + 0.5) / pw * W
            y = (1 - (py + 0.5) / ph) * H
            d = depth(sc, x, y)
            if d <= 0:
                row += [0, 0, 0, 0]
            elif d <= 0.5:
                row += [158, 202, 225, 190]
            elif d <= 1.0:
                row += [66, 146, 198, 200]
            else:
                row += [8, 81, 156, 210]
        rows.append(row)
    png = base64.b64encode(png_rgba(pw, ph, rows)).decode()
    return {"scenario": sc, "png": "data:image/png;base64," + png, "bounds": [[LAT0, LON0], [LAT1, LON1]],
            "legend": [{"label": "0 - 0.5 m", "color": "#9ecae1"}, {"label": "0.5 - 1 m", "color": "#4292c6"},
                       {"label": "more than 1 m", "color": "#08519c"}]}


# ---------------------------------------------------------------- assemble
bundle = {
    "meta": {
        "title": "Smart shelter system: planning aid (MOCK DATA)",
        "area": "Synthetic mock area (not a real place)",
        "generated_utc": "2026-10-29T12:00:00Z",
        "mock": True,
        "bounds": [LON0, LAT0, LON1, LAT1],
        "disclaimer": "Planning aid, not live guidance. Built from a 2021 flood snapshot, 2026 OpenStreetMap and "
                      "unverified assumptions. Shelters are candidate buildings, not officially designated; routes "
                      "avoid mapped flooded roads only and are not verified as safe. All numbers are minimums or "
                      "assumption-driven estimates. THIS FILE IS SYNTHETIC MOCK DATA.",
        "data_notes": ["MOCK: the roads, buildings, zones and floods in this file are invented to test the page.",
                       "Flood levels: one 'observed' snapshot and three 'modelled' return periods, drawn from a made-up river model.",
                       "Population per zone is a made-up number of residents to place at each flood level (a minimum)."],
        "limits": ["MOCK: no result here says anything about a real place.",
                   "Travel time = length / assumed class speed; no congestion, no traffic simulation.",
                   "Unmapped or not-assessed areas are not dry; a route avoiding mapped flooded roads is not verified safe.",
                   "Assignment is a greedy nearest-shelter method with capacity limits, not an optimum."],
    },
    "assumptions": {
        "capacity": CAPACITY,
        "vehicles": VEH,
        "road_capacity_veh_per_h": ROAD_CAP,
        "assignment": {"method": "greedy nearest shelter, capacity limited", "max_travel_min": MAX_MIN},
        "notes": ["ASSUMPTION: capacity = footprint x usable share / m2 per person, capped at cap_max; 'core' types are school, sports hall, community centre, civic; 'extended' adds churches, hotels etc.",
                  "ASSUMPTION: vehicles per hour = people x car share / persons per car / evacuation window (h).",
                  "ASSUMPTION: class speeds 80/50/40/16 km/h for primary/secondary/tertiary/residential."],
    },
    "scenarios": [
        {"id": "obs2021", "label": "Observed July 2021 (EMS snapshot)", "kind": "observed",
         "note": "MOCK. A snapshot after the peak; flooded areas that were not mapped appear dry.",
         "closures": [{"id": c, "label": l} for c, l, _ in CLOSURE_RULES["obs2021"]]},
        {"id": "rp10", "label": "10-year flood (EFAS model)", "kind": "modelled", "note": "MOCK. Modelled depth.",
         "closures": [{"id": c, "label": l} for c, l, _ in CLOSURE_RULES["rp10"]]},
        {"id": "rp100", "label": "100-year flood (EFAS model)", "kind": "modelled", "note": "MOCK. Modelled depth.",
         "closures": [{"id": c, "label": l} for c, l, _ in CLOSURE_RULES["rp100"]]},
        {"id": "rp500", "label": "500-year flood (EFAS model)", "kind": "modelled",
         "note": "MOCK. A ceiling-type map; real events can exceed it.",
         "closures": [{"id": c, "label": l} for c, l, _ in CLOSURE_RULES["rp500"]]},
    ],
    "capacities": [{"id": "restrictive", "label": "Restrictive shelter capacity"},
                   {"id": "generous", "label": "Generous shelter capacity"}],
    "floods": {"obs2021": {"type": "FeatureCollection", "features": [flood_polygon("obs2021")]}},
    "overlays": [overlay(s) for s in ["rp10", "rp100", "rp500"]],
    "network": {"edges": [{"id": e["id"], "c": [lonlat(x, y) for x, y in e["pts"]], "h": e["cls"], "n": e["name"],
                           "b": e["bridge"], "t": 0} for e in edges]},
    "zones": [{k: v for k, v in z.items() if not k.startswith("_")} for z in zones],
    "shelters": [{k: v for k, v in s.items() if not k.startswith("_")} for s in shelters],
    "results": results,
    "road_ratio_note": "worst_road_ratio and any road colour = people on the edge, turned into vehicles per hour, "
                       "divided by an ASSUMED capacity: a stress indicator, not a traffic forecast",
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))

print("wrote", OUT, os.path.getsize(OUT) // 1024, "KB;", len(edges), "edges,", len(zones), "zones,",
      len(shelters), "shelters,", len(results), "results")
for k, r in results.items():
    s = r["summary"]
    maxdet = max([a[3] - a[4] for a in r["assign"]] or [0])
    print(f"{k:24s} people {s['people_to_place']:5d} placed {s['placed']:5d} unassigned {s['unassigned']:5d} "
          f"closed {s['closed_edges']:3d} fill {s['max_shelter_fill']:.2f} detour {s['mean_detour_min']:4.1f} "
          f"maxdetour_s {maxdet:4d} ratio {s['worst_road_ratio']:.2f}")
