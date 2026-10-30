"""Question:    Policy tool (smart shelter system). Build a routable road network for the hero area (Eifel: Schleiden / Kall; Ahr valley: Altenahr - Sinzig; Germany only).
Data:         Geofabrik extracts rheinland-pfalz and nordrhein-westfalen (OSM state 29 Oct 2026, (c) OpenStreetMap contributors, ODbL; cached on the Colab disk, provider MD5 re-verified),
              layer 'lines', highway classes motorway ... living_street (+ links); service roads, tracks and paths are left out on purpose (not evacuation routes).
Assumptions:  hero-area bbox lon 6.30-7.45, lat 50.30-50.78 (covers the Eifel and Ahr cases plus about 10 km margin for shelter reach). Ways are split at shared vertices (challenge.roads,
              11 known-answer tests); a crossing without a shared vertex (bridge, tunnel) is not a junction. One-way: tagged, or implied for motorways, links and roundabouts. Travel time =
              length / tagged maxspeed, else the class default speed (ASSUMPTION, free flow, no congestion). Bridges and tunnels are kept as flags because a flood can close a bridge approach.
Tools:        pyogrio 0.13 (OSM driver, Arrow stream), shapely 2, challenge.roads, geopandas (GeoParquet), scipy (connected components).
Outputs:      $YUNAI_RUN_DIR/ edges.parquet (EPSG:3035 LineStrings), nodes.parquet, roads_meta.json
Finding:      research/r01/NOTE.md
"""
import hashlib
import json
import os
import re
import sys
import time
import warnings

sys.path.insert(0, "/content/yunai_src")
warnings.filterwarnings("ignore")
import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyogrio
import pyogrio.raw
import requests
import shapely
from pyproj import Transformer
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from challenge import roads as rd

T0 = time.time()
OUT = os.environ["YUNAI_RUN_DIR"]
CACHE = "/content/cache/osm"
GEOF = "https://download.geofabrik.de/europe/germany/"
FILES = ["rheinland-pfalz-latest.osm.pbf", "nordrhein-westfalen-latest.osm.pbf"]
BBOX = (6.30, 50.30, 7.45, 50.78)
CLASSES = list(rd.SPEED_KMH)
WHERE = "highway IN (" + ",".join(f"'{c}'" for c in CLASSES) + ")"
RE = {k: re.compile(rf'"{k}"=>"([^"]*)"') for k in ("oneway", "maxspeed", "bridge", "tunnel", "junction", "ref")}
CHECKS, FAILED = {}, []


def lap(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def check(name, ok, detail):
    CHECKS[name] = {"pass": bool(ok), **detail}
    if not ok:
        FAILED.append(name)
    lap(f"check {name}: {'PASS' if ok else 'FAIL'} {json.dumps(detail, default=str)[:300]}")


geoms, attrs, seen, cards = [], [], set(), []
for name in FILES:
    url, path = GEOF + name, os.path.join(CACHE, name)
    head = requests.head(url, timeout=60, allow_redirects=True)
    pub = requests.get(url + ".md5", timeout=60).text.split()[0]
    if not (os.path.exists(path) and os.path.getsize(path) == int(head.headers["Content-Length"])):
        with requests.get(url, stream=True, timeout=120) as r, open(path, "wb") as fh:
            for ch in r.iter_content(1 << 24):
                fh.write(ch)
    md5 = hashlib.md5()
    with open(path, "rb") as fh:
        for ch in iter(lambda: fh.read(1 << 24), b""):
            md5.update(ch)
    check(f"md5_matches_provider_{name.split('-latest')[0]}", md5.hexdigest() == pub, {"bytes": os.path.getsize(path)})
    cards.append({"file": name, "md5": pub, "last_modified": head.headers.get("Last-Modified")})
    n = 0
    with pyogrio.raw.open_arrow(path, layer="lines", where=WHERE, columns=["osm_id", "name", "highway", "other_tags"], bbox=BBOX, batch_size=50000, use_pyarrow=True) as (meta, reader):
        gname = meta.get("geometry_name") or "wkb_geometry"
        for batch in reader:
            tbl = pa.Table.from_batches([batch]) if isinstance(batch, pa.RecordBatch) else batch
            g = shapely.from_wkb(tbl.column(gname).to_numpy(zero_copy_only=False))
            oid, nm, hw, tg = (tbl.column(c).to_pylist() for c in ("osm_id", "name", "highway", "other_tags"))
            for k in range(len(g)):
                if g[k] is None or oid[k] in seen or shapely.get_num_coordinates(g[k]) < 2:
                    continue
                seen.add(oid[k])
                t = tg[k] or ""
                ow = RE["oneway"].search(t)
                ow = ow.group(1) if ow else None
                jn = RE["junction"].search(t)
                implied = hw[k] in ("motorway", "motorway_link") or (jn is not None and jn.group(1) == "roundabout")
                oneway = 1 if ow in ("yes", "true", "1") else (-1 if ow == "-1" else (0 if ow in ("no", "false", "0") else (1 if implied else 0)))
                ms = RE["maxspeed"].search(t)
                br, tn = RE["bridge"].search(t), RE["tunnel"].search(t)
                rf = RE["ref"].search(t)
                geoms.append(g[k])
                attrs.append((oid[k], nm[k], hw[k], rf.group(1) if rf else None, oneway, rd.parse_maxspeed(ms.group(1) if ms else None), br is not None and br.group(1) not in ("no", ""), tn is not None and tn.group(1) not in ("no", "")))
            n += len(g)
    lap(f"{name}: {n:,} road ways read")
at = pd.DataFrame(attrs, columns=["osm_id", "name", "highway", "ref", "oneway", "maxspeed", "bridge", "tunnel"])
lap(f"{len(at):,} distinct road ways; by class: {at.highway.value_counts().to_dict()}")

# ---- split at shared vertices
res = rd.split_ways(np.array(geoms, dtype=object), scale=1e7)
tr = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
seg = shapely.transform(res["geom"], lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))
way = res["way"]
ed = pd.DataFrame({"u": res["u"], "v": res["v"], "osm_id": at.osm_id.values[way], "highway": at.highway.values[way], "name": at.name.values[way], "ref": at.ref.values[way],
                   "oneway": at.oneway.values[way], "bridge": at.bridge.values[way], "tunnel": at.tunnel.values[way], "length_m": shapely.length(seg)})
