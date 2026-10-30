"""Question:    Policy tool (smart shelter system). For each flood level (observed 2021 and EFAS 10-, 100-, 500-year), how many residents sit inside the flood, where (250 m nodes,
              dasymetric), and what is the EFAS depth field (so roads under water can be closed locally)? Hero area: Eifel and Ahr valley, Germany.
Data:         EMS flood layers of all 19 AOIs (pinset q1_ems), EFAS river flood depth RP10 / RP100 / RP500 (bucket cems-efas), GHS-POP E2020, GHS-OBAT DE (pinset q1_exposure,
              hash-verified), all read from the challenge bucket.
Assumptions:  hero bbox lon 6.30-7.45, lat 50.30-50.78 (Germany only). Residents are placed on OBAT buildings of their GHS-POP cell by footprint area (challenge.zonal.people_per_building,
              4 known-answer tests); buildings are read for the whole bbox plus a 3 km margin so border cells are complete. A building is 'in the flood' if it lies in the EMS flood or
              trace (observed 2021) or has EFAS depth > 0 (RPxx). EFAS holds values only where wet (>= 0.1 m): an empty cell is 'dry OR not modelled' (smaller rivers are
              missing), so a scenario count is a MINIMUM and never a 'known dry' share; the 500-year map is a ceiling that 2021 exceeded in places. Observed 2021 is one satellite snapshot per area (14-20 July 2021), not the peak.
Tools:        challenge.zonal / population / ems / efas / pins / common, shapely, numpy, pandas.
Outputs:      $YUNAI_RUN_DIR/ scenario_nodes.csv (250 m nodes with people per scenario), efas_windows.npz (depth arrays + transforms), scenarios_meta.json
Finding:      research/r01/NOTE.md
"""
import json
import os
import sys
import time
import warnings

sys.path.insert(0, "/content/yunai_src")
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
from challenge import common, efas, ems, pins, population, zonal

T0 = time.time()
OUT = os.environ["YUNAI_RUN_DIR"]
CRS = common.CRS
CHECKS, FAILED = {}, []
HERO = (6.30, 50.30, 7.45, 50.78)         # lon/lat bbox of the hero area
PADM = 3000.0                             # margin (m) so border cells of the population grid are complete


