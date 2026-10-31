"""Monte Carlo parameter-uncertainty propagation for the Smart Shelter System (pitch).

Question: how many residents of Bad Neuenahr-Ahrweiler (inside the July 2021 flood, closure 'any', 2020 residents)
are assigned to shelter buildings OUTSIDE Kreis Euskirchen and Landkreis Ahrweiler (in_area == False), under parameter uncertainty?
Also: all residents of the two districts sent outside, town residents placed, share of town trips > 30 min, Johan's (zone 246) minutes.

Run:  python -I -X utf8 powerpoint/pitch/stats/mc_sendaway.py [--bundle PATH] [--n 500] [--seed 20261030]
Input: the Smart Shelter System bundle JSON (git blob pinned in build_pitch_data.py). Output: mc_results.json next to this file.
Only numpy and scipy are used. See STATS_METHOD.md for the method, distributions, sources and limits.
"""
import argparse
import json
import math
import subprocess
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").is_file())
BUNDLE_PATH = "ideas/05-smart-shelter-map/data/bundle.json"
ap = argparse.ArgumentParser()
ap.add_argument("--bundle", default=str(ROOT / BUNDLE_PATH))
ap.add_argument("--ref", default="origin/team1-smart-shelter-map")
ap.add_argument("--n", type=int, default=500)
ap.add_argument("--seed", type=int, default=20261030)
ap.add_argument("--out", default=str(HERE / "mc_results.json"))
args = ap.parse_args()
t_start = time.time()

src = Path(args.bundle)
raw = src.read_bytes() if src.exists() else subprocess.run(["git", "show", f"{args.ref}:{BUNDLE_PATH}"], cwd=ROOT, capture_output=True, check=True).stdout
B = json.loads(raw)
blob = subprocess.run(["git", "hash-object", "--stdin"], input=raw, capture_output=True).stdout.decode().strip()

# ------------------------------------------------------------------ constants taken from the model code
SPEED = {"motorway": 100.0, "motorway_link": 60.0, "trunk": 80.0, "trunk_link": 50.0, "primary": 70.0, "primary_link": 50.0, "secondary": 60.0, "secondary_link": 40.0,
         "tertiary": 50.0, "tertiary_link": 40.0, "unclassified": 40.0, "residential": 30.0, "living_street": 10.0}   # roads.py, km/h
WALK_MS, ACCESS_MAX_M, SNAP_SHELTER_M, K_NEAREST, LIMIT_S = 4000 / 3600, 2000.0, 400.0, 200, 3600.0                      # 20_tool_pipeline.py
CORE = {"school", "university", "sports_hall", "community_centre", "public", "civic", "townhall", "college"}
CHURCHY = {"church", "chapel", "cathedral"}
TOWN, JOHAN_ZONE = "Bad Neuenahr-Ahrweiler", 246
# CALIBRATION (see STATS_METHOD.md): the bundle holds only the display network (33,652 of 85,852 edges, no residential minor roads, no one-way flags,
# 3 m simplified geometry), so routed times from it are on average 6 % longer than the tool's. One factor, fitted so that set A reproduces the town figure.
TIME_FACTOR = 1.06

# ------------------------------------------------------------------ road graph from the bundle
E = B["network"]["edges"]
ne = len(E)
eid = np.array([e["id"] for e in E])
pos = {int(i): k for k, i in enumerate(eid)}


def metres(a, b):
    k = math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot((a[0] - b[0]) * k, a[1] - b[1]) * 111_320


Len = np.array([sum(metres(p, q) for p, q in zip(e["c"], e["c"][1:])) for e in E])
T = Len / (np.array([SPEED.get(e["h"], 30.0) for e in E]) / 3.6) * TIME_FACTOR
ids = {}
u = np.empty(ne, int)
v = np.empty(ne, int)
for i, e in enumerate(E):
    for arr, p in ((u, e["c"][0]), (v, e["c"][-1])):
        arr[i] = ids.setdefault((round(p[0] * 1e5), round(p[1] * 1e5)), len(ids))