ed["time_s"] = rd.travel_time_s(ed.length_m.values, ed.highway.values, at.maxspeed.values[way])
nx_, ny_ = tr.transform(res["nodes_xy"][:, 0], res["nodes_xy"][:, 1])
nodes = pd.DataFrame({"node": np.arange(len(nx_)), "x": np.round(nx_, 2), "y": np.round(ny_, 2)})
lap(f"{len(ed):,} edges from {len(at):,} ways, {len(nodes):,} vertices")

# ---- checks
way_len = shapely.length(shapely.transform(np.array(geoms, dtype=object), lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1]))))
check("splitting_conserves_total_length", abs(ed.length_m.sum() - way_len.sum()) / way_len.sum() < 1e-6, {"edges_km": round(ed.length_m.sum() / 1e3, 1), "ways_km": round(float(way_len.sum()) / 1e3, 1)})
check("no_degenerate_edges", bool((ed.length_m > 0).all() and (ed.time_s > 0).all()), {"min_length_m": float(ed.length_m.min())})
n = len(nodes)
used, inv_ = np.unique(np.concatenate([ed.u.values, ed.v.values]), return_inverse=True)           # only vertices that an edge uses are graph nodes (the rest are interior shape points)
cu, cv = inv_[:len(ed)], inv_[len(ed):]
a = coo_matrix((np.ones(len(ed)), (cu, cv)), shape=(len(used), len(used)))
nc, lab = connected_components(a, directed=False)
sizes = np.bincount(lab)
big = sizes.max() / len(used)
check("largest_component_holds_most_graph_nodes", big > 0.85, {"graph_nodes": int(len(used)), "components": int(nc), "largest_share": round(float(big), 3), "second_largest": int(np.sort(sizes)[-2])})
deg = np.bincount(np.concatenate([ed.u.values, ed.v.values]), minlength=n)
check("junction_vertices_exist", int((deg >= 3).sum()) > 1000, {"vertices_with_degree_ge_3": int((deg >= 3).sum())})
nodes["main_component"] = False
nodes.loc[used[lab == sizes.argmax()], "main_component"] = True        # snap people and shelters only onto the main network, never onto an island
ed_g = gpd.GeoDataFrame(ed, geometry=seg, crs="EPSG:3035")
ed_g.to_parquet(os.path.join(OUT, "edges.parquet"))
nodes.to_parquet(os.path.join(OUT, "nodes.parquet"))
json.dump({"checks": CHECKS, "failed": FAILED, "cards": cards, "bbox": BBOX, "ways": int(len(at)), "edges": int(len(ed)), "nodes": int(n), "classes": at.highway.value_counts().to_dict(), "seconds": round(time.time() - T0, 1)},
          open(os.path.join(OUT, "roads_meta.json"), "w"), indent=1, default=str)
lap(f"done; failed: {FAILED or 'none'}")
raise SystemExit(1 if FAILED else 0)