def lap(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def check(name, ok, detail):
    CHECKS[name] = {"pass": bool(ok), **detail}
    if not ok:
        FAILED.append(name)
    lap(f"check {name}: {'PASS' if ok else 'FAIL'} {json.dumps(detail, default=str)[:350]}")


AOIS = [("de", "EMSR517", a) for a in ("AOI01", "AOI03", "AOI04", "AOI05", "AOI06", "AOI07", "AOI08", "AOI09", "AOI10", "AOI11", "AOI14",
                                         "AOI15", "AOI16", "AOI17", "AOI18", "AOI20")] + [("be", "EMSR518", "AOI01"), ("be", "EMSR518", "AOI02"), ("nl", "EMSR520", "AOI01")]
fs = common.gcs()
p1, p2 = pins.load_pinset("q1_ems"), pins.load_pinset("q1_exposure")
pv1, pv2 = pins.verify(fs, p1), pins.verify(fs, p2)
check("inputs_match_pinned_generations", pv1["ok"] and pv2["ok"] and len(p1) == 243 and len(p2) == 5, {"ems": [pv1["pinned"], pv1["checked"]], "exposure": [pv2["pinned"], pv2["checked"]]})
E = {(emsr, aoi): ems.load(fs, cc, emsr, aoi, notation=None) for cc, emsr, aoi in AOIS}
flood_t = shapely.make_valid(shapely.union_all([a.flood_u["UNION"] for a in E.values()]))      # observed 2021: flood + trace (decision H2)
tr = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
xs, ys = tr.transform([HERO[0], HERO[2], HERO[0], HERO[2]], [HERO[1], HERO[1], HERO[3], HERO[3]])
bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
lap(f"observed flood ready; hero bbox EPSG:3035 {round(bx0)}, {round(by0)}, {round(bx1)}, {round(by1)}")

# ---- population window and ALL buildings of the padded hero bbox (5 km tiles)
inv = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
pl, pb = inv.transform([bx0 - PADM, bx1 + PADM], [by0 - PADM, by1 + PADM])
bounds_pad = (min(pl), min(pb), max(pl), max(pb))
pw = population.PopWindow(bounds_pad)
boxes, people = zonal.cell_boxes(pw)
total_people_window = float(pw.pv.sum())
gx0, gy0 = int(np.floor((bx0 - PADM) / 5000)), int(np.floor((by0 - PADM) / 5000))
gx1, gy1 = int(np.ceil((bx1 + PADM) / 5000)), int(np.ceil((by1 + PADM) / 5000))
squares = shapely.multipolygons([shapely.box(gx * 5000, gy * 5000, (gx + 1) * 5000, (gy + 1) * 5000) for gx in range(gx0, gx1) for gy in range(gy0, gy1)])
tiles = zonal.tile_bboxes(squares, buffer_m=0.0, cell_m=5000.0)
lap(f"{len(tiles)} tiles to read; GHS-POP window {pw.nr}x{pw.nc} cells, {total_people_window:,.0f} residents")
pts = zonal.read_points_in_tiles(fs, tiles, countries=("de",))
lap(f"{len(pts):,} OBAT building points read")
ci = zonal.cell_index(pts.lon.values, pts.lat.values, pw)
pp, unalloc, alloc = zonal.people_per_building(ci, pts.area.values, pts.use.values, pw.pv.ravel(), cells_wanted=None)
check("people_conserved_in_window", abs(alloc + unalloc - total_people_window) < 1e-6 * total_people_window,
      {"allocated": round(alloc, 1), "unallocated_cells_without_usable_building": round(unalloc, 1), "window_residents": round(total_people_window, 1)})
x, y = tr.transform(pts.lon.values, pts.lat.values)
inside = (pts.lon.values >= HERO[0]) & (pts.lon.values <= HERO[2]) & (pts.lat.values >= HERO[1]) & (pts.lat.values <= HERO[3])

# ---- scenarios
rasters = efas.read_windows(fs, bounds_pad)
member = {"obs2021": shapely.contains_xy(flood_t, x, y)}
for rp in ("RP10", "RP100", "RP500"):
    d = efas.sample(rasters[rp], pts.lon.values, pts.lat.values)
    member[rp.lower()] = np.isfinite(d) & (d > 0)
people_b = np.nan_to_num(pp)
nodes = pd.DataFrame({"gx": (x // 250).astype(int), "gy": (y // 250).astype(int)})
for k, m in member.items():
    nodes[f"people_{k}"] = np.where(m & inside, people_b, 0.0)
nodes["people_all"] = np.where(inside, people_b, 0.0)
nd = nodes.groupby(["gx", "gy"]).sum().reset_index()
nd = nd[(nd[[c for c in nd.columns if c.startswith("people_") and c != "people_all"]] > 0).any(axis=1)].copy()
nd["x"], nd["y"] = (nd.gx + 0.5) * 250, (nd.gy + 0.5) * 250
nd.round(3).to_csv(os.path.join(OUT, "scenario_nodes.csv"), index=False)
tot = {k: float(nd[f"people_{k}"].sum()) for k in member}
lap(f"residents inside each scenario (hero area, minimum): {({k: round(v) for k, v in tot.items()})}; all residents in the hero bbox {nodes.people_all.sum():,.0f}")
check("node_sums_equal_building_sums", all(abs(tot[k] - float(people_b[member[k] & inside].sum())) < 1e-6 * max(1.0, tot[k]) for k in member), {k: round(v, 1) for k, v in tot.items()})
viol = {a: float((member[a] & ~member[b]).sum() / max(1, member[a].sum())) for a, b in (("rp10", "rp100"), ("rp100", "rp500"))}
check("efas_scenarios_are_nested", all(v < 0.02 for v in viol.values()), {"share_of_smaller_scenario_buildings_missing_from_larger": {k: round(v, 4) for k, v in viol.items()}})
check("observed_inside_german_q1_total", 0 < tot["obs2021"] <= 29360 * 1.01, {"hero_observed_residents": round(tot["obs2021"]), "german_q1_dasymetric_total": 29360})
np.savez_compressed(os.path.join(OUT, "efas_windows.npz"), **{f"{rp}_arr": r.arr.astype(np.float16) for rp, r in rasters.items()}, **{f"{rp}_tf": np.array(tuple(r.tf)[:6]) for rp, r in rasters.items()})
json.dump({"checks": CHECKS, "failed": FAILED, "hero_lonlat": HERO, "residents_in_scenario_minimum": {k: round(v) for k, v in tot.items()}, "residents_in_hero_bbox": round(float(nodes.people_all.sum())),
           "nodes": int(len(nd)), "efas_window_shapes": {rp: list(r.arr.shape) for rp, r in rasters.items()}, "seconds": round(time.time() - T0, 1)}, open(os.path.join(OUT, "scenarios_meta.json"), "w"), indent=1, default=str)
lap(f"done; failed: {FAILED or 'none'}")
raise SystemExit(1 if FAILED else 0)
