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
    jam: { a: J, e: xy(J, -12, 84), align: 'down' },          // down and right of the jam
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

  // ranges: the same model under its alternative closure rule and shelter set (PITCH.ranges, build_pitch_data.py); not a statistical interval
  const R = P.ranges || {};
  const dots = n => `<svg class="cdots" viewBox="0 0 26 8" width="30" height="9" aria-hidden="true">${[0, 1, 2].map(i => `<circle cx="${4 + i * 9}" cy="4" r="3" class="${i < n ? 'on' : 'off'}"/>`).join('')}</svg>`;
  const dash = (a, b, d = 0) => `${fmt(a, d)}–${fmt(b, d)}`;
  const RK = R.closed_km_town || {}, RJ = R.jam || {}, RT = R.trip_min || {};
  // residents sent away: Monte Carlo over uncertain inputs (PITCH.ranges.sentAway, stats/mc_results.json), main variant = every resident needs a public shelter;
  // the tile is the same in the route A and route B steps
  const SA = R.sentAway && num(R.sentAway.median) ? R.sentAway : null;
  const srcLine = ['Smart Shelter System · bundle ' + bundleUtc + (commit ? ` (commit ${commit})` : ''), 'flood: Copernicus EMS EMSR517',
    'residents: GHS-POP 2020 estimate', 'roads © OpenStreetMap contributors',
    'capacity, car share, speeds are assumptions; trip minutes are model free-flow times; stress is an indicator, not a forecast',
    'model ranges = same model under the other closure rule (mapped water only vs also flood traces) and shelter set (A vs B), not a statistical interval; dots: ●○○ low, ●●○ medium',
    SA ? `sent away: median of ${fmt(SA.n_draws)} model draws (10–90%: ${dash(SA.p10, SA.p90)}) if all residents in the flood need a public shelter; if only 10–100% seek one: median ${fmt(SA.wide.median)} (${dash(SA.wide.p10, SA.wide.p90)}). Model range under uncertain inputs, not a validated interval` : ''].filter(Boolean).join(' · ');
  const CONF = R.confidence || { closed_km: 1, road_stress: 1, trip: 2, sent_away: 2 };
  const swatch = inner => `<svg viewBox="0 0 36 18" aria-hidden="true">${inner}</svg>`;

  const html = `
    <h2 class="h2 s3-title" data-b="0">Streets close.<br>Exits overload.</h2>

    <div class="s3-key" data-b="0" data-b-out="1" aria-label="Key">
      <span>${swatch('<rect x="3" y="3" width="30" height="12" rx="2" fill="rgba(86,180,233,.35)" stroke="#0072B2" stroke-width="1.5"/>')}Flood</span>
      <span>${swatch('<path d="M3 9 H33" stroke="#111" stroke-width="2.6" stroke-linecap="round"/>')}Closed</span>
      <span>${swatch('<path d="M3 9 H11" stroke="#269B4E" stroke-width="4"/><path d="M11 9 H19" stroke="#E4CF2A" stroke-width="4"/><path d="M19 9 H27" stroke="#E17327" stroke-width="4"/><path d="M27 9 H35" stroke="#7A0019" stroke-width="4"/>')}Stress</span>
    </div>

    <div class="s3-conf" data-b="0" data-b-out="2" aria-label="Confidence"><span>${dots(1)}Low</span><span>${dots(2)}Medium</span></div>

    <div class="s3-hud">
      <div class="s3-chip glass" data-b="2"><span class="chip-a">Core public</span><span class="chip-b">+ Extended</span></div>
      <div class="s3-tile glass" data-b="2"><span class="t-l">Trip<small class="mono t-r">range ${dash(Math.round(RT.lo), Math.round(RT.hi))}</small></span><span class="t-v"><b class="mono num v-trip">0.0</b><small>min</small>${dots(CONF.trip)}</span></div>
      <div class="s3-tile glass" data-b="2"><span class="t-l">Closed roads</span><span class="t-v"><b class="mono num v-wet">0</b></span></div>
      <div class="s3-tile glass" data-b="2"><span class="t-l">Sent away${SA ? `<small class="mono t-r">${dash(SA.p10, SA.p90)}</small>` : ''}</span><span class="t-v"><b class="mono num v-out">${SA ? '~' + fmt(SA.median) : '–'}</b>${SA ? dots(CONF.sent_away) : ''}</span></div>
    </div>

    <div class="s3-map">
      <div class="s3-art">
        <img class="s3-base" width="${W}" height="${H}" alt="The tool's map of ${esc(P.town && P.town.name)}: the July 2021 flood in blue, closed roads dark, open roads coloured by modelled stress">
        <svg class="s3-ov" viewBox="${VB.join(' ')}" width="${W}" height="${H}" aria-hidden="true">
          <defs><filter id="s3-glow" filterUnits="userSpaceOnUse" x="${VB[0]}" y="${VB[1]}" width="${VB[2]}" height="${VB[3]}"><feGaussianBlur stdDeviation="5"/></filter></defs>
          <g class="s3-route s3-ra" data-at="2" data-draw data-draw-lead data-draw-ms="1800" data-draw-ease="cubic-bezier(0.45, 0, 0.2, 1)"><path class="ra-case" d="${dPath(oa.path)}"/><path class="ra-line" d="${dPath(oa.path)}"/></g>
          <g class="s3-route s3-rb" data-at="3" data-draw data-draw-lead data-draw-ms="1400" data-draw-delay="150" data-draw-ease="cubic-bezier(0.45, 0, 0.2, 1)"><path class="rb-glow" d="${dPath(ob.path)}" filter="url(#s3-glow)"/><path class="rb-case" d="${dPath(ob.path)}"/><path class="rb-line" d="${dPath(ob.path)}"/></g>
          <g class="s3-pin s3-pin-flood">${leader('flood', pins.flood)}<circle class="s3-dot dot-flood" cx="${F[0]}" cy="${F[1]}" r="7"/></g>
          <g class="s3-pin s3-pin-jam">${leader('jam', pins.jam)}<circle class="s3-dot dot-jam" cx="${J[0]}" cy="${J[1]}" r="7"/></g>
          <g class="s3-pin s3-pin-dest">${leader('dest', pins.dest)}
            <g class="s3-dot dot-dest"><g transform="translate(${K[0] - 12} ${K[1] - 12}) scale(0.75)"><circle cx="16" cy="16" r="15"/><path d="${HOUSE}"/></g></g></g>
          <g class="s3-pin s3-pin-home">${leader('home', pins.home)}
            <circle class="s3-ping" cx="${Hm[0]}" cy="${Hm[1]}" r="9"/><circle class="s3-ping s3-ping-2" cx="${Hm[0]}" cy="${Hm[1]}" r="9"/><circle class="s3-dot dot-home" cx="${Hm[0]}" cy="${Hm[1]}" r="8"/></g>
        </svg>
      </div>

      ${label('flood', pins.flood, `up to <b class="mono num" data-to="${num(C.flood && C.flood.closed_km_town) ? C.flood.closed_km_town : ''}" data-dec="0">${fmt(C.flood && C.flood.closed_km_town)}</b> km closed${dots(CONF.closed_km)}<small class="mono">${dash(RK.lo, RK.hi)} km</small>`)}
      ${label('jam', pins.jam, `up to <b class="mono num" data-to="${num(C.jam && C.jam.ratio) ? C.jam.ratio : ''}" data-dec="1" data-suf="×">${fmt(C.jam && C.jam.ratio, 1)}×</b> capacity${dots(CONF.road_stress)}<small class="mono"><span>${dash(RJ.lo, RJ.hi, 1)}×</span> <span>model</span></small>`)}
      ${label('home', pins.home, 'Johan')}
      ${label('dest', pins.dest, esc(shB.title))}
      <div class="s3-anchor a-l" style="${at(endAnchor)}"><div class="s3-row"><div class="s3-call glass s3-end">${esc(shA.town)}
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
      `${town}, July 2021. ` +
      `Up to ${fmt(RK.hi)} kilometres of the town's streets touch it, so the roads that stay open carry the routed residents. ` +
      `On ${road} traffic reaches up to ${fmt(RJ.hi, 1)} times an assumed capacity. ` +
      `These are the upper end under our assumptions; with the stricter rule, ${fmt(RK.lo)} kilometres and ${fmt(RJ.lo, 1)} times. ` +
      `Johan goes to a ${lower(shA.title)} in ${shA.town || ''}, ${fmt(A.total_min)} minutes; with extended buildings, ${fmt(B.total_min, 1)}. ` +
      (SA ? `If everyone needed a public shelter, about ${fmt(SA.p10)} to ${fmt(SA.p90)} would be sent to other districts; if only a share seek one, probably none. ` : '') +
      'The tool does not yet reroute around jams; it flags them. ' +
      'Same flood, same roads: what changes is which buildings count as shelters, and how much room we assume per person. ' +
      'Minutes are model free-flow times.',
    notes: [
      `Base map: the tool's full-analysis map of ${town}, July 2021 flood (Copernicus EMS EMSR517), assumption set A; overlays come from the same bundle (${bundleUtc}).`,
      `Ranges are the same model under its alternative closure rule (mapped water only vs also flood traces) and shelter assumption set (A vs B); they are not a statistical interval. The headline numbers are the upper ends: ${dash(RK.lo, RK.hi)} km of closed streets (${fmt(RK.mapped, 1)} km with mapped water only, ${fmt(RK.any, 1)} km with flood traces too); road stress ${dash(RJ.lo, RJ.hi, 1)}× on ${road}.`,
      `${fmt(C.jam && C.jam.ratio, 1)}× = ${fmt(C.jam && C.jam.people)} people routed on ${road}, as vehicles per hour (${fmt(veh.car_share * 100)} % by car, ${fmt(veh.persons_per_car)} per car, ${fmt(veh.evacuation_window_h)} h window), over an assumed ${fmt(capJam)} vehicles per hour for a ${String((C.jam && C.jam.road_class) || '').replace('_', ' ')}. ` +
        `Varying only the traffic assumptions (car share ${dash(...((RJ.envelope || {}).car_share || [0, 0]), 1)}, persons per car ${dash(...((RJ.envelope || {}).persons_per_car || [0, 0]), 1)}, window ${dash(...((RJ.envelope || {}).window_h || [0, 0]), 1)} h; capacity unchanged) gives ${dash((RJ.envelope || {}).lo, (RJ.envelope || {}).hi, 1)}× in plan A.`,
      'Road stress is an indicator, not a forecast, and it is not fed back into the routes: the tool flags jams; it does not reroute around them.',
      `${setLabel('restrictive')}; ${setLabel('generous')}. Johan's trip (${dash(RT.lo, RT.hi, 1)} min under B and A) shows the two sets side by side.`,
      SA ? `The ${fmt(townA.outside)} residents sent away under set A is a pessimistic corner: it assumes every resident in the flood needs a public shelter and set A's strict capacity (core buildings, 5 m² per person). Monte Carlo over uncertain inputs (m² per person, usable share, building tiers, floors, population ±15 %; ${fmt(SA.n_draws)} draws, seed ${SA.seed}): median ${fmt(SA.median)}, 10–90%: ${dash(SA.p10, SA.p90)}; ${fmt(SA.share_zero * 100)} % of draws give zero. If only 10–100% of residents seek a public shelter: median ${fmt(SA.wide.median)} (${dash(SA.wide.p10, SA.wide.p90)}). Several inputs are judgement, not sourced for this region: a model range, not a validated interval.` : '',
      'Confidence dots: one filled = low (model rule and assumptions: closed kilometres, road stress); two = medium (Johan\'s trip).',
      `Johan is fictional; his zone, his street (${(P.johan && P.johan.street) || ''}) and both routes are the model's, and neither route uses a closed road.`,
    ],
  };

  const timers = [];
  Deck.register({
    id: 's3', order: 3, title: 'The map', steps: 4, time: [125, 185], notes, html,

    mount(el, P2, D) {
      D.mapSrc(el.querySelector('.s3-base'));
      el.querySelectorAll('.s3-leader').forEach(l => l.style.setProperty('--len', `${Math.ceil(l.getTotalLength()) + 1}px`));
    },

    step(el, n, dir) {
      const D = Deck, fwd = dir > 0;
      // routes A and B draw themselves: data-draw / data-draw-lead in the markup (js/motion.js), 1.8 s and 1.4 s,
      // with a gold dot riding the tip; going back restores the previous step at once.
      // HUD: set A values at step 2, set B values at step 3 (the numbers run while the route is drawn)
      const val = (a, b) => (n < 2 ? 0 : n < 3 ? a : b);
      const opt = (d, ms) => ({ decimals: d, duration: fwd && n >= 2 ? ms : 0 });
      D.tick(el.querySelector('.v-trip'), val(A.total_min, B.total_min), opt(1, n === 2 ? 1800 : 1400));
      D.tick(el.querySelector('.v-wet'), val(wet(A), wet(B)), opt(0, 600));
      if (SA) D.tick(el.querySelector('.v-out'), n < 2 ? 0 : SA.median, { decimals: 0, prefix: '~', duration: fwd && n === 2 ? 1600 : 0 });   // same at steps 2 and 3: it does not depend on the route
      // pin labels count up once when they appear (step 1); anywhere else they show the final value
      timers.forEach(clearTimeout); timers.length = 0;
      el.querySelectorAll('.s3-call b[data-to]').forEach((b, i) => {
        const to = parseFloat(b.dataset.to);
        if (!isFinite(to)) return;
        const o = { decimals: +b.dataset.dec || 0, suffix: b.dataset.suf || '', duration: 0 };
        if (n === 1 && fwd) {
          D.tick(b, 0, o);
          timers.push(setTimeout(() => D.tick(b, to, { ...o, duration: 1100 }), 260 + 360 * i));
        } else D.tick(b, to, o);
      });
    },
  });
})();
