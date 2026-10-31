# Monte Carlo for "residents sent outside the two districts"

Script: `mc_sendaway.py` (numpy + scipy only; `python -I -X utf8 presentation/stats/mc_sendaway.py`, about 15 min for N = 1000 per variant). Results: `mc_results.json`. Seed 20261030, N = 1000 draws per variant, all variants share the same draws for every parameter except the shelter-seeking share.

## What is computed
Output: residents of Bad Neuenahr-Ahrweiler inside the July 2021 flood (closure 'any', GHS-POP 2020) assigned to a shelter with `in_area == False`, i.e. outside Kreis Euskirchen and Landkreis Ahrweiler. Also: the same for all residents of the two districts (`sentAwayAll`), town residents placed (`townPlaced`), share of town trips over 30 min (`townOver30Share`), Johan's minutes in zone 246 (`johanMin` flow-weighted, `johanMainMin` to his largest-flow shelter; walk + drive).
Each draw runs the model's own assignment: a capacity-limited transport LP (minimise person-time, HiGHS, as `evac.assign`) on the pairs "200 fastest dry shelters per zone within 1 h on open roads + 4 km/h walk to the nearest open road (max 2 km)". Closures are fixed (July 2021 'any'); shelters that are wet in any flood map are excluded, as in the tool.

## Rebuilding the model from the bundle, and validation
The bundle holds only the display road network (33,652 of 85,852 edges; no residential minor roads, no one-way flags, geometry simplified to 3 m), so the routing cannot be copied exactly. What is reproduced, checked in `mc_results.json` under `validation`:

| Check (nominal set) | Mine | Bundle |
|---|---|---|
| Set A: town sent outside | 8,643 | 8,645 |
| Set B: town sent outside | 0 | 0 |
| Set A / B: town placed | 14,841.5 | 14,841.2 / 14,841.5 |
| Set A / B: people placed (all zones) | 25,559 | 25,559 |
| Set A: people over 30 min | 5,624 | 5,639 |
| Set B: people over 30 min | 159 | 159 |
| Set A / B: mean time, min | 22.4 / 10.6 | 22.7 / 10.8 |
| Set A / B: town share over 30 min | 0.348 / 0.0003 | 0.349 / 0.0003 |
| Set A / B: Johan's largest-flow trip, min | 28.25 / 2.38 | 28.25 / 2.38 |
| Capacity function vs `shelters[].cap` | max 1 person | footprint is rounded to whole m2 in the bundle; 2,802 of 3,144 shelters exact |

Why the earlier prototype differed on set A: with the display network alone (road times x 1.00, no anchoring) set A strands 972 residents (no route within 1 h) and sends 7,422 of the town outside (-14 %); set B was already exact. The display network lacks minor roads, so routed times are on average 6 % longer than the tool's (mean ratio 1.06 on the 902 pairs the tool used) and the tool's matching of neighbouring zones competes differently. Two documented fixes, both fitted on the nominal sets only: (1) all routed times x 1.06; (2) the pairs the tool itself used for each set are added with the tool's own time if shorter ("anchor": 41 pairs for A, 3 for B). Known remaining gaps: mean time 0.2-0.3 min (1-3 %) below the bundle, people over 30 min -0.3 % (A). Because the anchors are the tool's own optimal plan, the nominal reproduction is partly by construction; the draws away from the nominal sets rely on my rebuilt times, which carry roughly +-10 % pair-level noise (5th-95th percentile of mine/bundle time ratio 0.89-1.17 before calibration). This noise is not part of the interval.
Tagged OSM building levels are not in the bundle: they are recovered per building as the integer that reproduces both `cap` values (542 buildings have a tagged level; 342 differ by 1 person from rounding).

## Parameters (sampled independently)
Sources are in `STATS_RESEARCH.md` (secondary sources not re-read; open before the pitch).

