# Fact-check: slide 05 "The policy tool" (slides/s4-policy.js)

Sources recomputed from origin/main: data-analysis/shelter_alert_*_summary.json (generated 2026-10-29), policy-tool/index.html, q2_evidence.csv, DEMO.md. The six-area region totals exclude de_15 (Ahr, comparison only).

## Claim table

| # | Claim | Step | Source / field | Verdict |
|---|---|---|---|---|
| 1 | 3,360 homes in the 2021 flood in Schleiden | 1 + script + notes | de_18 `homes_in_flood` = 3360 (checks vs reference all true) | OK numerically. WORDING: these are GHS-OBAT residential building points inside the EMS flood, not "homes"/households |
| 2 | Schleiden "most exposed" | 1 | 3,360 of 3,978 region homes (84%); rank 1 by residents who cannot walk (3,580) | OK |
| 3 | 92% get a place (Schleiden) | 2 | 4,819.8 / 5,233.2 = 92.1% | OK. Residents are a GHS-POP 2020 modelled estimate (building-weighted); the area-weighted reference is 2,139 |
| 4 | 32% can walk | 2 | 1,652.7 / 5,233.2 = 31.6% | OK. WORDING: "walk" means within 2 km straight-line |
| 5 | 8% no place at all | script | 413.4 / 5,233.2 = 7.9% | OK |
| 6 | "Most others need transport" | script | 4,819.8 - 1,652.7 = 3,167 = 60% of residents | OK |
| 7 | Screenshot: 94% place, 43% walk | 3 (action.jpg) | Region of 6 areas: 6,056.9 / 6,470.3 = 93.6%; 2,755.9 / 6,470.3 = 42.6% | OK, but it contradicts the 92/32 on steps 1-2 unless said aloud (the notes cover it only for Q&A) |
| 8 | 413 "would get a generic warning, as in 2021" | 3 (screenshot) | 413 = Schleiden's only unplaced count (region total is also 413). "As in 2021" is Q2 desk research, tagged "verify" in the tool | OK for 413; UNSUPPORTED for "as in 2021" unless the Q2 row is verified |
| 9 | Schleiden 3,580 cannot walk | 3 (region + action screenshots) | 5,233.2 - 1,652.7 = 3,580.5 (68%) | OK. Residents, not homes. Risk: 3,360 homes and 3,580 residents appear side by side |
| 10 | Euskirchen-Steinbach dam 115 | 3 (screenshot) | de_08: 275.8 - 161.2 = 114.6 (42%) | OK. Summary name is "Euskirchen-Rheinbach-Steinbachtalsperre"; the tool's label is shorter |
| 11 | Liège 11 | 3 (screenshot) | be_01: 295.4 - 284.7 = 10.7 (4%) | OK |
| 12 | 164 homes in the Liège area | 3 (screenshot) | be_01 `residential_event` = 164 in aoi_metrics.csv | OK. Flagged as under-measured, which is right |
| 13 | 18 schools and care sites | decide.jpg, action.jpg | de_18 `vulnerable_sites_in_flood` = 18 (the region total is 25) | OK, Schleiden only |
| 14 | 6 open questions | action.jpg | q2_evidence.csv: 17 verified / 15 claimed / 6 unknown | OK |
| 15 | Plan assumptions: 3.5 m² per person, 50% usable, 5 km, walk 2 km | src line + screenshots | summary `scenario` block | OK. The "50% usable" is only in the notes and the decide.jpg rule box |
| 16 | "Matches every home to the nearest safe school, sports hall or community building that still has room" | script | Tool logic; shelters are OSM candidates, not designated | WORDING: "safe" means outside the 2021 flood (+50 m) and the EFAS RP500 zone, not a guarantee; "home" should be "residential building" |
| 17 | "Ready on paper" | script, step 3 | 92% placed on capacity from modelled floor area | OK as an opinion. Keep "paper" and name the OSM-candidate limit |
| 18 | Date "29 Oct 2026" on the source line | src | Summary `generated` 2026-10-29 | OK |

## AGENTS.md rule check

