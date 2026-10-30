/* Slide 5 (s4, after the message slide) · How it helps Anna (4 steps · 3:05-4:25). A guided demo of the policy tool (policy-tool/):
   0 Anna's question · 1 where is the risk (region view, Schleiden ringed) · 2 who gets a shelter (Schleiden, Decide)
   · 3 Anna's answer (view 3, the camera pushes into the tool's "one thing Anna can do first").
   The phone alert is slide 3, so this slide shows none. The deck has no other policy-ask slide: step 3 carries it.
   The screens are headless-Chrome captures of the tool at 1600 × 900, default plan, saved in assets/tool/. */
(function () {
  'use strict';

  /* Schleiden (de_18), default plan: data-analysis/shelter_alert_de_18_summary.json (generated 29 Oct 2026).
     placed = residents_placed / residents_in_flood_building_weighted = 4,819.8 / 5,233.2;
     walk = residents_placed_within_walk / the same = 1,652.7 / 5,233.2; noPlace = residents_unplaced / the same = 413.4 / 5,233.2.
     The tool shows the same values. */
  const FIG = { homes: '3,360', placed: 92, walk: 32, noPlace: 8 };

  const notes = {
    title: 'How it helps Anna',
    script: 'Johan’s Ahr valley is just outside Anna’s region. Anna coordinates flood crises across the Belgian, Dutch and German border. ' +
      'Her question: would we be better prepared if 2021 returned tomorrow? First, where is the risk? ' +
      `Schleiden is her most exposed area: ${FIG.homes} residential buildings stood in the 2021 flood. ` +
      'Second, is there a shelter for everyone? The tool matches every home to the nearest safe building that still has room. ' +
      `${FIG.placed} percent of estimated residents get a place, but only ${FIG.walk} percent can walk there, and ${FIG.noPlace} percent have no place at all. ` +
      'Across all six areas it is 94 and 43 percent. So our answer: ready on paper, not yet in practice. ' +
      'Anna’s next actions: one cross-border register of shelters with their capacity, so every flood alert names a shelter, starting in Schleiden. ' +
      'Then plan transport where people cannot walk, and get Belgian damage records for the Vesdre.',
    notes: [
      `Schleiden, default plan: ${FIG.homes} residential buildings in the mapped 2021 flood (Copernicus EMS × GHS-OBAT, checked against the team reference table); ${FIG.placed} % of the estimated residents get a shelter place within 5 km, ${FIG.walk} % within walking distance (2 km).`,
      'Residents are a GHS-POP 2020 estimate (2,139 to 5,233 depending on the method); the percentages use the building-weighted estimate.',
      'Shelters are OpenStreetMap candidates (schools, sports halls, community buildings), not designated shelters; capacity assumes 3.5 m² per person on half the floor area; matching uses straight-line distance.',
      `If asked: the tool’s box says 94 % and 43 % for all six areas in her region; build 2 says ${FIG.placed} % and ${FIG.walk} % for Schleiden alone.`,
      'Step 3 gives Anna’s next actions in three lines; the tool’s view 3 has the detail (spoken, not shown): who registers (each municipality, one shared format), who sends (crisis centres via BE-Alert, NL-Alert, Cell Broadcast), and Belgian damage records for the Vesdre, which the European data under-measures.',
      'The live tool: policy-tool/index.html (or the Vercel deploy). View 3 also stress-tests the plan: space per person, furthest shelter, shelter types.',
    ],
  };

  const html = `
    <h2 class="h2 s4-title" data-b="0">How it helps Anna.</h2>

    <div class="s4-say" data-b="0" data-b-out="1">
      <p class="kicker s4-who">Anna · crisis coordinator<br>Belgium · Netherlands · Germany</p>
      <p class="s4-quote">“Would we be better prepared if 2021 returned tomorrow?”</p>
    </div>
    <div class="s4-say" data-b="1" data-b-out="2">
      <p class="kicker">01 · Where is the risk?</p>
      <div class="s4-big num">${FIG.homes}</div>
      <p class="lead">residential buildings in Schleiden’s 2021 flood.</p>
    </div>
    <div class="s4-say" data-b="2" data-b-out="3">
      <p class="kicker">02 · A shelter for everyone?</p>
      <div class="s4-stat"><b class="num">${FIG.placed}<small>%</small></b><span>of estimated residents get a place</span></div>
      <div class="s4-stat slow"><b class="num">${FIG.walk}<small>%</small></b><span>can walk there</span></div>
    </div>
    <div class="s4-say s4-act" data-b="3">
      <p class="kicker">03 · Anna’s next actions</p>
      <ol class="s4-steps">
        <li><span class="n mono">1</span>One cross-border shelter register.</li>
        <li><span class="n mono">2</span>Every flood alert names a shelter.</li>
        <li><span class="n mono">3</span>Start in Schleiden.</li>
      </ol>
    </div>

    <figure class="s4-browser" data-b="0" aria-label="The policy tool">
      <div class="s4-bar" aria-hidden="true"><i></i><i></i><i></i><span>If 2021 returned tomorrow</span></div>
      <div class="s4-screen">
        <img class="s4-shot region" src="assets/tool/tool-region.jpg" width="1716" height="965" decoding="async"
             alt="Policy tool, region view: the six areas Copernicus mapped in Anna's region, ranked by residents who cannot walk to a shelter">
        <img class="s4-shot decide" src="assets/tool/tool-decide-map.jpg" width="1246" height="802" decoding="async"
             alt="Policy tool, Schleiden: every home matched to the nearest safe shelter with room">
        <i class="s4-ring map" aria-hidden="true"></i>
        <i class="s4-ring rank" aria-hidden="true"></i>
      </div>
    </figure>

    <p class="src s4-src">Policy tool, default plan, 29 Oct 2026 · Schleiden · buildings: EMS 2021 flood × GHS-OBAT · residents: GHS-POP 2020 estimate<br>
      Shelters: OSM candidates, not designated · 3.5 m² per person · ≤ 5 km, walk ≤ 2 km · map © OpenStreetMap</p>`;

  Deck.register({
    id: 's4', order: 4, title: 'The policy tool', steps: 4, time: [185, 265],
    notes, html,
  });
})();
