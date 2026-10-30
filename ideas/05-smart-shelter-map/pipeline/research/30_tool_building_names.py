"""Question:    Policy tool, backlog B24. What is the OSM name and street address of each shelter candidate, so the page can tell two buildings of the same type in one town apart?
Data:         The SAME Geofabrik extracts that 15_q3_shelter_candidates.py read (rheinland-pfalz and nordrhein-westfalen, OSM state 29 Oct 2026, (c) OpenStreetMap contributors, ODbL),
              from the runtime cache /content/cache/osm; the MD5 of each cached file must equal the one recorded by run 20261029-134745-b0be, else the script stops (no download).
Assumptions:  Same candidate rule as 15_q3_shelter_candidates.py (same tag filter, building polygon required, same type rule, first key wins), restricted to the shelter tiers
              (core + extended; critical facilities are not shelters) and to a box around Kreis Euskirchen and Landkreis Ahrweiler plus the 12 km shelter margin of 20_tool_pipeline.py.
              Only three public OSM tags are kept: name, addr:street, addr:housenumber. Missing tags stay empty; nothing is guessed here (20_tool_pipeline.py adds a road fallback).
Tools:        pyogrio 0.13 (OSM driver, Arrow stream), hashlib.
Outputs:      $YUNAI_RUN_DIR/ building_names.csv, building_names_meta.json
Finding:      research/r01/NOTE.md
"""
import hashlib
import json
import os
import re
import time
import warnings

warnings.filterwarnings("ignore")
import pandas as pd
import pyarrow as pa
import pyogrio.raw
import shapely

T0 = time.time()
OUT = os.environ["YUNAI_RUN_DIR"]
CHECKS, FAILED = {}, []
CACHE = "/content/cache/osm"
MD5 = {"rheinland-pfalz-latest.osm.pbf": "183edf52d3d25774d8f7c5f15d825241", "nordrhein-westfalen-latest.osm.pbf": "513e094adb91b97f3e90dfdc50674482"}      # run 20261029-134745-b0be, cards
# tag rule copied from 15_q3_shelter_candidates.py so the keys match q3_candidates.csv exactly
CORE = {"school", "college", "university", "sports_hall", "community_centre", "townhall", "civic", "public"}
EXT = {"kindergarten", "church", "chapel", "cathedral", "hotel", "hostel"}
BLD = CORE | EXT | {"hospital", "fire_station", "police"}
AMEN = {"school": "school", "college": "college", "university": "university", "kindergarten": "kindergarten", "community_centre": "community_centre", "townhall": "townhall",
        "hospital": "hospital", "clinic": "clinic", "nursing_home": "nursing_home", "fire_station": "fire_station", "police": "police"}
WHERE = "building IN (" + ",".join(f"'{b}'" for b in BLD) + ") OR amenity IN (" + ",".join(f"'{a}'" for a in AMEN) + ") OR leisure IN ('sports_centre','sports_hall')"
BBOX = (5.95, 50.05, 7.80, 51.00)        # hero area (6.30-7.45 E, 50.30-50.78 N) plus more than the 12 km shelter margin; the pipeline's own region test decides the rest
RE_TAG = re.compile(r'"((?:[^"\\]|\\.)*)"=>"((?:[^"\\]|\\.)*)"')      # GDAL hstore: "key"=>"value", quotes inside escaped


def lap(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def check(name, ok, detail):
    CHECKS[name] = {"pass": bool(ok), **detail}
    if not ok:
        FAILED.append(name)
    lap(f"check {name}: {'PASS' if ok else 'FAIL'} {json.dumps(detail, default=str)[:350]}")


def clean(v):
    return re.sub(r"\s+", " ", v.replace('\\"', '"').replace("\\\\", "\\")).strip() if v else ""


rows, seen = [], set()
for fname, want in MD5.items():
    path = os.path.join(CACHE, fname)
    md5 = hashlib.md5()
    with open(path, "rb") as fh:
        for ch in iter(lambda: fh.read(1 << 24), b""):
            md5.update(ch)
    ok = md5.hexdigest() == want
    check(f"same_extract_as_candidates_{fname.split('-latest')[0]}", ok, {"md5": md5.hexdigest(), "expected": want, "bytes": os.path.getsize(path)})
    if not ok:
        continue                                                # a newer extract could carry other names; never mix states
    n_read = 0
    with pyogrio.raw.open_arrow(path, layer="multipolygons", where=WHERE, columns=["osm_id", "osm_way_id", "name", "building", "amenity", "leisure", "other_tags"], bbox=BBOX, batch_size=50000, use_pyarrow=True) as source:
        meta, reader = source
        gname = meta.get("geometry_name") or "wkb_geometry"
        for batch in reader:
            tbl = pa.Table.from_batches([batch]) if isinstance(batch, pa.RecordBatch) else batch
            geoms = shapely.from_wkb(tbl.column(gname).to_numpy(zero_copy_only=False))
            bld, amen, leis = tbl.column("building").to_pylist(), tbl.column("amenity").to_pylist(), tbl.column("leisure").to_pylist()
            oid, wid, tags, nm = tbl.column("osm_id").to_pylist(), tbl.column("osm_way_id").to_pylist(), tbl.column("other_tags").to_pylist(), tbl.column("name").to_pylist()
            for k in range(len(geoms)):
                if geoms[k] is None or bld[k] is None:
                    continue
                typ = bld[k] if bld[k] in BLD else (AMEN.get(amen[k]) or ("sports_hall" if leis[k] in ("sports_centre", "sports_hall") else None))
                if typ is None:
                    continue
                key = f"w{wid[k]}" if wid[k] is not None else f"r{oid[k]}"
                if key in seen:
                    continue
                seen.add(key)
                if typ not in CORE and typ not in EXT:
                    continue                                    # critical facility only, never a shelter candidate
                t = dict(RE_TAG.findall(tags[k] or ""))
                rows.append((key, typ, clean(nm[k]), clean(t.get("addr:street")), clean(t.get("addr:housenumber"))))
            n_read += len(geoms)
    lap(f"{fname}: {n_read:,} candidate-tagged polygons read in the box")

df = pd.DataFrame(rows, columns=["osm_key", "type", "name", "addr_street", "addr_housenumber"])
df.to_csv(os.path.join(OUT, "building_names.csv"), index=False)
share = {c: round(float((df[c] != "").mean()), 3) for c in ("name", "addr_street", "addr_housenumber")}
check("keys_unique_and_rows_read", len(df) > 1000 and df.osm_key.is_unique, {"rows": len(df), "share_with_tag": share})
json.dump({"checks": CHECKS, "failed": FAILED, "rows": len(df), "share_with_tag": share, "bbox": BBOX, "seconds": round(time.time() - T0, 1)},
          open(os.path.join(OUT, "building_names_meta.json"), "w"), indent=1)
lap(f"done; {len(df):,} shelter-tier candidates; with a name {share['name']:.0%}, with a street {share['addr_street']:.0%}; failed: {FAILED or 'none'}")
raise SystemExit(1 if FAILED else 0)
