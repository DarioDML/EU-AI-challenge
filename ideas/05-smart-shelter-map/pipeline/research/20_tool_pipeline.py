"""Question:    Policy tool (smart shelter system). For each flood level (observed 2021, EFAS RP10 / RP100 / RP500), each road-closure rule and each shelter-capacity assumption:
              which zone goes to which shelter, by which route, with what detour, and which roads carry how many people? Writes the bundle the web page reads.
Data:         roads: run of 18_tool_roads.py (OSM ways split at shared vertices, state 29 Oct 2026); scenarios: run of 19_tool_scenarios.py (residents per flood level on 250 m nodes, EFAS
              depth windows); shelters: run 20261029-134745-b0be q3_candidates.csv (OSM building polygons, state 29 Oct 2026); observed flood: run 20261029-101321-bf98 (EMS flood + trace);
              GISCO LAU 2024 (municipality names and country).
Assumptions:  GERMANY ONLY, hero area Eifel and Ahr valley (decision 2026-10-29). Every number rests on ASSUMPTIONS without a verified source: free-flow speeds per road class, closure
              depth (any water / more than 0.5 m under EFAS; touching the EMS flood or trace for 2021), shelter capacity (space per person, usable share, per-building cap; restrictive =
              core buildings only, generous = core + extended), car share, persons per car, an evacuation window, road capacities. A flooded shelter is not usable; reach is by road on the open
              network (a closed road is removed, never driven through). EFAS holds values only where wet and misses rivers under about 500 km2 catchment, so an EFAS closure set is a MINIMUM and
              empty never means dry. Observed 2021 is a snapshot after the peak. Zones are 500 m cells; people on a zone are placed together. The road 'stress' is people turned into vehicles per hour
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
zg = sn.groupby(["zx", "zy"]).agg(**{c: (c, "sum") for c in PC}, people_all=("people_all", "sum")).reset_index()
wsum = sn.assign(wx=sn.x * sn.people_all, wy=sn.y * sn.people_all).groupby(["zx", "zy"]).agg(wx=("wx", "sum"), wy=("wy", "sum")).reset_index()
zg = zg.merge(wsum, on=["zx", "zy"])
zg["x"] = np.where(zg.people_all > 0, zg.wx / zg.people_all.replace(0, 1), (zg.zx + 0.5) * 500)      # zone point = residents-weighted centre of its nodes
zg["y"] = np.where(zg.people_all > 0, zg.wy / zg.people_all.replace(0, 1), (zg.zy + 0.5) * 500)
zg = zg[(zg[PC] > 0).any(axis=1)].reset_index(drop=True)
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
flooded = {"obs2021": cand.in_flood.values.astype(bool), "obs2021_mapped": cand.in_mapped_flood.values.astype(bool)}      # touching the mapped flood or a trace / touching the mapped flood only
for rp in ("rp10", "rp100", "rp500"):
    d = efas_sample(rp.upper(), slon, slat)
    flooded[rp] = np.isfinite(d) & (d > 0)
lap(f"{len(cand):,} shelter candidates snapped to roads; flooded: " + ", ".join(f"{k} {int(v.sum())}" for k, v in flooded.items()))

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
for sc, rules in SC:
    people = zg["people_" + sc].values
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
            cap = cand["cap_" + capname].values.astype(float) * (~flooded[fkey])
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
            key = f"{sc}|{rule}|{capname}"
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
          f"Supply: assumption set A offers {SUPPLY['restrictive']:,} places and set B {SUPPLY['generous']:,}, against at most {round(max(tot_lvl.values())):,} people to place. Set B is an optimistic supply case (no competing demand), not an expected one.",
          f"Modelled flood levels are dominated by a few places along the Rhine (100-year, people in the flood: {top3_txt}); EFAS does not model the Ahr or small Eifel rivers well, so modelled totals are not comparable with observed 2021 by area" + (f" (Bad Neuenahr-Ahrweiler: {round(bn.people_obs2021):,} in the observed flood, {round(bn.people_rp500):,} in the 500-year model; Kall: {round(kall.people_obs2021):,} observed, {round(kall.people_rp500):,} modelled)" if bn is not None and kall is not None else "") + ".",
          f"Road stress statistics count short road segments: the worst ratio is often a short link where several zones' routes join; read the colours, not the maximum.",
          "Observed 2021: a road is closed if it touches the mapped flood or a flood-trace feature (traces are residue of where water had been, a different timing); the sensitivity 'mapped' closes only roads touching the mapped flood and keeps shelters that only touch a trace. EMS covers only the requested areas, mapped on different dates (15-20 July), so roads elsewhere are treated as open. Bridges and tunnels are closed on a touch test.",
          "EFAS closures use the depth sampled at least every 25 m along each road: modelled rivers only (small rivers are missing, for example no EFAS flood at Kall), a bridge is closed if any point on it is wet (deck height not modelled), and a model can also overstate. The three return-period maps are independent model runs; where they disagreed on a road the larger flood is made to include it (counts in meta.edges_made_nested).",
          "A shelter is unusable if its building footprint (observed) or centre (modelled levels) is flooded.",
          "OSM is the 2026 state, not the 2021 state; buildings and roads may have changed.",
          f"Not modelled: residents inside each flood level outside Kreis Euskirchen and Landkreis Ahrweiler but inside the map box (Rhine corridor, Bonn): {OUTSIDE}; inside the hero area but more than 600 m from any road: {LOST_PEOPLE}; observed residents outside the map box: about {max(G_Q1 - round(Q1_TOT['obs2021']), 0):,} (Germany total {G_Q1:,} from the Q1 analysis minus {round(Q1_TOT['obs2021']):,} in the box)."]
bundle = {
    "meta": {"title": "Smart shelter system: planning aid", "area": "Eifel (Kreis Euskirchen) and Ahr valley (Landkreis Ahrweiler), Germany", "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "bounds": [round(float(min(zlon.min(), slon.min())) - 0.01, 4), round(float(min(zlat.min(), slat.min())) - 0.01, 4), round(float(max(zlon.max(), slon.max())) + 0.01, 4), round(float(max(zlat.max(), slat.max())) + 0.01, 4)],
             "hero_nuts": list(HERO_NUTS), "edges_made_nested": FLIPPED, "limit_check": LIMIT_CHECK, "total_places": SUPPLY, "outside_road_network_whole_bbox": LOST_ALL,
             "zone_bounds": [round(float(zlon.min()) - 0.01, 4), round(float(zlat.min()) - 0.01, 4), round(float(zlon.max()) + 0.01, 4), round(float(zlat.max()) + 0.01, 4)],
             "provenance": {"roads_run": RUNID(ROADS), "scenarios_run": RUNID(SCEN), "shelter_candidates_run": RUNID(CAND), "observed_flood_run": RUNID(FLOODOUT), "pipeline": "research/r01/20_tool_pipeline.py", "checks": "research/r01/outputs/tool_pipeline_checks.json", "osm_state": "Geofabrik extracts of 29 Oct 2026"}, "q1_totals_bbox": {k: round(v) for k, v in Q1_TOT.items()}, "outside_hero_area": OUTSIDE, "outside_road_network": LOST_PEOPLE, "candidate_list_check": K_CHECK,
             "disclaimer": "Planning aid, not live guidance and not an official evacuation plan. Shelters are candidate buildings from OpenStreetMap, not designated shelters, and everyone is assumed warned in time and leaving at once. Germany only. Built from a July 2021 satellite snapshot, EFAS flood models, OpenStreetMap of 29 Oct 2026 and unverified assumptions. Routes avoid mapped flooded roads only; not-mapped does not mean dry. Numbers are assumption-driven estimates; observed-flood counts are minimums.",
             "data_notes": ["Residents: GHS-POP 2020 (1 km grid, modelled) placed on GHS-OBAT buildings by footprint; zones are 500 m cells.", "Observed 2021: EMS rapid mapping (Sentinel-1 15-17 July, Pleiades 18-20 July 2021), flood and flood-trace features, only the requested areas; a snapshot after the peak.",
                            "Modelled levels: EFAS river flood depth for 10-, 100- and 500-year floods; empty cells mean dry OR not modelled: small rivers are missing (nothing is mapped at Kall, where residents were inside the 2021 flood) and the exact coverage rule of these files is not documented; the 500-year map is a ceiling that 2021 exceeded in places.",
                            "Roads and shelters: OpenStreetMap (c) contributors, ODbL, Geofabrik extracts of 29 Oct 2026; road classes motorway to living street; service roads, tracks and paths are not used.",
                            "Germany only; shelters and people across the border are not used."],
             "limits": LIMITS},
    "assumptions": {"capacity": {"restrictive": {"m2_per_person": 5.0, "usable_share": 0.4, "floors": "tagged levels, else 1", "cap_max": 500, "tiers": "core (schools, colleges, universities, sports halls, community and civic buildings)"},
                                 "generous": {"m2_per_person": 3.5, "usable_share": 0.7, "floors": "tagged levels, else 2 (1 for churches, chapels, cathedrals)", "cap_max": 1500, "tiers": "core + extended (kindergartens, churches, chapels, hotels)"}},
                    "total_places": SUPPLY, "vehicles": VEH, "road_capacity_veh_per_h": RCAP, "notes": ["free-flow speeds per road class (motorway 100, primary 70, secondary 60, tertiary 50, residential 30 km/h) unless a numeric maxspeed is tagged",
                                                                           "closure: observed 2021 = a road touching the flood or trace; EFAS = any water or more than 0.5 m (selectable)", "people inside the flood are assumed to reach the nearest road that stays open on foot (4 km/h, at most 2 km) before the water rises; from there only open roads are used", "minimum shelter building footprint 100 m2; a flooded shelter is not used"]},
    "scenarios": [{"id": "obs2021", "label": "Observed July 2021 (EMS snapshot)", "kind": "observed", "note": "Flood and flood-trace features mapped by EMS; a snapshot after the peak, only in the requested areas.", "closures": [{"id": "any", "label": "road closed if it touches the mapped flood OR a flood-trace feature"}, {"id": "mapped", "label": "road closed only if it touches the mapped flooded area (traces ignored)"}]}]
                 + [{"id": rp, "label": f"{n}-year flood (EFAS model)", "kind": "modelled", "note": "Modelled river flood depth; empty cells are dry OR not modelled.", "closures": [{"id": "wet", "label": "closed under any water"}, {"id": "d05", "label": "closed under 0.5 m or more"}]}
                    for rp, n in (("rp10", 10), ("rp100", 100), ("rp500", 500))],
    "capacities": [{"id": "restrictive", "label": "Assumption set A: core public buildings only, 5 m2 per person"}, {"id": "generous", "label": "Assumption set B: core + extended buildings, 3.5 m2 per person"}],
    "floods": floods, "overlays": overlays, "network": {"edges": net},
    "zones": [{"id": int(i), "lon": round(float(zlon[i]), 5), "lat": round(float(zlat[i]), 5), "muni": str(zg.muni.values[i]), "people": {s: round(float(zg["people_" + s].values[i]), 1) for s in ("obs2021", "rp10", "rp100", "rp500")}} for i in range(len(zg))],
    "shelters": [{"id": int(i), "lon": round(float(slon[i]), 5), "lat": round(float(slat[i]), 5), "type": str(cand.type.values[i]), "kind": str(cand.kind.values[i]), "footprint_m2": int(cand.footprint_m2.values[i]), "muni": str(cand.muni.values[i]),
                  "cap": {"restrictive": int(cand.cap_restrictive.values[i]), "generous": int(cand.cap_generous.values[i])}, "flooded": {s: bool(flooded[s][i]) for s in flooded}} for i in range(len(cand))],
    "results": results,
    "road_ratio_note": "worst_road_ratio and road colours = people on the edge turned into vehicles per hour (car share, persons per car, evacuation window) divided by an ASSUMED capacity of the road class: a stress indicator, not a traffic forecast",
}
OUTB.parent.mkdir(parents=True, exist_ok=True)
OUTB.write_text(json.dumps(bundle, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
(root / "research/r01/outputs/tool_pipeline_checks.json").write_text(json.dumps(CHECKS, indent=1, default=str), encoding="utf-8")
lap(f"bundle written: {OUTB.stat().st_size / 1e6:.1f} MB; {len(results)} result sets; {len(net):,} display edges; {len(zg):,} zones; {len(cand):,} shelters")