nn = len(ids)
xy = np.array(sorted(ids, key=ids.get), float) / 1e5
kx, ky = math.cos(math.radians(50.5)) * 111_320, 111_320
nxy = np.c_[xy[:, 0] * kx, xy[:, 1] * ky]


def graph(closed):
    keep = ~closed & (u != v)
    r, c, w = np.r_[u[keep], v[keep]], np.r_[v[keep], u[keep]], np.r_[T[keep], T[keep]]
    o = np.lexsort((w, c, r))
    r, c, w = r[o], c[o], w[o]
    first = np.r_[True, (r[1:] != r[:-1]) | (c[1:] != c[:-1])]          # parallel arcs keep the fastest
    return csr_matrix((w[first], (r[first], c[first])), shape=(nn, nn))


closed_ids = B["results"]["obs2021|any|restrictive"]["closed"]
cl = np.zeros(ne, bool)
cl[[pos[c] for c in closed_ids]] = True
g0, g = graph(np.zeros(ne, bool)), graph(cl)
_, l0 = connected_components(g0, directed=False)
main = l0 == np.bincount(l0).argmax()
_, l1 = connected_components(g, directed=False)
open_main = l1 == np.bincount(l1).argmax()

# ------------------------------------------------------------------ zones (July 2021 'any', 2020 residents) and access walk
Z, S = B["zones"], B["shelters"]
zp_all = np.array([z["people"]["obs2021"] for z in Z])
live = np.nonzero(zp_all > 0)[0]
zpop = zp_all[live]
zxy = np.array([[Z[i]["lon"] * kx, Z[i]["lat"] * ky] for i in live])
oid = np.nonzero(open_main)[0]
d_acc, j_acc = cKDTree(nxy[oid]).query(zxy)
assert (d_acc <= ACCESS_MAX_M).all()
dnode, acc = oid[j_acc], d_acc / WALK_MS
town = np.array([Z[i]["muni"] == TOWN for i in live])
jz = int(np.nonzero(live == JOHAN_ZONE)[0][0])

# ------------------------------------------------------------------ shelters: capacity function reproduced from bundle fields
fp = np.array([s["footprint_m2"] for s in S], float)
is_core = np.array([s["type"] in CORE for s in S])
churchy = np.array([s["type"] in CHURCHY for s in S])
in_area = np.array([s.get("in_area", True) for s in S])
dry = np.array([not any(s["flooded"][k] for k in ("obs2021", "rp10", "rp100", "rp500")) for s in S])   # dry in every flood map (model rule)
mid = np.nonzero(main)[0]
dsn, jsn = cKDTree(nxy[mid]).query(np.array([[s["lon"] * kx, s["lat"] * ky] for s in S]))
snap = np.where(dsn <= SNAP_SHELTER_M, mid[jsn], -1)
usable = dry & (snap >= 0)


def cap_fn(floors_default, usable_share, m2pp, cap_max, ext, tag):
    """Persons per building: floor(footprint x floors x usable / m2pp), capped; floors = tagged levels else default (1 for churches); extended tier only if ext."""
    fl = np.where(tag > 0, tag, np.where(churchy, 1, floors_default))
    c = np.minimum(np.floor(fp * fl * usable_share / m2pp), cap_max)
    return np.where(is_core | bool(ext), c, 0.0)


# tagged OSM levels are not in the bundle: recover the integer that reproduces BOTH shelters[].cap values (footprint is rounded to whole m2: +-1 person)
tag = np.zeros(len(S))
for i, s in enumerate(S):
    best = None
    for L in range(0, 13):
        fa, fb = (1, 1 if churchy[i] else 2) if L == 0 else (L, L)
        ea = abs(min(math.floor(fp[i] * fa * .4 / 5), 500) - s["cap"]["restrictive"]) if is_core[i] else (0 if s["cap"]["restrictive"] == 0 else 9e9)
        eb = abs(min(math.floor(fp[i] * fb * .7 / 3.5), 1500) - s["cap"]["generous"])
        if best is None or max(ea, eb) < best[0]:
            best = (max(ea, eb), L)
        if best[0] == 0:
            break
    tag[i] = best[1]
