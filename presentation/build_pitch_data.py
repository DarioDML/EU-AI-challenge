"""Build pitch-data.js for the 5-minute pitch from the Smart Shelter System bundle.

Input: the tool's bundle (ideas/05-smart-shelter-map/data/bundle.json, or the same path read from a git ref)
and georef.json (the fit of the map assets/route-stress-map.svg to Web Mercator, written by fit_screenshot.py). Output: pitch-data.js with
  - region summaries for 8 plans: 4 flood levels x 2 shelter assumption sets (2020 residents; roads closed
    if they touch the 2021 flood, or under any modelled water),
  - Johan's zone (default 246, Bad Neuenahr-Ahrweiler): his household's shelter, times and route per plan,
  - slide-3 overlay geometry in map pixels (1244 x 894).
Every number comes from the bundle; the build stops when a check fails.

Run from the repository root:
    python powerpoint/pitch/build_pitch_data.py
    python powerpoint/pitch/build_pitch_data.py --bundle path/to/bundle.json --zone 246
"""
import argparse
import hashlib
import json
import math
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").is_file())
BUNDLE_PATH = "ideas/05-smart-shelter-map/data/bundle.json"
BUNDLE_BLOB = "92c3d36692b7a17d34fec8c90d9f8c59c728d91c"
LEVELS = [("obs2021", "any"), ("rp10", "wet"), ("rp100", "wet"), ("rp500", "wet")]
SETS = ["restrictive", "generous"]
R = 6378137.0

ap = argparse.ArgumentParser()
ap.add_argument("--bundle", default=str(ROOT / BUNDLE_PATH))
ap.add_argument("--ref", default="origin/team1-smart-shelter-map", help="git ref used when --bundle does not exist")
ap.add_argument("--georef", default=str(HERE / "georef.json"))
ap.add_argument("--zone", type=int, default=246)
ap.add_argument("--out", default=str(HERE / "pitch-data.js"))
args = ap.parse_args()

src = Path(args.bundle)
if src.exists():
    raw, origin = src.read_bytes(), str(src.relative_to(ROOT)) if src.is_relative_to(ROOT) else src.name
else:
    raw = subprocess.run(["git", "show", f"{args.ref}:{BUNDLE_PATH}"], cwd=ROOT, capture_output=True, check=True).stdout
    origin = f"{args.ref}:{BUNDLE_PATH}"
blob = subprocess.run(["git", "hash-object", "--stdin"], cwd=ROOT, input=raw, capture_output=True, check=True).stdout.decode().strip()
if blob != BUNDLE_BLOB:
    raise SystemExit(f"Bundle changed: expected pinned blob {BUNDLE_BLOB}, got {blob}; no output written")
B = json.loads(raw)
G = json.loads(Path(args.georef).read_text())

E = {e["id"]: e for e in B["network"]["edges"]}
S = {s["id"]: s for s in B["shelters"]}
Z = {z["id"]: z for z in B["zones"]}
veh, cap = B["assumptions"]["vehicles"], B["assumptions"]["road_capacity_veh_per_h"]
CHECKS = []


def check(name, ok, **info):
    CHECKS.append({"check": name, "ok": bool(ok), **info})
    if not ok:
        raise SystemExit(f"CHECK FAILED: {name} {info}")


check("map fit uses the pinned bundle", G.get("bundle_blob") == blob)
check("map fit uses July 2021 set A", G.get("key") == "obs2021|any|restrictive")
map_file = G.get("file", "")
check("map filename is an asset basename", bool(map_file) and Path(map_file).name == map_file)
map_path = HERE / "assets" / map_file
check("map asset matches fitted bytes", map_path.is_file() and hashlib.sha256(map_path.read_bytes()).hexdigest() == G.get("map_sha256"))
if map_path.suffix.lower() == ".svg":
    svg = ET.parse(map_path).getroot()
    check("SVG dimensions and viewBox match map pixels",
          [float(svg.get("width")), float(svg.get("height"))] == [G["W"], G["H"]]
          and [float(v) for v in svg.get("viewBox", "").split()] == [0, 0, G["W"], G["H"]])
check("map has a valid Mercator transform", all(math.isfinite(G[k]) for k in ("X0", "Y0", "s_px_per_merc_m", "zoom_eff"))
      and G["s_px_per_merc_m"] > 0
      and math.isclose(G["s_px_per_merc_m"], 256 * 2 ** G["zoom_eff"] / (2 * math.pi * R), rel_tol=1e-5))


