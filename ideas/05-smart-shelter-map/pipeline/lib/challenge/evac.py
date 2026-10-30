"""Zone-to-shelter assignment on a road graph (policy tool, smart shelter system).

Pipeline: snap demand zones and shelters to graph vertices -> travel time from each zone to its k fastest reachable shelters -> a capacity-limited transport problem
(minimise total person-time; people who cannot be placed are reported as UNASSIGNED, never dropped) -> shortest path per used zone-shelter pair -> people summed on every road edge.
Travel times are free-flow (no congestion), capacities are inputs; nothing here is an observation or a traffic forecast.
"""
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from . import roads as rd


def snap(xy, node_xy, allowed=None, max_m=500.0):
    """Nearest graph vertex (id) for each point; -1 if none lies within max_m. `allowed` (bool per vertex) restricts to e.g. the main connected component."""
    node_xy = np.asarray(node_xy, float)
    ids = np.arange(len(node_xy)) if allowed is None else np.nonzero(np.asarray(allowed))[0]
    d, j = cKDTree(node_xy[ids]).query(np.asarray(xy, float).reshape(-1, 2))
    return np.where(d <= max_m, ids[j], -1)


def nearest_shelters(g, d_nodes, s_nodes, k=8, limit_s=3600.0, chunk=40):
    """For each demand vertex the k fastest REACHABLE shelter vertices within limit_s. Returns DataFrame columns d, s (indices into the input arrays), t (seconds)."""
    d_nodes, s_nodes = np.asarray(d_nodes), np.asarray(s_nodes)
    rows = []
    for a in range(0, len(d_nodes), chunk):
        idx = np.arange(a, min(a + chunk, len(d_nodes)))
        valid = d_nodes[idx] >= 0
        if not valid.any():
            continue
        dist = dijkstra(g, directed=True, indices=d_nodes[idx[valid]], limit=limit_s)
        for r, i in enumerate(idx[valid]):
            t = dist[r][s_nodes]
            ok = np.nonzero(np.isfinite(t) & (s_nodes >= 0))[0]
            if len(ok):
                top = ok[np.argsort(t[ok], kind="stable")[:k]]
                rows.append(pd.DataFrame({"d": i, "s": top, "t": t[top]}))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame({"d": [], "s": [], "t": []})


def assign(people, cap, pairs, penalty=None):
    """Capacity-limited transport LP. people: per demand; cap: per shelter; pairs: DataFrame d, s, t.

    Minimises sum(time * flow) + penalty * unassigned, with each demand fully accounted for (placed + unassigned = people) and each shelter at or under capacity.
    Returns (flow per pair, unassigned per demand). penalty defaults to 10x the slowest pair time (so placing anyone beats leaving them out)."""
    people, cap = np.asarray(people, float), np.asarray(cap, float)
    nd, ns, ne = len(people), len(cap), len(pairs)
    if ne == 0:
        return np.zeros(0), people.copy()
    pen = penalty if penalty is not None else 10.0 * float(pairs.t.max() + 1.0)
    c = np.concatenate([pairs.t.values, np.full(nd, pen)])
    ar = np.arange(ne)
    a_eq = coo_matrix((np.ones(ne + nd), (np.concatenate([pairs.d.values, np.arange(nd)]), np.concatenate([ar, ne + np.arange(nd)]))), shape=(nd, ne + nd)).tocsr()
    a_ub = coo_matrix((np.ones(ne), (pairs.s.values, ar)), shape=(ns, ne + nd)).tocsr()
    res = linprog(c, A_ub=a_ub, b_ub=cap, A_eq=a_eq, b_eq=people, bounds=(0, None), method="highs")
    if not res.success:
        raise RuntimeError(f"assignment LP failed: {res.message}")
    x = np.clip(res.x, 0, None)
    return x[:ne], x[ne:]


def pair_times(g, d_nodes, s_nodes, d_idx, s_idx, chunk=40):
    """Travel time (s) on graph g for each (demand, shelter) pair, e.g. on the graph WITHOUT closures to measure the detour a closure causes. inf if unreachable."""
    d_nodes, s_nodes = np.asarray(d_nodes), np.asarray(s_nodes)
    d_idx, s_idx = np.asarray(d_idx), np.asarray(s_idx)
    out = np.full(len(d_idx), np.inf)
    ds = np.unique(d_idx)
    for a in range(0, len(ds), chunk):
        part = ds[a:a + chunk]
        dist = dijkstra(g, directed=True, indices=d_nodes[part])
        for r, d in enumerate(part):
            rows = np.nonzero(d_idx == d)[0]
            out[rows] = dist[r][s_nodes[s_idx[rows]]]
    return out


def route_loads(g, arc_edge, d_nodes, s_nodes, pairs, flow, n_edges, min_flow=1e-6, limit_s=3600.0, chunk=40):
    """Shortest path for every pair with flow > min_flow and the people carried by each road edge.

    Returns (load per edge, routes) where routes is a list of (pair row, edge ids along the path)."""
    load = np.zeros(n_edges)
    routes = []
    use = np.nonzero(flow > min_flow)[0]
    if len(use) == 0:
        return load, routes
    by_d = pd.Series(use).groupby(pairs.d.values[use]).apply(list)
    ds = list(by_d.index)
    for a in range(0, len(ds), chunk):
        part = ds[a:a + chunk]
        _, pred = dijkstra(g, directed=True, indices=d_nodes[part], return_predecessors=True, limit=limit_s)
        for r, d in enumerate(part):
            for row in by_d[d]:
                es = rd.path_edges(pred[r], int(d_nodes[d]), int(s_nodes[pairs.s.values[row]]), arc_edge)
                routes.append((row, es))
                load[es] += flow[row]
    return load, routes