NOM = {"A": dict(floors=1, usable=.4, m2pp=5.0, cap_max=500, ext=0), "B": dict(floors=2, usable=.7, m2pp=3.5, cap_max=1500, ext=1)}
capdiff = {}
for k, name in (("A", "restrictive"), ("B", "generous")):
    p = NOM[k]
    c = cap_fn(p["floors"], p["usable"], p["m2pp"], p["cap_max"], p["ext"], tag)
    capdiff[k] = {"max_abs_diff_persons": float(np.abs(c - [s["cap"][name] for s in S]).max()), "exact_share": float(np.mean(c == [s["cap"][name] for s in S]))}

# ------------------------------------------------------------------ pairs: 200 fastest usable shelters per zone within 1 h (road time), + access walk
D = dijkstra(g, directed=False, indices=dnode, limit=LIMIT_S)
zidx = {int(z): k for k, z in enumerate(live)}


def build_pairs(pool, bundle_key):
    sel = np.nonzero(pool)[0]
    pd_, ps_, pt_ = [], [], []
    for r in range(len(live)):
        t = D[r][snap[sel]]
        ok = np.nonzero(np.isfinite(t))[0]
        top = ok[np.argsort(t[ok], kind="stable")[:K_NEAREST]]
        pd_.append(np.full(len(top), r)), ps_.append(sel[top]), pt_.append(t[top] + acc[r])
    pd_, ps_, pt_ = np.concatenate(pd_), np.concatenate(ps_), np.concatenate(pt_)
    # anchor: the pairs the tool itself used for this set keep the tool's own total time when it is shorter (restores the roads the display network lacks)
    key = {(a, b): i for i, (a, b) in enumerate(zip(pd_.tolist(), ps_.tolist()))}
    extra = []
    for a in B["results"][bundle_key]["assign"]:
        k = (zidx[a[0]], a[1])
        if k in key:
            pt_[key[k]] = min(pt_[key[k]], a[3])
        else:
            extra.append((k[0], k[1], a[3]))
    if extra:
        ex = np.array(extra)
        pd_, ps_, pt_ = np.r_[pd_, ex[:, 0].astype(int)], np.r_[ps_, ex[:, 1].astype(int)], np.r_[pt_, ex[:, 2]]
    us, inv = np.unique(ps_, return_inverse=True)
    nd, npair, ns = len(live), len(pt_), len(us)
    ar = np.arange(npair)
    pen = 10 * (pt_.max() + 1)
    return dict(pd=pd_, ps=ps_, t=pt_, us=us, c=np.r_[pt_, np.full(nd, pen)], anchors=len(extra),
                aeq=coo_matrix((np.ones(npair + nd), (np.r_[pd_, np.arange(nd)], np.r_[ar, npair + np.arange(nd)])), shape=(nd, npair + nd)).tocsr(),
                aub=coo_matrix((np.ones(npair), (inv, ar)), shape=(ns, npair + nd)).tocsr(),
                out_pair=(~in_area[ps_]), town_pair=town[pd_], over30=pt_ > 1800.0, johan=(pd_ == jz))


POOLS = {0: build_pairs(usable & is_core, "obs2021|any|restrictive"), 1: build_pairs(usable, "obs2021|any|generous")}


