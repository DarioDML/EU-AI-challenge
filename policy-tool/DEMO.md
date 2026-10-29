# 5-minute demo script

One presenter drives (arrow keys), one speaks, or one person does both. About 650 spoken words. Numbers are the tool's default plan as of 29 Oct; if the data is rebuilt, check them on screen.

## Before you start

- Run `python -m http.server 8765 --directory policy-tool`, open <http://localhost:8765> and press F11 (full screen). Check the map tiles load (needs internet).
- Reload the page right before presenting: it resets the plan to the default. Do not click "Pool shelters" during a rehearsal and forget to reload.
- Keep the mouse off the map when scrolling the page: the wheel zooms the map.
- Fallback without a server: open `deliverables/shelter-alert-tool.html` (run `python scripts/bundle_policy_tool.py` first).

## 0:00 – 0:40 · Step 1 Detect

**Screen:** step 1, dashed EMS area on the map, empty phone.

> "This is Anna. She coordinates flood crises across borders, between Belgium, Germany and the Netherlands. In July 2021 the forecasts saw the flood coming days ahead. The signal travelled down a chain: European forecasters, national weather services, regional flood centres, crisis centres, mayors, and finally the public. But the warnings people got mostly said *danger*. They did not say *where to go*." *(Researchers: confirm the last claim with the Q2 sources.)*

> "Our idea: every flood alert names a shelter. Let me show you, using the real 2021 flood in the Ahr valley."

**Click:** →

## 0:40 – 1:30 · Step 2 Interpret

**Screen:** blue flood, homes appear; orange homes are outside the EFAS 500-year zone.

> "In blue is the flood Copernicus mapped in July 2021. We treat it as if it had been forecast perfectly. Inside it are 6,975 homes, about 15,000 to 21,000 people. We give a range because the population grid can be spread over buildings in two ways."

> "Now the orange dots. Only 48 % of these homes were inside Europe's 500-year flood hazard map. So a plan built on hazard maps alone would have left half of these homes out. The alert zone has to come from the live forecast."

**Click:** →

## 1:30 – 2:30 · Step 3 Decide

**Screen:** shelters (green circles), homes green / light green / red, KPI tiles.

> "This is the core of our idea. It works like a ride-hailing app: each home is matched to the nearest shelter that still has room. Shelters are schools, sports halls and community buildings from OpenStreetMap. They must lie outside the 2021 flood and outside the 500-year zone. Their capacity comes from the building size in the JRC building data, at 3.5 square metres per person. It runs in under a tenth of a second."

> "Result: 53 % of residents get a reserved place within 5 km, and only 29 % can walk there. 9,771 people get no place nearby. And the purple dots are 31 schools and care sites inside the flood. They cannot be shelters; they need their own evacuation."

**Click:** →

## 2:30 – 3:15 · Step 4 Alert

**Screen:** lines from homes to shelters.

**Click:** any **green** home in Bad Neuenahr. The phone shows the shelter, the distance and "a place is reserved for your address".

> "This is what that household receives: not just *danger*, but *go here, this far, there is a place for you*." *(read the shelter name and distance off the phone)*

**Click:** FR, then NL on the phone.

> "The same message in every language of the region, because floods don't stop at borders. Technically, cell broadcast reaches every phone in an area, so the zone is split into sectors with one shelter each. Registered addresses and the alert apps can carry the exact assignment."

**Click:** →

## 3:15 – 4:15 · Step 5 Johan

**Screen:** zoom to Dernau; Johan's phone says "No shelter named".

> "Meet Johan, 11, in the village of Dernau. With local shelters only, 86 of the 549 homes in Dernau get a place. Johan's family gets a generic warning, exactly like in 2021."

**Click:** "Pool shelters up to 10 km".

> "Now Anna pools shelters across municipal borders. Every home in Dernau gets a place, and coverage in the valley rises from 53 to 74 %. Johan, his parents and his school all receive the same shelter, so the family meets there instead of searching for each other."

## 4:15 – 5:00 · Anna's action

**Scroll** to the dark box "The one thing Anna can do".

> "So our recommendation to Anna is one action: set up one shared, cross-border register of shelters with their capacity, and connect it to BE-Alert, NL-Alert and NINA before the next flood season. The matching technology already works on open European data. What is missing is the register."

> "We are open about the limits: our distances are straight lines, capacity is estimated from building size, and resident numbers are modelled. They are all listed at the bottom of the tool, and each one is a next step, not a blocker. Thank you."

## Likely jury questions

| Question | Answer |
|---|---|
| Can we trust the resident numbers? | They are estimates from GHS-POP 2020: 15,337 when the population grid is shared by area, 20,895 when it is shared by building floor area. The home count (6,975) and the EFAS counts are checked against the team's reference table; the build stops if they differ. |
| Your lines cross the river / Johan is sent up-valley to Altenahr. | Yes: we use straight-line distance. A real plan needs road routing, bridge closures and transport. The matching stays the same; only the distance changes. |
| Can cell broadcast target one home? | No. It reaches all phones in an area, so we split the zone into sectors with one shelter each. Exact per-home messages need registered addresses (BE-Alert offers registration) or the alert app. *(verify the BE-Alert detail)* |
| Is the 2021 extent a forecast? | No. We use it as a perfect-forecast stand-in, to test the shelter side. The 48 % finding shows why static hazard maps are not enough to define the zone. |
| Why the Ahr and not Belgium? | The data is strongest there: 6,975 homes mapped. Annex 2 warns that the building data undercounts Belgian flood areas. The script takes any EMS area (`--aoi`); the Ahr is the first one we built. |
| Where did AI help, and where did it go wrong? | See the AI sheet. AI wrote the data build and the tool; we verified them with the reference-table checks and by matching the browser result to the Python result. A review caught a double count of schools and care sites (66 reported, 31 distinct), which we fixed. |
