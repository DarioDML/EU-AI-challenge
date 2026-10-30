"""Zonal exposure for Q1: residents and building points per municipality for an observed flood extent.

Rules (same as the rest of the package; field guide in YunAI):
  * three statuses, never two: `exposed` (inside a flood polygon) / `not_mapped_flooded_inside_aoi` (inside the EMS AOI, no polygon: NOT dry) /
    `not_assessed_outside_aoi`; people are conserved: the statuses of all zones plus `outside_zones` equal the people of the cells used;
  * residents are an areal allocation (uniform density inside each ~930 x 600 m cell); a cell cut by a municipality border is split by area;
  * everything is computed in an equal-area metric CRS (EPSG:3035); a point counts once even where polygons touch;
  * nothing here estimates harm: results are exposure counts, and minimums where the AOI covers only part of a municipality.
"""
import numpy as np
import pandas as pd
import shapely
from shapely.strtree import STRtree

from .common import CRS

STATUSES = ("exposed", "not_mapped_flooded_inside_aoi", "not_assessed_outside_aoi")


def cell_boxes(pw):
    """EPSG:3035 polygons and people of every GHS-POP cell with people in a `PopWindow` (corners transformed, not relabelled)."""
    import geopandas as gpd
    rr, cc = np.nonzero(pw.pv > 0)
    x0, y0 = pw.tf.c + cc * pw.tf.a, pw.tf.f + rr * pw.tf.e
    boxes = gpd.GeoSeries(shapely.box(x0, y0 + pw.tf.e, x0 + pw.tf.a, y0), crs="EPSG:4326").to_crs(CRS).values
    return np.asarray(boxes), pw.pv[rr, cc]


def residents_by_zone(boxes, people, zones, zone_ids, flood, aoi):
    """Residents per zone and status by areal weighting.

    boxes/people: cell polygons and people per cell; zones/zone_ids: municipality polygons and keys; flood, aoi: shapely geometries in
    the same CRS (the flood is clipped to the AOI first). Returns (DataFrame indexed by zone id with the three STATUSES plus
    `people_in_zone_cells`, outside_zones people not inside any zone)."""
    boxes, people, zones = np.asarray(boxes), np.asarray(people, float), np.asarray(zones)
    zone_ids = np.asarray(zone_ids)
    flood = shapely.intersection(flood, aoi) if not shapely.is_empty(flood) else flood
    barea = shapely.area(boxes)
    bi, zi = STRtree(zones).query(boxes, predicate="intersects")
    part = shapely.intersection(boxes[bi], zones[zi])
    a_part = shapely.area(part)
    keep = a_part > 0
    bi, zi, part, a_part = bi[keep], zi[keep], part[keep], a_part[keep]
    # the flood and the AOI inside each cell, computed once per cell, then cut by the zone part
    fl_cell = np.full(len(boxes), shapely.Polygon(), dtype=object)
    if not shapely.is_empty(flood):
        fparts = shapely.get_parts(flood)
        cb, fb = STRtree(fparts).query(boxes, predicate="intersects")
        for c in np.unique(cb):
            fl_cell[c] = shapely.intersection(boxes[c], shapely.union_all(fparts[fb[cb == c]]))
    aoi_cell = shapely.intersection(boxes, aoi)
    a_flood = shapely.area(shapely.intersection(part, fl_cell[bi]))
    a_aoi = shapely.area(shapely.intersection(part, aoi_cell[bi]))
    a_aoi = np.maximum(a_aoi, a_flood)               # flood is inside the AOI by construction; guards float noise
    w = people[bi] / barea[bi]
    df = pd.DataFrame({"zone": zone_ids[zi], "exposed": w * a_flood, "not_mapped_flooded_inside_aoi": w * (a_aoi - a_flood),
                       "not_assessed_outside_aoi": w * (a_part - a_aoi), "people_in_zone_cells": w * a_part})
    out = df.groupby("zone").sum()
    covered = np.bincount(bi, weights=a_part / barea[bi], minlength=len(boxes))
    outside = float((people * np.clip(1 - covered, 0, 1)).sum())
    return out, outside


def assign_zone(x, y, zones, zone_ids):
    """Zone id of each point (None if inside no zone). Zones should tile without overlap; a point on a shared border gets the first match
    only, so no point is counted twice."""
    zones, zone_ids = np.asarray(zones), np.asarray(zone_ids, dtype=object)
    pts = shapely.points(np.asarray(x, float), np.asarray(y, float))
    pi, zi = STRtree(zones).query(pts, predicate="intersects")
    out = np.full(len(pts), None, dtype=object)
    order = np.argsort(pi, kind="stable")
    pi, zi = pi[order], zi[order]
    first = np.r_[True, pi[1:] != pi[:-1]]
    out[pi[first]] = zone_ids[zi[first]]
    return out


def points_by_zone(x, y, mask, zones, zone_ids):
    """Count of points with mask True per zone (Series, zero-filled for all zones) and the count in no zone."""
    z = assign_zone(np.asarray(x)[np.asarray(mask)], np.asarray(y)[np.asarray(mask)], zones, zone_ids)
    s = pd.Series(z[z != None]).value_counts()                       # noqa: E711 (object array: elementwise comparison)
    return s.reindex(list(zone_ids), fill_value=0), int((z == None).sum())  # noqa: E711


