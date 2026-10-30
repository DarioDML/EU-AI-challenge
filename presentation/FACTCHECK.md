> Final style-pass correction: the earlier arithmetic verdict on 60/33 dots below does not validate combining different respondent groups. The final opening uses independent grids for 29%, 85% and 46%, and labels the geographic/response denominators. The 29% RP non-warning share is not used to derive counts for the combined-state warned sample. The source is Thieken et al. (2023), DOI 10.5194/nhess-23-973-2023, abstract. This file otherwise records the earlier content audit, including unresolved team-brief claims.

# Fact-check and timekeeping (30 Oct 2026, 12:45-12:55 local; read-only pass on slides s1-s5 as of that time)

Sources: `pitch-data.js` (bundle generated 2026-10-30T09:46Z), `PITCH_BLUEPRINT.md` s.7-8, `slides/s1..s5.js`. External checks: Thieken abstract (nhess.copernicus.org/articles/23/973/2023/), web search for WMO/JRC.

## 1. Claim table

| # | Claim | Slide/step | Source | Verdict |
|---|---|---|---|---|
| 1 | n = 1,315 online survey | S1 step 1 src, script | Thieken abstract: "Data from an online survey (n=1315)" | OK |
| 2 | 29% RP no warning (35% NRW) | S1 step 1, src | Abstract: "35 % of the respondents from NW and 29 % from RP did not receive any warning" | OK |
| 3 | 85% of those warned did not expect severe flooding | S1 step 2 | Abstract: "Of those who were warned, 85 % did not expect very severe flooding" | OK |
| 4 | 46% "didn't know what to do" | S1 step 2, script | Abstract: "46 % reported a lack of situational knowledge on protective behaviour". Abstract does not state the denominator (warned or all) | WORDING |
| 5 | "Of the 71 who did [get a warning]" | S1 script, step-2 headline "Of the 71 warned" | 100 - 29 = 71 per 100 respondents (RP only). Not 71 people | WORDING |
| 6 | Dots: 71 x 0.85 = 60.35 -> 60; 71 x 0.46 = 32.66 -> 33 | S1 waffle | Recomputed | OK (aria-label says 60 and 33; consistent) |
| 7 | "In a survey of 1,315 residents" | S1 script | Respondents were flood-affected people, in two states, not "residents" generally | WORDING |
| 8 | Johan is 11, lives in Bad Neuenahr-Ahrweiler, fictional | S1 | Blueprint s.1; DEMO.md says Gemünd | OK (town conflict still open) |
| 9 | "14 July 2021" kicker, "water came at night" | S1 | Blueprint: night of 14-15 July 2021. Water-at-night is general, not from the tool | OK (generic) |
| 10 | Closed road = touches EMS flood or under EFAS water | S2 script | blueprint s.2; `20_tool_pipeline.py` | OK |
| 11 | "public buildings that still have room" | S2 script | Set A is core public; set B adds extended (kindergartens etc.) | WORDING |
| 12 | "turns the result into a short plain-text alert"; "Cell Broadcast reaches phones in the area, even on 2G" | S2 script, lens 3 | Tool writes demo message text; it does not send anything. Cell Broadcast on 2G is external, unsourced in the deck | WORDING / UNSUPPORTED (external) |
| 13 | "Every route is checked: no closed road" | S2, S3 | `johan route avoids closed roads` check in build script (53 checks, note: blueprint says 52) | OK |
| 14 | 71 km of Bad Neuenahr-Ahrweiler roads touch 2021 flood | S3 step 1 | `callouts.flood.closed_km_town` = 71 | OK |
| 15 | "so the few open exits must carry everyone" | S3 script | No exit count in data; "everyone" is 14,842 in-flood residents of the town in the model | UNSUPPORTED |
| 16 | 3.8x road capacity, Johannisstraße | S3 step 1 | `callouts.jam.ratio` 3.8 (worst_ratio 3.83), 3,830 people, assumed 200 veh/h (living_street) | OK |
| 17 | Johan: Polch school, 28.2 min (A) | S3 step 2 | `johan.plans[obs2021\|any\|restrictive]`: total 28.2 (walk 1.3 + drive 27.0), 37.3 km | OK |
| 18 | 8,645 town residents sent to other districts (A) = 58% of 14,841 | S3 HUD | `plans[A].town.outside` | OK (58% not on slide) |
| 19 | Set B: Kindergarten Vehner Weg 7, 2.4 min, 0 sent out | S3 step 3 | `johan.plans[...generous]` 2.4 min, 0.5 km; `town.outside` 0 | OK |
| 20 | "Same flood, same roads: what changes is which buildings are prepared" (S3, S4) | S3, S4 scripts | Set B also changes capacity assumption 5 -> 3.5 m2 per person | WORDING (overclaim) |
| 21 | Trip times 28.2 / 2.4 min presented as real | S3, S4 | Free-flow speeds, congestion not fed back; Johan's route A runs through the 3.8x road. Times are model minimums | WORDING |
| 22 | 25,559 residents inside 2021 flood; 78% within 30 min (A) | S4 | `within30/to_place` = 19,920/25,559 = 77.9% -> 78 | OK |
| 23 | "Everyone gets a place within the hour, but 5,639 travel > 30 min" | S4 script | `no_place` 0, `over30` 5,639 | OK |
| 24 | 500-year A: no place 4,694; B: 3 | S4 | `rp500` plans | OK |
| 25 | Johan 500-yr: Jünkerath school ~1 h (60.9); Landskroner Festhalle ~3 min (3.2) | S4 | `johan.plans[rp500...]` | OK |
| 26 | Alert text "This route avoids flooded roads" | S4 phone | In rp10/100/500 plans `street_closed` is true and `via` lists Rüstringer Straße (his own closed street; alert drops it from the via list). Walk part to the nearest open road is not a road-checked leg | WORDING |
| 27 | Cross-level comparison (2021 vs EFAS levels) | S4 | 2021 uses closure `any` (touches), EFAS uses `wet`; EMS covers only the mapped area; to_place 25,559 (2021) < 30,012 (500-yr), 15,091 (10-yr) | WORDING (not like-for-like; not stated) |
| 28 | Set A / B "alternative assumption sets, not bounds"; OSM candidates | S4 script, src | Matches blueprint | OK |
| 29 | ~230 lives lost (BE, DE, NL) | S5 | Brief refs [2],[9],[20]. Web: ~184 DE + ~38-43 BE (varies by date; Wikipedia 196 + 39) so ~220-240 is plausible; no NL deaths found | UNSUPPORTED here (plausible; cite a dated source) |
| 30 | EUR 32-53 bn damage | S5 | Not found in a primary source in my search (Wikipedia: USD 54 bn property damage; insured >= EUR 2 bn). Brief refs only | UNSUPPORTED (verify before presenting) |
| 31 | "Early warning pays back about ten times its cost" (WMO 2022) | S5 | Origin is Global Commission on Adaptation 2019 (via WMO). PreventionWeb: limited evidence for 10x; WMO wording varies (9x vs nearly 10x). Script states it as fact, "pays back" | WORDING (say "WMO estimates about tenfold") |
| 32 | "Built only on open EU-wide data" | S5 | Copernicus EMS, EFAS, GHSL, OSM; OSM is not EU-run; Geofabrik extracts | WORDING ("open data, mostly EU-wide") |
| 33 | "so the method can be repeated for other valleys" | S5 | Not tested; no other valley run | WORDING ("could") |
| 34 | Demo date "Saturday 31 October", 06:12 on phone | S4 phone | Cosmetic; implies a 2026 alert; flagged "Demo message" | OK |

