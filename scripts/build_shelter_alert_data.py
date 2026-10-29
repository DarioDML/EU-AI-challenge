"""Build the shelter-alert policy-tool data for EMS areas: residents inside the mapped 2021 flood, candidate shelters and their capacity."""

from __future__ import annotations

import argparse
import http.client
import json
import math
import os
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import TypeAlias

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import rasterio
import shapely
from affine import Affine
from rasterio.windows import Window
from shapely.geometry import LineString, MultiPoint, Point, Polygon, mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union

os.environ.setdefault("GS_NO_SIGN_REQUEST", "YES")

REPO = Path(__file__).resolve().parents[1]
BUCKET = "/vsigs/datasets_challenge/working_data"
ISO3 = {"be": "BEL", "de": "DEU", "nl": "NLD"}
COUNTRY_EXTENT = {"be": (2.5, 49.4, 6.45, 51.55), "de": (5.8, 47.2, 15.1, 55.1), "nl": (3.3, 50.7, 7.3, 53.6)}
REGION_AOIS = ("be_01", "nl_01", "de_08", "de_09", "de_10", "de_18")
COMPARISON_AOIS = ("de_15",)
SITE_SEARCH_M = 1000.0
POP_PATH = f"{BUCKET}/ghs_pop/GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0/GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0.tif"
EFAS_PATH = BUCKET + "/cems-efas/Europe_RP{}_filled_depth.tif"
OVERPASS_URLS = os.environ.get(
    "OVERPASS_URL", "https://z.overpass-api.de/api/interpreter,https://maps.mail.ru/osm/tools/overpass/api/interpreter"
).split(",")
OVERPASS_TILE_DEG = 0.2
OVERPASS_PAUSE_S = 2.0
OVERPASS_ATTEMPTS = 4
OVERPASS_RETRY_S = 20.0
LAEA = 3035
STOREY_M = 3.0
NODE_MATCH_M = 30.0
MIN_SHELTER_FLOOR_M2 = 100.0
EARTH_RADIUS_M = 6_371_000.0

Json: TypeAlias = dict[str, "Json"] | list["Json"] | str | int | float | bool | None

CARE = {"hospital", "clinic", "nursing_home", "kindergarten"}
CARE_FACILITY = {"nursing_home", "group_home", "assisted_living"}
SCHOOL = {"school", "college", "university"}
SPORTS = {"sports_hall", "sports_centre", "gymnasium"}
COMMUNITY = {"community_centre", "townhall", "social_centre", "events_venue", "civic"}


@dataclass(frozen=True)
class Scenario:
    m2_per_person: float = 3.5
    usable_share: float = 0.5
    max_distance_m: float = 5000.0
    walk_distance_m: float = 2000.0
    flood_buffer_m: float = 50.0
    exclude_rp500: bool = True
    kinds: tuple[str, ...] = ("school", "sports", "community")


@dataclass(frozen=True)
class Area:
    aoi_id: str
    country: str
    locality: str
    event: BaseGeometry
    aoi: BaseGeometry


def load_area(aoi_id: str) -> Area:
    frame = gpd.read_parquet(REPO / "data" / "reference" / "aoi_event_unions.parquet")
    rows = frame[frame["aoi_id"] == aoi_id].to_crs(LAEA)
    if rows.empty:
        raise SystemExit(f"Unknown AOI {aoi_id!r}")
    kinds = dict(zip(rows["kind"], rows.geometry))
    first = rows.iloc[0]
    return Area(aoi_id, str(first["country"]), str(first["locality"]), kinds["event"], kinds["aoi"])


def to_wgs84(geometry: BaseGeometry) -> BaseGeometry:
    return gpd.GeoSeries([geometry], crs=LAEA).to_crs(4326).iloc[0]


def overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def read_obat(bbox: tuple[float, float, float, float], cache: Path) -> gpd.GeoDataFrame:
    if cache.exists():
        return gpd.read_parquet(cache)
    frames: list[gpd.GeoDataFrame] = []
    for country, iso in ISO3.items():
        if not overlaps(bbox, COUNTRY_EXTENT[country]):
            continue
        name = f"GHS_OBAT_GPKG_{iso}_E2020_R2024A_V1_0"
        frame = pyogrio.read_dataframe(f"{BUCKET}/obat_{country}/{name}/{name}.gpkg", bbox=bbox, columns=["use", "height", "area"])
        frame["country"] = country
        frames.append(frame)
    combined = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=frames[0].crs)
    cache.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(cache)
    return combined


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
        window = Window(
            math.floor(col0), math.floor(row0), math.ceil(col1) - math.floor(col0), math.ceil(row1) - math.floor(row0)
        )
        values = source.read(1, window=window)
        return Grid(values, source.window_transform(window), source.nodata)


def cell_index(grid: Grid, lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    inverse = ~grid.transform
    cols, rows = inverse * (lon, lat)
    height, width = grid.values.shape
    return np.clip(np.floor(rows).astype(int), 0, height - 1), np.clip(np.floor(cols).astype(int), 0, width - 1)


def sample_depth(grid: Grid, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    rows, cols = cell_index(grid, lon, lat)
    inside = (rows >= 0) & (rows < grid.values.shape[0]) & (cols >= 0) & (cols < grid.values.shape[1])
    depth = np.full(lon.shape, np.nan)
    depth[inside] = grid.values[rows[inside], cols[inside]]
    if grid.nodata is not None:
        depth[depth == grid.nodata] = np.nan
    depth[depth <= 0] = np.nan
    return depth


def allocate_residents(grid: Grid, lon: np.ndarray, lat: np.ndarray, weight: np.ndarray) -> tuple[np.ndarray, float]:
    rows, cols = cell_index(grid, lon, lat)
    height, width = grid.values.shape
    cells = rows * width + cols
    weight = np.nan_to_num(weight)
    weight_sum = np.bincount(cells, weights=weight, minlength=height * width)
    population = np.nan_to_num(grid.values.astype(float)).ravel()
    shared = weight_sum[cells] > 0
    residents = np.zeros(weight.shape)
    residents[shared] = population[cells[shared]] * weight[shared] / weight_sum[cells[shared]]
    unallocated = float(population[(weight_sum <= 0) & (population > 0)].sum())
    return residents, unallocated


def overpass_tile(tile: tuple[float, float, float, float]) -> list[dict[str, Json]]:
    west, south, east, north = tile
    box = f"{south:.5f},{west:.5f},{north:.5f},{east:.5f}"
    query = f"""[out:json][timeout:120];
(
  nwr["amenity"~"^(school|college|university|community_centre|townhall|social_centre|events_venue|kindergarten|hospital|clinic|nursing_home|social_facility)$"]({box});
  nwr["leisure"~"^(sports_hall|sports_centre)$"]({box});
  nwr["building"~"^(school|sports_hall|gymnasium|civic|hospital|kindergarten)$"]({box});
  node["place"~"^(town|village|hamlet|suburb)$"]({box});
);
out geom;"""
    for attempt in range(OVERPASS_ATTEMPTS):
        elements = overpass_attempt(query)
        if elements is not None:
            return elements
        print(f"Overpass tile {box} failed (attempt {attempt + 1}); waiting {OVERPASS_RETRY_S:.0f} s")
        time.sleep(OVERPASS_RETRY_S)
    raise SystemExit("All Overpass endpoints failed; set OVERPASS_URL to a working mirror")


def overpass_attempt(query: str) -> list[dict[str, Json]] | None:
    for endpoint in OVERPASS_URLS:
        request = urllib.request.Request(
            endpoint,
            data=urllib.parse.urlencode({"data": query}).encode(),
            headers={"User-Agent": "EU-AI-challenge-hackathon/1.0 (shelter-alert demo)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                answer: Json = json.loads(response.read())
        except (OSError, http.client.HTTPException, ValueError) as error:
            print(f"Overpass {endpoint} failed: {error}")
            continue
        remark = str(answer.get("remark", "")) if isinstance(answer, dict) else ""
        elements = answer.get("elements") if isinstance(answer, dict) else None
        if isinstance(elements, list) and "error" not in remark.lower():
            return [item for item in elements if isinstance(item, dict)]
        print(f"Overpass {endpoint} gave an incomplete answer: {remark or 'no elements'}")
    return None


def fetch_overpass(bbox: tuple[float, float, float, float], cache: Path) -> list[dict[str, Json]]:
    if not cache.exists():
        west, south, east, north = bbox
        cols = max(1, math.ceil((east - west) / OVERPASS_TILE_DEG))
        rows = max(1, math.ceil((north - south) / OVERPASS_TILE_DEG))
        width, height = (east - west) / cols, (north - south) / rows
        merged: list[dict[str, Json]] = []
        seen: set[tuple[str, str]] = set()
        for col in range(cols):
            for row in range(rows):
                tile = (west + col * width, south + row * height, west + (col + 1) * width, south + (row + 1) * height)
                tile_cache = cache.with_name(f"{cache.stem}_tile{col}_{row}.json")
                if not tile_cache.exists():
                    tile_cache.parent.mkdir(parents=True, exist_ok=True)
                    tile_cache.write_text(json.dumps({"elements": overpass_tile(tile)}, ensure_ascii=False), encoding="utf-8")
                    time.sleep(OVERPASS_PAUSE_S)
                stored: Json = json.loads(tile_cache.read_text(encoding="utf-8"))
                tile_elements = stored.get("elements") if isinstance(stored, dict) else None
                if not isinstance(tile_elements, list):
                    raise SystemExit(f"Unexpected Overpass tile in {tile_cache}")
                for element in (item for item in tile_elements if isinstance(item, dict)):
                    key = (str(element.get("type")), str(element.get("id")))
                    if key not in seen:
                        seen.add(key)
                        merged.append(element)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"elements": merged}, ensure_ascii=False), encoding="utf-8")
    document: Json = json.loads(cache.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("elements"), list):
        raise SystemExit(f"Unexpected Overpass response in {cache}")
    return [item for item in document["elements"] if isinstance(item, dict)]


def tags_of(element: dict[str, Json]) -> dict[str, str]:
    tags = element.get("tags")
    if not isinstance(tags, dict):
        return {}
    return {str(key): value for key, value in tags.items() if isinstance(value, str)}


def coordinates(points: Json) -> list[tuple[float, float]]:
    if not isinstance(points, list):
        return []
    result: list[tuple[float, float]] = []
    for point in points:
        if isinstance(point, dict):
            lon, lat = point.get("lon"), point.get("lat")
            if isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
                result.append((float(lon), float(lat)))
    return result


def ring_geometry(ring: list[tuple[float, float]]) -> BaseGeometry | None:
    if len(ring) >= 4 and ring[0] == ring[-1]:
        polygon = Polygon(ring)
        return polygon if polygon.is_valid else polygon.buffer(0)
    if len(ring) >= 3:
        return MultiPoint(ring).convex_hull
    return None


def element_geometry(element: dict[str, Json]) -> BaseGeometry | None:
    kind = element.get("type")
    if kind == "node":
        found = coordinates([element])
        return Point(found[0]) if found else None
    if kind == "way":
        return ring_geometry(coordinates(element.get("geometry")))
    members = element.get("members")
    if not isinstance(members, list):
        return None
    lines = [
        coordinates(member.get("geometry"))
        for member in members
        if isinstance(member, dict) and member.get("role") in ("outer", "")
    ]
    lines = [line for line in lines if len(line) >= 2]
    if not lines:
        return None
    polygons = list(polygonize(unary_union([LineString(line) for line in lines])))
    if polygons:
        return unary_union(polygons)
    return MultiPoint([point for line in lines for point in line]).convex_hull


def classify(tags: dict[str, str]) -> str | None:
    values = {tags.get("amenity", ""), tags.get("leisure", ""), tags.get("building", "")}
    if values & CARE or tags.get("social_facility", "") in CARE_FACILITY:
        return "care"
    if values & SCHOOL:
        return "school"
    if values & SPORTS:
        return "sports"
    if values & COMMUNITY:
        return "community"
    if "place" in tags:
        return "place"
    return None


def street_of(tags: dict[str, str]) -> str:
    return " ".join(part for part in (tags.get("addr:street", ""), tags.get("addr:housenumber", "")) if part)


def osm_features(elements: list[dict[str, Json]]) -> gpd.GeoDataFrame:
    records: list[dict[str, str | int | BaseGeometry]] = []
    for element in elements:
        tags = tags_of(element)
        kind = classify(tags)
        geometry = element_geometry(element)
        if kind is None or geometry is None or geometry.is_empty:
            continue
        records.append(
            {
                "osm": f"{element.get('type')}/{element.get('id')}",
                "kind": kind,
                "name": tags.get("name", ""),
                "street": street_of(tags),
                "place_type": tags.get("place", ""),
                "geometry": geometry,
            }
        )
    return gpd.GeoDataFrame(records, geometry="geometry", crs=4326).to_crs(LAEA)


def attach_buildings(features: gpd.GeoDataFrame, buildings: gpd.GeoDataFrame) -> pd.DataFrame:
    polygons = features[features.geom_type != "Point"].copy()
    polygons["feature_area"] = polygons.area
    polygons = polygons.sort_values("feature_area", ascending=False)
    hits = gpd.sjoin(buildings[["geometry"]], polygons[["geometry", "feature_area"]], predicate="within")
    hits = hits.sort_values("feature_area", ascending=False)
    owner = hits[~hits.index.duplicated(keep="first")]["index_right"]
    points = features[features.geom_type == "Point"]
    points = points[~points.within(unary_union(polygons.geometry.to_list()).buffer(NODE_MATCH_M))]
    free = buildings.drop(index=owner.index)
    if not points.empty and not free.empty:
        nearest = gpd.sjoin_nearest(points[["geometry"]], free[["geometry"]], max_distance=NODE_MATCH_M)
        nearest = nearest[~nearest["index_right"].duplicated(keep="first")]
        owner = pd.concat([owner, pd.Series(nearest.index, index=nearest["index_right"].to_numpy())])
    return pd.DataFrame({"feature": owner.to_numpy()}, index=owner.index)


def distinct_sites(sites: gpd.GeoDataFrame, event: BaseGeometry) -> list[dict[str, str | float | bool]]:
    near = event.buffer(SITE_SEARCH_M)
    candidates = sites[sites["kind"].isin(["care", "school"]) & sites.intersects(near)].copy()
    candidates["size"] = candidates.area
    kept: dict[str, list[BaseGeometry]] = {"care": [], "school": []}
    result: list[dict[str, str | float | bool]] = []
    for _, site in candidates.sort_values("size", ascending=False, kind="stable").iterrows():
        spot = site.geometry.representative_point()
        same_kind = kept[str(site["kind"])]
        if any(other.distance(spot) <= NODE_MATCH_M for other in same_kind):
            continue
        same_kind.append(site.geometry)
        location = to_wgs84(spot)
        result.append(
            {
                "name": site["name"] or f"Unnamed {site['kind']}",
                "kind": site["kind"],
                "lon": round(location.x, 5),
                "lat": round(location.y, 5),
                "in_flood": bool(site.geometry.intersects(event)),
            }
        )
    return result


def project_xy(lon: np.ndarray, lat: np.ndarray, lat0: float) -> tuple[np.ndarray, np.ndarray]:
    scale = math.pi / 180.0 * EARTH_RADIUS_M
    return lon * scale * math.cos(lat0 * math.pi / 180.0), lat * scale


def assign(
    home_x: np.ndarray, home_y: np.ndarray, residents: np.ndarray,
    shelter_x: np.ndarray, shelter_y: np.ndarray, capacity: np.ndarray, max_distance: float,
) -> tuple[np.ndarray, np.ndarray]:
    distance = np.hypot(home_x[:, None] - shelter_x[None, :], home_y[:, None] - shelter_y[None, :])
    home_idx, shelter_idx = np.nonzero(distance <= max_distance)
    pair_distance = distance[home_idx, shelter_idx]
    order = np.lexsort((shelter_idx, home_idx, pair_distance))
    remaining = capacity.astype(float).copy()
    chosen = np.full(home_x.shape, -1)
    chosen_distance = np.full(home_x.shape, np.nan)
    for pair in order:
        home, shelter = home_idx[pair], shelter_idx[pair]
        if chosen[home] >= 0 or remaining[shelter] < residents[home]:
            continue
        chosen[home] = shelter
        chosen_distance[home] = pair_distance[pair]
        remaining[shelter] -= residents[home]
    return chosen, chosen_distance


def simplified_geojson(geometry: BaseGeometry, tolerance_m: float) -> Json:
    shape = to_wgs84(geometry.simplify(tolerance_m))
    return json.loads(json.dumps(mapping(shape), default=float), parse_float=lambda value: round(float(value), 5))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aoi", nargs="+", default=[*REGION_AOIS, *COMPARISON_AOIS], help="EMS areas; default: Anna's region plus the Ahr comparison")
    parser.add_argument("--buffer-deg", type=float, default=0.04, help="Search margin around the AOI for shelters")
    parser.add_argument("--johan-place", default=None, help="Village for the illustrative Johan home; default: most homes")
    args = parser.parse_args()
    failed: list[str] = []
    for aoi_id in args.aoi:
        try:
            build(aoi_id, args.buffer_deg, args.johan_place)
        except SystemExit as error:
            print(f"{aoi_id} failed: {error}")
            failed.append(aoi_id)
    if failed:
        raise SystemExit(f"Failed areas: {', '.join(failed)}")


def build(aoi_id: str, margin: float, johan_place_name: str | None) -> None:
    area = load_area(aoi_id)
    aoi_wgs = to_wgs84(area.aoi)
    west, south, east, north = aoi_wgs.bounds
    bbox = (west - margin * 1.5, south - margin, east + margin * 1.5, north + margin)

    buildings = read_obat(bbox, REPO / "data" / "processed" / f"obat_{aoi_id}_{margin:g}.parquet")
    buildings = buildings.to_crs(4326).reset_index(drop=True)
    lon = buildings.geometry.x.to_numpy()
    lat = buildings.geometry.y.to_numpy()
    floors = np.maximum(1.0, np.nan_to_num(buildings["height"].to_numpy(dtype=float), nan=STOREY_M) / STOREY_M)
    floor_area = buildings["area"].to_numpy(dtype=float) * floors
    residential = buildings["use"].to_numpy() == 1

    population = read_grid(POP_PATH, bbox)
    residents = np.zeros(len(buildings))
    residents[residential], unallocated = allocate_residents(
        population, lon[residential], lat[residential], floor_area[residential]
    )
    rp500 = read_grid(EFAS_PATH.format(500), bbox)
    rp100 = read_grid(EFAS_PATH.format(100), bbox)
    depth500 = sample_depth(rp500, lon, lat)
    depth100 = sample_depth(rp100, lon, lat)

    buildings_laea = buildings.to_crs(LAEA)
    shapely.prepare(area.event)
    in_event = buildings_laea.within(area.event).to_numpy()
    homes = np.flatnonzero(in_event & residential)
    if homes.size == 0:
        raise SystemExit(f"{aoi_id}: no residential buildings inside the mapped flood")

    overpass_cache = REPO / "data" / "raw" / "osm" / f"overpass_{aoi_id}_{margin:g}.json"
    features = osm_features(fetch_overpass(bbox, overpass_cache))
    places = features[(features["kind"] == "place") & (features["name"] != "")].to_crs(4326)
    if places.empty:
        raise SystemExit(f"{aoi_id}: no named OSM places in the search area")
    sites = features[features["kind"] != "place"]
    owner = attach_buildings(sites, buildings_laea)

    lat0 = round(float(np.mean(lat[homes])), 4) if homes.size else float(lat.mean())
    home_lon, home_lat = np.round(lon[homes], 5), np.round(lat[homes], 5)
    home_res = np.round(residents[homes], 2)
    place_lon, place_lat = places.geometry.x.to_numpy(), places.geometry.y.to_numpy()
    hx, hy = project_xy(home_lon, home_lat, lat0)
    px, py = project_xy(place_lon, place_lat, lat0)
    home_place = np.argmin(np.hypot(hx[:, None] - px[None, :], hy[:, None] - py[None, :]), axis=1)

    shelters: list[dict[str, str | float | int | None]] = []
    critical = distinct_sites(sites, area.event)
    for feature_id, site in sites.iterrows():
        members = owner.index[owner["feature"] == feature_id].to_numpy()
        if site["kind"] == "care" or members.size == 0:
            continue
        total_floor = float(floor_area[members].sum())
        if total_floor < MIN_SHELTER_FLOOR_M2:
            continue
        main = members[np.argmax(buildings["area"].to_numpy()[members])]
        member_points = buildings_laea.geometry.iloc[members]
        deepest500 = np.nanmax(depth500[members]) if np.isfinite(depth500[members]).any() else None
        deepest100 = np.nanmax(depth100[members]) if np.isfinite(depth100[members]).any() else None
        shelters.append(
            {
                "osm": site["osm"],
                "country": str(buildings["country"].iloc[main]),
                "name": site["name"],
                "kind": site["kind"],
                "street": site["street"],
                "lon": round(float(lon[main]), 5),
                "lat": round(float(lat[main]), 5),
                "buildings": int(members.size),
                "footprint_m2": round(float(buildings["area"].to_numpy()[members].sum())),
                "floor_area_m2": round(total_floor),
                "flood_dist_m": round(float(member_points.distance(area.event).min())),
                "rp100_m": None if deepest100 is None else round(float(deepest100), 2),
                "rp500_m": None if deepest500 is None else round(float(deepest500), 2),
            }
        )

    for shelter in shelters:
        if not shelter["name"]:
            sx, sy = project_xy(np.array([shelter["lon"]]), np.array([shelter["lat"]]), lat0)
            nearest = int(np.argmin(np.hypot(px - sx[0], py - sy[0])))
            label = {"school": "School", "sports": "Sports hall", "community": "Community building"}[str(shelter["kind"])]
            shelter["name"] = f"{label}, {places['name'].iloc[nearest]}"

    scenario = Scenario()
    eligible = [
        index for index, shelter in enumerate(shelters)
        if shelter["kind"] in scenario.kinds
        and float(shelter["flood_dist_m"] or 0) > scenario.flood_buffer_m
        and not (scenario.exclude_rp500 and shelter["rp500_m"] is not None)
    ]
    capacity = np.array(
        [math.floor(float(shelters[i]["floor_area_m2"] or 0) * scenario.usable_share / scenario.m2_per_person) for i in eligible],
        dtype=int,
    )
    sx, sy = project_xy(np.array([shelters[i]["lon"] for i in eligible]), np.array([shelters[i]["lat"] for i in eligible]), lat0)
    chosen, distance = assign(hx, hy, home_res, sx, sy, capacity, scenario.max_distance_m)
    placed = chosen >= 0
    walk = placed & (distance <= scenario.walk_distance_m)

    johan_matches = places.index[places["name"] == johan_place_name]
    johan_place = int(places.index.get_loc(johan_matches[0])) if len(johan_matches) else int(np.bincount(home_place).argmax())
    candidates = np.flatnonzero(home_place == johan_place)
    if candidates.size == 0:
        candidates = np.arange(homes.size)
    johan = int(candidates[np.argmin(np.hypot(hx[candidates] - px[johan_place], hy[candidates] - py[johan_place]))])

    reference = pd.read_csv(REPO / "data" / "reference" / "aoi_metrics.csv").set_index("aoi_id").loc[area.aoi_id]
    checks = {
        "homes_in_flood_vs_reference_residential_event": int(homes.size) == int(reference["residential_event"]),
        "homes_rp500_vs_reference_rp500_positive_residential": int(np.isfinite(depth500[homes]).sum())
        == int(reference["rp500_positive_residential"]),
        "homes_rp100_vs_reference_rp100_positive_residential": int(np.isfinite(depth100[homes]).sum())
        == int(reference["rp100_positive_residential"]),
    }
    if not all(checks.values()):
        raise SystemExit(f"Reference check failed: {checks}")

    summary: dict[str, Json] = {
        "aoi_id": area.aoi_id,
        "locality": area.locality,
        "generated": date.today().isoformat(),
        "scenario": asdict(scenario),
        "homes_in_flood": int(homes.size),
        "homes_in_flood_height_missing": int(buildings["height"].isna().to_numpy()[homes].sum()),
        "homes_in_flood_by_country": {str(k): int(v) for k, v in buildings["country"].iloc[homes].value_counts().items()},
        "residents_in_flood_building_weighted": round(float(home_res.sum()), 1),
        "residents_in_flood_area_weighted_reference": round(float(reference["pop2020_fractional"]), 1),
        "residents_unallocated_in_bbox_cells_without_homes": round(unallocated, 1),
        "homes_in_flood_with_rp500_depth": int(np.isfinite(depth500[homes]).sum()),
        "homes_in_flood_with_rp100_depth": int(np.isfinite(depth100[homes]).sum()),
        "shelters_found": len(shelters),
        "shelters_eligible": len(eligible),
        "shelters_eligible_by_country": {
            str(k): int(v) for k, v in pd.Series([shelters[i]["country"] for i in eligible]).value_counts().items()
        },
        "shelter_capacity": int(capacity.sum()),
        "residents_placed": round(float(home_res[placed].sum()), 1),
        "residents_placed_within_walk": round(float(home_res[walk].sum()), 1),
        "residents_unplaced": round(float(home_res[~placed].sum()), 1),
        "median_distance_m": round(float(np.nanmedian(distance))) if placed.any() else None,
        "vulnerable_sites_in_flood": sum(1 for site in critical if site["in_flood"]),
        "osm_retrieved": date.fromtimestamp(overpass_cache.stat().st_mtime).isoformat(),
        "checks": checks,
    }

    data: dict[str, Json] = {
        "meta": {
            "aoi_id": area.aoi_id,
            "locality": area.locality,
            "country": area.country,
            "generated": date.today().isoformat(),
            "lat0": lat0,
            "johan_home": johan,
            "storey_m": STOREY_M,
            "default_scenario": asdict(scenario),
            "summary": summary,
        },
        "flood": simplified_geojson(area.event, 8.0),
        "aoi": simplified_geojson(area.aoi, 25.0),
        "places": [
            {"name": str(name), "lon": round(float(x), 5), "lat": round(float(y), 5)}
            for name, x, y in zip(places["name"], place_lon, place_lat)
        ],
        "homes": {
            "lon": home_lon.tolist(),
            "lat": home_lat.tolist(),
            "res": home_res.tolist(),
            "place": home_place.tolist(),
            "rp500": np.isfinite(depth500[homes]).astype(int).tolist(),
            "country": buildings["country"].iloc[homes].tolist(),
        },
        "shelters": shelters,
        "critical": critical,
    }

    tool = REPO / "policy-tool" / "data"
    tool.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (tool / f"{aoi_id}.js").write_text(
        f"(window.SHELTER_AREAS = window.SHELTER_AREAS || {{}})[{json.dumps(aoi_id)}] = {payload};\n", encoding="utf-8"
    )
    analysis = REPO / "data-analysis"
    pd.DataFrame(shelters).to_csv(analysis / f"shelter_alert_{aoi_id}_shelters.csv", index=False, encoding="utf-8")
    (analysis / f"shelter_alert_{aoi_id}_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
