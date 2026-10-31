# Parameter ranges for the shelter Monte Carlo (Ahr valley, July 2021)

Research date: 2026-10-30. Method: web search plus page/PDF fetches. Quotes are exact where marked "quote"; many search-engine summaries were not re-read in the primary document, and these are tagged **[secondary]**. Anything tagged **[UNVERIFIED]** is a judgement, not a sourced number. Sources not read in full must be opened before the pitch.

Model: `shelter_capacity = usable_share x gross_floor_area / m2_per_person`; demand = `shelter_seeking_share x residents_in_flooded_area x GHS-POP_factor`; outflow = max(0, demand - capacity).

## 1. m2 per person in shelters

| | Low (more space needed per person, worse case) | Central | High (tight) | Distribution |
|---|---|---|---|---|
| Sleeping/accommodation area, m2/person | 4.0 (DRK sleeping) | 4.0 | 3.5 (Sphere) | Triangular(3.5, 4.0, 5.5), where 5.5 = 4.0 sleeping + 1.5 day room (DRK) |

Wording note: for capacity, a LARGER m2/person lowers capacity. Use mode 4.0 as the central value; 3.5 is the optimistic tail, 5.5 the pessimistic tail.

- **DRK Rheinland-Pfalz pocket card, Betreuungsdienst 1/2 (Stand 11.09.2024; the file URL says 05.03.2025)**
  https://bildungsinstitut-rlp.drk.de/fileadmin/downloads/Bereitschaften/Fachdienst_Betreuungsdienst/BtHe_16-16_Taschenkarte_BtD_1_2_-_Stand_05.03.2025.pdf (read directly via pdftotext). Quotes: "Unterbringung 4 m²", "Aufenthalt 1,5 m²" (Richtzahlen: 10/50/100/200 persons -> 40/200/400/800 m2 sleeping and 15/75/150/300 m2 day room); "Sporthalle 2-Feld 968 m² = 242 Betten = 500 Sitzplätze"; "Sporthalle 1-Feld 405 m² = 101 Betten"; "Sporthalle 3-Feld 1.215 m² = 304 Betten"; "Klassenraum normal 60 m² = 15 Betten". The ratios are exactly 4.0 m2 per bed in every case (my calculation). Sanitary planning figures on the same card: WC 5%, washing 20%, showers 5% of the affected. Caveat: these are room areas of a DRK planning card, not gross floor area, and they describe overnight beds, not a legal standard.