def read_points_in_tiles(fs, tiles, countries=("be", "de", "nl"), country_geoms=None, pad_deg=0.002):
    """GHS-OBAT building points inside EPSG:3035 tiles, read by bbox from the remote country tables (never a whole-country scan).

    Returns a DataFrame (lon, lat, area, use, epoch, height, cc, fid) with every building once: tiles can overlap, so rows are
    de-duplicated on (country, feature id). `country_geoms` (EPSG:3035, optional): a country is skipped for tiles it does not touch."""
    import geopandas as gpd
    import pyogrio
    from pyproj import Transformer
    from .buildings import COLUMNS
    from .common import ROOT, VSI, one
    tr = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
    src = {}
    for cc in countries:
        gp = one([p for p in fs.find(f"{ROOT}/obat_{cc}") if p.endswith(".gpkg")], f"OBAT {cc}")
        src[cc] = (VSI + gp, pyogrio.list_layers(VSI + gp)[0][0])
    seen, parts = set(), []
    for t in tiles:
        xs, ys = tr.transform([t[0], t[2], t[0], t[2]], [t[1], t[1], t[3], t[3]])
        bb = (min(xs) - pad_deg, min(ys) - pad_deg, max(xs) + pad_deg, max(ys) + pad_deg)
        for cc, (path, layer) in src.items():
            if country_geoms is not None and not shapely.box(*t).intersects(country_geoms[cc]):
                continue
            g = gpd.read_file(path, layer=layer, bbox=bb, columns=COLUMNS, fid_as_index=True)
            if not len(g):
                continue
            keep = [(cc, int(i)) not in seen for i in g.index]
            g = g[keep]
            seen.update((cc, int(i)) for i in g.index)
            if len(g):
                parts.append(pd.DataFrame({"lon": g.geometry.x.values, "lat": g.geometry.y.values, "area": g["area"].values, "use": g["use"].values,
                                           "epoch": g["epoch"].values, "height": g["height"].values, "cc": cc, "fid": g.index.values}))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["lon", "lat", "area", "use", "epoch", "height", "cc", "fid"])


def cell_index(lon, lat, pw):
    """Flat index (row * columns + column) of the GHS-POP cell of each point in a `PopWindow`; -1 outside the window."""
    col = np.floor((np.asarray(lon, float) - pw.tf.c) / pw.tf.a).astype(int)
    row = np.floor((np.asarray(lat, float) - pw.tf.f) / pw.tf.e).astype(int)
    ok = (row >= 0) & (row < pw.nr) & (col >= 0) & (col < pw.nc)
    return np.where(ok, row * pw.nc + col, -1)


def people_per_building(cell, area, use, people_flat, cells_wanted=None):
    """Dasymetric allocation: each cell's residents are shared among that cell's built-up buildings (use 1 or 2, so also non-residential; finite positive
    footprint area) in proportion to footprint area. `cell` = flat cell index per building, `people_flat` = residents per flat cell.
    `cells_wanted` (bool per flat cell, optional): allocate only there; the caller must then have read ALL buildings of those cells.
    Returns (people per building, NaN where the building gets none; unallocated people = people of wanted cells without a usable building;
    allocated people)."""
    cell, area, use = np.asarray(cell), np.asarray(area, float), np.asarray(use)
    usable = (cell >= 0) & (use > 0) & np.isfinite(area) & (area > 0)
    if cells_wanted is not None:
        usable &= np.asarray(cells_wanted)[np.where(cell >= 0, cell, 0)]
    cell_area = np.bincount(cell[usable], weights=area[usable], minlength=len(people_flat))
    out = np.full(len(cell), np.nan)
    out[usable] = np.asarray(people_flat)[cell[usable]] * area[usable] / cell_area[cell[usable]]
    wanted = np.ones(len(people_flat), bool) if cells_wanted is None else np.asarray(cells_wanted)
    unallocated = float(np.asarray(people_flat)[wanted & (cell_area == 0)].sum())
    return out, unallocated, float(np.nansum(out))


def tile_bboxes(flood, buffer_m=100.0, cell_m=5000.0):
    """Few bounding boxes (EPSG:3035 metres) that together cover every part of `flood` plus `buffer_m`: parts are grouped by the
    `cell_m` grid cell of their centre, so a remote building table is read per tile instead of for the whole AOI box."""
    parts = shapely.get_parts(flood)
    parts = parts[~shapely.is_empty(parts)]
    if not len(parts):
        return []
    b = shapely.bounds(parts)
    cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
    key = pd.Series(list(zip(np.floor(cx / cell_m).astype(int), np.floor(cy / cell_m).astype(int))))
    tiles = []
    for _, idx in key.groupby(key).groups.items():
        bb = b[list(idx)]
        tiles.append((bb[:, 0].min() - buffer_m, bb[:, 1].min() - buffer_m, bb[:, 2].max() + buffer_m, bb[:, 3].max() + buffer_m))
    return tiles
