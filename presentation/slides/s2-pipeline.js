/* Slide 2 · How it works (0:45-1:30). Three stages in columns, joined by gold pulses:
   flood + roads -> match + route -> Johan's alert.
   Lens 1 is a transparent crop of the tool's map around PITCH.callouts.flood.px (source pixels).
   Wording rule (blueprint s.2): the engine matches people to buildings with room and routes on roads that are
   not flooded. Never call it "AI"; never say it balances or reroutes traffic. */
(function () {
  'use strict';
  const LENS = 300, ZOOM = 1.6;

  // Lens 2 is a schematic, not data: one 500 m zone of residents (navy dots, Johan gold) linked to two shelter
  // badges drawn like the tool's "battery" (pink disc, magenta fill rising with the share of places taken).
  const HOUSE = 'M16 6.8 L26 15.8 H23 V24.5 H18.4 V18.6 H13.6 V24.5 H9 V15.8 H6 Z';   // the tool's house glyph, 32-unit badge
  const BADGE_K = 2.3;                                                                // 32 units -> 74 px
  const badges = { a: { x: 226, y: 100, fill: 1 }, b: { x: 226, y: 200, fill: 0.55 } }; // a: full, b: room left
  const homes = [[60, 122, 'a'], [90, 112, 'a'], [114, 136, 'a'], [62, 158, 'a'], [80, 190, 'b'], [106, 174, 'j']];

  const link = ([x, y, to]) => {
    const b = badges[to === 'j' ? 'b' : to], bx = b.x - 16 * BADGE_K * 0.9, by = b.y;
    const d = `M${x} ${y} C${x + 56} ${y} ${bx - 50} ${by} ${bx} ${by}`;
    const casing = to === 'j' ? `<path class="s2-link-casing" d="${d}"/>` : '';
    return `${casing}<path class="s2-link${to === 'j' ? ' is-johan' : ''}" d="${d}"/>`;
  };
  const badge = (id, { x, y, fill }) => `
    <g class="s2-badge s2-badge-${id}" transform="translate(${x - 16 * BADGE_K} ${y - 16 * BADGE_K}) scale(${BADGE_K})">
      <circle class="s2-badge-outline" cx="16" cy="16" r="15.4"/>
      <circle class="s2-badge-base" cx="16" cy="16" r="13.2"/>
      <g clip-path="url(#s2-badge-clip)"><rect class="s2-fill" x="0" y="2.8" width="32" height="26.4" style="--f:${fill}"/></g>
      <circle class="s2-badge-rim" cx="16" cy="16" r="13.2" stroke-width="${fill >= 0.99 ? 1.4 : 0.8}"/>
      <path class="s2-badge-house" d="${HOUSE}"/>
    </g>`;

  const lens2 = `
    <svg class="s2-svg" viewBox="0 0 ${LENS} ${LENS}" aria-hidden="true">
      <defs><clipPath id="s2-badge-clip"><circle cx="16" cy="16" r="13.2"/></clipPath></defs>
      <rect class="s2-zone" x="40" y="94" width="92" height="116" rx="3"/>
      ${homes.map(link).join('')}
      ${homes.map(([x, y, to]) => `<circle class="s2-home${to === 'j' ? ' is-johan' : ''}" cx="${x}" cy="${y}" r="${to === 'j' ? 7 : 5.5}"/>`).join('')}
      ${badge('a', badges.a)}${badge('b', badges.b)}
    </svg>`;

  // Lens 3: a minimal phone; EU blue keeps the third answer readable on paper.
  const line = (i, y, w1, w2) => `
    <g class="s2-ans s2-ans-${i}" style="--d:${120 + 100 * i}ms">
      <text x="106" y="${y + 5}" class="s2-ans-n">${i}</text>
      <rect class="s2-bar" x="122" y="${y - 4}" width="${w1}" height="7" rx="1"/>
      <rect class="s2-bar" x="122" y="${y + 9}" width="${w2}" height="7" rx="1"/>
    </g>`;
  const lens3 = `
    <svg class="s2-svg" viewBox="0 0 ${LENS} ${LENS}" aria-hidden="true">
      <rect class="s2-phone" x="88" y="34" width="124" height="232" rx="17"/>
      <rect class="s2-island" x="130" y="46" width="40" height="11" rx="5.5"/>
      <text class="s2-net" x="196" y="55" text-anchor="end">2G</text>
      <rect class="s2-card" x="98" y="80" width="104" height="150" rx="3"/>
      ${line(1, 104, 64, 44)}${line(2, 148, 58, 36)}${line(3, 192, 66, 50)}
    </svg>`;

  // column heads (number + rule) are always on the slide, so step 0 is never two thirds empty; lens and caption build in
  const stage = (n, cls, inner, name, sub, micro) => `
    <figure class="s2-fig s2-fig-${n}">
      <div class="s2-stage-head"><span class="s2-n mono" aria-hidden="true">0${n}</span><span class="s2-stage-rule" aria-hidden="true"></span></div>
      <div class="s2-lens ${cls}" data-b="${n - 1}">${inner}</div>
      <figcaption data-b="${n - 1}" data-stagger="110" data-stagger-delay="200">
        <b class="s2-name" data-stagger-item>${name}</b>
        <span class="s2-sub" data-stagger-item><i aria-hidden="true">→</i> ${sub}</span>
        <span class="s2-micro mono" data-stagger-item>${micro}</span>
      </figcaption>
    </figure>`;

  const connector = n => `<div class="s2-conn s2-conn-${n}" aria-hidden="true"><span class="s2-rail"></span></div>`;

  // speaker notes (html-slides format, plain text): script = the words said aloud, steps 0-2 in order
  const P = window.PITCH || {}, src = P.source || {}, assume = src.assumptions || {};
  const efas = (P.levels || []).filter(l => l.id !== 'obs2021').map(l => String(l.label).split(' ')[0]);
  const notes = {
    title: 'How it works',
    script:
      'The Smart Shelter System starts from the flood map. Any road that touches the flood Copernicus mapped in July 2021, ' +
      'or lies under modelled EFAS water, is closed. Next, it matches residents (GHS-POP estimates) to OpenStreetMap candidate buildings ' +
      'with room, and routes each group on open roads. ' +
      'Last, it drafts a short plain-text message, written for Cell Broadcast, that answers Johan\'s three questions. It ' +
      'supports official warnings and evacuation decisions; it does not replace them.',
    notes: [
      `Closed road: touches the July 2021 flood (Copernicus EMS EMSR517) or lies under modelled EFAS water${efas.length ? ` (${efas.join(', ')} floods)` : ''}.`,
      `Residents: ${src.population || 'GHS-POP 2020 modelled estimate'}.`,
      `Room: ${(P.sets || []).map(s => s.label).join('; ')}. Capacity = floor area × usable share ÷ m² per person.`,
      `Route: walk${assume.walk_kmh ? ` at ${Deck.fmt(assume.walk_kmh)} km/h` : ''} to the nearest open road, then the fastest path on open roads. Road stress is flagged, not fed back into the routes: no traffic simulation, no rerouting around jams.`,
      'Alert: plain text for Cell Broadcast, which also works on 2G; it supports, and does not replace, official warnings and evacuation decisions.',
    ],
  };

  Deck.register({
    id: 's2', order: 2, title: 'How it works', steps: 3, time: [45, 80],
    notes,
    html: `
      <h2 class="h2 s2-title" data-b="0">From flood map to one message.</h2>
      ${stage(1, 's2-lens-map', '<img class="s2-map" alt="Crop of the tool\'s map of Bad Neuenahr-Ahrweiler: the July 2021 flood in blue, closed roads dark">',
        'Flood + roads', 'closed roads', 'Copernicus EMS · EFAS · OpenStreetMap')}
      ${connector(1)}
      ${stage(2, 's2-lens-match', lens2, 'Match + route', 'shelter with room', 'GHS-POP · building capacity · open roads')}
      ${connector(2)}
      ${stage(3, 's2-lens-alert', lens3, 'Johan\'s alert', 'three plain-text answers', 'Cell Broadcast · works on 2G')}
      <p class="src s2-src">Supports, and does not replace, official warnings and evacuation decisions.</p>`,

    mount(el, P, D) {
      // Lens 1: source dimensions and callout coordinates are one contract, including SVG refits.
      const img = el.querySelector('.s2-map');
      const W = Number(P.screenshot && P.screenshot.w), H = Number(P.screenshot && P.screenshot.h);
      const [fx, fy] = (P.callouts && P.callouts.flood && P.callouts.flood.px) || [];
      if (![W, H, fx, fy].every(Number.isFinite) || W <= 0 || H <= 0) {
        throw new Error('Slide 2 requires map dimensions and a flood callout from PITCH.');
      }
      // The map never uses transform: scale (the browser would rasterise at the base size and upscale it). The zoom is
      // the image's real size and position, so the vector map is re-drawn sharp at every frame; the flood callout stays centred.
      const box = z => ({ width: `${W * z}px`, height: `${H * z}px`, left: `${LENS / 2 - fx * z}px`, top: `${LENS / 2 - fy * z}px` });
      Object.assign(img.style, box(ZOOM));
      D.mapSrc(img);
      // slow push-in on entry: 1.10 x -> 1 x of the final zoom, the engine's spring, 2.4 s (size and position only)
      document.addEventListener('deck:enter', e => {
        if (e.detail.id !== 's2' || D.reduced || typeof img.animate !== 'function') return;
        img.getAnimations().forEach(a => a.cancel());
        img.animate([box(ZOOM * 1.1), box(ZOOM)], { duration: 2400, delay: 100, easing: D.SPRING });
      });
      // lens 2: links draw in with stroke-dashoffset (CSS reads --len)
      el.querySelectorAll('.s2-link, .s2-link-casing').forEach(p => p.style.setProperty('--len', `${Math.ceil(p.getTotalLength()) + 1}px`));
    },
  });
})();
