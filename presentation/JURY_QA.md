# Jury Q&A: Johan's way out (after the 5-minute pitch)

Spoken answers, 40-60 words each. Numbers are the "May say" claims of `PITCH_BLUEPRINT.md` section 8. Sources read: blueprint, `ideas/05-shelter-planning/README.md` and `AI_USE.md`, and, from `origin/team1-smart-shelter-map`, `DESIGN.md`, `README.md` and `LIMITS` in `20_tool_pipeline.py` (the `ideas/05-smart-shelter-map/` folder is not in the current branch). Annex 3 and 4 PDFs were read. Jury criteria (Annex 4): evidence, policy usefulness, clarity, responsible AI use. "NEEDS TEAM INPUT" = the repo cannot confirm it; fill in or cut before presenting.

**Do not say:** live or real-time; traffic simulation or "balances traffic"; "AI engine" or "AI predicts"; official, designated or verified-safe shelters or routes; set A and B as lower and upper bounds; Johan is real; "everyone is safe" or "zero risk"; exact head counts.

---

**1. Why Bad Neuenahr-Ahrweiler?**
"It is where the 2021 flood is best documented: the richest Copernicus mapping, thousands of graded buildings, and a town where we can see streets close. The tool covers Kreis Euskirchen and Landkreis Ahrweiler; Bad Neuenahr-Ahrweiler is our worked example, with 14,842 residents inside the mapped flood." (Align Johan's town: the Gemünd line in `policy-tool/DEMO.md` must not be spoken.)

**2. Is this real-time data?**
"No. It is a planning tool for before the night. It uses the July 2021 satellite flood map and modelled 10, 100 and 500-year floods, plus 2020 population. Nothing is live. It supports, and does not replace, official warnings and evacuation decisions by the authorities."

**3. Does it simulate traffic?**
"No. It routes around closed, flooded roads at free-flow speeds and respects shelter capacity. Separately, it flags roads where routed people exceed an assumed capacity, for example Johannisstraße at 3.8 times. That is an indicator, not a forecast, and it is not fed back into the routes."

**4. Where did you use AI, and where was it wrong?**
"Claude Code wrote most of the code and drafts; we set the rules and checked every number against the tables. It went wrong in documented ways: it treated modelled population as a head count, treated 2024 buildings as 2020, and counted missing flood data as dry. Checks caught these. Our AI sheet lists them." NEEDS TEAM INPUT: confirm this list also holds for the tool pipeline (the documented errors above come from the shelter-planning AI sheet, `AI_USE.md`) and add any tool-specific error.

**5. How did you assume shelter capacity, and why do set A and B differ?**
"Capacity is floor area times a usable share, divided by space per person. Set A uses core public buildings at 5 square metres each; set B adds extended buildings at 3.5. They are alternative assumption sets, not bounds, and have no verified source. The gap shows that capacity assumptions, not flood size, drive the result: 77.9 versus 99.4 percent within 30 minutes."

**6. What about privacy?**
"No personal data is used or sent to any AI. Residents are GHS-POP estimates spread over building points, so we know zones, not people or households. A building point is not a household. The map shows 500-metre zones. Johan is fictional, and the alert on screen is a labelled demo message."

**7. Who is the responsible public actor, and what exact action?**
"Crisis authorities in Belgium, Germany and the Netherlands: publish a list of flood shelters, make every alert answer three questions, and drill the route at school. For the Ahr, the natural addressee is the Landkreis Ahrweiler civil-protection authority." NEEDS TEAM INPUT: the brief names no single actor and the legal competence was flagged "to verify" in the repo; confirm before naming it.

**8. What does it cost, and is it feasible?**
"We have not costed it, and we will not invent a number. The data are open EU sources, the tool is a static page, and the alert uses existing cell broadcast. The real work is the authority designating and checking buildings. We would call that a pilot for one district." NEEDS TEAM INPUT: any cost or staffing estimate, and who maintains the data.

**9. You say Belgium, Germany, Netherlands. Does it work across borders?**
"The method does, because it uses only EU-wide open data: Copernicus EMS, EFAS, GHSL and OpenStreetMap. But our analysis so far covers Germany only: Kreis Euskirchen and Landkreis Ahrweiler. We have not run Belgium or the Netherlands, and shelter rules differ by country. That is our first next step."

**10. Why a 2G cell-broadcast alert?**
"Because the 2021 warning chain broke, and cell broadcast reaches phones in an area without an app, a number or mobile data. Plain text works on 2G, so it can work when networks are degraded. Our message is a demo in that format and is not a live alert." NEEDS TEAM INPUT: cite a source for the 2G and network-resilience claim, and for Germany's cell-broadcast rollout, before the jury; neither is in the repo.

**11. What are the limits of OpenStreetMap buildings?**
"OSM tells us a building exists, and its name or type if mapped. It does not tell us if it is open, owned by the municipality, or has toilets or power. So these are candidates, not designated shelters. Building points also come from 2024, so houses destroyed in 2021 and not rebuilt are missing."

**12. What happens if the shelters are full?**
"The tool sends overflow to the next-nearest building with room. In set A with the 500-year flood, 4,694 people find no place within an hour by road; in set B only 3. Allowing two hours cuts that to 1,179. So it is a reach gap, and it tells authorities where to add capacity."

**13. Why trust GHS-POP, and how do you validate?**
"We do not trust it as a count. It is a modelled 2020 grid, so we read counts as minimum, rounded estimates. Recounting four ways gave 10,600 to 13,500 for the 100-year zone, not one number. Validation so far: automated checks and a comparison with the 2021 flood and EMS damage. We have not tested routes on the ground." NEEDS TEAM INPUT: whether the manual QGIS and Excel checks (AI sheet, "Checks to do by hand") were done; if not, say "still to do".

**14. Equity and next steps: what about people who cannot walk?**
"A real gap. The tool assumes everyone is warned, can walk up to 2 kilometres, and leaves together. That excludes people with limited mobility, without a car, or in care homes. Next steps: add accessibility and care sites, verify buildings with the authority, extend to Belgium and the Netherlands, and test with real residents."

---

## Likely follow-ups, one line each
- "Why is the 2021 total different from the model?" The modelled floods miss places the real flood hit (14,841 observed versus 4,631 in the 500-year model for Bad Neuenahr-Ahrweiler); EFAS does not model the Ahr well, so we show 2021 observed and the model separately.
- "Why 28 minutes for Johan in A?" Under A no core public building nearby has room, so he goes to the school in Polch, 37 km; under B the kindergarten at Vehner Weg 7 is 0.5 km. It shows the assumptions matter, not that either is right.
- "Is the shelter safe?" We only use buildings dry in every flood map we have; that is not a safety certification.
