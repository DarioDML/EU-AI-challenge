"""Question:    Policy tool (smart shelter system). For each flood level (observed 2021, EFAS RP10 / RP100 / RP500), each road-closure rule and each shelter-capacity assumption:
              which zone goes to which shelter, by which route, with what detour, and which roads carry how many people? Writes the bundle the web page reads.
Data:         roads: run of 18_tool_roads.py (OSM ways split at shared vertices, state 29 Oct 2026); scenarios: run of 19_tool_scenarios.py (residents per flood level on 250 m nodes, EFAS
              depth windows); shelters: run 20261029-134745-b0be q3_candidates.csv (OSM building polygons, state 29 Oct 2026); observed flood: run 20261029-101321-bf98 (EMS flood + trace);
              GISCO LAU 2024 (municipality names and country); optional building names: run of 30_tool_building_names.py (OSM name and address tags of the candidates, same extract).
Assumptions:  GERMANY ONLY, hero area Eifel and Ahr valley (decision 2026-10-29). Every number rests on ASSUMPTIONS without a verified source: free-flow speeds per road class, closure
              depth (any water / more than 0.5 m under EFAS; touching the EMS flood or trace for 2021), shelter capacity (space per person, usable share, per-building cap; restrictive =
              core buildings only, generous = core + extended), car share, persons per car, an evacuation window, road capacities. A flooded shelter is not usable; reach is by road on the open
              network (a closed road is removed, never driven through). EFAS holds values only where wet and misses smaller rivers (for example at Kall and on the Ahr), so an EFAS closure set is a MINIMUM and
              empty never means dry. Observed 2021 is one satellite snapshot per area (14-20 July 2021), not the peak. Zones are 500 m cells; people on a zone are placed together. The road 'stress' is people turned into vehicles per hour
              divided by an assumed capacity: an indicator, not a traffic forecast. Nothing is a designated shelter or an official route.
Tools:        challenge.roads / evac / shelter (26 known-answer tests), geopandas, shapely STRtree, scipy sparse Dijkstra and HiGHS, PIL (overlay PNGs).
Outputs:      tool/data/bundle.json (+ research/r01/outputs/tool_pipeline_checks.json)
Finding:      research/r01/NOTE.md
"""
import base64
import io
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from PIL import Image
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.strtree import STRtree

root = Path(sys.argv[1])
ROADS, SCEN, CAND, FLOODOUT = (root / a for a in sys.argv[2:6])
SCEN25 = root / sys.argv[6] if len(sys.argv) > 6 else None      # optional: residents per scenario from GHS-POP E2025 (a projection; sensitivity only, 19b_tool_scenarios_pop2025.py)
NAMES = root / sys.argv[7] if len(sys.argv) > 7 else None       # optional: OSM name and address per candidate (30_tool_building_names.py, same 29 Oct 2026 extract); without it shelters get no name/street
YEARS = [("pop2020", "people_", "")] + ([("pop2025", "p25_", "|pop2025")] if SCEN25 else [])      # (id, zone column prefix, result-key suffix): 2020 keys stay unchanged
OUTB = root / "tool/data/bundle.json"
sys.path.insert(0, str(root / "lib"))
from challenge import evac, roads as rd, shelter as sh

T0 = time.time()
G = root / "reference/data_docs/retrieval-cache/external/gisco"
HERO = (6.30, 50.30, 7.45, 50.78)
CHECKS = {}


def lap(msg):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def check(name, ok, **detail):
    CHECKS[name] = {"pass": bool(ok), **detail}
    lap(f"check {name}: {'PASS' if ok else 'FAIL'} {json.dumps(detail, default=str)[:300]}")
    assert ok, f"check failed: {name} {detail}"


import re
RUNID = lambda p: (re.search(r"\d{8}-\d{6}-[0-9a-f]{4}", str(p)) or [None])[0]
tr = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
inv = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)

# ---------------------------------------------------------------- roads -> compact graph
ed = gpd.read_parquet(ROADS / "edges.parquet").reset_index(drop=True)
nd = pd.read_parquet(ROADS / "nodes.parquet")
used, comp = np.unique(np.concatenate([ed.u.values, ed.v.values]), return_inverse=True)
cu, cv = comp[:len(ed)], comp[len(ed):]
node_xy = nd.loc[used, ["x", "y"]].values
main = nd.loc[used, "main_component"].values
NN = len(used)
g0, arc0 = rd.build_digraph(cu, cv, ed.time_s.values, ed.oneway.values, NN)
lap(f"{len(ed):,} edges, {NN:,} graph nodes, {int(main.sum()):,} in the main component")

# ---------------------------------------------------------------- closures per scenario
geo = ed.geometry.values
xy, eidx = shapely.get_coordinates(shapely.segmentize(geo, 25.0), return_index=True)      # EFAS depth is sampled at least every 25 m along each road, so a wet cell between two vertices is not missed
lon, lat = inv.transform(xy[:, 0], xy[:, 1])
z = np.load(SCEN / "efas_windows.npz")


def efas_sample(rp, lo, la):
    arr, tf = z[f"{rp}_arr"].astype("float32"), z[f"{rp}_tf"]
    a, c, e, f = tf[0], tf[2], tf[4], tf[5]
    col, row = np.floor((lo - c) / a).astype(int), np.floor((la - f) / e).astype(int)
    ok = (row >= 0) & (row < arr.shape[0]) & (col >= 0) & (col < arr.shape[1])
    d = np.full(len(lo), np.nan, dtype="float32")
    d[ok] = arr[row[ok], col[ok]]
    return d


flood_t = gpd.read_file(FLOODOUT / "q1_flood_layers.gpkg", layer="flood_with_traces").geometry.union_all()
flood_h = gpd.read_file(FLOODOUT / "q1_flood_layers.gpkg", layer="flood_headline").geometry.union_all()
tree_e = STRtree(geo)
closed = {"obs2021|any": np.zeros(len(ed), bool), "obs2021|mapped": np.zeros(len(ed), bool)}
closed["obs2021|any"][tree_e.query(flood_t, predicate="intersects")] = True            # flood OR flood trace
closed["obs2021|mapped"][tree_e.query(flood_h, predicate="intersects")] = True         # the mapped flooded area only (traces ignored): a sensitivity
for rp in ("rp10", "rp100", "rp500"):
    d = efas_sample(rp.upper(), lon, lat)
    mx = pd.Series(d).groupby(eidx).max().reindex(np.arange(len(ed))).values            # max depth along each edge (NaN: empty = dry OR not modelled)
    closed[f"{rp}|wet"] = np.isfinite(mx) & (mx > 0)
    closed[f"{rp}|d05"] = np.isfinite(mx) & (mx >= 0.5)
FLIPPED = {}
for th in ("wet", "d05"):             # a larger flood must not reopen a road that a smaller flood closed: enforce it and count the edges where the independent EFAS maps disagreed
    FLIPPED[th] = int((closed[f"rp10|{th}"] & ~closed[f"rp100|{th}"]).sum() + (closed[f"rp100|{th}"] & ~closed[f"rp500|{th}"]).sum())
    closed[f"rp100|{th}"] |= closed[f"rp10|{th}"]
    closed[f"rp500|{th}"] |= closed[f"rp100|{th}"]
lap("closures: " + ", ".join(f"{k} {int(v.sum()):,}" for k, v in closed.items()) + f"; edges made nested (EFAS maps disagreed): {FLIPPED}")
check("closures_nested_by_threshold_and_return_period", bool((closed["rp100|d05"] <= closed["rp100|wet"]).all() and (closed["rp10|d05"] <= closed["rp100|d05"]).all() and (closed["rp100|d05"] <= closed["rp500|d05"]).all()
                                                           and (closed["rp10|wet"] <= closed["rp100|wet"]).all() and (closed["rp100|wet"] <= closed["rp500|wet"]).all()), edges_made_nested=FLIPPED)

# ---------------------------------------------------------------- municipalities (country and name by location)
bx0, by0 = tr.transform(HERO[0], HERO[1])
bx1, by1 = tr.transform(HERO[2], HERO[3])
lau = gpd.read_file(G / "LAU_RG_01M_2024_3035.gpkg", bbox=(min(bx0, bx1) - 5000, min(by0, by1) - 5000, max(bx0, bx1) + 5000, max(by0, by1) + 5000)).to_crs("EPSG:3035")
lau = lau[lau.CNTR_CODE == "DE"].reset_index(drop=True)
tree_l = STRtree(lau.geometry.values)


def muni(x, y):
    pts = shapely.points(np.asarray(x, float), np.asarray(y, float))
    out = np.full(len(pts), "", dtype=object)
    for i, j in zip(*tree_l.query(pts, predicate="within")):
        if out[i] == "":
            out[i] = str(lau.LAU_NAME.values[j]).split(",")[0]
    return out