def name_of(e):
    n = e.get("n")
    return n if n not in (None, "", "nan", "None") else ""


def ratio(eid, people):
    """Road stress as the tool computes it: people turned into vehicles per hour over an ASSUMED class capacity."""
    e = E[eid]
    c = cap.get(e["h"]) or cap.get(e["h"].replace("_link", ""))
    return None if not c else people * veh["car_share"] / veh["persons_per_car"] / veh["evacuation_window_h"] / c


def metres(a, b):
    k = math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot((a[0] - b[0]) * k, a[1] - b[1]) * 111_320


def px(p):
    x = R * math.radians(p[0])
    y = R * math.log(math.tan(math.pi / 4 + math.radians(p[1]) / 2))
    return ((x - G["X0"]) * G["s_px_per_merc_m"], (G["Y0"] - y) * G["s_px_per_merc_m"])


def inside(pt, margin=0.0):
    return -margin <= pt[0] <= G["W"] + margin and -margin <= pt[1] <= G["H"] + margin


def polyline(es):
    """Route edges (travel order) joined into one lon/lat line; returns the line and the largest gap in metres."""
    pts, gap = [], 0.0
    for i, eid in enumerate(es):
        c = [tuple(p) for p in E[eid]["c"]]
        if not pts:
            if len(es) > 1:
                nxt = E[es[1]]["c"]
                if min(metres(c[0], nxt[0]), metres(c[0], nxt[-1])) < min(metres(c[-1], nxt[0]), metres(c[-1], nxt[-1])):
                    c.reverse()
            pts.extend(c)
            continue
        if metres(pts[-1], c[-1]) < metres(pts[-1], c[0]):
            c.reverse()
        gap = max(gap, metres(pts[-1], c[0]))
        pts.extend(c[1:] if metres(pts[-1], c[0]) < 0.5 else c)
    return pts, gap


