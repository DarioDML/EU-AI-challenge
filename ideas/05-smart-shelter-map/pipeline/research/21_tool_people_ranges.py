"""Question:    How much do the residents inside each flood level depend on our choices? Counts with four ways of spreading GHS-POP cells and with the
              flood edge moved one EFAS cell in and out; then the shelter plan at the lowest and highest count.
Data:         GHS-POP E2020, GHS-OBAT DE, EFAS RP10 / RP100 / RP500 (public challenge bucket); EMS flood + trace union (analysis/out/flood_union.gpkg,
              optional, for the observed 2021 level); data/bundle.json (municipality outlines, zones, plans, shelter capacities).
Assumptions:  Same area as the tool (municipalities of Kreis Euskirchen and Landkreis Ahrweiler inside the hero bbox). Base rule = the tool's rule
              (cell residents shared over OBAT points with use 1 or 2, by footprint). The shelter plan at the two ends is the bundle's plan with each zone's
              residents scaled, not re-optimised: shelters over capacity overflow, so the unplaced count is an upper estimate.
Standalone:   needs geopandas, pyogrio, rasterio, shapely, pyproj, numpy (no Colab library). Writes `people_ranges` into data/bundle.json.
Usage:        python -P pipeline/research/21_tool_people_ranges.py [path/to/flood_union.gpkg]
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

import geopandas as gpd
import numpy as np
import pyogrio
import rasterio
import shapely
from affine import Affine
from pyproj import Transformer
from rasterio.windows import Window

os.environ.setdefault("GS_NO_SIGN_REQUEST", "YES")

Json: TypeAlias = dict[str, "Json"] | list["Json"] | str | int | float | bool | None

TOOL = Path(__file__).resolve().parents[2]
REPO = TOOL.parents[1]
BUNDLE = TOOL / "data" / "bundle.json"
CACHE = REPO / "data" / "raw" / "obat_de_hero_ranges.parquet"
BUCKET = "/vsigs/datasets_challenge/working_data"
POP_PATH = f"{BUCKET}/ghs_pop/GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0/GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0.tif"
EFAS_PATH = BUCKET + "/cems-efas/Europe_RP{}_filled_depth.tif"
OBAT_NAME = "GHS_OBAT_GPKG_DEU_E2020_R2024A_V1_0"
OBAT_PATH = f"{BUCKET}/obat_de/{OBAT_NAME}/{OBAT_NAME}.gpkg"
HERO = (6.30, 50.30, 7.45, 50.78)
MARGIN_DEG = 0.05
STOREY_M = 3.0
ZONE_M = 500.0
OBS_EDGE_M = 60.0
CHECK_TOLERANCE = 0.03
LEVELS = ("obs2021", "rp10", "rp100", "rp500")
BUILDING_RULES = ("footprint", "equal", "floor_area")
RULE_LABELS = {
    "footprint": "footprint share (tool's rule)",
    "equal": "equal split over buildings",
    "floor_area": "floor-area share",
    "cell_area": "flooded share of the cell area",
    "cell_centre": "whole cell if its centre is flooded",
    "edge_in": "flood edge one EFAS cell inward",
    "edge_out": "flood edge one EFAS cell outward",
}
TO_LAEA = Transformer.from_crs(4326, 3035, always_xy=True)
T0 = time.time()


def lap(message: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {message}", flush=True)


@dataclass(frozen=True)
class Grid:
    values: np.ndarray
    transform: Affine
    nodata: float | None


def read_grid(path: str, bbox: tuple[float, float, float, float]) -> Grid:
    with rasterio.open(path) as source:
        west, south, east, north = bbox
        inverse = ~source.transform
        col0, row0 = inverse * (west, north)
        col1, row1 = inverse * (east, south)
        window = Window(math.floor(col0), math.floor(row0), math.ceil(col1) - math.floor(col0), math.ceil(row1) - math.floor(row0))
        return Grid(source.read(1, window=window), source.window_transform(window), source.nodata)


def cell_index(grid: Grid, lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    cols, rows = ~grid.transform * (lon, lat)
    height, width = grid.values.shape
    return np.clip(np.floor(rows).astype(int), 0, height - 1), np.clip(np.floor(cols).astype(int), 0, width - 1)


def cell_centres(grid: Grid) -> tuple[np.ndarray, np.ndarray]:
    rows, cols = np.indices(grid.values.shape)
    return grid.transform * (cols + 0.5, rows + 0.5)


def wet_mask(grid: Grid) -> np.ndarray:
    values = grid.values.astype(float)
    if grid.nodata is not None:
        values[values == grid.nodata] = np.nan
    return np.isfinite(values) & (values > 0)


def shift_any(mask: np.ndarray, combine_all: bool) -> np.ndarray:
    padded = np.pad(mask, 1, mode="edge")
    height, width = mask.shape
    out = mask.copy()
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        window = padded[1 + dr:1 + dr + height, 1 + dc:1 + dc + width]
        out = (out & window) if combine_all else (out | window)
    return out


def read_buildings(bbox: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    if CACHE.exists():
        return gpd.read_parquet(CACHE)
    frame = pyogrio.read_dataframe(OBAT_PATH, bbox=bbox, columns=["use", "height", "area"])
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(CACHE)
    return frame


def share(population: np.ndarray, cells: np.ndarray, weight: np.ndarray) -> np.ndarray:
    weight_sum = np.bincount(cells, weights=weight, minlength=population.size)
    out = np.zeros(weight.shape)
    shared = weight_sum[cells] > 0
    out[shared] = population[cells[shared]] * weight[shared] / weight_sum[cells[shared]]
    return out


def zone_keys(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    x, y = TO_LAEA.transform(lon, lat)
    return np.floor(np.asarray(x) / ZONE_M).astype(np.int64) * 100_000 + np.floor(np.asarray(y) / ZONE_M).astype(np.int64)


def by_zone(keys: np.ndarray, people: np.ndarray) -> dict[int, float]:
    unique, inverse = np.unique(keys, return_inverse=True)
    sums = np.bincount(inverse, weights=people)
    return {int(k): float(v) for k, v in zip(unique, sums) if v > 0}


def scaled_plan(result: dict[str, Json], zone_of_bundle: dict[int, int], base_zone: dict[int, float], variant_zone: dict[int, float],
                capacity: dict[int, float], total_places: float) -> dict[str, float | int]:
    ratio: dict[int, float] = {}
    new_people = 0.0
    for key, people in variant_zone.items():
        zone = zone_of_bundle.get(key)
        base = base_zone.get(key, 0.0)
        if zone is None or base <= 0:
            new_people += people
        else:
            ratio[zone] = people / base
    load: dict[int, float] = {}
    for row in result["assign"]:
        zone, shelter, people = int(row[0]), int(row[1]), float(row[2])
        load[shelter] = load.get(shelter, 0.0) + people * ratio.get(zone, 0.0)
    overflow = sum(max(0.0, people - capacity[s]) for s, people in load.items())
    unplaced = sum(float(people) * ratio.get(int(zone), 0.0) for zone, people in result["unassigned"].items())
    total = sum(variant_zone.values())
    return {
        "people": round(total),
        "places_per_resident": round(total_places / total, 1) if total > 0 else 0.0,
        "shelters_full": sum(1 for s, people in load.items() if people >= capacity[s] - 0.5),
        "shelters_used": sum(1 for people in load.values() if people > 0.05),
        "unplaced_at_most": round(unplaced + overflow + new_people),
    }


def main() -> None:
    flood_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    bundle: dict[str, Json] = json.loads(BUNDLE.read_text(encoding="utf-8"))
    area = shapely.union_all([shapely.geometry.shape(m["geometry"]) for m in bundle["munis"]])
    shapely.prepare(area)
    bbox = (HERO[0] - MARGIN_DEG, HERO[1] - MARGIN_DEG, HERO[2] + MARGIN_DEG, HERO[3] + MARGIN_DEG)

    buildings = read_buildings(bbox)
    lon, lat = buildings.geometry.x.to_numpy(), buildings.geometry.y.to_numpy()
    usable = np.isin(buildings["use"].to_numpy(), (1, 2))
    lon, lat = lon[usable], lat[usable]
    footprint = buildings["area"].to_numpy(dtype=float)[usable]
    floors = np.maximum(1.0, np.nan_to_num(buildings["height"].to_numpy(dtype=float)[usable], nan=STOREY_M) / STOREY_M)
    lap(f"{usable.sum():,} usable OBAT points")

    pop = read_grid(POP_PATH, bbox)
    population = np.nan_to_num(pop.values.astype(float)).ravel()
    population[population < 0] = 0.0
    rows, cols = cell_index(pop, lon, lat)
    cells = rows * pop.values.shape[1] + cols
    people = {
        "footprint": share(population, cells, footprint),
        "equal": share(population, cells, np.ones_like(footprint)),
        "floor_area": share(population, cells, footprint * floors),
    }
    in_area = shapely.contains_xy(area, lon, lat) & (lon >= HERO[0]) & (lon <= HERO[2]) & (lat >= HERO[1]) & (lat <= HERO[3])
    keys = zone_keys(lon, lat)
    cx, cy = cell_centres(pop)
    cx, cy = cx.ravel(), cy.ravel()
    cell_in_area = shapely.contains_xy(area, cx, cy) & (cx >= HERO[0]) & (cx <= HERO[2]) & (cy >= HERO[1]) & (cy <= HERO[3])
    cell_keys = zone_keys(cx, cy)

    wet_building: dict[str, dict[str, np.ndarray]] = {}
    cell_share: dict[str, np.ndarray] = {}
    cell_centre_wet: dict[str, np.ndarray] = {}
    for rp in (10, 100, 500):
        efas = read_grid(EFAS_PATH.format(rp), bbox)
        wet = wet_mask(efas)
        variants = {"base": wet, "edge_in": shift_any(wet, combine_all=True), "edge_out": shift_any(wet, combine_all=False)}
        b_rows, b_cols = cell_index(efas, lon, lat)
        wet_building[f"rp{rp}"] = {name: mask[b_rows, b_cols] for name, mask in variants.items()}
        ex, ey = cell_centres(efas)
        e_rows, e_cols = cell_index(pop, ex.ravel(), ey.ravel())
        e_cells = e_rows * pop.values.shape[1] + e_cols
        wet_count = np.bincount(e_cells, weights=wet.ravel().astype(float), minlength=population.size)
        all_count = np.bincount(e_cells, minlength=population.size)
        cell_share[f"rp{rp}"] = np.divide(wet_count, all_count, out=np.zeros(population.size), where=all_count > 0)
        c_rows, c_cols = cell_index(efas, cx, cy)
        cell_centre_wet[f"rp{rp}"] = wet[c_rows, c_cols]
        lap(f"RP{rp}: EFAS window {wet.shape}, {wet.sum():,} wet cells")

    if flood_path is not None:
        flood = gpd.read_file(flood_path).to_crs(3035)
        flood_geom = shapely.make_valid(shapely.union_all(flood.geometry.to_numpy()))
        bx, by = TO_LAEA.transform(lon, lat)
        bx, by = np.asarray(bx), np.asarray(by)
        geoms = {"base": flood_geom, "edge_in": flood_geom.buffer(-OBS_EDGE_M), "edge_out": flood_geom.buffer(OBS_EDGE_M)}
        for geom in geoms.values():
            shapely.prepare(geom)
        wet_building["obs2021"] = {name: shapely.contains_xy(geom, bx, by) for name, geom in geoms.items()}
        height, width = pop.values.shape
        boxes_lonlat = [shapely.box(*(pop.transform * (c, r + 1)), *(pop.transform * (c + 1, r))) for r in range(height) for c in range(width)]
        boxes = gpd.GeoSeries(boxes_lonlat, crs=4326).to_crs(3035).to_numpy()
        hit = shapely.intersects(boxes, flood_geom) & cell_in_area
        part = np.zeros(population.size)
        part[hit] = shapely.area(shapely.intersection(boxes[hit], flood_geom)) / shapely.area(boxes[hit])
        cell_share["obs2021"] = part
        ccx, ccy = TO_LAEA.transform(cx, cy)
        cell_centre_wet["obs2021"] = shapely.contains_xy(flood_geom, np.asarray(ccx), np.asarray(ccy))
        lap("observed 2021 flood ready")

    zones: list[dict[str, Json]] = bundle["zones"]
    zone_of_bundle: dict[int, int] = {}
    for zone in zones:
        corners = np.array(zone["cell"], dtype=float)
        key = zone_keys(np.array([corners[:, 1].mean()]), np.array([corners[:, 0].mean()]))[0]
        zone_of_bundle[int(key)] = int(zone["id"])
    capacity = {int(s["id"]): {k: float(v) for k, v in s["cap"].items()} for s in bundle["shelters"]}
    total_places: dict[str, float] = bundle["meta"]["total_places"]

    levels_out: dict[str, Json] = {}
    plans_out: dict[str, Json] = {}
    checks: dict[str, Json] = {}
    for level in LEVELS:
        if level not in wet_building:
            continue
        wet = wet_building[level]
        variant_zone: dict[str, dict[int, float]] = {}
        for rule in BUILDING_RULES:
            mask = wet["base"] & in_area
            variant_zone[rule] = by_zone(keys[mask], people[rule][mask])
        for edge in ("edge_in", "edge_out"):
            mask = wet[edge] & in_area
            variant_zone[edge] = by_zone(keys[mask], people["footprint"][mask])
        variant_zone["cell_area"] = by_zone(cell_keys[cell_in_area], (population * cell_share[level])[cell_in_area])
        centre = cell_centre_wet[level] & cell_in_area
        variant_zone["cell_centre"] = by_zone(cell_keys[centre], population[centre])
        totals = {name: sum(z.values()) for name, z in variant_zone.items()}
        low_rule, high_rule = min(totals, key=totals.__getitem__), max(totals, key=totals.__getitem__)
        bundle_total = sum(float(z["people"][level]) for z in zones)
        diff = (totals["footprint"] - bundle_total) / bundle_total if bundle_total > 0 else 0.0
        checks[f"{level}_base_matches_bundle"] = {"pass": abs(diff) <= CHECK_TOLERANCE, "ours": round(totals["footprint"]), "bundle": round(bundle_total),
                                                  "relative_difference": round(diff, 4)}
        levels_out[level] = {
            "base": round(bundle_total),
            "low": math.floor(min(totals[low_rule], bundle_total) / 100) * 100,
            "high": math.ceil(max(totals[high_rule], bundle_total) / 100) * 100,
            "low_rule": low_rule,
            "high_rule": high_rule,
            "spreading": [round(min(totals[r] for r in (*BUILDING_RULES, "cell_area", "cell_centre"))), round(max(totals[r] for r in (*BUILDING_RULES, "cell_area", "cell_centre")))],
            "edge": [round(min(totals["edge_in"], totals["footprint"])), round(max(totals["edge_out"], totals["footprint"]))],
            "variants": {name: round(v) for name, v in totals.items()},
        }
        lap(f"{level}: {levels_out[level]}")
        base_zone = variant_zone["footprint"]
        for key, result in bundle["results"].items():
            if not key.startswith(level + "|"):
                continue
            set_id = key.split("|")[2]
            cap = {s: c[set_id] for s, c in capacity.items()}
            plans_out[key] = {end: scaled_plan(result, zone_of_bundle, base_zone, variant_zone[rule], cap, float(total_places[set_id]))
                              for end, rule in (("base", "footprint"), ("low", low_rule), ("high", high_rule))}
            plans_out[key]["base"]["unplaced_in_tool"] = round(float(result["summary"]["unassigned"]))

    bundle["people_ranges"] = {
        "label": "range across methods",
        "not_a": "confidence interval: GHS-POP publishes no error per cell, so there is no statistical interval",
        "rules": RULE_LABELS,
        "rounding": "low and high rounded to 100; base = the tool's count",
        "edge_shift": "EFAS: wet mask grown or shrunk by one 3 arc-second cell (about 60 x 90 m) across its sides, not diagonals; observed 2021: mapped flood buffered by +/- 60 m",
        "direction": "Probably more people near the river: houses destroyed in 2021 are missing from the 2024 building data (GHS-OBAT), so their residents are counted in surviving buildings further away.",
        "plan_method": "the tool's plan with each zone's residents scaled to the low or high count, not re-routed: people beyond a building's capacity are counted as without a place, as if no other building took them; most buildings in the plan are already full, so at the high end this is a worst case, and whether everyone gets a place within 1 h needs the route optimisation re-run",
        "levels": levels_out,
        "plans": plans_out,
        "checks": checks,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "script": "pipeline/research/21_tool_people_ranges.py",
    }
    BUNDLE.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    lap(f"checks: {json.dumps(checks)}")
    lap(f"plans: {json.dumps({k: v for k, v in plans_out.items() if k.endswith('restrictive')})}")
    if not all(bool(c["pass"]) for c in checks.values()):
        raise SystemExit("base check failed: our footprint count differs from the bundle by more than 3%")


if __name__ == "__main__":
    main()