| Parameter | Distribution (low / mode / high) | Status |
|---|---|---|
| m2 per person | triangular 3.5 / 4.0 / 5.5 | sourced: DRK RLP pocket card 4.0 m2 per bed + 1.5 day room; Sphere 3.5 (secondary) |
| usable share of floor area | triangular 0.40 / 0.55 / 0.70 | **judgement / not sourced for this region** (DIN 277 net-to-gross proxy 0.60-0.70 is for offices and housing) |
| cap per building | uniform 500 to 1500 | judgement (the limits of sets A and B) |
| extended buildings (kindergartens, churches, chapels, hotels) included | Bernoulli 0.5 | judgement; tier switch, so the 200-nearest list is rebuilt for each case |
| default floors of untagged buildings | 1 or 2, p 0.5 | judgement; sets A and B use 1 and 2 (churches always 1). Added by me, not in the brief; it is the source of much of the A-B gap |
| population factor | triangular 0.85 / 1.00 / 1.15 | judgement anchored on GHS-POP local MAPE 5-12 % (Calka and Bielecka 2020, other countries) |
| shelter-seeking share, **variant fixed1** | 1.0 (model's present assumption) | assumption of the tool, not an estimate |
| shelter-seeking share, **variant research** | displaced share tri 0.34 / 0.40 / 1.0 x share needing public shelter tri 0.05 / 0.10 / 0.25 | **judgement / not sourced for this region**: 34 % evacuated (Rocha Silva et al. 2025, NHESS); 10-20 % rule is a US hurricane planning convention |
| shelter-seeking share, **variant wide** | triangular 0.10 / 0.35 / 1.0 (share of all residents) | provisional judgement, deliberately wide |

Not sampled: closures, speeds, road network, flood extent, snapping, shelter list, 1-h and 200-shelter limits, walk speed.

## Results (town sent outside, residents; 10th-90th percentile, median)
| Variant | Median | p10 - p90 | p5 - p95 | Draws with 0 sent | Nominal A / B |
|---|---|---|---|---|---|
| fixed1 (everyone needs a shelter) | 3,047 | 379 - 7,028 | 1 - 7,743 | 5 % | 8,643 / 0 |
| wide (share 0.10-1.0) | 0 | 0 - 1,521 | 0 - 2,803 | 68 % | same |
| research (share about 2-25 %) | 0 | 0 - 0 | 0 - 0 | 100 % | same |

Other quantities (fixed1, median, p10-p90): all residents of the two districts sent outside 5,118 (1,299 - 10,167; nominal A 12,004, B 579); town placed 14,865 (13,603 - 16,046); town share over 30 min 7.9 % (0.1 - 20.6 %; A 34.8 %, B 0.03 %); Johan's minutes 14.5 (13.5 - 20.8; A 22.9, B 6.0). Under the research variant Johan's trip is 2.4 min (1.6 - 3.3): with few people seeking shelter the nearest building has room.
Note: the nominal set A (8,643) lies above the fixed1 p95 (7,743): A pairs all pessimistic values (floors 1, no extended tier, 0.4 usable, 5 m2 per person, 500 cap) at once; the draws are independent, so such a corner is rare by construction.

Tornado (fixed1, town sent outside, residents; output at the first / second value; baseline 2,772 = mean of the four binary-switch cases): usable 0.70 / 0.40: 1,548 / 4,719; floors 1 / 2: 4,304 / 1,240; extended no / yes: 4,184 / 1,359; population 0.85 / 1.15: 1,663 / 4,359; m2 per person 3.5 / 5.5: 2,046 / 4,719; cap per building 1500 / 500: 2,770 / 2,923. Spearman with the output (fixed1): extended -0.66, floors -0.61, usable -0.29, m2pp +0.28, population +0.23, cap -0.05. Full per-quantity tornado and Spearman values (including the other variants) are in `mc_results.json`. With the seeking share sampled (wide), the share is the dominant driver (Spearman +0.61, tornado 0 to 2,772).

## What the interval means
A model range under parameter uncertainty, not a validated prediction interval. Structural errors are not included: OSM completeness and the display network, free-flow speeds, missing traffic, closures, GHS-POP spatial allocation, who actually goes to a shelter, and correlation between inputs (a severe event raises demand and removes usable buildings; independent draws understate the tails). There is no observed 2021 shelter-occupancy record to validate against.
Reading: the 8,645 headline is the pessimistic corner of the tool, not a central estimate; with everyone needing a shelter the range is 0.4k to 7.0k (10th-90th); with shelter-seeking shares in the planning range the outflow is zero.

## Suggested one-line wording for the slide
"Residents of Bad Neuenahr-Ahrweiler sent outside the two districts: median about 3,000 (10th-90th percentile 400 to 7,000) if every resident in the flood needs a shelter, 0 in 2 of 3 draws if only 10-100 % do; a model range under parameter uncertainty, not a validated forecast."
Short form for a tile: "Model range, parameter uncertainty only: 0.4k-7.0k (median 3.0k) if everyone needs a shelter; 0 if few do."