def simplify(pts, tol):
    """Douglas-Peucker in pixel space."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-9
    dists = [abs(dy * (x - x1) - dx * (y - y1)) / norm for x, y in pts[1:-1]]
    i = max(range(len(dists)), key=dists.__getitem__)
    if dists[i] <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[: i + 2], tol)[:-1] + simplify(pts[i + 1:], tol)


def clip_to_frame(line):
    """Pixel points of the route up to where it first leaves the screenshot; the exit point is on the frame edge."""
    out = []
    for a in line:
        if inside(a):
            out.append(a)
            continue
        if out:
            b = out[-1]
            t = 1.0
            for lim, va, vb in ((0, a[0], b[0]), (G["W"], a[0], b[0]), (0, a[1], b[1]), (G["H"], a[1], b[1])):
                if (va - lim) * (vb - lim) < 0:
                    t = min(t, (vb - lim) / (vb - va))
            out.append((b[0] + (a[0] - b[0]) * t, b[1] + (a[1] - b[1]) * t))
        return out, True
    return out, False


def in_poly(pt, geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    hit = False
    for poly in polys:
        for ring in poly:
            j = len(ring) - 1
            for i in range(len(ring)):
                (xi, yi), (xj, yj) = ring[i], ring[j]
                if (yi > pt[1]) != (yj > pt[1]) and pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi:
                    hit = not hit
                j = i
    return hit


def shelter_label(s):
    kind = {"school": "School", "sports_hall": "Sports hall", "community_centre": "Community hall", "kindergarten": "Kindergarten",
            "church": "Church", "public": "Public building", "townhall": "Town hall", "hotel": "Hotel", "college": "College"}.get(s["type"], s["type"].replace("_", " ").capitalize())
    title = s.get("name") or kind
    where = s.get("street") or (f"near {s['near_street']}" if s.get("near_street") else "")
    return {"title": title, "kind": kind, "where": where, "town": s["muni"], "in_area": bool(s.get("in_area", True))}


zone = Z[args.zone]
bna = next(m for m in B["munis"] if m["name"] == zone["muni"])
# Johan's street: the road closed by the July 2021 flood nearest to his zone's resident-weighted centre
res0 = B["results"]["obs2021|any|restrictive"]
centre = (zone["lon"], zone["lat"])
near = min(res0["closed"], key=lambda e: min(metres(centre, p) for p in E[e]["c"]))
street = name_of(E[near])
check("johan street is a named closed road", bool(street), edge=near)
plans, johan = {}, {}
for lvl, closure in LEVELS:
    for cset in SETS:
        key = f"{lvl}|{closure}|{cset}"
        res = B["results"][key]
        s_ = res["summary"]
        check(f"conservation {key}", abs(s_["placed"] + s_["unassigned"] - s_["people_to_place"]) < 0.5 + 0.001 * s_["people_to_place"])
        worst = max((ratio(int(e), v) or 0) for e, v in res["load"].items())
        check(f"worst road ratio {key}", abs(worst - s_["worst_road_ratio"]) < 0.011, page=round(worst, 3), bundle=s_["worst_road_ratio"])
        over = sum(1 for e, v in res["load"].items() if (ratio(int(e), v) or 0) > 1)
        check(f"roads over capacity {key}", over == s_["stress_edges_over_1"], recomputed=over, bundle=s_["stress_edges_over_1"])
        placed = s_["placed"]
        plans[key] = {"to_place": round(s_["people_to_place"]), "placed": round(placed), "no_place": round(s_["unassigned"]),
                      "over30": round(s_["people_over_30min"]), "within30": round(placed - s_["people_over_30min"]),
                      "mean_min": s_["mean_time_min"], "roads_over": s_["stress_edges_over_1"], "worst_ratio": s_["worst_road_ratio"],
                      "closed_edges": s_["closed_edges"], "shelters_used": s_["shelters_used"], "shelters_full": s_["shelters_at_capacity"]}
        # Bad Neuenahr-Ahrweiler only: residents sent outside Kreis Euskirchen and Landkreis Ahrweiler, and trips over 30 min
        local = [a for a in res["assign"] if Z[a[0]]["muni"] == zone["muni"]]
        plans[key]["town"] = {"placed": round(sum(a[2] for a in local)), "outside": round(sum(a[2] for a in local if not S[a[1]].get("in_area", True))),
                              "over30": round(sum(a[2] for a in local if a[3] > 1800))}

        rows = sorted([a for a in res["assign"] if a[0] == zone["id"]], key=lambda a: -a[2])
        people = zone["people"].get(lvl, 0)
        j = {"people_in_zone": round(people), "no_place": round(res["unassigned"].get(str(zone["id"]), 0)),
             "street_closed": street in {name_of(E[e]) for e in res["closed"] if metres((zone["lon"], zone["lat"]), E[e]["c"][0]) < 400}}
        if not rows:
            j["status"] = "no_people" if people < 0.5 else "no_place"
            johan[key] = j
            continue
        a = rows[0]
        es = a[5]
        closed = set(res["closed"])
        check(f"johan route avoids closed roads {key}", not any(e in closed for e in es))
        check(f"johan detour not negative {key}", a[3] >= a[4] - 1.5)
        line, gap = polyline(es)
        check(f"johan route is continuous {key}", gap < 30, max_gap_m=round(gap, 1))
        walk = res.get("access_s", {}).get(str(zone["id"]), 0)
        names = []
        for e in es:
            n = name_of(E[e])
            if n and n not in names:
                names.append(n)
        ratios = [ratio(e, res["load"].get(str(e), 0)) or 0 for e in es]
        j.update({"status": "placed", "shelter": shelter_label(S[a[1]]), "shelter_id": a[1], "share": round(a[2] / sum(r[2] for r in rows), 2),
                  "destinations": len(rows), "walk_min": round(walk / 60, 1), "total_min": round(a[3] / 60, 1),
                  "drive_min": round((a[3] - walk) / 60, 1), "detour_min": round((a[3] - a[4]) / 60, 1),
                  "km": round(sum(metres(p, q) for p, q in zip(line, line[1:])) / 1000, 1), "via": names[:5],
                  "roads_over_on_route": sum(1 for r in ratios if r > 1), "max_ratio_on_route": round(max(ratios), 2)})
        if lvl == "obs2021":
            pix, leaves = clip_to_frame([px(p) for p in line])
            j["overlay"] = {"path": [[round(x, 1), round(y, 1)] for x, y in simplify(pix, 0.8)], "leaves_frame": leaves,
                            "shelter_px": [round(v, 1) for v in px((S[a[1]]["lon"], S[a[1]]["lat"]))]}
        johan[key] = j

# Johan's pin = his zone's resident-weighted centre, the point the model starts the walk from
home_px = px(centre)
check("johan home lies in the screenshot", inside(home_px), px=[round(v) for v in home_px])
check("johan street is within 150 m of his pin", min(metres(centre, p) for p in E[near]["c"]) < 150)

# Slide-3 callouts, all for the plan the screenshot shows (July 2021, set A)
worst_edge = max((int(e) for e in res0["load"]), key=lambda e: (ratio(e, res0["load"][str(e)]) or 0) if inside(px(E[e]["c"][len(E[e]["c"]) // 2])) else -1)
w_mid = px(E[worst_edge]["c"][len(E[worst_edge]["c"]) // 2])
closed_km = sum(sum(metres(p, q) for p, q in zip(E[e]["c"], E[e]["c"][1:])) for e in res0["closed"]
                if in_poly(E[e]["c"][len(E[e]["c"]) // 2], bna["geometry"])) / 1000
# flood callout: the town's closed-road vertex nearest the centroid of the town's closed-road vertices inside the map
town_closed = [px(p) for e in res0["closed"] if in_poly(E[e]["c"][len(E[e]["c"]) // 2], bna["geometry"]) for p in E[e]["c"] if inside(px(p), -20)]
check("town has closed roads in the map", len(town_closed) > 50, vertices=len(town_closed))
cx, cy = sum(p[0] for p in town_closed) / len(town_closed), sum(p[1] for p in town_closed) / len(town_closed)
flood_px = tuple(round(v, 1) for v in min(town_closed, key=lambda p: math.dist(p, (cx, cy))))
check("flood callout sits on a closed road in the map", any(math.dist(flood_px, px(p)) < 5 for e in res0["closed"] for p in E[e]["c"]))
residents_town = sum(z["people"]["obs2021"] for z in B["zones"] if z["muni"] == zone["muni"])
callouts = {"flood": {"px": list(flood_px), "closed_km_town": round(closed_km)},
            "jam": {"px": [round(v, 1) for v in w_mid], "road": name_of(E[worst_edge]), "ratio": round(ratio(worst_edge, res0["load"][str(worst_edge)]), 1),
                    "people": round(res0["load"][str(worst_edge)]), "road_class": E[worst_edge]["h"]},
            "home": {"px": [round(v, 1) for v in home_px], "street": street}}

# Slide "The message": Johan's alert for the best case (July 2021, assumption set B) and the map box that shows his route.
# Lines use the same template as slide 4; his own street is closed, so the last line says the route avoids flooded roads AFTER it.
AKEY = "obs2021|any|generous"
aj = johan[AKEY]
check("alert plan is placed and has an overlay", aj["status"] == "placed" and "overlay" in aj)
check("alert: Johan's own street is closed, so the route claim starts after it", aj["street_closed"] is True)
a_via = [n for n in aj["via"] if n != street][:2]
check("alert: route names a road after his street", len(a_via) >= 1, via=a_via)
a_walk, a_drive = max(1, round(aj["walk_min"])), max(1, round(aj["drive_min"]))
a_sh = aj["shelter"]
a_town = "" if a_sh["in_area"] else f", {a_sh['town']}"
a_lines = {
    "danger": f"EXTREME FLOOD DANGER. {street} is in the flood area.",
    "severity": "LIFE-THREATENING. The same flood as July 2021.",
    "go": f"LEAVE NOW. Go to: {a_sh['title']}, {a_sh['where']}{a_town}.",
    "route": f"Walk {a_walk} min to the nearest open road, then {a_drive} min by car via {', '.join(a_via)}.",
    "safe": "After your street, this route avoids flooded roads.",
}
ov = aj["overlay"]
a_pts = [tuple(q) for q in ov["path"]] + [tuple(ov["shelter_px"]), tuple(home_px)]
check("alert: route, home and shelter are inside the map", all(inside(q) for q in a_pts))
check("alert: route starts within 30 px of Johan's pin", math.dist(ov["path"][0], home_px) < 30)
check("alert: route ends within 12 px of the shelter", math.dist(ov["path"][-1], ov["shelter_px"]) < 12)
# crop: bounding box + 18 % padding, widened to at least 210 px so the road context stays readable, aspect 3:2, inside the map
bx0, bx1 = min(q[0] for q in a_pts), max(q[0] for q in a_pts)
by0, by1 = min(q[1] for q in a_pts), max(q[1] for q in a_pts)
cw = max((bx1 - bx0) * 1.36, (by1 - by0) * 1.36 * 1.5, 210.0)
ch = cw / 1.5
ccx, ccy = (bx0 + bx1) / 2, (by0 + by1) / 2
cx0 = min(max(ccx - cw / 2, 0), G["W"] - cw)
cy0 = min(max(ccy - ch / 2, 0), G["H"] - ch)
a_crop = {"x": round(cx0, 1), "y": round(cy0, 1), "w": round(cw, 1), "h": round(ch, 1)}
check("alert: crop is 3:2 and inside the map", abs(a_crop["w"] / a_crop["h"] - 1.5) < 0.01 and a_crop["x"] >= 0 and a_crop["y"] >= 0
      and a_crop["x"] + a_crop["w"] <= G["W"] and a_crop["y"] + a_crop["h"] <= G["H"], crop=a_crop)
check("alert: crop holds home, route and shelter with margin", all(a_crop["x"] + 8 <= q[0] <= a_crop["x"] + a_crop["w"] - 8 and a_crop["y"] + 8 <= q[1] <= a_crop["y"] + a_crop["h"] - 8 for q in a_pts))
check("alert: capitals only on the three openers", all(a_lines[k].split(". ")[0].isupper() for k in ("danger", "severity", "go")) and not any(a_lines[k].split(". ")[0].isupper() for k in ("route", "safe")))
check("alert: every line is filled from data", all(v and "{" not in v and "None" not in v for v in a_lines.values()) and street in a_lines["danger"] and a_sh["title"] in a_lines["go"])
alert = {"plan": AKEY, "street": street, "street_closed": aj["street_closed"], "severity_text": "as in July 2021",
         "shelter": {"title": a_sh["title"], "where": a_sh["where"], "town": a_sh["town"]},
         "walk_min": aj["walk_min"], "drive_min": aj["drive_min"], "total_min": aj["total_min"], "via": a_via, "lines": a_lines,
         "crop": a_crop, "route": ov["path"], "home": [round(v, 1) for v in home_px], "shelterPx": ov["shelter_px"]}

meta = B["meta"]
out = {
    "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "source": {"bundle": origin, "git_blob": blob, "bundle_generated_utc": meta["generated_utc"], "area": meta["area"],
               "osm_state": meta["provenance"]["osm_state"], "population": "GHS-POP 2020 (modelled estimate), residents inside the flood",
               "assumptions": {"vehicles": veh, "road_capacity_veh_per_h": cap, "walk_kmh": 4, "capacity_sets": B["capacities"]}},
    "screenshot": {"file": G["file"], "w": G["W"], "h": G["H"], "plan": G["key"], "sha256": G["map_sha256"]},
    "levels": [{"id": l, "closure": c, "label": next(s["label"] for s in B["scenarios"] if s["id"] == l)} for l, c in LEVELS],
    "sets": [{"id": c["id"], "label": c["label"]} for c in B["capacities"]],
    "plans": plans,
    "town": {"name": zone["muni"], "residents_in_flood_2021": round(residents_town)},
    "johan": {"zone": zone["id"], "street": street, "plans": johan},
    "callouts": callouts,
    "alert": alert,
    "checks": len(CHECKS),
}
Path(args.out).write_text("// Generated by powerpoint/pitch/build_pitch_data.py; do not edit by hand.\n"
                          f"// Source: {origin} (git blob {blob[:12]}, bundle generated {meta['generated_utc']}).\n"
                          "window.PITCH = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
dst = Path(args.out).resolve()
print(f"{len(CHECKS)} checks passed; wrote {dst.relative_to(ROOT) if dst.is_relative_to(ROOT) else dst} ({dst.stat().st_size:,} bytes)")
for key in plans:
    p, j = plans[key], johan[key]
    trip = f"{j['shelter']['title']} ({j['shelter']['town']}), {j['total_min']} min, walk {j['walk_min']}, roads over cap on route {j['roads_over_on_route']}" if j["status"] == "placed" else j["status"]
    print(f"{key:26s} place {p['to_place']:>6,} | <=30 {p['within30']:>6,} | >30 {p['over30']:>5,} | none {p['no_place']:>5,} | roads>1 {p['roads_over']:>2} | town outside {p['town']['outside']:>5,} | Johan: {trip}")
print("street", street, "| callouts", json.dumps(callouts))
