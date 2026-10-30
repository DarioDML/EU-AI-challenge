/* Slide 5 (s4, after the message slide) · How it helps Anna (5 steps · 3:05-4:20). A guided demo of the policy tool (policy-tool/) in four moves:
   0 Anna's question · 1 where is the risk (region view, Schleiden ringed) · 2 who gets a shelter (Schleiden, Decide)
   · 3 what each home hears (Alert, the tool's phone magnified) · 4 Anna's answer.
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
    script: 'Johan needs one answer. Anna needs one for a whole border region. ' +
      'This is our policy tool, built for her. Anna coordinates flood crises across the Belgian, Dutch and German border. ' +
      'Her question: would we be better prepared if 2021 returned tomorrow? ' +
      `First, where is the risk? The tool replays the 2021 flood across her region. Schleiden is the most exposed area: ${FIG.homes} homes stood in the water. ` +
      'Second, is there a shelter for everyone? The tool matches every home to the nearest safe school, sports hall or community building that still has room. ' +
      `${FIG.placed} percent get a place. But only ${FIG.walk} percent can walk there; most others need transport, and ${FIG.noPlace} percent have no place at all. ` +
      'Third, what does each home hear? Not just danger, but where to go, and that a place is waiting. Plain text, so it reaches any phone. ' +
      'So our answer to Anna: ready on paper, not yet in practice. Her first step: one shelter register across the border, so every alert can name a shelter.',
    notes: [
      `Schleiden, default plan: ${FIG.homes} homes in the mapped 2021 flood (Copernicus EMS × GHS-OBAT, checked against the team reference table); ${FIG.placed} % of the estimated residents get a shelter place within 5 km, ${FIG.walk} % within walking distance (2 km).`,
      'Residents are a GHS-POP 2020 estimate (2,139 to 5,233 depending on the method); the percentages use the building-weighted estimate.',
      'Shelters are OpenStreetMap candidates (schools, sports halls, community buildings), not designated shelters; capacity assumes 3.5 m² per person on half the floor area; matching uses straight-line distance.',
      'Cell broadcast reaches every phone in an area, so the zone is split into sectors with one shelter each. The alert on screen is a demo message, not a real alert.',
      'The live tool: policy-tool/index.html (or the Vercel deploy). View 2 steps through Detect to Johan; any home on the map shows its own alert.',
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
      <p class="lead">homes in the 2021 flood in Schleiden, her most exposed area.</p>
    </div>
    <div class="s4-say" data-b="2" data-b-out="3">
      <p class="kicker">02 · A shelter for everyone?</p>
      <div class="s4-stat"><b class="num">${FIG.placed}<small>%</small></b><span>get a safe place with room</span></div>
      <div class="s4-stat slow"><b class="num">${FIG.walk}<small>%</small></b><span>can walk there</span></div>
    </div>
    <div class="s4-say" data-b="3" data-b-out="4">
      <p class="kicker">03 · What does each home hear?</p>
      <p class="s4-quote">Not just “danger”: where to go, and that a place is waiting.</p>
    </div>
    <div class="s4-say" data-b="4">
      <p class="kicker">Anna’s answer</p>
      <p class="s4-answer">Ready on paper.<br>Not yet in practice.</p>
      <p class="lead">First step: one shelter register across the border, named in every alert.</p>
    </div>

    <figure class="s4-browser" data-b="0" aria-label="The policy tool">
      <div class="s4-bar" aria-hidden="true"><i></i><i></i><i></i><span>If 2021 returned tomorrow</span></div>
      <div class="s4-screen">
        <img class="s4-shot region" src="assets/tool/tool-region.jpg" width="1716" height="965" decoding="async"
             alt="Policy tool, region view: the six areas Copernicus mapped in Anna's region, ranked by residents who cannot walk to a shelter">
        <img class="s4-shot decide" src="assets/tool/tool-decide.jpg" width="2288" height="1287" decoding="async"
             alt="Policy tool, Schleiden: every home matched to the nearest safe shelter with room">
        <img class="s4-shot alert" src="assets/tool/tool-alert.jpg" width="1716" height="965" decoding="async"
             alt="Policy tool, Schleiden: lines from homes to their shelters and the alert on a phone">
        <i class="s4-ring map" aria-hidden="true"></i>
        <i class="s4-ring rank" aria-hidden="true"></i>
      </div>
    </figure>
    <img class="s4-phone" src="assets/tool/tool-phone.png" width="540" height="1120" decoding="async"
         alt="The alert from the tool: extreme flood danger; go to your shelter, Sporthalle, 4.1 km, transport will collect you; a place is reserved for your address. Demo message, not a real alert.">

    <p class="src s4-src">Policy tool, default plan, 29 Oct 2026 · Schleiden · homes: EMS 2021 flood × GHS-OBAT · residents: GHS-POP 2020 estimate<br>
      Shelters: OSM candidates, not designated · 3.5 m² per person · ≤ 5 km, walk ≤ 2 km · map © OpenStreetMap · demo alert</p>`;

  Deck.register({
    id: 's4', order: 4, title: 'The policy tool', steps: 5, time: [185, 260],
    notes, html,
  });
})();