Overclaim scan: no "AI", "live", "traffic simulation", "balances traffic" or "designated shelters" appear on slides. Johan fictional is said on S1 and in S3 notes. Set A/B bounds and OSM candidates are said on S4. Not said anywhere in spoken script on S3: that stress is an assumption of capacity (it is, "assumed"). OK.

## 2. Timing (130 words/min)

| Slide | Window | Words | Spoken | Delta |
|---|---|---|---|---|
| 1 | 0:00-0:45 (45 s) | 100 | 46 s | +1 s |
| 2 | 0:45-1:30 (45 s) | 96 | 44 s | -1 s |
| 3 | 1:30-2:45 (75 s) | 149 | 69 s | -6 s |
| 4 | 2:45-4:15 (90 s) | 168 | 78 s | -12 s |
| 5 | 4:15-5:00 (45 s) | 103 | 48 s | +3 s |
| Total | 300 s | 616 | 284 s | -16 s |

Animation build time that the speaker must wait for (not in word counts):
- S1: 29% tick starts 0.95 s after step 1, runs 1.2 s (done ~2.2 s); step 2: 85% done ~2 s, 46% tick starts 2.15 s, done ~3.65 s. Say the 46% line only after ~3.7 s.
- S3: route A draws 1.8 s; route B 0.3 + 1.4 s; HUD ticks 1.1 s. Pause 2 s on each route before talking numbers.
- S4: entry delay 0.32 s + 0.9 s counters; phone slide-in 0.75 s, ETA tick 0.42 + 1.1 s; each slider move 0.9 s. Four slider moves plus the phone eat roughly 8-10 s that the script has room for (-12 s).
- S5: stats tick starts 0.82 s, 1.5 s.