- **Sphere:** a secondary source (Shelter Projects, "B01 3point5", https://mail.shelterprojects.org/shelterprojects2011-2012/B01-3point5.pdf) states: "The figure of 3.5m2 per person is often quoted as being the sphere standard for shelter, however, it is only a 'key indicator' under the broader standard of covered living space". Same source: "A covered area of less than 3.5m2 per person may be appropriate to save life and to provide adequate short-term shelter." A Better Shelter document attributes 4.5-5.5 m2 to cold climates or urban settings that include cooking and sanitation. I could not open the Sphere Handbook itself (HTTP 403), so verify the wording in the Shelter and Settlement chapter. **[secondary]**
- **Short-term evacuation halls (about 2 m2):** NOT FOUND in any source. Do not cite it. If used, label it **[UNVERIFIED]** and use only as a stress test, not in the main distribution.
- **BBK/DRK "Betreuungsplatz 500":** Hessian Sonderschutzplan quote (via search summary, PDF not opened, the URL gave 404): "Ein Betreuungsplatz 500 ist für die Betreuung von 500 Personen in üblicher Zusammensetzung von Bevölkerungsanteilen ausgelegt." This sets a site size, not m2/person. **[secondary]**
- Other: EUAA sets 4 m2 minimum per person for asylum collective housing (a different framework; a corroborating order of magnitude only).

## 2. Usable share of gross floor area (schools, halls, community buildings)

| Low | Central | High | Distribution |
|---|---|---|---|
| 0.40 | 0.55 | 0.70 | Triangular(0.40, 0.55, 0.70) **[UNVERIFIED as a shelter-specific number]** |

- No German or international source gave a net/gross ratio for school or sports-hall shelter use. Found only definitions: DIN 277 splits BGF (gross) into NRF (net room area) and KGF (construction area); NUF (use area) excludes Verkehrsfläche (circulation) and Technikfläche. **[secondary, baunetzwissen / bauprofessor]**
- Closest quantitative proxy: TU Wien thesis (Vujicic 2020, https://repositum.tuwien.at/handle/20.500.12708/15291): NUF is "about 60 to 70%" of BGF for office/administration buildings and "about 62 to 76%" for residential. This is not about schools. **[secondary]**
- Why 0.40-0.70: the proxy gives an upper bound near 0.70. Shelter-usable area is smaller still (kitchen, sanitary, storage, staff and first-aid areas, fire routes, corridors that cannot be used for sleeping). The 0.55 centre is a judgement. A sensitivity run is more honest than claiming a sourced value. Suggested sentence: "Usable share is an assumption bracketed by DIN 277 net-to-gross proxies of 0.60-0.70."
- Better still, this parameter and section 1 can be merged: effective gross m2 per person = m2_per_person / usable_share, which gives about 5.7 to 14 m2 gross per person (3.5/0.70 to 5.5/0.40), centre about 7.3 (4.0/0.55). This is my arithmetic.
- Note: the DRK card figures (4.0 m2 per bed in a 968 m2 hall) imply the whole hall floor is used as bed area, i.e. a hall-level share near 1.0 before sanitary and day rooms. A gym is therefore the best case; a mixed school is worse.

## 3. Shelter-seeking share

| Low | Central | High | Distribution |
|---|---|---|---|
| 0.05 | 0.10 | 0.25 | Triangular(0.05, 0.10, 0.25) as share of EVACUATED/DISPLACED people |

Also needed: the share of flooded-area residents who are displaced at all. See the table below.

| Quantity | Value | Source |
|---|---|---|
| Evacuated or rescued, share of Ahr population | about 34% | Rocha Silva et al. 2025, NHESS 25, 1501. Quote (abstract, read directly): "Consequently, only about 34 % of the population evacuated their homes or were rescued." https://nhess.copernicus.org/articles/25/1501/2025/ Caveat: a survey-calibrated agent-based model input, not a shelter count. |
| Had to leave home because of destruction | "Etwas mehr als 40 %" of 516 surveyed Ahr households; 15.2% of them still could not return after a year | KAHR project brochure, summer 2022 survey, https://hochwasser-kahr.de/images/pdf/FlyerIGUuIREUSBroschuere_KAHR_final.pdf (via search summary; the PDF text was not extractable, so check it) **[secondary]** |
| Share of evacuees needing public shelter (planning rule) | 10-20% | Taylor & Francis chapter (author and year not retrieved), https://www.taylorfrancis.com/books/9781439821244/chapters/10.1201%2Fb11954-21 . Quote (via search): "Normally, emergency managers expect that between 10 and 20 percent of the evacuating public will need shelter." A planning convention from US hurricanes, not an empirical flood estimate. |
| Same, "about a quarter" | 25% | 1996 FEMA-prepared exercise (via search): "On the average, about 25% of people displaced by a disaster seek public shelter." **[secondary]** |
| Hurricane survey, Florida | 65% friends/relatives, 15% hotel, 6% community shelter | BEBR, University of Florida, FloridaFocus 1(2) 2005 (via search) **[secondary]** |
| Hurricane Irma, Saint Martin | 3% | Dutch Water Sector page "Lessons learned Hurricane Irma", https://www.dutchwatersector.com/node/1888 **[secondary]** |
| Florida regional plans | public-shelter use about 5-15% of evacuees by zone | Florida regional evacuation studies (Broward, Miami-Dade tables) **[secondary]** |
| Ahr 2021, snapshot | "rund 3.500 Menschen seien in Betreuungseinrichtungen untergebracht" | wetter.de chronicle, quoting a Kreis Ahrweiler tweet, undated: https://www.wetter.de/cms/flutkatastrophe-im-ahrtal-chronik-des-hochwassers-im-juli-2021-was-geschah-wann-4996381.html **[secondary, date unknown]**. Against about 42,000 affected in the Ahr valley (BMI report via DKKV: "Anzahl betroffener Menschen ca. 65.000, davon ca. 42.000 im Landkreis Ahrweiler"), this is about 8% (my arithmetic). Counts a snapshot, and "affected" is not "in the flooded polygon". |

- **Not found:** any DRK or BBK total of persons in Notunterkünfte or Sammelunterkünfte for the Ahr flood; any peer-reviewed split of evacuees between shelter, relatives and hotels for 2021. Thieken et al. 2023 (NHESS 23, 973) and Rocha Silva et al. 2025 do not report where evacuees stayed (checked by page fetch). The 2021 situation also had a COVID twist: Karl Lauterbach said "Massenunterkünfte sind eine Gefahr für die Menschen, denn dort herrscht ein hohes Corona-Ansteckungsrisiko" (Berliner Zeitung live blog, July 2021), i.e. policy pushed people toward hotels and private housing, so 2021 may understate shelter demand in a non-COVID event.
- Suggested structure: `P(shelter) = P(displaced) x P(shelter | displaced)`. P(displaced): triangular(0.34, 0.40, 1.0)? Use 0.34-0.40 as an observed lower range for the 2021 Ahr and 1.0 as the model's conservative worst case. P(shelter | displaced): triangular(0.05, 0.10, 0.25). The all-residents assumption in the base model is the extreme upper tail of this distribution (1.0 x 1.0), which should be shown to the jury as "upper bound, not forecast".

## 4. GHS-POP uncertainty

| Low | Central | High | Distribution |
|---|---|---|---|
| 0.85 | 1.00 | 1.15 | Triangular multiplicative factor on resident count in the flooded area **[judgement, anchored below]** |

- Calka and Bielecka (2020), "GHS-POP Accuracy Assessment: Poland and Portugal Case Study", Remote Sensing 12(7), 1105, https://www.mdpi.com/2072-4292/12/7/1105 (abstract via search, full paper not read). Quote: "At the national level, MAPE ranges from 1.8% to 4.5% for the 250 m and 1 km resolutions of GHS-POP data in Portugal and 1.5% to 1.6%, respectively in Poland. At the local level, however, the error rates range from 4.5% to 5.8% in Poland, for 250 m and 1 km, and 5.7% to 11.6% in Portugal, respectively." Also: "For densely populated regions the GHS-POP underestimates the population number, while for thinly populated regions it overestimates." Caveats: an earlier GHS-POP release; errors are at the LAU/NUTS unit level, not cell or building level; not Germany or the 100 m grid.
- JRC evaluation (Pesaresi et al. 2024, slides at https://www.digitalearth-isde.org/uploadfile/2024/1112/20241112015132926.pdf, read by pdftotext): "GHS-POP achieves higher agreement than WorldPop when compared to authoritative gridded population estimates across 24 countries". The slides give a qualitative ranking only; I found no numeric cell-level relative error for R2023A in Europe. **A cell-level relative error number is [UNVERIFIED].**
- The GHSL dataset page states the product estimates residential population (not daytime or transient), disaggregated from census units. In July 2021 (night of 14 July) residential is the right concept, but tourists and hotel guests are missing.
- German census: Destatis Zensus 2022 (reference 15 May 2022) found about 1.4 million fewer people than the 2011-based Fortschreibung, around -1.6% nationally; regional deviations were larger (e.g. Münster +4.9% instead of the previously assumed +10.1%). **[secondary, via search summaries; open destatis.de/zensus2022 before quoting]**. GHS-POP R2023A is anchored on older census rounds, so a few-percent national bias plus larger local differences is plausible.
- Why +-15%: aggregation to a whole flooded town averages out the cell-level noise; the 5-12% local MAPE in two countries plus a 1.6% national census correction plus the unexplored cell-to-polygon mismatch (flood extent vs cell boundaries, with partial-cell overlap treated by the team) gives a defensible +-15% for a town-sized sum. Say clearly that it is a judgement bracket. Run a +-30% case for single cells or small villages.

## 5. Road-stress indicator (car share, occupancy, time window)

| Parameter | Low | Central | High | Distribution | Status |
|---|---|---|---|---|---|
| Car share of evacuees | 0.60 | 0.80 | 0.90 | Triangular | 0.80 from the Rocha Silva Ahr model; range **[UNVERIFIED]** |
| Persons per car | 1.5 | 2.0 | 3.0 | Triangular | **[UNVERIFIED]**; no source retrieved |
| Evacuation time window | see below | | | scenario, not a distribution | |

- Car share: Rocha Silva et al. 2025, quote: "an evacuation mode fraction of 80 % by vehicle and 20 % on foot". Authors call it calibrated, not an observed survey figure. The text does not state occupancy in the part read (Table 2 and supplement Table S1 were images and were not read).
- Persons per car: the US hurricane surveys (Texas CBHES Harvey report, Louisiana NIMSAT) list occupants per vehicle, but I could not open the figures (404 or only the contents listing). Do not quote a figure. State it as an assumption and test 1.5-3.0.
- Road capacity (German planning): the DRK pocket card lists for traffic jams "Pro km / Spur: ca. 130-140" vehicles. Use this in the stress indicator as vehicle density on a jammed lane (read directly, but the layout of the card is ambiguous about the second entry "Fahrzeuge = ca. 200 Pers."). **[verify on the card]**
- Time window: no sourced evacuation time. Context only: Rocha Silva et al. report that "Only 17.5 % of those affected received a warning with evacuation instructions", and Thieken et al. 2023 report 29% (RLP) and 35% (NRW) of respondents received no warning at all (https://www.uni-potsdam.de/de/nachrichten/detail/2023-03-10-besser-warnen-forschende-untersuchen-flutkatastrophe-2021-aus-sicht-der-betroffenen). The Kreis Ahrweiler order of 14 July 2021 (23:15 update) covered "alle Gebäude im Umkreis von 50 Metern rechts und links der Ahr". So the realistic window was hours in the night, with many people never warned. Present road stress as a scenario (e.g. 2, 6, 12 h) not as a fitted distribution.

## 6. Ahr 2021 qualitative validation

What I could verify:
- 14 July 2021, 23:15 Kreis Ahrweiler update: "Derzeit werden Notunterkünfte eingerichtet." No capacity numbers. https://kreis-ahrweiler.de/update-lagebericht-starkregen-und-hochwasser-an-der-ahr/ (read directly).
- DRK Rheinland-Pfalz Hochwassereinsatz 2021 report (read via pdftotext), https://www.drk-rlp.de/fileadmin/Hochwassereinsatz_2021_Blitzlichter.pdf : "Ein Teil der evakuierten Menschen betreuten die Einsatzkräfte vorübergehend in der Turnhalle." and the Kreisgeschäftsstelle "diente z.B. als Aufenthaltsstelle für evakuierte Senior*innen". Shows that gym use and ad hoc places happened; it is not a capacity analysis. (The text near it may concern a different Landkreis, as the report covers several, so check the context.)
- Courthouse News (2021), via search: "Thousands of evacuees and those made homeless were housed in shelters and strangers' homes." **[secondary]**
- A photo caption (DOCKS Collective) says a hotel at the Nürburgring took in evacuees free of charge. **[secondary, anecdotal]**
- About 3,500 people "in Betreuungseinrichtungen" (see section 3, date unknown).
- Longer-term: 170 "winter homes" (mobile homes) set up, and at Christmas 2021 numerous families still dependent on emergency housing (Volksstimme). **[secondary]**

What I could NOT find: any report that the shelters were over capacity, or that people were bussed to other districts as a planned outflow, or official shelter capacity in the valley. The federal report (BMI, "Bericht zur Hochwasserkatastrophe 2021", March 2022) could not be downloaded (HTTP 400); its Katastrophenhilfe chapter, the RLP Landtag Untersuchungsausschuss Ahr-Flut records and Kreis Ahrweiler's Lage reports are the next place to look. Our "outflow to shelters outside the district" is therefore an unvalidated model output; the only observed fact is that displaced people were spread across shelters, private homes, hotels (including outside the valley) and later mobile homes.

## What we can and cannot claim

Can claim:
- The Monte Carlo propagates **parameter uncertainty** (m2 per person, usable share, shelter-seeking share, GHS-POP error) through a transparent capacity-versus-demand formula, and shows how the outflow number changes across plausible inputs.
- Each input range is anchored where a source exists (4.0 m2/bed DRK, 3.5 m2 Sphere, 10-20% planning rule, 34% evacuated, +-15% from MAPE evidence), and every judgement range is labelled as such.
- The all-residents-need-a-shelter case is a conservative planning bound; the same model shows how far it is from a realistic share.
- The qualitative pattern (shelters set up at night, gyms used, many displaced people in private homes or hotels, long-term housing in mobile homes) matches the documented 2021 events.

Cannot claim:
- That the output is a validated predictive or confidence interval. No observed count of people sheltered in the Ahr valley by shelter, date and capacity was found, so there is nothing to calibrate or test against.
- That the usable-share range (0.40-0.70) is sourced for shelters: it is a bracket from DIN 277 proxies and judgement.
- That the shelter-seeking range transfers from US hurricane evacuations to a German flash flood during COVID. Its centre (10%) rests on a planning convention.
- That GHS-POP error at the building or cell scale is known; only aggregated-unit errors in two other countries were found.
- Any persons-per-car or evacuation-time figure. They are assumptions to be stress-tested.
- Independence: the inputs are probably correlated (a severe event raises both shelter-seeking and the lost share of usable buildings; flooded schools cannot be shelters). Draws assumed independent will understate tails. Use the wording "scenario ranges from parameter uncertainty" in the pitch, not "95% interval".

Suggested one-liner for the jury: "We propagate documented parameter ranges; we do not claim predictive coverage, because no 2021 shelter-occupancy record exists to validate against."

## Open items (to close before the pitch)
1. Sphere Handbook wording for 3.5 m2 (open the handbook).
2. DRK card ambiguity on "Fahrzeuge = ca. 200 Pers." and the traffic figures.
3. BMI report and RLP Landtag Untersuchungsausschuss records for shelter counts and capacity.
4. Persons per car (Texas CBHES Harvey report Table, Louisiana NIMSAT).
5. Destatis Zensus 2022 exact national deviation.
6. Calka and Bielecka full paper (cell-size sections).