def run(par):
    """One model run: capacity from parameters, demand = residents x population factor x shelter-seeking share, capacity-limited transport LP (as evac.assign)."""
    P = POOLS[int(par["ext"])]
    cap = cap_fn(par["floors"], par["usable"], par["m2pp"], par["cap_max"], par["ext"], tag)
    people = zpop * par["pop"] * par["seek"]
    nd, npair = len(people), len(P["t"])
    r = linprog(P["c"], A_ub=P["aub"], b_ub=cap[P["us"]], A_eq=P["aeq"], b_eq=people, bounds=(0, None), method="highs")
    if not r.success:
        raise RuntimeError(r.message)
    x = np.clip(r.x, 0, None)
    f, un = x[:npair], x[npair:]
    tp, tt = f[P["town_pair"]], P["t"][P["town_pair"]]
    jf = f[P["johan"]]
    main_j = P["t"][P["johan"]][np.argmax(jf)] / 60 if jf.sum() > 1e-6 else np.nan
    return {"sentAway": float(f[P["town_pair"] & P["out_pair"]].sum()),
            "sentAwayAll": float(f[P["out_pair"]].sum()),
            "townPlaced": float(tp.sum()),
            "townOver30Share": float(f[P["town_pair"] & P["over30"]].sum() / tp.sum()) if tp.sum() > 1e-6 else np.nan,
            "johanMin": float(np.average(P["t"][P["johan"]], weights=jf) / 60) if jf.sum() > 1e-6 else np.nan,
            "johanMainMin": float(main_j),
            "townUnassigned": float(un[town].sum()),
            "meanMin": float(np.average(P["t"], weights=f) / 60) if f.sum() > 1e-6 else np.nan,
            "over30": float(f[P["over30"]].sum()), "placed": float(f.sum())}


QUANT = ["sentAway", "sentAwayAll", "townPlaced", "townOver30Share", "johanMin", "johanMainMin"]
UNIT = {"sentAway": "residents of the town sent outside the two districts", "sentAwayAll": "residents of the two districts sent outside",
        "townPlaced": "town residents placed in any shelter", "townOver30Share": "share of placed town residents with a trip over 30 min (incl. walk)",
        "johanMin": "minutes, zone 246, flow-weighted over its shelters (walk + drive)", "johanMainMin": "minutes, zone 246, to its largest-flow shelter (walk + drive)"}

# ------------------------------------------------------------------ 1. VALIDATION against the bundle's own results
validation = {}
for k, name in (("A", "restrictive"), ("B", "generous")):
    r = run({**NOM[k], "pop": 1.0, "seek": 1.0})
    bs = B["results"][f"obs2021|any|{name}"]
    bt = [a for a in bs["assign"] if Z[a[0]]["muni"] == TOWN]
    ba = [a for a in bs["assign"] if a[0] == JOHAN_ZONE]
    top = max(ba, key=lambda a: a[2])
    validation[k] = {
        "town_outside": {"mine": round(r["sentAway"], 1), "bundle": round(sum(a[2] for a in bt if not S[a[1]].get("in_area", True)), 1)},
        "town_placed": {"mine": round(r["townPlaced"], 1), "bundle": round(sum(a[2] for a in bt), 1)},
        "placed_all": {"mine": round(r["placed"], 1), "bundle": bs["summary"]["placed"]},
        "mean_time_min": {"mine": round(r["meanMin"], 2), "bundle": bs["summary"]["mean_time_min"]},
        "people_over_30min": {"mine": round(r["over30"]), "bundle": bs["summary"]["people_over_30min"]},
        "johan_main_min": {"mine": round(r["johanMainMin"], 2), "bundle": round(top[3] / 60, 2)},
        "town_over30_share": {"mine": round(r["townOver30Share"], 4), "bundle": round(sum(a[2] for a in bt if a[3] > 1800) / sum(a[2] for a in bt), 4)},
        "town_unassigned": round(r["townUnassigned"], 1), "run": r}