Recommendations: S5 is the only slide over; cut the data sentence ("We built this only on open EU-wide data...") to "Open data only, so any valley can follow." (saves ~8 s, 3 s spare). S3 and S4 have slack; use it for the demo pauses, do not add words. S1: cut "He is 11 and" no; instead drop the sentence "Johan is a fictional character; he stands for residents of flood-prone streets" only if time is tight, but keep the "fictional" word on slide.

## 3. Prioritised fix list

1. WRONG-ish / UNSUPPORTED: `slides/s5-europe.js` script and stat. Current: "the floods cost around 230 lives and 32 to 53 billion euros. Early warning pays back about ten times its cost." Replace: "the floods cost roughly 230 lives and an estimated 32 to 53 billion euros. WMO estimates that early warning can return about ten times its cost." Verify the 32-53 and 230 figures against the brief's refs [2], [9], [20] before presenting; I could not confirm them. Also the src caption: add "estimates".
2. `slides/s1-johan.js` script. Current: "In a survey of 1,315 residents, 29% in Rhineland-Palatinate never got a warning. Of the 71 who did, 85% didn't expect severe flooding, and 46% didn't know what to do." Replace: "In a survey of 1,315 flood-affected people, 29% in Rhineland-Palatinate got no warning. Of those who were warned, 85% didn't expect very severe flooding, and 46% reported a lack of knowledge on how to protect themselves." Slide step 2 headline "Of the 71 warned:" -> "Of those warned:" (keep dots as "per 100 respondents"). Slide label "didn't know what to do" -> "lacked knowledge on what to do".
3. `slides/s3-map.js` script. Current: "so the few open exits must carry everyone." Replace: "so the roads that stay open carry the routed residents." Current: "Same flood, same roads: what changes is which buildings are prepared." Replace: "Same flood, same roads: what changes is which buildings count as shelters, and how much room we assume per person."
4. `slides/s4-policy.js` script. Current: "Same flood, same roads. What changed is the shelter plan." Replace: "Same flood, same roads. What changed is the shelter plan and the space we assume per person." Add after the 78% line (or in notes): "Minutes are model free-flow times, without congestion." Add to `srcLines()` second line: "flood levels use different closure rules and areas (2021: mapped snapshot; EFAS: modelled)".
5. `slides/s2-pipeline.js` script. Current: "to public buildings that still have room". Replace: "to candidate buildings from OpenStreetMap that still have room". Current: "Last, it turns the result into a short plain-text alert". Replace: "Last, it drafts a short plain-text message, written for Cell Broadcast, that answers Johan's three questions." (Cell Broadcast on 2G: keep, but note it is the team's brief claim.)
6. `slides/s4-policy.js` alertText: "This route avoids flooded roads." Consider "This route uses only roads outside the mapped flood after your street." Check with `build_pitch_data.py` whether the closed-road check covers the first leg in `rp*` plans (street_closed true, via lists Rüstringer Straße).
7. `slides/s5-europe.js` line "Built only on open EU-wide data" -> "Built on open data: Copernicus EMS, EFAS, GHSL, OpenStreetMap" and script "so the method can be repeated for other valleys" -> "so it could be repeated for other valleys".
8. `PITCH_BLUEPRINT.md` s.8: "52 checks" vs `pitch-data.js` `checks: 53` (cosmetic).
9. Open: Johan's town (Gemünd vs Bad Neuenahr-Ahrweiler) as per blueprint s.9.
