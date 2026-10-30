# 5-minute demo script

One presenter drives, one speaks (or one person does both). About 650 spoken words. Numbers are the tool's default plan as of 29 Oct; if data or Q2 evidence changes, read them off the screen.

## Before you start

- Open the deployed site (or run `python -m http.server 8765 --directory policy-tool` and open <http://localhost:8765>), press F11. Check the map tiles load (needs internet).
- Reload right before presenting: it resets the plan sliders.
- Keep the mouse off the map when scrolling: the wheel zooms the map.
- Researchers: fill `q2_evidence.csv` first, otherwise Q2 shows only question marks.

## 0:00 – 1:30 · View 1 · Region

**Screen:** region map with six areas, the Q1–Q4 list on the left, the ranking on the right.

> "This is Anna. She coordinates flood crises across Liège and Limburg, Dutch Limburg and Region Aachen. This morning's bulletin warns of heavy rain on the Meuse and Vesdre. Ministers ask her one question: after everything we've done since 2021, would we be better prepared if that flood returned tomorrow?"

> "We answered it for the areas that Copernicus mapped in her region. **Q1:** *(read homes and residents from the Q1 line)* sat in the water. **Q2:** this is what the public record shows has changed since 2021 — green is verified, orange is announced, grey is what we could not verify." *(Read the Q2 line.)*

> "**Q3:** if it came back tomorrow, there is a safe shelter place within 5 km for almost everyone *(read the % from the Q3 line)*. But far fewer could *walk* there *(read the walk %)*. And *(read the number)* schools and care sites sit in the water themselves."

> "And one honest warning: the Vesdre was among the worst-hit valleys, yet the European data shows only 164 homes in the Liège area flood. Belgium is under-measured — we flag that rather than hide it."

**Click:** "Zoom into Schleiden →".

## 1:30 – 3:30 · View 2 · Schleiden

**Screen:** step 2, Schleiden flood, homes coloured.

> "Schleiden is the most exposed area: 3,360 homes in the mapped flood, about 2,100 to 5,200 people, along the Urft and Olef."

**Press →** (step 3, Decide).

> "Like a ride-hailing app matching riders to drivers, every home is matched to the nearest safe shelter that still has room — schools, sports halls, community buildings, on either side of a border. 92 % get a place. But only 32 % can walk there; the rest need transport in a narrow valley where roads flood first. And 18 schools and care sites are in the water."

**Press →** (step 4, Alert). **Click** a green home near the river.

> "This is what that household receives: not just *danger*, but *go here, this way, a place is reserved for you* — with the walking route street by street, and a warning when part of it flooded in 2021. Plain text only, because cell broadcast must reach old phones on 2G: no map, no link. In German here, and in French or Dutch across the border." *(Click FR, then NL.)*

**Press →** (step 5, Johan).

> "Johan, 11, in Gemünd. His phone, his parents' phones and his school get the same shelter, so the family meets there instead of searching for each other."

## 3:30 – 4:00 · The extreme case

**Click** the area chip "Bad Neuenahr-Ahrweiler (comparison)".

> "For scale, the Ahr valley, just outside Anna's region: 6,975 homes in the water, and only 53 % would find a shelter place within 5 km. That's what a dense valley looks like when the plan is missing."

## 4:00 – 5:00 · View 3 · Anna's action

**Click:** tab "3 · Anna's action".

> "So our answer to Anna: we are better prepared on paper — there is room — but not in practice, because people don't know where to go and many can't get there on foot. One action: build one cross-border register of shelters with their capacity, and make every flood alert name a shelter — BE-Alert, NL-Alert and Cell Broadcast — starting in Schleiden, where most people cannot walk to a shelter. Plan transport where people can't walk. And get Belgian damage records for the Vesdre, because the European data misses it."

> "Our limits are on the page: modelled residents, capacity from building size, straight-line distances. Each one is a next step, not a blocker. Thank you."

## Likely jury questions

| Question | Answer |
|---|---|
| Why these six areas? | They are all the areas Copernicus EMS mapped inside Anna's mandate. Outside them the data says nothing — unknown, not dry. The Ahr is shown only for comparison. |
| Can we trust the resident numbers? | They are estimates from GHS-POP 2020, shown as a range: spread by area or by building floor area. Home counts and EFAS counts are checked against the team's reference table; the build stops if they differ. |
| Why is Liège so small? | Radar images of 15–17 July miss water between buildings, and Annex 2 warns the building data undercounts Belgian flood areas. That is a finding: Belgium needs its own damage records in this assessment. |
| Your lines cross rivers. | The matching uses straight-line distance. The route in the alert follows real streets (OpenStreetMap) and says how much of it flooded in 2021, but it does not yet avoid flooded streets or closed bridges. A real plan needs flood-aware routing and transport. |
| Can cell broadcast target one home? | No. It reaches all phones in an area, so the zone is split into sectors with one shelter each. Exact per-home messages need registered addresses or the alert app. *(verify the BE-Alert registration detail)* |
| Where did AI help, and where did it go wrong? | See the AI sheet. AI wrote the data build and the tool; we checked every area against the reference table and matched the browser result to the Python result. Reviews caught a double count of schools and care sites (66 → 31 in the Ahr) and cross-border counting that ignored the home's country; both fixed. |