vA, vB = validation["A"], validation["B"]
validation["pass"] = {"A_town_outside_within_1pct": abs(vA["town_outside"]["mine"] - vA["town_outside"]["bundle"]) <= 0.01 * vA["town_outside"]["bundle"],
                      "B_town_outside_zero": vB["town_outside"]["mine"] < 0.5,
                      "all_placed": bool(abs(vA["placed_all"]["mine"] - vA["placed_all"]["bundle"]) < 1 and abs(vB["placed_all"]["mine"] - vB["placed_all"]["bundle"]) < 1),
                      "mean_time_within_0_5_min": bool(all(abs(x["mean_time_min"]["mine"] - x["mean_time_min"]["bundle"]) <= 0.5 for x in (vA, vB))),
                      "capacity_within_1_person": all(c["max_abs_diff_persons"] <= 1 for c in capdiff.values())}
validation["capacity_reproduction"] = capdiff
validation["time_factor"] = TIME_FACTOR
validation["anchored_extra_pairs"] = {"A": POOLS[0]["anchors"], "B": POOLS[1]["anchors"]}
print(json.dumps({k: v for k, v in validation.items() if k != "run"}, default=float)[:1500])
print("validation:", validation["pass"])
if not all(validation["pass"].values()):
    raise SystemExit("VALIDATION FAILED: no Monte Carlo written")
nominal = {"A": vA["run"], "B": vB["run"]}
for k in "AB":
    del validation[k]["run"]

# ------------------------------------------------------------------ 2. parameter distributions
# (low, mode, high); sources in STATS_RESEARCH.md; flags: SOURCED / JUDGEMENT
TRI = {"m2pp": (3.5, 4.0, 5.5),            # DRK 4.0 m2/bed (+1.5 day room), Sphere 3.5: SOURCED (partly secondary)
       "usable": (0.40, 0.55, 0.70),       # DIN 277 net/gross proxy 0.60-0.70, shelter-specific value not sourced: JUDGEMENT
       "pop": (0.85, 1.00, 1.15)}          # GHS-POP local MAPE 5-12 % (Poland, Portugal), +-15 % bracket: JUDGEMENT anchored
DISPLACED = (0.34, 0.40, 1.0)              # share of flooded residents displaced: 34 % evacuated (Rocha Silva 2025), 1.0 = model worst case
SHELTER_GIVEN_DISPLACED = (0.05, 0.10, 0.25)   # US planning rule 10-20 %, 25 % (FEMA exercise): JUDGEMENT, not sourced for this region
WIDE_SEEK = (0.10, 0.35, 1.0)              # coordinator's provisional wide range for the share of ALL residents seeking a shelter
CAPMAX = (500.0, 1500.0)                   # the two assumption sets' limits, uniform: JUDGEMENT
rng = np.random.default_rng(args.seed)
N = args.n
tri = lambda t, n: rng.triangular(t[0], t[1], t[2], n)
DRAWS = {"m2pp": tri(TRI["m2pp"], N), "usable": tri(TRI["usable"], N), "pop": tri(TRI["pop"], N), "cap_max": rng.uniform(*CAPMAX, N),
         "ext": rng.integers(0, 2, N), "floors": rng.integers(1, 3, N)}
SEEK = {"fixed1": np.ones(N), "research": tri(DISPLACED, N) * tri(SHELTER_GIVEN_DISPLACED, N), "wide": tri(WIDE_SEEK, N)}
PARAMS = ["m2pp", "usable", "cap_max", "ext", "floors", "pop", "seek"]
LABEL = {"m2pp": "m2 per person (3.5 / 4.0 / 5.5)", "usable": "usable share (0.40 / 0.55 / 0.70)", "cap_max": "cap per building (500 to 1500)",
         "ext": "extended buildings included (no / yes)", "floors": "default floors, untagged buildings (1 / 2)", "pop": "population factor (0.85 / 1.00 / 1.15)", "seek": "shelter-seeking share"}