- No "damage" is used for exposure on the slide or in the script. "Belgian damage records" is in the notes only, as a request for records. That is OK.
- No "household" is used on the slide. "Homes" stands for OBAT building points. Prefer "residential buildings" in the spoken script.
- Residents are labelled as a GHS-POP estimate on the source line. The spoken "92 percent get a place" does not say "estimated". Add "of residents (modelled)".
- Observed evidence (EMS flood) is mixed with a scenario (EFAS RP500 in the "safe" rule). The decide.jpg rule box shows it; the script does not. That is acceptable.
- The slide never says "Schleiden" next to 92/32 on the screen itself. The kicker is "A shelter for everyone?" and only the src line names Schleiden. A viewer will read the screenshot's 94/43 as the same figures. See fix 1.
- decide.jpg shows a phone with "Samstag, 31. Oktober" and 2G. That is a scenario date. It is not an observed fact.

## Consistency of "Schleiden" vs "Schleiden (3,580)"

Slide text, screenshots and script agree on 3,580 cannot walk, 413 no place and 18 sites. The only gap is that the slide's headline is 92/32 (Schleiden) while the visible box in action.jpg says 94/43 (region). The frozen captures match the default plan in the JSON.

## Johan vs Anna

- s1 puts Johan in Bad Neuenahr-Ahrweiler. In the tool that area is "comparison, outside Anna's region", with 53% placed.
- Anna's region is the six areas Liège, Venlo, Eschweiler, Wassenberg, Schleiden and Euskirchen-Steinbach.
- No other slide mentions Anna, so s4 is her first appearance.
- Risk: the opening "Johan needs one answer. Anna needs one for a whole border region" implies the same place.
- DEMO.md puts Johan in Gemünd (Schleiden). The deck says Ahrweiler. Do not use the DEMO wording.
- The screenshots do not contradict the deck. The region map shows the Ahr as a grey "comparison" dot.
- Bridge, one line: "Johan's Ahr valley lies just outside Anna's region; her most exposed area is Schleiden, the next valley north."
- The Ahr is not "the next valley north" of Schleiden; it is south-east. Use: "Johan's Ahr valley is just outside Anna's region; inside it, the most exposed area is Schleiden."

## Timing

- Window 185-265 s = 80 s for 4 steps.
- The script has about 172 words, which is 79 s at 130 wpm. There is no buffer and no pause for the camera push.
- Cut about 15 words (fix 4).

## Prioritised fixes

1. WORDING / mismatch of 94/43 against 92/32 (step 2-3). Replace the script sentence with: "In her whole region 94 percent get a place and 43 percent can walk; in Schleiden alone, 92 and 32."
   Shorter alternative if time is tight: "Schleiden: 92 percent get a place, only 32 percent can walk."
2. Johan/Anna bridge. Replace the opening with: "Johan's Ahr valley lies just outside Anna's region. Anna coordinates flood crises across the Belgian, Dutch and German border, and her most exposed area is Schleiden."
3. Homes/residents. Replace "${FIG.homes} homes stood in the water" with "${FIG.homes} residential buildings stood in the mapped flood". Replace "matches every home" with "matches every residential building's estimated residents". On the slide, make the lead "residential buildings in the 2021 flood in Schleiden, her most exposed area." If the jury asks about 3,360 against 3,580: homes are buildings, 3,580 are modelled residents.
4. Timing, to free about 15 words. Delete "This is our policy tool, built for her." Delete "Her question: would we be better prepared if 2021 returned tomorrow?" (the slide quote shows it), or trim "the tool replays the 2021 flood across her region".
5. "Safe": say "the nearest school, sports hall or community building outside the 2021 flood that still has room". Add "estimated" before "residents" in the 92/32 sentence. Add "OSM candidates" if time allows.
6. Screenshot caveat "413 ... as in 2021" is a Q2 claim marked "verify". Do not read it aloud. Prefer re-capturing action.jpg after the Q2 row is verified, or crop it.
7. Minor: action.jpg's tab label reads "Zoom in: Liège" while decide.jpg reads "Zoom in: Schleiden". This is harmless but visible. Crop or ignore.