# ---------------------------------------------------------------- zones: 500 m cells of the scenario nodes
sn = pd.read_csv(SCEN / "scenario_nodes.csv")
sn["zx"], sn["zy"] = (sn.x // 500).astype(int), (sn.y // 500).astype(int)
PC = ["people_obs2021", "people_rp10", "people_rp100", "people_rp500"]
PC25 = []
if SCEN25:   # same 250 m nodes from the 2025 grid, side by side; a node only in one year gets 0 in the other
    s25 = pd.read_csv(SCEN25 / "scenario_nodes.csv").rename(columns=lambda c: "p25_" + c[7:] if c.startswith("people_") else c)
    PC25 = ["p25_obs2021", "p25_rp10", "p25_rp100", "p25_rp500"]
    sn = sn.merge(s25[["gx", "gy", "x", "y"] + PC25 + ["p25_all"]], on=["gx", "gy", "x", "y"], how="outer").fillna(0.0)
    sn["zx"], sn["zy"] = (sn.x // 500).astype(int), (sn.y // 500).astype(int)
else:
    sn["p25_all"] = 0.0
zg = sn.groupby(["zx", "zy"]).agg(**{c: (c, "sum") for c in PC + PC25}, people_all=("people_all", "sum"), w25=("p25_all", "sum")).reset_index()
wsum = sn.assign(wx=sn.x * sn.people_all, wy=sn.y * sn.people_all, vx=sn.x * sn.p25_all, vy=sn.y * sn.p25_all).groupby(["zx", "zy"])[["wx", "wy", "vx", "vy"]].sum().reset_index()
zg = zg.merge(wsum, on=["zx", "zy"])
only25 = (zg.people_all <= 0) & (zg.w25 > 0)          # zone points use 2020 weights (so 2020 results stay exactly as before); 2025 weights only for zones with no 2020 residents
zg.loc[only25, ["wx", "wy", "people_all"]] = zg.loc[only25, ["vx", "vy", "w25"]].values
zg["x"] = np.where(zg.people_all > 0, zg.wx / zg.people_all.replace(0, 1), (zg.zx + 0.5) * 500)      # zone point = residents-weighted centre of its nodes
zg["y"] = np.where(zg.people_all > 0, zg.wy / zg.people_all.replace(0, 1), (zg.zy + 0.5) * 500)
zg = zg[(zg[PC + PC25] > 0).any(axis=1)].reset_index(drop=True)
zg["node"] = evac.snap(zg[["x", "y"]].values, node_xy, allowed=main, max_m=600.0)
lost = zg[zg.node < 0]
zg = zg[zg.node >= 0].reset_index(drop=True)
zg["muni"] = muni(zg.x.values, zg.y.values)
zg = zg[zg.muni != ""].reset_index(drop=True)
Q1_TOT = {s: float(sn["people_" + s].sum()) for s in ("obs2021", "rp10", "rp100", "rp500")}           # residents inside each flood level in the whole bbox (the Q1-style totals)
LOST_ALL = {s: round(float(lost["people_" + s].sum())) for s in Q1_TOT}                            # in zones more than 600 m from any road, whole bbox
HERO_NUTS = ("DEA28", "DEB12")                                                                      # Kreis Euskirchen (Eifel) and Landkreis Ahrweiler (Ahr valley)
nuts = gpd.read_file(G / "NUTS_RG_01M_2021_3035_LEVL_3.geojson").to_crs("EPSG:3035")
hero_poly = nuts[nuts.NUTS_ID.str.startswith(HERO_NUTS)].union_all()
LOST_PEOPLE = {s: round(float(lost.loc[shapely.contains_xy(hero_poly, lost.x.values, lost.y.values), "people_" + s].sum())) for s in Q1_TOT}      # the same, inside the hero area only
zg_all = zg
zg = zg[shapely.contains_xy(hero_poly, zg.x.values, zg.y.values)].reset_index(drop=True)
OUTSIDE = {s: round(float(zg_all["people_" + s].sum() - zg["people_" + s].sum())) for s in Q1_TOT}  # residents inside the flood in the rest of the bbox (Rhine corridor, Bonn ...): NOT modelled
region_poly = hero_poly.buffer(12000.0)                                                             # roads and shelters are used within 12 km of the hero area
ctr = shapely.centroid(geo)
region_mask = shapely.contains_xy(region_poly, shapely.get_x(ctr), shapely.get_y(ctr))
for k_ in closed:
    closed[k_] &= region_mask                                                                       # closures are modelled inside the region only (no demand or shelters beyond it)
lap(f"{len(zg):,} zones (500 m) in Kreis Euskirchen and Landkreis Ahrweiler; {len(lost)} cells could not be snapped within 600 m ({LOST_PEOPLE}); residents in the flood outside the hero area, not modelled: {OUTSIDE}")
zlon, zlat = inv.transform(zg.x.values, zg.y.values)
# corners of each zone's 500 m EPSG:3035 grid cell in WGS84 (SW, SE, NE, NW), so the page can draw the true cell, not a box around the zone point
CELL = [inv.transform((zg.zx.values + dx) * 500.0, (zg.zy.values + dy) * 500.0) for dx, dy in ((0, 0), (1, 0), (1, 1), (0, 1))]
check("zone_point_inside_its_500m_cell", bool(((zg.x // 500).astype(int).eq(zg.zx) & (zg.y // 500).astype(int).eq(zg.zy)).all()), zones=len(zg))

# ---------------------------------------------------------------- shelters
cand = pd.read_csv(CAND / "q3_candidates.csv")
cand = cand[cand.tier.isin(["core", "extended"]) & (cand.footprint_m2 >= 100)].sort_values("footprint_m2", ascending=False).reset_index(drop=True)
pairs = cKDTree(cand[["x", "y"]].values).query_pairs(3.0, output_type="ndarray")
cand = cand.drop(index=sorted({int(j) for i, j in pairs if cand.type.values[i] == cand.type.values[j]})).reset_index(drop=True)
cand["muni"] = muni(cand.x.values, cand.y.values)
cand = cand[(cand.muni != "") & shapely.contains_xy(region_poly, cand.x.values, cand.y.values)].reset_index(drop=True)
cand["node"] = evac.snap(cand[["x", "y"]].values, node_xy, allowed=main, max_m=400.0)
cand = cand[cand.node >= 0].reset_index(drop=True)
CAP = {"restrictive": dict(floors=1, usable=0.4, m2pp=5.0, cap_max=500, tiers={"core"}), "generous": dict(floors=2, usable=0.7, m2pp=3.5, cap_max=1500, tiers={"core", "extended"})}
for k, p in CAP.items():
    fl = np.where(cand.type.isin(["church", "chapel", "cathedral"]), 1, p["floors"])               # a one-room worship building is not given a second floor by default
    cap = np.minimum(sh.capacity_persons(cand.footprint_m2.values, cand.levels.values, fl, p["usable"], p["m2pp"]), p["cap_max"])
    cand["cap_" + k] = np.where(cand.tier.isin(p["tiers"]), cap, 0).astype(int)
slon, slat = inv.transform(cand.x.values, cand.y.values)
# names and a street per building (B24), so two buildings of one type in one town can be told apart. A map lookup, never a merge: a repeated key must not add rows
# (row order = shelter ids, which every result refers to). Fallback for a building without OSM tags: the nearest named road of the graph.
n_cand = len(cand)
for c_ in ("name", "addr_street", "addr_housenumber"):
    cand[c_] = ""
if NAMES:
    bn_ = pd.read_csv(NAMES / "building_names.csv", dtype=str, keep_default_na=False).drop_duplicates("osm_key").set_index("osm_key")
    for c_ in ("name", "addr_street", "addr_housenumber"):
        cand[c_] = cand.osm_key.map(bn_[c_]).fillna("").astype(str)
    check("building_names_cover_every_shelter", len(cand) == n_cand and bool(cand.osm_key.isin(bn_.index).all()), shelters=len(cand), found=int(cand.osm_key.isin(bn_.index).sum()),
          with_name=int((cand["name"] != "").sum()), with_street=int((cand.addr_street != "").sum()), with_neither=int(((cand["name"] == "") & (cand.addr_street == "")).sum()))
_named_e = np.nonzero(np.array([isinstance(v, str) and v not in ("", "nan") for v in ed.name.values]))[0]
_ne = STRtree(geo[_named_e]).query_nearest(shapely.points(cand.x.values, cand.y.values), return_distance=True, all_matches=False)
cand["near_street"] = ""
cand.loc[_ne[0][0], "near_street"] = [str(ed.name.values[_named_e[j]]) if dd <= 300.0 else "" for j, dd in zip(_ne[0][1], _ne[1])]      # farther than 300 m is no help to find the door
flooded ={"obs2021": cand.in_flood.values.astype(bool), "obs2021_mapped": cand.in_mapped_flood.values.astype(bool)}      # touching the mapped flood or a trace / touching the mapped flood only
for rp in ("rp10", "rp100", "rp500"):
    d = efas_sample(rp.upper(), slon, slat)
    flooded[rp] = np.isfinite(d) & (d > 0)
lap(f"{len(cand):,} shelter candidates snapped to roads; flooded: " + ", ".join(f"{k} {int(v.sum())}" for k, v in flooded.items()))
# A shelter is used only if it is dry in EVERY flood map we have: the 2021 map misses the Rhine (outside its areas of interest) and EFAS misses smaller
# rivers (Kall), so a building that one map calls dry can be under water in the other. The per-level flags stay in the bundle for display.
DRY_IN_ALL_MAPS = True
WET_ANY = flooded["obs2021"] | flooded["rp10"] | flooded["rp100"] | flooded["rp500"]
use_wet = {k: (v | WET_ANY | (flooded["obs2021_mapped"] if k == "obs2021_mapped" else False)) if DRY_IN_ALL_MAPS else v for k, v in flooded.items()}
lap(f"shelter rule: {'dry in all maps' if DRY_IN_ALL_MAPS else 'dry at the level shown'}; wet in any map {int(WET_ANY.sum())}")

# areas of interest of the July 2021 EMS map: outside them 2021 is 'not assessed', never dry (the Rhine banks Remagen - Bad Breisig lie outside)
aoi_g = gpd.read_file(FLOODOUT / "q1_flood_layers.gpkg", layer="aoi")
AOI_U = aoi_g[aoi_g.country == "DE"].to_crs(3035).geometry.union_all()

# ---------------------------------------------------------------- run every combination
VEH = {"car_share": 0.8, "persons_per_car": 2.0, "evacuation_window_h": 2.0}                       # ASSUMPTIONS
RCAP = {"motorway": 3600, "trunk": 2400, "primary": 1600, "secondary": 1200, "tertiary": 900, "unclassified": 600, "residential": 400, "living_street": 200}      # veh/h, ASSUMPTION
base_class = ed.highway.str.replace("_link", "", regex=False).values
caph = np.array([RCAP.get(h, 400) for h in base_class], float)
results, used_edges, closed_any = {}, set(), np.zeros(len(ed), bool)
K_NEAREST = 200         # candidate shelters per zone (fastest by road): a small k makes neighbouring zones compete for the same few buildings and strands people (k=40 stranded 10,000+ people)
K_CHECK = {}
LIMIT_CHECK = {}
SC = [("obs2021", ["any", "mapped"]), ("rp10", ["wet", "d05"]), ("rp100", ["wet", "d05"]), ("rp500", ["wet", "d05"])]
d_nodes = zg.node.values.astype(int)
s_nodes = cand.node.values.astype(int)
WALK_MS = 4000.0 / 3600.0      # ASSUMPTION: walking speed (4 km/h) for the first leg from a zone inside the flood to the nearest road that stays open
ACCESS_MAX_M = 2000.0          # ASSUMPTION: a zone farther than this from any open road has no route (reported as unassigned, no route)
from scipy.sparse.csgraph import connected_components
for (yr, ypre, ysuf), (sc, rules) in [(y, s) for y in YEARS for s in SC]:
    people = zg[ypre + sc].values
    live_d = np.nonzero(people > 0)[0]
    zxy = zg[["x", "y"]].values[live_d]
    for rule in rules:
        cl = closed[f"{sc}|{rule}"]
        closed_any |= cl
        g, arc = rd.build_digraph(cu, cv, ed.time_s.values, ed.oneway.values, NN, closed=cl)
        _, lab = connected_components(g, directed=True, connection="strong")
        open_main = lab == np.bincount(lab).argmax()                              # the largest STRONGLY connected open network: nodes one can both enter and leave (one-way stubs and dead ends excluded)
        # people inside the flood stand on closed roads: they are assumed to reach the nearest open road on foot BEFORE the water rises (access leg); from there only open roads are used
        d_open = evac.snap(zxy, node_xy, allowed=open_main, max_m=ACCESS_MAX_M)
        acc_s = np.where(d_open >= 0, np.hypot(*(node_xy[np.where(d_open >= 0, d_open, 0)] - zxy).T), np.inf) / WALK_MS
        for capname in ("restrictive", "generous"):
            fkey = "obs2021_mapped" if (sc == "obs2021" and rule == "mapped") else sc
            cap = cand["cap_" + capname].values.astype(float) * (~use_wet[fkey])
            live_s = np.nonzero(cap > 0)[0]
            dense = evac.nearest_shelters(g, d_open, s_nodes[live_s], k=K_NEAREST, limit_s=3600.0)       # d, s index the live zones / live shelters; t = routed seconds on open roads
            reach = dense.d.nunique() if len(dense) else 0
            lap(f"  {sc}|{rule}|{capname}: {len(live_d)} zones ({int((d_open >= 0).sum())} with an open road within {int(ACCESS_MAX_M)} m), {len(live_s)} usable shelters (capacity {int(cap[live_s].sum()):,}); zones with a reachable shelter {reach}")
            flow, un = evac.assign(people[live_d], cap[live_s], dense)
            load, routes = evac.route_loads(g, arc, d_open, s_nodes[live_s], dense, flow, len(ed))
            from_b = evac.pair_times(g0, d_open, s_nodes[live_s], dense.d.values, dense.s.values)               # same start node and pair on the network with NO closures
            tt = dense.t.values + acc_s[dense.d.values]                                                         # reported time = access leg + routed time on open roads
            t0 = from_b + acc_s[dense.d.values]                                                                 # the same access leg + routed time with no closures: detour = tt - t0 is road time only
            assign, acc_used = [], {}
            for row, es in routes:
                zi, sj = int(live_d[dense.d.values[row]]), int(live_s[dense.s.values[row]])
                assign.append([zi, sj, round(float(flow[row]), 1), round(float(tt[row])), round(float(t0[row])), [int(e) for e in es]])
                acc_used[str(zi)] = round(float(acc_s[dense.d.values[row]]))
                used_edges.update(int(e) for e in es)
            pl = float(flow.sum())
            ratio = (load * VEH["car_share"] / VEH["persons_per_car"] / VEH["evacuation_window_h"]) / caph
            used_ = flow > 1e-6
            tmin = (np.average(tt[used_], weights=flow[used_]) / 60.0) if pl > 0 else 0.0
            dmin = (np.average((tt - t0)[used_], weights=flow[used_]) / 60.0) if pl > 0 else 0.0               # road detour only
            acc_pair = acc_s[dense.d.values] if len(dense) else np.zeros(0)
            amin = (np.average(acc_pair[used_], weights=flow[used_]) / 60.0) if pl > 0 else 0.0
            gt10 = float(flow[used_ & (acc_pair > 600.0)].sum())
            no_route = float(people[live_d][~np.isin(np.arange(len(live_d)), dense.d.values if len(dense) else [])].sum())      # zones with no reachable shelter at all
            no_open = float(people[live_d][d_open < 0].sum())                                                   # of which: no open road within the access limit
            over1 = int((ratio > 1).sum())
            wr = int(np.argmax(ratio))
            shload = {}                       # from the UNROUNDED flows, so rounding in the display list can never look like an over-capacity shelter
            for row, es in routes:
                sj = int(live_s[dense.s.values[row]])
                shload[sj] = shload.get(sj, 0.0) + float(flow[row])
            key = f"{sc}|{rule}|{capname}{ysuf}"
            results[key] = {"closed": [int(i) for i in np.nonzero(cl)[0]], "assign": assign, "access_s": acc_used,
                            "unassigned": {str(int(live_d[i])): round(float(u), 1) for i, u in enumerate(un) if u > 0.05},
                            "shelter_load": {str(k): round(v, 1) for k, v in shload.items()},
                            "load": {str(int(i)): round(float(load[i]), 1) for i in np.nonzero(load > 0.5)[0]},
                            "summary": {"people_to_place": round(float(people.sum()), 1), "placed": round(pl, 1), "unassigned": round(float(un.sum()), 1), "unassigned_no_route": round(no_route, 1),
                                        "unassigned_no_capacity": round(max(float(un.sum()) - no_route, 0.0), 1), "unassigned_no_open_road": round(no_open, 1), "unassigned_no_shelter_reachable": round(max(no_route - no_open, 0.0), 1),
                                        "unassigned_capacity_limited": round(max(float(un.sum()) - no_route, 0.0), 1), "shelters_used": len(shload),
                                        "max_shelter_fill": round(max((v / cap[k] for k, v in shload.items()), default=0.0), 3), "closed_edges": int(cl.sum()),
                                        "mean_time_min": round(float(tmin), 1), "mean_detour_min": round(float(dmin), 1), "worst_road_ratio": round(float(ratio.max()), 2),
                                        "worst_road_class": str(base_class[wr]), "stress_edges_over_1": over1, "mean_access_min": round(float(amin), 1), "people_access_over_10min": round(gt10),
                                        "people_over_30min": round(float(flow[used_ & (tt > 1800.0)].sum())), "shelters_at_capacity": int(sum(1 for k, v in shload.items() if v >= 0.99 * cap[k])),
                                        "free_places_total": round(float(cap[live_s].sum() - pl))}}
            # ---- independent checks on this result
            s_ = results[key]["summary"]
            check(f"conservation_{key}", abs(s_["placed"] + s_["unassigned"] - s_["people_to_place"]) < 0.5 + 0.001 * s_["people_to_place"], **s_)
            capmap = {int(k): cap[int(k)] for k in shload}
            assert all(shload[k] <= capmap[int(k)] * (1 + 1e-6) + 1e-3 for k in shload), f"shelter over capacity in {key}"
            assert not any(cl[e] for a in assign for e in a[5]), f"route through a closed edge in {key}"
            for a in assign[:25]:      # routed time (reported minus the access leg) equals the sum of its edge times
                routed = a[3] - acc_used[str(a[0])]
                assert abs(sum(ed.time_s.values[e] for e in a[5]) - routed) <= 1.5 + 0.002 * routed, f"route time mismatch in {key}"
            assert all(a[3] >= a[4] - 1.5 for a in assign), f"negative road detour in {key}"
            if key in ("rp100|wet|restrictive", "rp500|wet|restrictive"):       # does a 2 h reach (instead of 1 h) place the people who are unassigned within 1 h?
                d3 = evac.nearest_shelters(g, d_open, s_nodes[live_s], k=K_NEAREST, limit_s=7200.0)
                f3, _ = evac.assign(people[live_d], cap[live_s], d3)
                LIMIT_CHECK[key] = {"unassigned_1h": round(float(people.sum() - pl)), "unassigned_2h": round(float(people.sum() - f3.sum()))}
            if key == "rp100|wet|restrictive":       # the sharpest sensitivity: does a longer candidate list place more people?
                d2 = evac.nearest_shelters(g, d_open, s_nodes[live_s], k=2 * K_NEAREST, limit_s=3600.0)
                f2, _ = evac.assign(people[live_d], cap[live_s], d2)
                K_CHECK.update({"k": K_NEAREST, "placed": round(pl), "k_double": 2 * K_NEAREST, "placed_double": round(float(f2.sum()))})
                check("candidate_list_size_does_not_strand_people", abs(float(f2.sum()) - pl) <= 0.015 * float(people.sum()), **K_CHECK)
            lap(f"{key}: place {s_['people_to_place']:,.0f}, placed {s_['placed']:,.0f}, unassigned {s_['unassigned']:,.0f} (no route {s_['unassigned_no_route']:,.0f}, no capacity {s_['unassigned_no_capacity']:,.0f}), "
                f"shelters used {s_['shelters_used']}, mean time {s_['mean_time_min']} min, detour {s_['mean_detour_min']} min, worst road ratio {s_['worst_road_ratio']}")

# ---------------------------------------------------------------- citizen plan (POLICY_TOOL_PLAN.md section 0, "Citizen v2"): ONE building per 250 m cell
# July 2021 flood, set A, 2020 residents. Each 250 m cell goes to exactly one candidate building (single assignment, capacity-limited, minimum person-time),
# except cells larger than the largest building, which may split. Areas = connected cells with the same building AND the same first open-road node,
# so their road route is identical (only the walk to that road differs).
from scipy.optimize import milp, LinearConstraint, Bounds


def single_assign(people, cap, pairs, split, pen, max_b=None, min_part=10.0, time_limit=180.0):
    """x per pair (share of the demand's people, 0..1; binary unless split[d]) and u per demand (unassigned share). Minimises people x time + pen x people unassigned.
    With max_b, a split demand may use at most max_b buildings (B27 / CIT-1: a list of 36 buildings is no instruction): binary y per split pair, x <= y, sum y <= max_b,
    and a used building takes at least min_part people of the cell (or the whole cell if smaller), so no building is listed for a fraction of a person."""
    nd, ns, ne = len(people), len(cap), len(pairs)
    dv, sv = pairs.d.values.astype(int), pairs.s.values.astype(int)
    sp = np.nonzero(split[dv])[0] if max_b is not None else np.zeros(0, int)          # split pairs that get a use variable
    m = len(sp)
    nv = ne + m + nd
    c = np.concatenate([people[dv] * pairs.t.values, np.zeros(m), people * pen])
    ar = np.arange(ne)
    A = lambda r_, c_, v, nr: coo_matrix((v, (r_, c_)), shape=(nr, nv)).tocsr()
    cons = [LinearConstraint(A(np.concatenate([dv, np.arange(nd)]), np.concatenate([ar, ne + m + np.arange(nd)]), np.ones(ne + nd), nd), 1, 1),      # x + u = 1 per demand
            LinearConstraint(A(sv, ar, people[dv], ns), -np.inf, cap)]                                                                           # building capacity
    if m:
        am, pp = np.arange(m), people[dv[sp]]
        cons += [LinearConstraint(A(np.concatenate([am, am]), np.concatenate([sp, ne + am]), np.concatenate([np.ones(m), -np.ones(m)]), m), -np.inf, 0),                  # x <= y
                 LinearConstraint(A(np.concatenate([am, am]), np.concatenate([sp, ne + am]), np.concatenate([pp, -np.minimum(min_part, pp)]), m), 0, np.inf),             # people x >= min_part y
                 LinearConstraint(A(dv[sp], ne + am, np.ones(m), nd), 0, max_b)]                                                                                      # at most max_b buildings
    integ = np.concatenate([np.where(split[dv], 0, 1), np.ones(m), np.zeros(nd)])
    r = milp(c, constraints=cons, integrality=integ, bounds=Bounds(0, 1), options={"time_limit": time_limit, "mip_rel_gap": 0.01})
    if r.x is None:
        raise RuntimeError(f"single assignment failed: {r.message}")
    x = np.clip(r.x, 0, 1)
    xs = x[:ne].copy()
    if m:
        xs[sp[x[ne:ne + m] < 0.5]] = 0.0                                                     # numerical dust on a building the cell does not use
    return xs, np.clip(1.0 - np.bincount(dv, weights=xs, minlength=nd), 0, 1), {"status": int(r.status), "message": str(r.message), "gap": float(getattr(r, "mip_gap", np.nan) or 0.0)}


from scipy.sparse import coo_matrix
# known answer: 3 cells of 100, buildings of 200 and 100; cell 2 can only reach building 0, cell 1 is cheaper than cell 0 at building 1 -> 0->0, 1->1, 2->0
_kp = pd.DataFrame({"d": [0, 0, 1, 1, 2], "s": [0, 1, 0, 1, 0], "t": [1.0, 5.0, 1.0, 2.0, 1.0]})
_kx, _ku, _ = single_assign(np.array([100.0, 100.0, 100.0]), np.array([200.0, 100.0]), _kp, np.zeros(3, bool), pen=100.0)
check("single_assign_known_answer", np.allclose(_kx, [1, 0, 0, 1, 1]) and np.allclose(_ku, 0), x=[round(float(v), 3) for v in _kx])

CIT_KEY = "obs2021|any|restrictive"
cl_c = closed["obs2021|any"]
g_c, arc_c = rd.build_digraph(cu, cv, ed.time_s.values, ed.oneway.values, NN, closed=cl_c)
_, lab_c = connected_components(g_c, directed=True, connection="strong")
open_c = lab_c == np.bincount(lab_c).argmax()
cn = sn[(sn.people_obs2021 > 0) & shapely.contains_xy(hero_poly, sn.x.values, sn.y.values)].reset_index(drop=True)
cxy = cn[["x", "y"]].values
c_open = evac.snap(cxy, node_xy, allowed=open_c, max_m=ACCESS_MAX_M)
c_acc = np.where(c_open >= 0, np.hypot(*(node_xy[np.where(c_open >= 0, c_open, 0)] - cxy).T), np.inf) / WALK_MS
cap_c = cand["cap_restrictive"].values.astype(float) * (~use_wet["obs2021"])
live_sc = np.nonzero(cap_c > 0)[0]
c_people = cn.people_obs2021.values.astype(float)
c_split = c_people > cap_c[live_sc].max()
K_CIT = 200          # as the main plan: a short candidate list strands people (k=40 placed only 12,704 of 25,559; check below)
cpairs = evac.nearest_shelters(g_c, c_open, s_nodes[live_sc], k=K_CIT, limit_s=3600.0)
cpairs["t"] = cpairs.t.values + c_acc[cpairs.d.values.astype(int)]          # person-time includes the walk
PEN = 10.0 * float(cpairs.t.max() + 1.0)
MAX_SPLIT = 3        # a cell that cannot go whole to one building is shared over at most 3 buildings (a list a resident can follow)
cx, cu_, csolve = single_assign(c_people, cap_c[live_sc], cpairs, c_split, PEN)
placed_stage1 = float((cx * c_people[cpairs.d.values.astype(int)]).sum())
# second step: a cell that cannot go WHOLE to one building within 1 h (most nearby buildings are smaller than the cell), or is larger than the largest building, may be
# shared over at most MAX_SPLIT buildings. Solved jointly with all other cells (they stay one building each), so a nearby building can be freed for a split cell;
# the old leftover-places step spread such cells over up to 36 buildings (CIT-1). What still does not fit stays unassigned at the penalty, never spread thinner.
u_cells = np.nonzero(cu_ * c_people > 0.05)[0]
c_flex = c_split | np.isin(np.arange(len(cn)), u_cells)
# to keep the joint MILP solvable in minutes, a one-building cell keeps only its K_KEEP fastest buildings plus its step-1 building (so the step-1 plan stays feasible);
# a split cell keeps its full list
K_KEEP = 30
_rank = cpairs.groupby("d").t.rank(method="first").values
_keep = c_flex[cpairs.d.values.astype(int)] | (_rank <= K_KEEP) | (cx > 0.5)
# a cell placed whole in step 1 costs 10x the penalty to drop: without it the solver dropped such a cell (110 people) to fit a split cell, and the page would
# then tell that area no building is in reach although step 1 found one (tested on the dumped inputs: unassigned stays in split cells only)
_x2, cu_, csolve2 = single_assign(c_people, cap_c[live_sc], cpairs[_keep].reset_index(drop=True), c_flex, PEN * np.where(c_flex, 1.0, 10.0), max_b=MAX_SPLIT, time_limit=300.0)
cx = np.zeros(len(cpairs))
cx[np.nonzero(_keep)[0]] = _x2
c_split = c_flex
lap(f"citizen plan: one building for {placed_stage1:,.0f} people; {len(u_cells)} cells ({c_people[u_cells].sum():,.0f} people) too large for one building within 1 h -> shared over at most {MAX_SPLIT} buildings; unassigned after step 2 {float((cu_ * c_people).sum()):,.0f}")
c_load, c_routes = evac.route_loads(g_c, arc_c, c_open, s_nodes[live_sc], cpairs, cx * c_people[cpairs.d.values.astype(int)], len(ed))
route_of = {row: es for row, es in c_routes}
used_edges.update(int(e) for _, es in c_routes for e in es)
cplaced = float((cx * c_people[cpairs.d.values.astype(int)]).sum())
cun = float((cu_ * c_people).sum()) + 0.0
cun_noroad = float(c_people[c_open < 0].sum())
# checks: integrality (one building per non-split cell), capacity, conservation, no closed road, solver status
nz = cpairs.assign(x=cx)
per_cell = nz[nz.x > 1e-6].groupby("d").x.agg(["count", "sum"])
check("citizen_plan_one_building_per_cell", bool(((per_cell["count"] == 1) | c_split[per_cell.index.values.astype(int)]).all()) and bool(((np.abs(cx[~c_split[cpairs.d.values.astype(int)]]) < 1e-6) | (np.abs(cx[~c_split[cpairs.d.values.astype(int)]] - 1) < 1e-6)).all()),
      cells=len(cn), split_cells=int(c_split.sum()), split_people=round(float(c_people[c_split].sum())))
shl = np.bincount(cpairs.s.values.astype(int), weights=cx * c_people[cpairs.d.values.astype(int)], minlength=len(live_sc))
check("citizen_plan_capacity", bool((shl <= cap_c[live_sc] + 1e-3).all()), max_fill=round(float((shl / np.maximum(cap_c[live_sc], 1)).max()), 3))
check("citizen_plan_conservation", abs(cplaced + float((cu_ * c_people).sum()) + float(c_people[~np.isin(np.arange(len(cn)), cpairs.d.values.astype(int))].sum()) - float(c_people.sum())) < 1.0,
      people=round(float(c_people.sum())), placed=round(cplaced), unassigned_in_model=round(float((cu_ * c_people).sum())), no_open_road_or_no_building_in_1h=round(float(c_people[~np.isin(np.arange(len(cn)), cpairs.d.values.astype(int))].sum())))
check("citizen_plan_no_closed_road", not any(cl_c[e] for _, es in c_routes for e in es), routes=len(c_routes))
check("citizen_plan_solver", csolve["status"] == 0 and csolve2["status"] == 0, step1_one_building=csolve, step2_split_capped=csolve2)
check("citizen_plan_split_cells_use_at_most_3_buildings", int(per_cell["count"].max()) <= MAX_SPLIT, max_buildings_per_cell=int(per_cell["count"].max()),
      split_cells=int(c_split.sum()), people_unassigned_in_model=round(float((cu_ * c_people).sum())))
check("citizen_plan_unassigned_only_in_split_cells", float((cu_ * c_people)[~c_split].sum()) < 0.5, unassigned_split=round(float((cu_ * c_people)[c_split].sum())),
      unassigned_one_building_cells=round(float((cu_ * c_people)[~c_split].sum()), 1))
# compare with the main (split) plan, and a doubled candidate list
main_s = results[CIT_KEY]["summary"]
cp2 = evac.nearest_shelters(g_c, c_open, s_nodes[live_sc], k=2 * K_CIT, limit_s=3600.0)
cp2["t"] = cp2.t.values + c_acc[cp2.d.values.astype(int)]
cx2, _, _ = single_assign(c_people, cap_c[live_sc], cp2, c_people > cap_c[live_sc].max(), PEN)
placed2 = float((cx2 * c_people[cp2.d.values.astype(int)]).sum())
check("citizen_plan_candidate_list_size", abs(placed2 - placed_stage1) <= 0.015 * float(c_people.sum()), k=K_CIT, placed_one_building=round(placed_stage1), k_double=2 * K_CIT, placed_one_building_double=round(placed2))
tt_c = cpairs.t.values
ctime = float(np.average(tt_c[cx > 1e-6], weights=(cx * c_people[cpairs.d.values.astype(int)])[cx > 1e-6]) / 60.0) if cplaced > 0 else 0.0
lap(f"citizen plan: {len(cn)} cells, placed {cplaced:,.0f} of {c_people.sum():,.0f}, mean {ctime:.1f} min (main split plan: placed {main_s['placed']:,.0f}, mean {main_s['mean_time_min']} min); solver {csolve}")
# areas: connected cells (4-neighbour) with the same building and the same first open-road node
cell_dest = {}
for row in np.nonzero(cx > 1e-6)[0]:
    cell_dest.setdefault(int(cpairs.d.values[row]), []).append(row)
keyc = {}
for i in range(len(cn)):
    rows_ = cell_dest.get(i, [])
    keyc[i] = ("split", i) if c_split[i] else (("none", i) if not rows_ else (int(cpairs.s.values[rows_[0]]), int(c_open[i])))
pos = {(int(a), int(b)): i for i, (a, b) in enumerate(zip(cn.gx.values, cn.gy.values))}
parent = list(range(len(cn)))
def _find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]; a = parent[a]
    return a
for (a, b), i in pos.items():
    for nb in ((a + 1, b), (a, b + 1)):
        j = pos.get(nb)
        if j is not None and keyc[i] == keyc[j] and keyc[i][0] not in ("split", "none"):
            parent[_find(i)] = _find(j)
groups = {}
for i in range(len(cn)):
    groups.setdefault(_find(i), []).append(i)
areas, area_polys = [], []            # area_polys: the same outlines in EPSG:3035, unrounded, for the street index
for gi, members in enumerate(groups.values()):
    m = np.array(members)
    poly = shapely.union_all([shapely.box(cn.gx.values[k] * 250.0, cn.gy.values[k] * 250.0, (cn.gx.values[k] + 1) * 250.0, (cn.gy.values[k] + 1) * 250.0) for k in m])
    area_polys.append(poly)
    gl = gpd.GeoSeries([poly], crs="EPSG:3035").to_crs("EPSG:4326").iloc[0]
    rows_ = cell_dest.get(int(m[0]), [])
    dest = []
    for row in rows_:
        sj = int(live_sc[int(cpairs.s.values[row])])
        ppl = float(sum(cx[r2] * c_people[int(cpairs.d.values[r2])] for k in m for r2 in cell_dest.get(int(k), []) if int(live_sc[int(cpairs.s.values[r2])]) == sj))
        dest.append({"s": sj, "people": round(ppl, 1), "road_s": round(float(tt_c[row] - c_acc[int(m[0])])), "route": [int(e) for e in route_of.get(row, [])]})
    acc_m = c_acc[m][np.isfinite(c_acc[m])]
    ctr = poly.centroid
    areas.append({"id": gi, "cells": int(len(m)), "people": round(float(c_people[m].sum()), 1), "muni": str(muni(np.array([ctr.x]), np.array([ctr.y]))[0]),
                  "split": bool(c_split[m].any()), "no_open_road": bool((c_open[m] < 0).all()),
                  "walk_s": [round(float(acc_m.min())), round(float(acc_m.max()))] if len(acc_m) else None,
                  "unassigned": round(float((cu_[m] * c_people[m]).sum() + c_people[m][~np.isin(m, cpairs.d.values.astype(int))].sum()), 1),
                  # why people of this area have no building: no open road, no building within 1 h, or the plan's own rule (at most MAX_SPLIT buildings per cell,
                  # buildings in reach already full); the main plan places everyone, so 'plan_rule' must never read as 'no room'
                  "unassigned_reason": ("no_road" if (c_open[m] < 0).all() else "none_in_1h" if not np.isin(m, cpairs.d.values.astype(int)).any() else "plan_rule")
                  if float((cu_[m] * c_people[m]).sum() + c_people[m][~np.isin(m, cpairs.d.values.astype(int))].sum()) >= 0.5 else "",
                  "dest": dest, "geometry": json.loads(shapely.to_geojson(shapely.set_precision(gl, 1e-5)))})
# backup per area: the fastest OTHER reachable building from the area's first cell that still has room for the whole area after the plan (else the fastest other one, flagged)
free_c = cap_c[live_sc] - shl
bk_rows = {}
for a_, members in zip(areas, groups.values()):
    if len(a_["dest"]) != 1:
        continue
    s0 = int(np.nonzero(live_sc == a_["dest"][0]["s"])[0][0])
    cand_rows = np.nonzero(cpairs.d.values.astype(int) == int(members[0]))[0]
    cand_rows = cand_rows[np.argsort(cpairs.t.values[cand_rows], kind="stable")]
    others = [r for r in cand_rows if int(cpairs.s.values[r]) != s0]
    roomy = [r for r in others if free_c[int(cpairs.s.values[r])] >= a_["people"]]
    if others:
        bk_rows[a_["id"]] = (roomy or others)[0], bool(roomy)
if bk_rows:
    flow_b = np.zeros(len(cpairs)); flow_b[[r for r, _ in bk_rows.values()]] = 1.0
    _, b_routes = evac.route_loads(g_c, arc_c, c_open, s_nodes[live_sc], cpairs, flow_b, len(ed))
    b_route_of = {row: es for row, es in b_routes}
    used_edges.update(int(e) for _, es in b_routes for e in es)
    for a_ in areas:
        if a_["id"] in bk_rows:
            r, roomy = bk_rows[a_["id"]]
            a_["backup"] = {"s": int(live_sc[int(cpairs.s.values[r])]), "road_s": round(float(tt_c[r] - c_acc[int(cpairs.d.values[r])])), "has_room": roomy, "route": [int(e) for e in b_route_of.get(r, [])]}
    check("citizen_backup_differs_and_avoids_closed_roads", all(a_["backup"]["s"] != a_["dest"][0]["s"] and not any(cl_c[e] for e in a_["backup"]["route"]) for a_ in areas if "backup" in a_),
          areas_with_backup=sum(1 for a_ in areas if "backup" in a_), with_room=sum(1 for a_ in areas if a_.get("backup", {}).get("has_room")))
same_route = all(len({int(cpairs.s.values[cell_dest[int(k)][0]]) for k in a_m if int(k) in cell_dest}) <= 1 for a_m in groups.values())
check("citizen_areas_one_building_one_first_road", same_route and sum(len(v) for v in groups.values()) == len(cn), areas=len(areas), cells=len(cn))
CITIZEN = {"key": CIT_KEY, "method": "one building per 250 m cell (single assignment, capacity-limited, minimum person-time; MILP solved with HiGHS; a cell that cannot go whole to one building within 1 h, or is larger than the largest building, is shared over at most 3 buildings, each taking at least 10 people or the whole rest)",
           "k": K_CIT, "solver": csolve, "solver_split": csolve2, "max_buildings_per_split_cell": MAX_SPLIT, "areas": areas,
           "summary": {"people": round(float(c_people.sum())), "placed": round(cplaced), "unassigned": round(float(c_people.sum()) - cplaced), "mean_time_min": round(ctime, 1),
                       "areas": len(areas), "buildings_used": int((shl > 1e-6).sum()), "split_cells": int(c_split.sum()), "split_people": round(float(c_people[c_split].sum())), "placed_one_building": round(placed_stage1)},
           "main_plan_summary": {k: main_s[k] for k in ("people_to_place", "placed", "unassigned", "mean_time_min", "shelters_used")}}

# ---------------------------------------------------------------- display network: main classes + every edge a route or a closure touches
disp = np.zeros(len(ed), bool)
disp[np.isin(base_class, ["motorway", "trunk", "primary", "secondary", "tertiary"])] = True
disp &= region_mask
disp[list(used_edges)] = True
disp |= closed_any
net = []
for i in np.nonzero(disp)[0]:
    c = shapely.simplify(geo[i], 3.0)
    lo, la = inv.transform(*np.array(c.coords).T)
    nm = next((str(v) for v in (ed.name.values[i], ed.ref.values[i]) if isinstance(v, str) and v and v != "nan"), "")
    net.append({"id": int(i), "c": [[round(a, 5), round(b, 5)] for a, b in zip(lo, la)], "h": str(ed.highway.values[i]), "n": nm, "b": int(bool(ed.bridge.values[i])), "t": int(bool(ed.tunnel.values[i]))})
lap(f"display network {len(net):,} of {len(ed):,} edges")

# ---------------------------------------------------------------- overlays (EFAS depth classes) and observed flood polygons
PAL = [(0.0, 0.5, (158, 202, 225, 150)), (0.5, 1.0, (66, 146, 198, 170)), (1.0, 2.0, (8, 81, 156, 190)), (2.0, 1e9, (8, 29, 88, 210))]
overlays = []
for rp in ("rp10", "rp100", "rp500"):
    arr, tf = z[f"{rp.upper()}_arr"].astype("float32"), z[f"{rp.upper()}_tf"]
    rgba = np.zeros(arr.shape + (4,), np.uint8)
    for lo_, hi_, col in PAL:
        rgba[np.isfinite(arr) & (arr > lo_) & (arr <= hi_)] = col
    h, w = arr.shape
    west, north = tf[2], tf[5]
    east, south = west + tf[0] * w, north + tf[4] * h
    mer = lambda la_: np.log(np.tan(np.pi / 4 + np.radians(la_) / 2))
    ym = np.linspace(mer(north), mer(south), 2 * h + 1)[1::2]                                         # centres of h rows equally spaced in Web Mercator
    lat_rows = np.degrees(2 * np.arctan(np.exp(ym)) - np.pi / 2)
    src = np.clip(np.floor((lat_rows - north) / tf[4]).astype(int), 0, h - 1)                         # source row (equal latitude steps) for each output row
    rgba = rgba[src]
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG", optimize=True)
    overlays.append({"scenario": rp, "png": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), "bounds": [[round(south, 5), round(west, 5)], [round(north, 5), round(east, 5)]],
                     "legend": [{"label": "up to 0.5 m", "color": "#9ecae1"}, {"label": "0.5 to 1 m", "color": "#4292c6"}, {"label": "1 to 2 m", "color": "#08519c"}, {"label": "more than 2 m", "color": "#081d58"}]})


def fc(geom, kind):
    g = shapely.simplify(shapely.make_valid(geom), 15.0)
    g = shapely.intersection(g, shapely.box(min(bx0, bx1), min(by0, by1), max(bx0, bx1), max(by0, by1)))
    gl = gpd.GeoSeries([g], crs="EPSG:3035").to_crs("EPSG:4326").iloc[0]
    return {"type": "Feature", "properties": {"kind": kind}, "geometry": json.loads(shapely.to_geojson(shapely.set_precision(gl, 1e-5)))}


floods = {"obs2021": {"type": "FeatureCollection", "features": [fc(flood_t, "flood or trace"), fc(flood_h, "mapped flood")]}}

# ---------------------------------------------------------------- derived disclosures (computed, never typed)
SM = json.loads((SCEN / "scenarios_meta.json").read_text(encoding="utf-8"))
PA = SM["checks"]["people_conserved_in_window"]                                                        # allocated / unallocated / window residents of the scenario run
POP = {"window_residents": round(PA["window_residents"]), "allocated_to_buildings": round(PA["allocated"]), "dropped_no_usable_building": round(PA["unallocated_cells_without_usable_building"]),
       "dropped_share": round(PA["unallocated_cells_without_usable_building"] / PA["window_residents"], 4), "window": "GHS-POP cells of the map box plus a margin (hero bbox)"}
DEF = results["obs2021|any|restrictive"]
dist_km = np.array([np.hypot(zg.x.values[a[0]] - cand.x.values[a[1]], zg.y.values[a[0]] - cand.y.values[a[1]]) / 1000.0 for a in DEF["assign"]])
wts = np.array([a[2] for a in DEF["assign"]])
share_2km = float(wts[dist_km <= 2.0].sum() / wts.sum())
order = np.argsort(dist_km)
median_km = float(dist_km[order][np.searchsorted(np.cumsum(wts[order]), 0.5 * wts.sum())])
tot_lvl = {s: zg["people_" + s].sum() for s in Q1_TOT}
top3 = zg.groupby("muni")["people_rp100"].sum().sort_values(ascending=False).head(3)
top3_txt = ", ".join(f"{m} {round(v):,}" for m, v in top3.items())
by_m = zg.groupby("muni")[["people_obs2021", "people_rp500"]].sum()
bn = by_m.loc["Bad Neuenahr-Ahrweiler"] if "Bad Neuenahr-Ahrweiler" in by_m.index else None
kall = by_m.loc["Kall"] if "Kall" in by_m.index else None
SUPPLY = {k: int(cand["cap_" + k].sum()) for k in CAP}
G_Q1 = 29360                                                                                           # Germany observed residents in flood + trace, claims register C3.1 (research/r01/NOTE.md)

# ---------------------------------------------------------------- assemble
LIMITS = ["Not a traffic simulation: speeds are free flow by road class. Road stress compares people on a road, turned into vehicles per hour, with an ASSUMED capacity; it is an indicator, not a forecast, and is not fed back into the plan.",
          "Everyone is assumed warned in time, able to walk up to 2 km (4 km/h, straight line, through any barrier) from inside the flood to the nearest road that is still open, and to leave at the same time; in reality roads close progressively. The walk is a large part of the reported travel time.",
          "Shelter capacity, usable share and space per person are assumptions without a verified source. The two capacity sets are alternative assumption sets, not lower and upper bounds. Official shelter lists are not used.",
          "No competing demand: people from outside the flood zone, or isolated but not flooded, may also need the same shelters; all residents inside the flood are assumed to need a public shelter.",
          f"Each zone considers its {K_NEAREST} fastest reachable shelters within 1 hour by open road, after the walk. Checked once (100-year flood, closed under any water, assumption set A): doubling the list to {2 * K_NEAREST} left the number placed unchanged ({K_CHECK.get('placed'):,}); other states were not re-tested. Allowing 2 hours instead of 1 changes the people left unassigned in set A as follows (1 h to 2 h): {LIMIT_CHECK}; so the unassigned people in set A are a time-reach gap (no shelter with space within 1 h), not an absence of space in the whole area.",
          f"Reach differs from the Q3 shelter study: Q3 counts shelters within 2 km in a straight line; this tool lets residents travel up to 1 hour by road after the walk. In the default state (observed 2021, set A) only {share_2km:.0%} of the people placed go to a shelter within 2 km and the median destination is {median_km:.1f} km away, so '0 unassigned' means a building with space exists within an hour by road, not nearby.",
          f"Residents: GHS-POP (30 arc-second grid, cells about 930 x 600 m here, modelled) is shared over the GHS-OBAT building points with use 1 or 2 (built-up domain, so non-residential buildings also receive residents: about 10% in our German analysis) of each cell in proportion to footprint area (not floors or volume, so a large low building gets more residents than a small block of flats). In the study window {POP['dropped_no_usable_building']:,} of {POP['window_residents']:,} residents ({POP['dropped_share']:.1%}) live in cells without a usable building point and are dropped: they can never be counted as inside a flood, one more reason all counts are minimums. Residents are not located by household; a building point is not a household. Reference year 2020 (the year before the flood; the 2026 population is not modelled; a 2025 JRC projection is offered as a sensitivity only in the population selector: it is not a census and does not show post-2021 rebuilding), and the grid is a modelled estimate from census counts and built-up volume: its error for a single 500 m cell is not quantified here and can be large, so read the counts as rounded orders of magnitude, never as an exact headcount.",
          f"Supply: assumption set A offers {SUPPLY['restrictive']:,} places and set B {SUPPLY['generous']:,}, against at most {round(max(tot_lvl.values())):,} people to place. Set B is an optimistic supply case (no competing demand), not an expected one.",
          f"Modelled flood levels are dominated by a few places on the Rhine and the lower Ahr (100-year, people in the flood: {top3_txt}); EFAS does not model the Ahr or small Eifel rivers well, so modelled totals are not comparable with observed 2021 by area" + (f" (Bad Neuenahr-Ahrweiler: {round(bn.people_obs2021):,} in the observed flood, {round(bn.people_rp500):,} in the 500-year model; Kall: {round(kall.people_obs2021):,} observed, {round(kall.people_rp500):,} modelled)" if bn is not None and kall is not None else "") + ".",
          f"Road stress statistics count short road segments: the worst ratio is often a short link where several zones' routes join; read the colours, not the maximum.",
          "Observed 2021: a road is closed if it touches the mapped flood or a flood-trace feature (traces are residue of where water had been, a different timing); the sensitivity 'mapped' closes only roads touching the mapped flood and keeps shelters that only touch a trace. EMS covers only the requested areas, mapped on different dates (14-20 July), so roads elsewhere are treated as open. Bridges and tunnels are closed on a touch test.",
          "EFAS closures use the depth sampled at least every 25 m along each road: modelled rivers only (small rivers are missing, for example no EFAS flood at Kall), a bridge is closed if any point on it is wet (deck height not modelled), and a model can also overstate. The three return-period maps are independent model runs; where they disagreed on a road the larger flood is made to include it (counts in meta.edges_made_nested).",
          "A shelter is used only if it is dry in every flood map we have (the July 2021 map and the 10-, 100- and 500-year model): its building footprint must not touch the 2021 flood or trace and its centre must be dry in all three model levels. The 2021 map does not cover the Rhine banks and the model misses smaller rivers, so a building dry in one map can be wet in the other.",
          "OSM is the 2026 state, not the 2021 state; buildings and roads may have changed.",
          f"Not modelled: residents inside each flood level outside Kreis Euskirchen and Landkreis Ahrweiler but inside the map box (Rhine corridor, Bonn): {OUTSIDE}; inside the hero area but more than 600 m from any road: {LOST_PEOPLE}; observed residents outside the map box: about {max(G_Q1 - round(Q1_TOT['obs2021']), 0):,} (Germany total {G_Q1:,} from the Q1 analysis minus {round(Q1_TOT['obs2021']):,} in the box)."]
ZONE_IN_EMS = shapely.contains_xy(AOI_U, zg.x.values, zg.y.values)      # zone point inside an area the July 2021 map covered
_ol = shapely.simplify(AOI_U.intersection(shapely.box(*hero_poly.buffer(15000).bounds)), 50.0, preserve_topology=True)      # outline for display only (50 m), never for counting
EMS_OUTLINE = json.loads(shapely.to_geojson(shapely.set_precision(shapely.transform(_ol, lambda c: np.column_stack(inv.transform(c[:, 0], c[:, 1]))), 1e-5)))
OUT_EMS = {s: round(float(zg["people_" + s].values[~ZONE_IN_EMS].sum())) for s in ("obs2021", "rp10", "rp100", "rp500")}
lap(f"zones inside the 2021 EMS areas: {int(ZONE_IN_EMS.sum())} of {len(zg)}; people outside them per level: {OUT_EMS}")
check("observed_2021_people_all_inside_ems_areas", OUT_EMS["obs2021"] == 0, people_outside=OUT_EMS)
bundle = {
    "meta": {"title": "Smart shelter system: planning aid", "area": "Eifel (Kreis Euskirchen) and Ahr valley (Landkreis Ahrweiler), Germany", "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "bounds": [round(float(min(zlon.min(), slon.min())) - 0.01, 4), round(float(min(zlat.min(), slat.min())) - 0.01, 4), round(float(max(zlon.max(), slon.max())) + 0.01, 4), round(float(max(zlat.max(), slat.max())) + 0.01, 4)],
             "hero_nuts": list(HERO_NUTS), "edges_made_nested": FLIPPED, "limit_check": LIMIT_CHECK, "total_places": SUPPLY, "outside_road_network_whole_bbox": LOST_ALL,
             "zone_bounds": [round(float(zlon.min()) - 0.01, 4), round(float(zlat.min()) - 0.01, 4), round(float(zlon.max()) + 0.01, 4), round(float(zlat.max()) + 0.01, 4)],
             "provenance": {"roads_run": RUNID(ROADS), "scenarios_run": RUNID(SCEN), "shelter_candidates_run": RUNID(CAND), "observed_flood_run": RUNID(FLOODOUT), "pipeline": "research/r01/20_tool_pipeline.py", "checks": "research/r01/outputs/tool_pipeline_checks.json", "osm_state": "Geofabrik extracts of 29 Oct 2026", "building_names_run": RUNID(NAMES) if NAMES else None}, "ems_coverage": {"outline": EMS_OUTLINE, "people_outside": OUT_EMS, "source": "union of the German EMSR517 areas of interest (run " + RUNID(FLOODOUT) + "), simplified 50 m for display"}, "shelter_rule": "dry_in_all_maps" if DRY_IN_ALL_MAPS else "dry_at_level", "q1_totals_bbox": {k: round(v) for k, v in Q1_TOT.items()}, "outside_hero_area": OUTSIDE, "outside_road_network": LOST_PEOPLE, "candidate_list_check": K_CHECK,
             "disclaimer": "Planning aid, not live guidance and not an official evacuation plan. Shelters are candidate buildings from OpenStreetMap, not designated shelters, and everyone is assumed warned in time and leaving at once. Germany only. Built from July 2021 satellite snapshots (one per area, 14-20 July, not the peak), EFAS flood models, OpenStreetMap of 29 Oct 2026 and unverified assumptions. Routes avoid mapped flooded roads only; not-mapped does not mean dry. Numbers are assumption-driven estimates; observed-flood counts are minimums.",
             "data_notes": ["Residents: GHS-POP 2020 (30 arc-second grid, cells about 930 x 600 m here, modelled). Each cell's residents are shared among the GHS-OBAT building points with use 1 or 2 (built-up domain, so non-residential buildings also receive residents: about 10% in our German analysis) of that cell (positive footprint) in proportion to footprint area; a building is 'in the flood' if it touches the mapped flood or a flood trace (observed) or has EFAS depth above 0 (modelled). Buildings are summed to 250 m nodes and then to 500 m zones. Cells without a usable building drop their residents (see limits).", "Observed 2021: EMS rapid mapping (radar 14-16 July, optical 18 July, one update 20 July 2021), flood and flood-trace features, only the requested areas; one satellite snapshot per area (14-20 July 2021), not the peak.",
                            "Modelled levels: EFAS river flood depth for 10-, 100- and 500-year floods; empty cells mean dry OR not modelled: small rivers are missing (nothing is mapped at Kall, where residents were inside the 2021 flood) and the exact coverage rule of these files is not documented; the 500-year map is a ceiling that 2021 exceeded in places.",
                            "Roads and shelters: OpenStreetMap (c) contributors, ODbL, Geofabrik extracts of 29 Oct 2026; road classes motorway to living street; service roads, tracks and paths are not used.",
                            "Germany only; shelters and people across the border are not used."],
             "limits": LIMITS},
    "assumptions": {"population": {"source": "GHS-POP 2020, 30 arc-second grid, cells about 930 x 600 m here (modelled estimate)", "allocation": "dasymetric: each cell's residents shared over the GHS-OBAT building points with use 1 or 2 (built-up domain, so non-residential buildings also receive residents: about 10% in our German analysis) of the cell in proportion to footprint area (not floors or volume)", "flood_test": "observed: building touches mapped flood or flood trace; modelled: EFAS depth above 0 at the building", "reference_year": 2020, "error": "not quantified: a modelled estimate (census counts spread by built-up volume, then by footprint); the error for one 500 m cell can be large; 2026 population not modelled; a 2025 JRC projection is offered as a sensitivity only (population selector): not a census, it does not show post-2021 rebuilding", "aggregation": "250 m nodes, then 500 m zones; zone point = residents-weighted centre of all residents of the cell", **POP},
                    "capacity": {"restrictive": {"m2_per_person": 5.0, "usable_share": 0.4, "floors": "tagged levels, else 1", "cap_max": 500, "tiers": "core (schools, colleges, universities, sports halls, community and civic buildings)"},
                                 "generous": {"m2_per_person": 3.5, "usable_share": 0.7, "floors": "tagged levels, else 2 (1 for churches, chapels, cathedrals)", "cap_max": 1500, "tiers": "core + extended (kindergartens, churches, chapels, hotels)"}},
                    "total_places": SUPPLY, "vehicles": VEH, "road_capacity_veh_per_h": RCAP, "notes": ["free-flow speeds per road class (motorway 100, primary 70, secondary 60, tertiary 50, residential 30 km/h) unless a numeric maxspeed is tagged",
                                                                           "closure: observed 2021 = a road touching the flood or trace; EFAS = any water or more than 0.5 m (selectable)", "people inside the flood are assumed to reach the nearest road that stays open on foot (4 km/h, at most 2 km) before the water rises; from there only open roads are used", "minimum shelter building footprint 100 m2; a flooded shelter is not used"]},
    "scenarios": [{"id": "obs2021", "label": "Observed July 2021 (EMS snapshot)", "kind": "observed", "note": "Flood and flood-trace features mapped by EMS; one satellite snapshot per area (14-20 July 2021), not the peak, only in the requested areas.", "closures": [{"id": "any", "label": "road closed if it touches the mapped flood OR a flood-trace feature"}, {"id": "mapped", "label": "road closed only if it touches the mapped flooded area (traces ignored)"}]}]
                 + [{"id": rp, "label": f"{n}-year flood (EFAS model)", "kind": "modelled", "note": "Modelled river flood depth; empty cells are dry OR not modelled.", "closures": [{"id": "wet", "label": "closed under any water"}, {"id": "d05", "label": "closed under 0.5 m or more"}]}
                    for rp, n in (("rp10", 10), ("rp100", 100), ("rp500", 500))],
    "capacities": [{"id": "restrictive", "label": "Assumption set A: core public buildings only, 5 m2 per person"}, {"id": "generous", "label": "Assumption set B: core + extended buildings, 3.5 m2 per person"}],
    "floods": floods, "overlays": overlays, "network": {"edges": net},
    "zones": [{"id": int(i), "lon": round(float(zlon[i]), 5), "lat": round(float(zlat[i]), 5), "muni": str(zg.muni.values[i]), "cell": [[round(float(c[1][i]), 5), round(float(c[0][i]), 5)] for c in CELL], "people": {s: round(float(zg["people_" + s].values[i]), 1) for s in ("obs2021", "rp10", "rp100", "rp500")}, "in_ems_area": bool(ZONE_IN_EMS[i])} for i in range(len(zg))],
    "shelters": [{"id": int(i), "lon": round(float(slon[i]), 5), "lat": round(float(slat[i]), 5), "type": str(cand.type.values[i]), "kind": str(cand.kind.values[i]), "footprint_m2": int(cand.footprint_m2.values[i]), "muni": str(cand.muni.values[i]),
                  "name": str(cand["name"].values[i]), "street": " ".join(v for v in (str(cand.addr_street.values[i]), str(cand.addr_housenumber.values[i])) if v) if cand.addr_street.values[i] else "",
                  "near_street": str(cand.near_street.values[i]),
                  "cap": {"restrictive": int(cand.cap_restrictive.values[i]), "generous": int(cand.cap_generous.values[i])}, "flooded": {s: bool(flooded[s][i]) for s in flooded}} for i in range(len(cand))],
    "results": results,
    "road_ratio_note": "worst_road_ratio and road colours = people on the edge turned into vehicles per hour (car share, persons per car, evacuation window) divided by an ASSUMED capacity of the road class: a stress indicator, not a traffic forecast",
}
# ---------------------------------------------------------------- map profiles (POLICY_TOOL_PLAN.md section 0): municipality outlines and a street index
def lau_idx(x, y):
    """index into `lau` of the municipality that contains each point (EPSG:3035), -1 if none"""
    pts = shapely.points(np.asarray(x, float), np.asarray(y, float))
    out = np.full(len(pts), -1, dtype=int)
    for i, j in zip(*tree_l.query(pts, predicate="within")):
        if out[i] < 0:
            out[i] = j
    return out


zl = lau_idx(zg.x.values, zg.y.values)
for i, z in enumerate(bundle["zones"]):
    z["lau"] = str(lau.GISCO_ID.values[zl[i]]) if zl[i] >= 0 else ""
rp_ = lau.geometry.representative_point()
hero_lau = lau[shapely.contains_xy(hero_poly, shapely.get_x(rp_.values), shapely.get_y(rp_.values))]      # every municipality of the two districts, also those with nobody in a flood
munis_out = []
for gid, nm_, gm in zip(hero_lau.GISCO_ID.values, hero_lau.LAU_NAME.values, hero_lau.geometry.values):
    gl = gpd.GeoSeries([shapely.simplify(gm, 40.0)], crs="EPSG:3035").to_crs("EPSG:4326").iloc[0]
    munis_out.append({"id": str(gid), "name": str(nm_).split(",")[0], "geometry": json.loads(shapely.to_geojson(shapely.set_precision(gl, 1e-5)))})
bundle["munis"] = munis_out
# in_area: the building lies in a municipality of the two districts (by its LAU id, so a homonym elsewhere cannot match). Many plans send people to buildings in
# neighbouring districts (finding MUN-2); the page can say so. Cross-checked against the district outline itself.
s_lau = lau_idx(cand.x.values, cand.y.values)
in_area = np.array([j >= 0 and str(lau.GISCO_ID.values[j]) in {m["id"] for m in munis_out} for j in s_lau])
for i, s_ in enumerate(bundle["shelters"]):
    s_["in_area"] = bool(in_area[i])
_by_poly = shapely.contains_xy(hero_poly, cand.x.values, cand.y.values)
_dflt = results["obs2021|any|restrictive"]["assign"]
check("shelter_in_area_matches_district_outline", int((in_area != _by_poly).sum()) <= 0.002 * len(cand), shelters=len(cand), in_area=int(in_area.sum()), differ_from_outline=int((in_area != _by_poly).sum()),
      default_plan_people_outside=round(sum(a[2] for a in _dflt if not in_area[a[1]])), default_plan_placed=round(sum(a[2] for a in _dflt)))
bundle["citizen_plan"] = CITIZEN
for a_ in CITIZEN["areas"]:   # the municipality id of each area (same LAU test as the zones)
    c_ = shapely.centroid(shapely.from_geojson(json.dumps(a_["geometry"])))
    cx3, cy3 = tr.transform(c_.x, c_.y)
    j_ = lau_idx(np.array([cx3]), np.array([cy3]))[0]
    a_["lau"] = str(lau.GISCO_ID.values[j_]) if j_ >= 0 else ""
mid_ = {m["id"]: m["name"] for m in munis_out}
check("every_zone_lies_in_an_exported_municipality", all(z["lau"] in mid_ and mid_[z["lau"]] == z["muni"] for z in bundle["zones"]), zones=len(bundle["zones"]), municipalities=len(munis_out))
# street index for the citizen search: unique (street name, municipality) of the FULL road graph (not only the display network), up to 6 points along each.
# Points alone miss a flooded stretch between them (data-1: 'Zum Fahrenbach, Kall' was reported dry), so each street also carries, from ALL its edges:
# wet = any edge closed in July 2021 or touching the observed flood or trace; areas = citizen areas any edge crosses; and the midpoint of every wet edge is added to p.
mid_pt = shapely.line_interpolate_point(geo, 0.5, normalized=True)
mx, my = shapely.get_x(mid_pt), shapely.get_y(mid_pt)
named = np.array([isinstance(v, str) and v != "" and v != "nan" for v in ed.name.values]) & shapely.contains_xy(hero_poly, mx, my)
wet_e = closed["obs2021|any"].copy()
wet_e[tree_e.query(flood_t, predicate="intersects")] = True
e_area = {}
for ei, ai in zip(*STRtree(np.array(area_polys, dtype=object)).query(geo[named], predicate="intersects")):
    e_area.setdefault(int(np.nonzero(named)[0][ei]), set()).add(int(areas[ai]["id"]))
sdf = pd.DataFrame({"e": np.nonzero(named)[0], "n": ed.name.values[named], "lau": lau_idx(mx[named], my[named]), "x": mx[named], "y": my[named]})
sdf = sdf[sdf.lau >= 0]
sdf["wet"] = wet_e[sdf.e.values]
streets = []
for (n_, j), g_ in sdf.groupby(["n", "lau"]):
    g_ = g_.sort_values(["x", "y"])
    take = g_.iloc[np.unique(np.linspace(0, len(g_) - 1, min(len(g_), 6)).round().astype(int))]
    take = pd.concat([take, g_[g_.wet & ~g_.index.isin(take.index)]])
    lo_, la_ = inv.transform(take.x.values, take.y.values)
    ar_ = sorted(set().union(*[e_area.get(int(e), set()) for e in g_.e.values]))
    streets.append({"n": str(n_), "m": str(lau.LAU_NAME.values[j]).split(",")[0], "p": [[round(float(a), 5), round(float(b), 5)] for a, b in zip(la_, lo_)],
                    "wet": bool(g_.wet.any()), "areas": ar_})
bundle["streets"] = streets
# checks from the edges, not from the street records: every wet named edge makes its street wet, every edge crossing an area lists that area; the three streets of finding data-1
s_by = {(st["n"], st["m"]): st for st in streets}
lname = {int(j): str(lau.LAU_NAME.values[j]).split(",")[0] for j in np.unique(sdf.lau.values)}
bad_wet = [(n_, lname[j]) for n_, j, w in zip(sdf.n.values, sdf.lau.values, sdf.wet.values) if w and not s_by[(n_, lname[j])]["wet"]]
bad_area = [(n_, lname[j]) for e, n_, j in zip(sdf.e.values, sdf.n.values, sdf.lau.values) if not e_area.get(int(e), set()) <= set(s_by[(n_, lname[j])]["areas"])]
# the closed edges named in data-1 lie (by midpoint) in Kall, Wershofen (not Fuchshofen) and Sinzig (not Remagen); the Fuchshofen record must still open its area
cases = {f"{n_}, {m_}": [s_by[(n_, m_)]["wet"], s_by[(n_, m_)]["areas"]] if (n_, m_) in s_by else None
         for n_, m_ in (("Zum Fahrenbach", "Kall"), ("Hauptstra" + chr(223) + "e", "Wershofen"), ("K" + chr(246) + "lner Stra" + chr(223) + "e", "Sinzig"), ("Hauptstra" + chr(223) + "e", "Fuchshofen"))}
check("street_index_flooded_streets_are_wet_and_list_their_areas", not bad_wet and not bad_area and all(v is not None and (v[0] or "Fuchshofen" in k_) and v[1] for k_, v in cases.items()),
      streets=len(streets), wet=sum(st["wet"] for st in streets), with_areas=sum(bool(st["areas"]) for st in streets), bad_wet=bad_wet[:5], bad_area=bad_area[:5], cases=cases)
lap(f"profiles: {len(munis_out)} municipality outlines, {len(streets):,} streets (name + municipality)")

# ---------------------------------------------------------------- population year (selectable like the capacity sets; 2020 is the default and the reference)
bundle["populations"] = [{"id": "pop2020", "label": "2020 (default)", "year": 2020,
                          "note": "Residents of 2020: the reference for the July 2021 flood (reference/data_notes.md)."}]
if SCEN25:
    SM25 = json.loads((SCEN25 / "scenarios_meta.json").read_text(encoding="utf-8"))
    PA25 = SM25["checks"]["people_conserved_in_window"]
    bundle["populations"].append({"id": "pop2025", "label": "2025 projection", "year": 2025,
                                  "note": "A projection by the JRC from earlier census data and built-up trends, not a newer census: it does not show homes abandoned or rebuilt after 2021. Use it to see how much the answer depends on the population year.",
                                  "window_residents": round(PA25["window_residents"]), "dropped_no_usable_building": round(PA25["unallocated_cells_without_usable_building"]),
                                  "file": SM25.get("population_file"), "file_generation": SM25.get("population_file_generation")})
    bundle["meta"]["provenance"]["scenarios_run_pop2025"] = RUNID(SCEN25)
    for i, z in enumerate(bundle["zones"]):
        z["people_pop2025"] = {s: round(float(zg["p25_" + s].values[i]), 1) for s in ("obs2021", "rp10", "rp100", "rp500")}
    # the 2025 run and the 2020 run must cover the same buildings and map box: only the residents per cell may differ
    check("pop2025_same_nodes_frame", set(s25.columns) >= {"gx", "gy", "x", "y"} and len(results) == 32, results=len(results))
    for key in [k for k in results if not k.endswith("|pop2025")]:
        a, b = results[key]["summary"], results[key + "|pop2025"]["summary"]
        lap(f"population year {key}: 2020 place {a['people_to_place']:,.0f} unassigned {a['unassigned']:,.0f} | 2025 place {b['people_to_place']:,.0f} unassigned {b['unassigned']:,.0f}")
OUTB.parent.mkdir(parents=True, exist_ok=True)
OUTB.write_text(json.dumps(bundle, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
(root / "research/r01/outputs/tool_pipeline_checks.json").write_text(json.dumps(CHECKS, indent=1, default=str), encoding="utf-8")
lap(f"bundle written: {OUTB.stat().st_size / 1e6:.1f} MB; {len(results)} result sets; {len(net):,} display edges; {len(zg):,} zones; {len(cand):,} shelters")
