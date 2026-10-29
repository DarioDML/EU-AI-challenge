"""Shelter capacity and reach (Q3): how many exposed people can be placed in safe buildings within reach?

Two numbers are kept apart on purpose:
  within_reach  people with at least one eligible safe shelter within the reach distance, CAPACITY IGNORED (the brief's "has one within reach")
  sheltered     the most people that can be placed when every shelter's capacity is respected and nobody is counted twice (maximum flow)
so sheltered <= within_reach <= total demand always holds. Reach is a straight-line distance (an optimistic proxy: a road distance is never shorter);
capacity inputs are ASSUMPTIONS passed in by the caller, nothing here is a standard or an observation.
"""
import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import maximum_flow
from scipy.spatial import cKDTree

SCALE = 10       # people are carried as integers in tenths so rounding never moves a total by more than 0.05 per node


def capacity_persons(footprint_m2, levels, floors_default, usable_share, m2_per_person, use_levels=True):
    """Whole persons a building can take: footprint x floors x usable share / space per person (floors = tagged levels if used and known, else the default)."""
    footprint_m2 = np.asarray(footprint_m2, float)
    lv = np.asarray(levels, float)
    floors = np.where(np.isfinite(lv) & (lv > 0) & use_levels, lv, floors_default)
    return np.floor(footprint_m2 * floors * usable_share / m2_per_person)


def shelter_flow(demand_xy, demand_people, supply_xy, supply_cap, reach_m):
    """Max-flow placement of demand nodes into supply nodes within a straight-line reach.

    Returns a dict: total, within_reach, sheltered, per_demand_within (bool array), per_demand_sheltered (array), capacity_in_reach (capacity of shelters that any demand can reach).
    """
    dxy, dp = np.asarray(demand_xy, float).reshape(-1, 2), np.asarray(demand_people, float)
    sxy, sc = np.asarray(supply_xy, float).reshape(-1, 2), np.asarray(supply_cap, float)
    nd, ns = len(dp), len(sc)
    out = {"total": float(dp.sum())}
    if nd == 0 or ns == 0:
        return {**out, "within_reach": 0.0, "sheltered": 0.0, "per_demand_within": np.zeros(nd, bool), "per_demand_sheltered": np.zeros(nd), "capacity_in_reach": 0.0}
    sd = cKDTree(dxy).sparse_distance_matrix(cKDTree(sxy), reach_m, output_type="coo_matrix")      # edges d -> s with distance <= reach (inclusive)
    within = np.zeros(nd, bool)
    within[np.unique(sd.row)] = True
    cap_in = float(sc[np.unique(sd.col)].sum()) if sd.nnz else 0.0
    n = nd + ns + 2
    src, snk = 0, n - 1
    big = int(max(dp.sum(), 1.0) * SCALE) + 1
    rows = np.concatenate([np.zeros(nd, int), sd.row + 1, nd + 1 + np.arange(ns)])
    cols = np.concatenate([1 + np.arange(nd), nd + 1 + sd.col, np.full(ns, snk)])
    caps = np.concatenate([np.rint(dp * SCALE).astype(np.int64), np.full(sd.nnz, big, dtype=np.int64), np.rint(sc * SCALE).astype(np.int64)])
    g = csr_matrix(coo_matrix((caps.astype(np.int32), (rows, cols)), shape=(n, n)))
    res = maximum_flow(g, src, snk)
    per = np.asarray(res.flow[src, 1:nd + 1].todense()).ravel() / SCALE
    return {**out, "within_reach": float(dp[within].sum()), "sheltered": float(res.flow_value) / SCALE, "per_demand_within": within, "per_demand_sheltered": per, "capacity_in_reach": cap_in}
