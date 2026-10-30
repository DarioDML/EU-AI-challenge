/* Slide 3 · The map (1:30-2:45). The team's transparent SVG at native size, with routes and callouts
   in the same fitted coordinate system. Dimensions and all overlay geometry come from PITCH.
   Step 0 title + key · 1 flood / jam / Johan pins · 2 route A (set A) + HUD · 3 route B (set B), A becomes a ghost.
   Every number comes from window.PITCH (build_pitch_data.py). The tool flags overloaded roads; it does not
   reroute around them. */
(function () {
  'use strict';
  const P = window.PITCH || {};
  const KA = 'obs2021|any|restrictive', KB = 'obs2021|any|generous';
  const W = (P.screenshot && P.screenshot.w) || 1244, H = (P.screenshot && P.screenshot.h) || 894;
  const VB = [0, 0, W, H];                         // full transparent SVG; never crop or stretch its geography
  const C = P.callouts || {}, JP = (P.johan && P.johan.plans) || {}, PL = P.plans || {};
  const A = JP[KA] || {}, B = JP[KB] || {};
  const oa = A.overlay || {}, ob = B.overlay || {};
  const townA = (PL[KA] && PL[KA].town) || {}, townB = (PL[KB] && PL[KB].town) || {};
  const shA = A.shelter || {}, shB = B.shelter || {};
  // "Flooded roads on his route": the bundle has no count field because build_pitch_data.py stops unless every
  // edge of Johan's route is open (check "johan route avoids closed roads"); a placed route therefore has 0.
  const wet = j => ('closed_on_route' in j ? j.closed_on_route : j.status === 'placed' ? 0 : NaN);

  const num = v => typeof v === 'number' && isFinite(v);
  const fmt = (v, d = 0) => (num(v) ? Deck.fmt(v, d) : '–');
  const xy = (p, dx = 0, dy = 0) => (p ? [p[0] + dx, p[1] + dy] : [NaN, NaN]);
  const at = ([x, y]) => `left:${(x - VB[0]).toFixed(1)}px;top:${(y - VB[1]).toFixed(1)}px`;
  const dPath = pts => (pts && pts.length > 1 ? 'M' + pts.map(p => `${p[0]} ${p[1]}`).join(' L') : '');
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // Pins: anchor on the map feature, leader to an elbow, paper label at the elbow (offsets are layout, not data).
  const F = xy(C.flood && C.flood.px), J = xy(C.jam && C.jam.px), Hm = xy(C.home && C.home.px), K = xy(ob.shelter_px);
  const pins = {
    flood: { a: F, e: xy(F, 14, -165), align: 'ur' },
    jam: { a: J, e: xy(J, 48, 84), align: 'down' },          // down and right of the jam
    home: { a: Hm, e: xy(Hm, -48, -64), align: 'ul' },       // up and left: Johan's home is ~10 px from the jam
    dest: { a: K, e: xy(K, 56, -62), align: 'ur' },
  };
  // route A leaves the frame at the bottom: label it just left of the last point inside the frame
  const inFrame = (oa.path || []).filter(p => p[1] <= VB[1] + VB[3] + 0.5 && p[0] >= VB[0] && p[0] <= VB[0] + VB[2]);
  const exitPt = inFrame.length ? inFrame[inFrame.length - 1] : [NaN, NaN];
  const endAnchor = [exitPt[0] - 56, VB[1] + VB[3] - 38];

  const leader = (k, p) => `<line class="s3-leader s3-leader-${k}" x1="${p.a[0]}" y1="${p.a[1]}" x2="${p.e[0]}" y2="${p.e[1]}"/>`;
  const label = (k, p, inner) => `<div class="s3-anchor a-${p.align}" style="${at(p.e)}"><div class="s3-row"><div class="s3-call s3-call-${k}">${inner}</div></div></div>`;
  const HOUSE = 'M16 6.8 L26 15.8 H23 V24.5 H18.4 V18.6 H13.6 V24.5 H9 V15.8 H6 Z';  // the tool's shelter glyph

  const bundleUtc = ((P.source && P.source.bundle_generated_utc) || '').replace('T', ' ').replace(/:\d\dZ$/, ' UTC');
  // the commit is not in PITCH; it is the one named in the blueprint for this bundle only
  const commit = (P.source && P.source.commit) || ((P.source && P.source.bundle_generated_utc) === '2026-10-30T09:46:28Z' ? '01abbb0' : '');

  const srcLine = ['Smart Shelter System · bundle ' + bundleUtc + (commit ? ` (commit ${commit})` : ''), 'flood: Copernicus EMS EMSR517',
    'residents: GHS-POP 2020 estimate', 'roads © OpenStreetMap contributors',
    'capacity, car share and speeds are assumptions; stress is an indicator, not a forecast'].join(' · ');
  const swatch = inner => `<svg viewBox="0 0 36 18" aria-hidden="true">${inner}</svg>`;

  const html = `
    <h2 class="h2 s3-title" data-b="0">Streets close.<br>Exits overload.</h2>

    <div class="s3-key" data-b="0" aria-label="Key">
      <span>${swatch('<rect x="3" y="3" width="30" height="12" rx="2" fill="rgba(86,180,233,.35)" stroke="#0072B2" stroke-width="1.5"/>')}Flood, July 2021</span>
      <span>${swatch('<path d="M3 9 H33" stroke="#111" stroke-width="2.6" stroke-linecap="round"/>')}Closed road</span>
      <span>${swatch('<path d="M3 9 H11" stroke="#269B4E" stroke-width="4"/><path d="M11 9 H19" stroke="#E4CF2A" stroke-width="4"/><path d="M19 9 H27" stroke="#E17327" stroke-width="4"/><path d="M27 9 H35" stroke="#7A0019" stroke-width="4"/>')}Road stress, model</span>
    </div>

    <div class="s3-hud">
      <div class="s3-chip glass" data-b="2"><span class="chip-a">Core public buildings only</span><span class="chip-b">+ Extended buildings</span></div>
      <div class="s3-tile glass" data-b="2"><span class="t-l">Johan's trip<small class="s3-time-note">Model, free-flow</small></span><span class="t-v"><b class="mono num v-trip">0.0</b><small>min</small></span></div>
      <div class="s3-tile glass" data-b="2"><span class="t-l">Closed roads on driving route</span><span class="t-v"><b class="mono num v-wet">0</b></span></div>
      <div class="s3-tile glass" data-b="2"><span class="t-l">Town residents sent to other districts</span><span class="t-v"><b class="mono num v-out">0</b></span></div>
    </div>

    <div class="s3-map">
      <div class="s3-art">
        <img class="s3-base" width="${W}" height="${H}" alt="The tool's map of ${esc(P.town && P.town.name)}: the July 2021 flood in blue, closed roads dark, open roads coloured by modelled stress">
        <svg class="s3-ov" viewBox="${VB.join(' ')}" width="${W}" height="${H}" aria-hidden="true">
          <defs><filter id="s3-glow" filterUnits="userSpaceOnUse" x="${VB[0]}" y="${VB[1]}" width="${VB[2]}" height="${VB[3]}"><feGaussianBlur stdDeviation="5"/></filter></defs>
          <g class="s3-route s3-ra"><path class="ra-case" d="${dPath(oa.path)}"/><path class="ra-line" d="${dPath(oa.path)}"/></g>
          <g class="s3-route s3-rb"><path class="rb-glow" d="${dPath(ob.path)}" filter="url(#s3-glow)"/><path class="rb-case" d="${dPath(ob.path)}"/><path class="rb-line" d="${dPath(ob.path)}"/></g>
          <g class="s3-pin s3-pin-flood">${leader('flood', pins.flood)}<circle class="s3-dot dot-flood" cx="${F[0]}" cy="${F[1]}" r="7"/></g>
          <g class="s3-pin s3-pin-jam">${leader('jam', pins.jam)}<circle class="s3-dot dot-jam" cx="${J[0]}" cy="${J[1]}" r="7"/></g>
          <g class="s3-pin s3-pin-dest">${leader('dest', pins.dest)}
            <g class="s3-dot dot-dest"><g transform="translate(${K[0] - 12} ${K[1] - 12}) scale(0.75)"><circle cx="16" cy="16" r="15"/><path d="${HOUSE}"/></g></g></g>
          <g class="s3-pin s3-pin-home">${leader('home', pins.home)}
            <circle class="s3-ping" cx="${Hm[0]}" cy="${Hm[1]}" r="9"/><circle class="s3-dot dot-home" cx="${Hm[0]}" cy="${Hm[1]}" r="8"/></g>
        </svg>
      </div>

      ${label('flood', pins.flood, `<b class="mono num">${fmt(C.flood && C.flood.closed_km_town)}</b> km of streets closed`)}
      ${label('jam', pins.jam, `<b class="mono num">${fmt(C.jam && C.jam.ratio, 1)}×</b> road capacity<small class="mono">${esc(C.jam && C.jam.road)} · model</small>`)}
      ${label('home', pins.home, 'Johan')}
      ${label('dest', pins.dest, esc(shB.title))}
      <div class="s3-anchor a-l" style="${at(endAnchor)}"><div class="s3-row"><div class="s3-call glass s3-end">${esc(shA.town)} · <b class="mono num">${fmt(A.total_min)}</b> min
        <svg class="s3-arrow" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4 L12 12 M12 5 V12 H5"/></svg></div></div></div>
    </div>
    <p class="src s3-src">${esc(srcLine)}</p>`;

  // speaker notes (html-slides format, plain text): script = the words said aloud, steps 0-3 in order
  const town = (P.town && P.town.name) || '', road = (C.jam && C.jam.road) || '';
  const viaJam = (A.via || []).includes(road);
  const lower = s => String(s || '').toLowerCase();
  const assume = (P.source && P.source.assumptions) || {};
  const capJam = (assume.road_capacity_veh_per_h || {})[C.jam && C.jam.road_class];
  const veh = assume.vehicles || {};
  const setLabel = id => ((P.sets || []).find(s => s.id === id) || {}).label || id;
  const notes = {
    title: 'The map',
    script:
      `${town}, July 2021, in our tool. Blue is the flood Copernicus mapped; every dark street is closed. ` +
      `${fmt(C.flood && C.flood.closed_km_town)} kilometres of the town's streets touch the flood, so the roads that stay open carry the routed residents. ` +
      `On ${road}, the routed traffic would reach ${fmt(C.jam && C.jam.ratio, 1)} times an assumed road capacity. ` +
      'Road stress is a model indicator, not a traffic forecast. Johan lives right here. ' +
      `With core public buildings only, Johan is sent to a ${lower(shA.title)} in ${shA.town || ''}: ${fmt(A.total_min, 1)} minutes, ` +
      `with no flooded road on the way${viaJam ? `, but through the overloaded ${road}` : ''}. ` +
      `${fmt(townA.outside)} residents of the town are sent to other districts. The tool does not yet reroute around jams; it flags them. ` +
      `Add extended buildings, such as kindergartens, and Johan reaches the ${lower(shB.title)} on ${shB.where || ''} in ${fmt(B.total_min, 1)} minutes; ` +
      `${townB.outside === 0 ? 'no resident of the town is' : `${fmt(townB.outside)} residents of the town are`} sent to another district. ` +
      'Same flood, same roads: what changes is which buildings count as shelters, and how much room we assume per person. ' +
      'Trip minutes are model free-flow times, with no congestion.',
    notes: [
      `Base map: the tool's full-analysis map of ${town}, July 2021 flood (Copernicus EMS EMSR517), assumption set A; overlays come from the same bundle (${bundleUtc}).`,
      `${fmt(C.flood && C.flood.closed_km_town)} km = length of the town's roads that touch the 2021 flood. ${fmt(C.jam && C.jam.ratio, 1)}× = ${fmt(C.jam && C.jam.people)} people routed on ${road}, as vehicles per hour ` +
        `(${fmt(veh.car_share * 100)} % by car, ${fmt(veh.persons_per_car)} per car, ${fmt(veh.evacuation_window_h)} h window), over an assumed ${fmt(capJam)} vehicles per hour for a ${String((C.jam && C.jam.road_class) || '').replace('_', ' ')}.`,
      'Road stress is an indicator, not a forecast, and it is not fed back into the routes: the tool flags jams; it does not reroute around them.',
      `${setLabel('restrictive')}; ${setLabel('generous')}. They are alternative assumptions, not lower and upper bounds.`,
      `Johan is fictional; his zone, his street (${(P.johan && P.johan.street) || ''}) and both routes are the model's, and neither route uses a closed road.`,
    ],
  };

  function setDrawn(p, shown) {
    const len = p.getTotalLength();
    p.style.transition = 'none';
    p.style.strokeDasharray = `${len} ${len}`;
    p.style.strokeDashoffset = shown ? 0 : len;
  }

  Deck.register({
    id: 's3', order: 3, title: 'The map', steps: 4, time: [90, 165], notes, html,

    mount(el, P2, D) {
      D.mapSrc(el.querySelector('.s3-base'));
      el.querySelectorAll('.s3-leader').forEach(l => l.style.setProperty('--len', `${Math.ceil(l.getTotalLength()) + 1}px`));
      el.querySelectorAll('.s3-route path').forEach(p => setDrawn(p, false));
    },

    step(el, n, dir) {
      const D = Deck, fwd = dir > 0;
      const ra = el.querySelectorAll('.s3-ra path'), rb = el.querySelectorAll('.s3-rb path');
      // route A (set A): drawn in on the forward build of step 2, otherwise shown or hidden at once
      if (n < 2) ra.forEach(p => setDrawn(p, false));
      else if (n === 2 && fwd) ra.forEach(p => D.draw(p, { duration: 950 }));
      else ra.forEach(p => setDrawn(p, true));
      // route B (set B) at step 3; going back to step 2 restores step 2 exactly
      if (n < 3) rb.forEach(p => setDrawn(p, false));
      else if (fwd) rb.forEach(p => D.draw(p, { duration: 700, delay: 120 }));
      else rb.forEach(p => setDrawn(p, true));
      // HUD: set A values at step 2, set B values at step 3
      const val = (a, b) => (n < 2 ? 0 : n < 3 ? a : b);
      const opt = d => ({ decimals: d, duration: fwd && n >= 2 ? 500 : 0 });
      D.tick(el.querySelector('.v-trip'), val(A.total_min, B.total_min), opt(1));
      D.tick(el.querySelector('.v-wet'), val(wet(A), wet(B)), opt(0));
      D.tick(el.querySelector('.v-out'), val(townA.outside, townB.outside), opt(0));
    },
  });
})();
