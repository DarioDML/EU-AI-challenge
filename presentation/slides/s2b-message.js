/* Slide · The message (1:20-2:05). The phone from slide 2 zooms in and shows the alert Johan receives (iOS lock
   screen, Cell Broadcast style) with a map of his route. Steps: 0 phone + message, 1 "Am I in danger?" highlights its
   answer, 2 "How serious is it?", 3 "Where should I go?" highlights Go to + route and the route card draws in.
   Every string on the phone comes from PITCH.alert (build_pitch_data.py): the highlights sit on the same lines the
   questions are answered by. The cell-broadcast text is plain text; the map is the citizen view the alert links to. */
(function () {
  'use strict';
  const P = window.PITCH || {};
  const A = P.alert || { lines: {}, crop: { x: 0, y: 0, w: 3, h: 2 }, route: [], home: [0, 0], shelterPx: [0, 0], shelter: {}, via: [] };
  const L = A.lines || {};
  const W = (P.screenshot && P.screenshot.w) || 1244, H = (P.screenshot && P.screenshot.h) || 894;
  const MAP_W = 440, K = MAP_W / A.crop.w, MAP_H = Math.round(A.crop.h * K);   // map px -> card px
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const dPath = pts => (pts && pts.length > 1 ? 'M' + pts.map(p => `${p[0]} ${p[1]}`).join(' L') : '');
  const px = v => (v / K).toFixed(2);                                              // card px -> map px (stroke widths)

  // severity gauge (step 2): residents inside the flood for the four flood levels, assumption set A (to_place); all from PITCH.plans
  const GAUGE = (P.levels || []).map(l => {
    const pl = (P.plans || {})[`${l.id}|${l.closure}|restrictive`] || {};
    return { id: l.id, label: l.id === 'obs2021' ? 'July 2021' : String(l.label).split(' ')[0], v: Number(pl.to_place) };
  }).filter(g => Number.isFinite(g.v));
  const GMAX = Math.max(1, ...GAUGE.map(g => g.v));
  const about = v => Deck.fmt(Math.round(v / 5000) * 5000);                   // "about 25,000": nearest 5,000
  const g21 = GAUGE.find(g => g.id === 'obs2021');
  const QUESTIONS = ['Am I in danger?', 'How serious is it?', 'Where should I go?'];
  const ICON = '<svg viewBox="0 0 24 24" width="25" height="25" aria-hidden="true"><path d="M12 3.5 2.5 20.5h19z" fill="#fff" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/><path d="M12 9.5v5M12 17.4v.2" stroke="#ff3b30" stroke-width="2.2" stroke-linecap="round"/></svg>';
  const HOUSE = 'M16 6.8 L26 15.8 H23 V24.5 H18.4 V18.6 H13.6 V24.5 H9 V15.8 H6 Z';

  const html = `
    <ol class="s2b-qs" aria-label="Johan's three questions">
      ${QUESTIONS.map((q, i) => `<li class="s2b-q s2b-q${i + 1}"><i class="s2b-dot" aria-hidden="true"></i><span class="s2b-n mono">0${i + 1}</span><h2 class="h2">${q}</h2></li>`).join('')}
    </ol>

    ${GAUGE.length ? `<div class="s2b-gauge" aria-label="How serious: residents inside the flood">
      <p class="g-head">About <b class="num">${g21 ? about(g21.v) : ''}</b> residents in the flood area</p>
      <ul class="g-rows">
        ${GAUGE.map((g, i) => `<li class="g-row${g.id === 'obs2021' ? ' is-now' : ''}" style="--i:${i};--w:${(g.v / GMAX).toFixed(4)}"><span class="g-l">${esc(g.label)}</span><span class="g-track"><i class="g-bar"></i>${g.id === 'obs2021' ? '<small class="g-note">The flood this alert describes</small>' : ''}</span><b class="g-v mono num" data-v="${g.v}">0</b></li>`).join('')}
      </ul>
      <p class="g-micro mono">Kreis Euskirchen + Landkreis Ahrweiler, modelled estimate</p>
      ${A.street_closed ? '<p class="g-street">Your street is closed by the flood<small class="mono">' + esc(A.street) + '</small></p>' : ''}
    </div>` : ''}

    <div class="s2b-rig">
      <div class="s2b-phone">
        <span class="s2b-btn action"></span><span class="s2b-btn up"></span><span class="s2b-btn down"></span><span class="s2b-btn power"></span>
        <div class="s2b-frame"><div class="s2b-bezel"><div class="s2b-screen">
          <div class="s2b-island"></div>
          <div class="s2b-status"><span class="sig" aria-hidden="true"><i style="height:5px"></i><i style="height:7px"></i><i style="height:9px"></i><i style="height:12px;opacity:.35"></i></span><span>2G</span><span class="bat" aria-hidden="true"><span></span></span></div>
          <div class="s2b-date">Saturday 31 October</div>
          <div class="s2b-time">06:12</div>

          <div class="s2b-stack">
            <div class="s2b-card">
              <div class="s2b-appicon">${ICON}</div>
              <div class="s2b-content">
                <div class="s2b-row"><span class="t">Emergency Alert</span><span class="w">now</span></div>
                <div class="s2b-text">
                  <div class="ln" data-q="1" style="--i:0">${esc(L.danger)}</div>
                  <div class="ln" data-q="2" style="--i:1">${esc(L.severity)}</div>
                  <div class="ln" data-q="3" style="--i:2"><span>${esc(L.go)}</span><span>${esc(L.route)}</span></div>
                  <div class="ln" data-q="0" style="--i:3">${esc(L.safe)}</div>
                </div>
              </div>
            </div>
            <div class="s2b-demo">Demo message, not a real alert</div>

            <div class="s2b-route">
              <div class="s2b-map" style="width:${MAP_W}px;height:${MAP_H}px">
                <img class="s2b-base" alt="Map of Johan's route from his street to the shelter" style="width:${W * K}px;height:${H * K}px;left:${-A.crop.x * K}px;top:${-A.crop.y * K}px">
                <svg class="s2b-ov" viewBox="${A.crop.x} ${A.crop.y} ${A.crop.w} ${A.crop.h}" width="${MAP_W}" height="${MAP_H}" aria-hidden="true">
                  <path class="rt-case" d="${dPath(A.route)}" stroke-width="${px(11)}"/>
                  <path class="rt-line" d="${dPath(A.route)}" stroke-width="${px(6)}"/>
                  <circle class="rt-home-ring" cx="${A.home[0]}" cy="${A.home[1]}" r="${px(12)}"/>
                  <circle class="rt-home" cx="${A.home[0]}" cy="${A.home[1]}" r="${px(8)}" stroke-width="${px(3)}"/>
                  <g transform="translate(${A.shelterPx[0]} ${A.shelterPx[1]}) scale(${(1 / K) * 0.95}) translate(-16 -16)"><circle cx="16" cy="16" r="15" class="rt-pin"/><path d="${HOUSE}" class="rt-house"/></g>
                </svg>
                <div class="s2b-route-h"><svg viewBox="0 0 20 20" width="19" height="19" aria-hidden="true"><path d="M10 1.8a5.6 5.6 0 0 0-5.6 5.6c0 4 5.6 10.8 5.6 10.8s5.6-6.8 5.6-10.8A5.6 5.6 0 0 0 10 1.8z" fill="#003399"/><circle cx="10" cy="7.4" r="2.1" fill="#fff"/></svg>Your route</div>
              </div>
            </div>
          </div>

          <div class="s2b-home" aria-hidden="true"></div>
          <div class="s2b-glare" aria-hidden="true"></div>
        </div></div></div>
      </div>
    </div>`;

  // speaker notes (html-slides format, plain text): script = the words said aloud, steps 0-3 in order
  const sh = A.shelter || {}, lower = s => String(s || '').toLowerCase();
  const notes = {
    title: 'The message',
    script:
      `Johan's phone shows one plain-text message. ` +
      `Am I in danger? ${L.danger} How serious is it? ${L.severity} Where should I go? ${L.go} ${L.route} ` +
      'The first words tell him how serious it is and what to do. ' +
      (g21 ? `In the model, about ${about(g21.v)} residents were inside that flood, ` : '') +
      (A.street_closed ? 'and his own street is closed. ' : '') +
      'It is a demonstration message, not a real alert.',
    notes: [
      `Plain text, written for Cell Broadcast, which the team describes as working on 2G. Nothing is sent: this is the tool's demo message for ${A.street || 'his street'}.`,
      `Built from the model: ${sh.title || 'shelter'}, ${sh.where || ''}; walk ${Deck.fmt(A.walk_min, 1)} min, drive ${Deck.fmt(A.drive_min, 1)} min (model free-flow times, no congestion); assumption set B (core + extended buildings), July 2021 flood.`,
      'The map is the citizen view the alert would link to; a Cell Broadcast text cannot carry a map.',
      `His street, ${A.street || ''}, is closed by the flood: the route avoids closed roads only after it. The tool checks every route for closed roads.`,
      'Supports, and does not replace, official warnings and evacuation decisions.',
    ],
  };

  function setDrawn(p, shown) {
    const len = p.getTotalLength();
    p.style.transition = 'none';
    p.style.strokeDasharray = `${len} ${len}`;
    p.style.strokeDashoffset = shown ? 0 : len;
  }

  Deck.register({
    id: 's2b', order: 2.5, title: 'The message', steps: 4, time: [80, 125], notes, html,

    mount(el, P2, D) {
      el.dataset.mood = 'cinematic';
      D.mapSrc(el.querySelector('.s2b-base'));
      el.querySelectorAll('.s2b-ov path.rt-case, .s2b-ov path.rt-line').forEach(p => setDrawn(p, false));
    },

    step(el, n, dir) {
      // gauge numbers tick up when step 2 is reached going forward; elsewhere they sit at their final value (hidden unless step 2)
      el.querySelectorAll('.g-v').forEach(v => Deck.tick(v, Number(v.dataset.v), { duration: n === 2 && dir > 0 ? 1100 : 0 }));
      const paths = el.querySelectorAll('.s2b-ov path.rt-case, .s2b-ov path.rt-line');
      if (n < 3) paths.forEach(p => setDrawn(p, false));
      else if (dir > 0) paths.forEach(p => Deck.draw(p, { duration: 1500, delay: 450 }));
      else paths.forEach(p => setDrawn(p, true));
    },
  });
})();