STATUS = {"m2pp": "sourced (DRK card, Sphere; secondary)", "usable": "judgement / not sourced for this region", "cap_max": "judgement (the two assumption sets' limits)",
          "ext": "judgement (tier inclusion switch, p=0.5)", "floors": "judgement (the two assumption sets' defaults, p=0.5)",
          "pop": "judgement anchored on GHS-POP local MAPE 5-12 %", "seek": "judgement / not sourced for this region (US planning rule 10-20 %)"}


def stats(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    q = np.percentile(x, [5, 10, 50, 90, 95])
    return {"median": q[2], "p10": q[1], "p90": q[3], "p5": q[0], "p95": q[4], "mean": x.mean(), "min": x.min(), "max": x.max()}


# ------------------------------------------------------------------ 3. Monte Carlo (three shelter-seeking variants share all other draws)
out = {}
for var in ("fixed1", "research", "wide"):
    rows = []
    for i in range(N):
        par = {k: DRAWS[k][i] for k in DRAWS}
        par["seek"] = SEEK[var][i]
        rows.append(run(par))
    res = {q: np.array([r[q] for r in rows]) for q in QUANT + ["townUnassigned"]}
    ent = {}
    for q in QUANT:
        s = stats(res[q])
        s.update({"nominalA": nominal["A"][q], "nominalB": nominal["B"][q], "n_draws": N, "seed": args.seed, "unit": UNIT[q]})
        if q == "sentAway":
            s["share_zero"] = float(np.mean(res[q] < 0.5))
            s["share_below_100"] = float(np.mean(res[q] < 100))
        s["spearman"] = {}
        for p in PARAMS:
            xv = SEEK[var] if p == "seek" else DRAWS[p]
            if np.std(xv) > 0 and np.nanstd(res[q]) > 0:
                m = np.isfinite(res[q])
                s["spearman"][p] = float(spearmanr(xv[m], res[q][m]).statistic)
        ent[q] = s
    ent["_unassigned_town_max"] = float(res["townUnassigned"].max())
    out[var] = ent
    print(var, "sentAway", {k: round(ent["sentAway"][k], 1) for k in ("median", "p10", "p90", "p5", "p95")}, "zero share", ent["sentAway"]["share_zero"], flush=True)

# ------------------------------------------------------------------ 4. one-at-a-time tornado (others central; binary switches averaged over the other switch)
CENTRAL = {"m2pp": TRI["m2pp"][1], "usable": TRI["usable"][1], "cap_max": 1000.0, "pop": 1.0}
RANGE = {"m2pp": (TRI["m2pp"][0], TRI["m2pp"][2]), "usable": (TRI["usable"][2], TRI["usable"][0]), "cap_max": (1500.0, 500.0), "pop": (TRI["pop"][0], TRI["pop"][2])}
# (low, high) below = parameter value giving the LOWER / HIGHER capacity or demand end; every entry reports output at both ends
SEEK_RANGE = {"fixed1": None, "research": (DISPLACED[0] * SHELTER_GIVEN_DISPLACED[0], DISPLACED[2] * SHELTER_GIVEN_DISPLACED[2]), "wide": (WIDE_SEEK[0], WIDE_SEEK[2])}
SEEK_CENTRAL = {"fixed1": 1.0, "research": DISPLACED[1] * SHELTER_GIVEN_DISPLACED[1], "wide": WIDE_SEEK[1]}
for var in ("fixed1", "research", "wide"):
    base = {**CENTRAL, "seek": SEEK_CENTRAL[var]}
    cache = {}

    def at(over):
        k = tuple(sorted({**base, **over}.items()))
        if k not in cache:
            cache[k] = run({**base, **over})
        return cache[k]

    def avg_bin(over, q):
        # average over the two binary switches not fixed in `over`
        free = [b for b in ("ext", "floors") if b not in over]
        vals = []
        for e in ((0, 1) if "ext" in free else (over.get("ext"),)):
            for f_ in ((1, 2) if "floors" in free else (over.get("floors"),)):
                vals.append(at({**over, "ext": e, "floors": f_})[q])
        return float(np.nanmean(vals))
    tor = {}
    for q in QUANT:
        rows = []
        baseline = avg_bin({}, q)
        for p in PARAMS:
            if p == "seek" and SEEK_RANGE[var] is None:
                continue
            if p in ("ext", "floors"):
                lo, hi = (avg_bin({p: (0 if p == "ext" else 1)}, q), avg_bin({p: (1 if p == "ext" else 2)}, q))
                vlo, vhi = (0, 1) if p == "ext" else (1, 2)
            elif p == "seek":
                vlo, vhi = SEEK_RANGE[var]
                lo, hi = avg_bin({"seek": vlo}, q), avg_bin({"seek": vhi}, q)
            else:
                vlo, vhi = RANGE[p]
                lo, hi = avg_bin({p: vlo}, q), avg_bin({p: vhi}, q)
            rows.append({"param": p, "label": LABEL[p], "status": STATUS[p], "value_low": vlo, "value_high": vhi, "out_at_low": lo, "out_at_high": hi, "swing": abs(hi - lo)})
        rows.sort(key=lambda r: -r["swing"])
        tor[q] = {"baseline": baseline, "rows": rows}
    out[var]["_tornado"] = tor
    print(var, "tornado sentAway", [(r["param"], round(r["out_at_low"]), round(r["out_at_high"])) for r in tor["sentAway"]["rows"]], flush=True)

# ------------------------------------------------------------------ 5. write
VARIANTS = {"fixed1": "shelter-seeking share fixed at 1.0 (the model's present assumption: every resident in the flood needs a shelter)",
            "research": "shelter-seeking share sampled: displaced share tri(0.34, 0.40, 1.0) x share needing public shelter tri(0.05, 0.10, 0.25); judgement / not sourced for this region",
            "wide": "shelter-seeking share sampled, wide: tri(0.10, 0.35, 1.0); judgement"}
result = {"title": "Monte Carlo parameter uncertainty, Smart Shelter System, July 2021 flood (closure 'any', 2020 residents)",
          "what_it_is": "model range under parameter uncertainty, not a validated prediction interval; structural errors (OSM completeness, free-flow speeds, no traffic, GHS-POP spatial allocation, who actually goes to a shelter) are not included",
          "bundle_git_blob": blob, "bundle_generated_utc": B["meta"]["generated_utc"], "n_draws": N, "seed": args.seed, "variants": VARIANTS,
          "headline_variant": "fixed1", "headline_note": "Top-level quantity keys below repeat the 'fixed1' variant, the one comparable with nominal A/B (both assume share 1.0). The tile must name the variant.",
          "validation": validation,
          "parameters": {"m2pp": {"dist": "triangular", "args": TRI["m2pp"], "status": STATUS["m2pp"]}, "usable": {"dist": "triangular", "args": TRI["usable"], "status": STATUS["usable"]},
                         "cap_max": {"dist": "uniform", "args": CAPMAX, "status": STATUS["cap_max"]}, "ext": {"dist": "bernoulli", "p": 0.5, "status": STATUS["ext"]},
                         "floors": {"dist": "discrete {1,2}", "p": 0.5, "status": STATUS["floors"]}, "pop": {"dist": "triangular", "args": TRI["pop"], "status": STATUS["pop"]},
                         "seek_research": {"dist": "tri(0.34,0.40,1.0) x tri(0.05,0.10,0.25)", "status": STATUS["seek"]}, "seek_wide": {"dist": "triangular", "args": WIDE_SEEK, "status": "judgement / provisional"}},
          "variant_results": {k: {q: v for q, v in out[k].items() if not q.startswith("_")} for k in out},
          "tornado": {k: out[k]["_tornado"] for k in out},
          "runtime_s": round(time.time() - t_start)}
for q in QUANT:
    result[q] = out["fixed1"][q]
Path(args.out).write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")
print("wrote", args.out, "in", round(time.time() - t_start), "s")
