/* Slide 2 · How it works (0:45-1:30). Three lenses on one line, joined by gold pulses:
   flood + roads -> match + route -> Johan's alert.
   Lens 1 is a real crop of the tool's map around PITCH.callouts.flood.px (image pixels).
   Wording rule (blueprint s.2): the engine matches people to buildings with room and routes on roads that are
   not flooded. Never call it "AI"; never say it balances or reroutes traffic. */
(function () {
  'use strict';
  const LENS = 300, ZOOM = 1.6;

  // Lens 2 is a schematic, not data: one 500 m zone of residents (white dots, Johan gold) linked to two shelter
  // badges drawn like the tool's "battery" (pink disc, magenta fill rising with the share of places taken).
  const HOUSE = 'M16 6.8 L26 15.8 H23 V24.5 H18.4 V18.6 H13.6 V24.5 H9 V15.8 H6 Z';   // the tool's house glyph, 32-unit badge
  const BADGE_K = 2.3;                                                                // 32 units -> 74 px
  const badges = { a: { x: 226, y: 100, fill: 1 }, b: { x: 226, y: 200, fill: 0.55 } }; // a: full, b: room left
  const homes = [[60, 122, 'a'], [90, 112, 'a'], [114, 136, 'a'], [62, 158, 'a'], [80, 190, 'b'], [106, 174, 'j']];

  const link = ([x, y, to]) => {
    const b = badges[to === 'j' ? 'b' : to], bx = b.x - 16 * BADGE_K * 0.9, by = b.y;
    return `<path class="s2-link${to === 'j' ? ' is-johan' : ''}" d="M${x} ${y} C${x + 56} ${y} ${bx - 50} ${by} ${bx} ${by}"/>`;
  };
  const badge = (id, { x, y, fill }) => `
    <g class="s2-badge s2-badge-${id}" transform="translate(${x - 16 * BADGE_K} ${y - 16 * BADGE_K}) scale(${BADGE_K})">
      <circle cx="16" cy="16" r="15.4" fill="none" stroke="rgba(255,255,255,.9)" stroke-width="1.2"/>
      <circle cx="16" cy="16" r="13.2" fill="#fbe3ee"/>
      <g clip-path="url(#s2-badge-clip)"><rect class="s2-fill" x="0" y="2.8" width="32" height="26.4" fill="#C2185B" style="--f:${fill}"/></g>
      <circle cx="16" cy="16" r="13.2" fill="none" stroke="#12000A" stroke-width="${fill >= 0.99 ? 3 : 2}"/>
      <path d="${HOUSE}" fill="#fff" stroke="#12000A" stroke-width="1"/>
    </g>`;

  const lens2 = `
    <svg class="s2-svg" viewBox="0 0 ${LENS} ${LENS}" aria-hidden="true">
      <defs><clipPath id="s2-badge-clip"><circle cx="16" cy="16" r="13.2"/></clipPath></defs>
      <rect class="s2-zone" x="40" y="94" width="92" height="116" rx="12"/>
      ${homes.map(link).join('')}
      ${homes.map(([x, y, to]) => `<circle class="s2-home${to === 'j' ? ' is-johan' : ''}" cx="${x}" cy="${y}" r="${to === 'j' ? 7 : 5.5}"/>`).join('')}
      ${badge('a', badges.a)}${badge('b', badges.b)}
    </svg>`;

  // Lens 3: a minimal phone with the alert's three answers as numbered lines (3 = where to go, in Johan's gold).
  const line = (i, y, w1, w2) => `
    <g class="s2-ans s2-ans-${i}" style="--d:${250 + 300 * i}ms">
      <text x="106" y="${y + 5}" class="s2-ans-n">${i}</text>
      <rect class="s2-bar" x="122" y="${y - 4}" width="${w1}" height="7" rx="3.5"/>
      <rect class="s2-bar" x="122" y="${y + 9}" width="${w2}" height="7" rx="3.5"/>
    </g>`;
  const lens3 = `
    <svg class="s2-svg" viewBox="0 0 ${LENS} ${LENS}" aria-hidden="true">
      <rect class="s2-phone" x="88" y="34" width="124" height="232" rx="26"/>
      <rect class="s2-island" x="130" y="46" width="40" height="11" rx="5.5"/>
      <text class="s2-net" x="196" y="55" text-anchor="end">2G</text>
      <rect class="s2-card" x="98" y="80" width="104" height="150" rx="14"/>
      ${line(1, 104, 64, 44)}${line(2, 148, 58, 36)}${line(3, 192, 66, 50)}
    </svg>`;

  const stage = (n, cls, inner, name, sub, micro) => `
    <figure class="s2-fig s2-fig-${n}" data-b="${n - 1}">
      <div class="s2-lens ${cls}">${inner}</div>
      <figcaption>
        <span class="s2-n mono">0${n}</span>
        <b class="s2-name">${name}</b>
        <span class="s2-sub"><i aria-hidden="true">→</i> ${sub}</span>
        <span class="s2-micro mono">${micro}</span>
      </figcaption>
    </figure>`;

  const pulses = n => `<div class="s2-conn s2-conn-${n}" aria-hidden="true"><span class="s2-rail"></span><i style="--k:0"></i><i style="--k:1"></i><i style="--k:2"></i></div>`;

  // speaker notes (html-slides format, plain text): script = the words said aloud, steps 0-2 in order
  const P = window.PITCH || {}, src = P.source || {}, assume = src.assumptions || {};
  const efas = (P.levels || []).filter(l => l.id !== 'obs2021').map(l => String(l.label).split(' ')[0]);
  const notes = {
    title: 'How it works',
    script:
      'The Smart Shelter System starts from the flood map. Any road that touches the flood Copernicus mapped in July 2021, ' +
      'or lies under modelled EFAS water, is closed. Next, it matches residents, using GHS-POP estimates, to public buildings ' +
      'that still have room, and routes each group on roads that are not flooded. Every route is checked: no closed road. ' +
      'Last, it turns the result into a short plain-text alert that answers Johan\'s three questions. Cell Broadcast reaches ' +
      'phones in the area, even on 2G. It supports official warnings and evacuation decisions; it does not replace them.',
    notes: [
      `Closed road: touches the July 2021 flood (Copernicus EMS EMSR517) or lies under modelled EFAS water${efas.length ? ` (${efas.join(', ')} floods)` : ''}.`,
      `Residents: ${src.population || 'GHS-POP 2020 modelled estimate'}.`,
      `Room: ${(P.sets || []).map(s => s.label).join('; ')}. Capacity = floor area × usable share ÷ m² per person.`,
      `Route: walk${assume.walk_kmh ? ` at ${Deck.fmt(assume.walk_kmh)} km/h` : ''} to the nearest open road, then the fastest path on open roads. Road stress is flagged, not fed back into the routes: no traffic simulation, no rerouting around jams.`,
      'Alert: plain text for Cell Broadcast, which also works on 2G; it supports, and does not replace, official warnings and evacuation decisions.',
    ],
  };

  Deck.register({
    id: 's2', order: 2, title: 'How it works', steps: 3, time: [45, 90],
    notes,
    html: `
      <h2 class="h2 s2-title" data-b="0">From flood map to one clear message.</h2>
      ${stage(1, 's2-lens-map', '<img class="s2-map" alt="Crop of the tool\'s map of Bad Neuenahr-Ahrweiler: the July 2021 flood in blue, closed streets dashed">',
        'Flood + roads', 'closed roads', 'Copernicus EMS · EFAS · OpenStreetMap')}
      ${pulses(1)}
      ${stage(2, 's2-lens-match', lens2, 'Match + route', 'a shelter with room', 'GHS-POP · building capacity · open roads')}
      ${pulses(2)}
      ${stage(3, 's2-lens-alert', lens3, 'Johan\'s alert', 'three answers, plain text', 'Cell Broadcast · works on 2G')}
      <p class="src s2-src">Supports, and does not replace, official warnings and evacuation decisions.</p>`,

    mount(el, P, D) {
      // lens 1: the screenshot at ZOOM x, the flood callout point at the lens centre
      const img = el.querySelector('.s2-map');
      const W = (P.screenshot && P.screenshot.w) || 1524, H = (P.screenshot && P.screenshot.h) || 919;
      const [fx, fy] = (P.callouts && P.callouts.flood && P.callouts.flood.px) || [W / 2, H / 2];
      Object.assign(img.style, {
        width: `${W * ZOOM}px`, height: `${H * ZOOM}px`,
        left: `${LENS / 2 - fx * ZOOM}px`, top: `${LENS / 2 - fy * ZOOM}px`,
        transformOrigin: `${fx * ZOOM}px ${fy * ZOOM}px`,
      });
      D.mapSrc(img);
      // lens 2: links draw in with stroke-dashoffset (CSS reads --len)
      el.querySelectorAll('.s2-link').forEach(p => p.style.setProperty('--len', `${Math.ceil(p.getTotalLength()) + 1}px`));
    },
  });
})();
