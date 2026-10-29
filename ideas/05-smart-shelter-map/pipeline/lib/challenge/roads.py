"""Road graph for the shelter tool: split OSM ways at shared vertices, then a directed graph with one-ways and closures.

Why splitting: an OSM way is a line; a side street joins a through road at a vertex in the MIDDLE of the through road's line, so a graph that only
uses line endpoints misses that junction. Two ways that cross WITHOUT sharing a vertex (a bridge over a road, a tunnel) are not connected, which is right.
Speeds and capacities below are ASSUMPTIONS (free-flow defaults per road class), to be verified; nothing here is observed traffic.
"""
import numpy as np
import pandas as pd
import shapely
from scipy.sparse import csr_matrix

# ASSUMPTION: default free-flow speed per OSM highway class, km/h (a tagged numeric maxspeed overrides it)
SPEED_KMH = {"motorway": 100.0, "motorway_link": 60.0, "trunk": 80.0, "trunk_link": 50.0, "primary": 70.0, "primary_link": 50.0, "secondary": 60.0, "secondary_link": 40.0,
             "tertiary": 50.0, "tertiary_link": 40.0, "unclassified": 40.0, "residential": 30.0, "living_street": 10.0}


def split_ways(geoms, scale=1e7):
    """Split LineStrings at every vertex shared by two or more ways and at every way end.

    geoms: array of LineString. scale: coordinates are matched after rounding to 1/scale (1e7 for lon/lat = about 1 cm; use 1e2 or less for metres).
    Returns dict: u, v (vertex ids), way (index into geoms), geom (segment LineStrings), nodes_xy (one coordinate per vertex id).
    """
    geoms = np.asarray(geoms, dtype=object)
    xy, widx = shapely.get_coordinates(geoms, return_index=True)
    ncoord = shapely.get_num_coordinates(geoms)
    ix, iy = np.round(xy[:, 0] * scale).astype(np.int64), np.round(xy[:, 1] * scale).astype(np.int64)
    ix -= ix.min()
    iy -= iy.min()
    key = ix * (iy.max() + 1) + iy
    uniq, first, vid = np.unique(key, return_index=True, return_inverse=True)
    nv, nw = len(uniq), len(geoms)
    pair = np.unique(vid.astype(np.int64) * nw + widx)                   # distinct (vertex, way) pairs
    ways_per_vertex = np.bincount(pair // nw, minlength=nv)
    brk = ways_per_vertex[vid] >= 2
    ends = np.cumsum(ncoord)
    brk[ends - 1] = True                                                 # last coordinate of every way
    brk[ends - ncoord] = True                                            # first coordinate of every way
    b = np.nonzero(brk)[0]
    s, e = b[:-1], b[1:]
    ok = (widx[s] == widx[e]) & (e > s)                                  # consecutive breakpoints of the SAME way
    s, e = s[ok], e[ok]
    length = e - s + 1
    start = np.concatenate([[0], np.cumsum(length)[:-1]])
    pos = np.arange(length.sum()) - np.repeat(start, length) + np.repeat(s, length)
    seg = shapely.linestrings(xy[pos], indices=np.repeat(np.arange(len(s)), length))
    return {"u": vid[s], "v": vid[e], "way": widx[s], "geom": seg, "nodes_xy": xy[first]}


def parse_maxspeed(tag):
    """Numeric km/h from an OSM maxspeed value, or NaN (unparsable, 'none', 'signals', mph and walk are ignored on purpose)."""
    if tag is None:
        return np.nan
    t = str(tag).strip()
    return float(t) if t.isdigit() and 5 <= int(t) <= 130 else np.nan


def travel_time_s(length_m, highway, maxspeed_kmh=None):
    """Seconds at the tagged speed if given, otherwise at the class default (ASSUMPTION)."""
    sp = np.array([SPEED_KMH.get(h, 30.0) for h in highway], float)
    if maxspeed_kmh is not None:
        ms = np.asarray(maxspeed_kmh, float)
        sp = np.where(np.isfinite(ms), ms, sp)
    return np.asarray(length_m, float) / (sp / 3.6)


def build_digraph(u, v, time_s, oneway, n_nodes, closed=None):
    """Directed travel-time graph as a scipy CSR matrix plus the edge id that realises each arc.

    oneway: 0 two-way, 1 forward only (u -> v), -1 reverse only (v -> u). closed: boolean per edge, True = removed (flooded).
    Parallel arcs keep the fastest one. Returns (csr matrix, arc_edge array aligned with csr.data order is NOT guaranteed, so a dict (row, col) -> edge id is returned instead).
    """
    u, v, t, ow = (np.asarray(a) for a in (u, v, time_s, oneway))
    keep = np.ones(len(u), bool) if closed is None else ~np.asarray(closed, bool)
    eid = np.arange(len(u))
    fw, bw = keep & (ow >= 0), keep & (ow <= 0)
    r = np.concatenate([u[fw], v[bw]])
    c = np.concatenate([v[fw], u[bw]])
    w = np.concatenate([t[fw], t[bw]])
    e = np.concatenate([eid[fw], eid[bw]])
    df = pd.DataFrame({"r": r, "c": c, "w": w, "e": e})
    df = df[df.r != df.c].sort_values("w").drop_duplicates(["r", "c"])
    g = csr_matrix((df.w.values, (df.r.values, df.c.values)), shape=(n_nodes, n_nodes))
    return g, dict(zip(zip(df.r.values.tolist(), df.c.values.tolist()), df.e.values.tolist()))


def path_edges(pred_row, source, target, arc_edge):
    """Edge ids along the shortest path source -> target from one row of a scipy predecessor matrix (empty list if unreachable)."""
    out, node = [], target
    while node != source:
        p = pred_row[node]
        if p < 0:
            return []
        out.append(arc_edge[(int(p), int(node))])
        node = int(p)
    return out[::-1]
