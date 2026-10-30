/* Slide 4 · Decide before the night (agent 8 · 2 steps · 2:45-4:15).
   Left: two policy sliders (flood level, shelter buildings) drive the headline KPI, one stacked bar, its legend
   and a telemetry line. Step 1: Johan's iPhone slides in with his cell-broadcast alert for the same plan, and an
   ETA chip sits on the stage next to it. Every number is read from window.PITCH (pitch-data.js).
   Keys while this slide is active: 1-4 flood level, B shelter buildings, Esc releases a focused slider.
   Screenshot preset (optional): ?s4=<level>,<set> in the URL sets both sliders at load, e.g.
     index.html?static&s4=rp500,generous#4.1
   level: obs2021 | rp10 | rp100 | rp500 (or 2021 | 10 | 100 | 500); set: restrictive | generous (or core | extended, a | b).
   The range inputs are real, keyboard-accessible <input type=range> elements with appearance:none and a transparent
   native thumb; the visible track, stops and thumb are drawn beside them so that the thumb can glide with the spring. */
(function () {
  'use strict';
  const P = window.PITCH || {};
  const LEVELS = P.levels || [], SETS = P.sets || [];
  const STOP = { obs2021: '2021', rp10: '10-yr', rp100: '100-yr', rp500: '500-yr' };
  const SEV = { obs2021: 'as in July 2021', rp10: 'a 1-in-10-year flood', rp100: 'a 1-in-100-year flood', rp500: 'a 1-in-500-year flood' };
  const LEVEL_TEXT = { obs2021: 'July 2021 flood, mapped', rp10: '10-year flood, model', rp100: '100-year flood, model', rp500: '500-year flood, model' };
  const SET_UI = { restrictive: 'Core public', generous: '+ Extended' };
  const SET_TEXT = { restrictive: 'core public buildings (set A)', generous: 'core and extended buildings (set B)' };
  const SEGS = [['within30', 'Within 30 min', 'ok'], ['over30', 'Over 30 min', 'slow'], ['no_place', 'No place', 'none']];
  const BAR_W = 1034, GAP = 2, CAP = 4, MINW = 4, THUMB = 40;   // px; CAP = rounded outer end, MINW keeps a non-zero part visible

  const ok = !!(P.plans && P.johan && P.johan.plans && LEVELS.length >= 2 && SETS.length >= 2);
  const keyOf = (li, si) => `${LEVELS[li].id}|${LEVELS[li].closure}|${SETS[si].id}`;
  const fmt = (n, d = 0) => Number(n).toLocaleString('en-GB', { minimumFractionDigits: d, maximumFractionDigits: d });
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const pctOf = p => Math.round(100 * p.within30 / p.to_place);
  const m2 = (s, dflt) => ((s && s.label || '').match(/([\d.]+)\s*m2/) || [])[1] || dflt;
  const setById = id => SETS.find(s => s.id === id);

  /* Johan's alert: plain sentences, GSM 7-bit characters only (it is sent as 2G cell-broadcast text). */
  function alertText(levelId, j) {
    const street = P.johan.street, home = P.town && P.town.name;
    const head = `Flood danger: ${SEV[levelId] || 'flood'}.`;
    if (!j || j.status === 'no_people') return `${head}\nYour street is outside this flood map. Follow official warnings.`;
    const first = `${head} ${street} is in the flood area.`;
    if (j.status === 'no_place' || !j.shelter) return `${first}\nNo shelter place within 1 hour in this plan. Follow official instructions.`;
    const s = j.shelter;
    const dest = [s.title, s.where, s.town && s.town !== home ? s.town : ''].filter(Boolean).join(', ');
    const walk = Math.max(1, Math.round(j.walk_min)), drive = Math.max(1, Math.round(j.drive_min));
    const via = (j.via || []).filter(v => v !== street).slice(0, 2);
    return [first, `Leave now. Go to: ${dest}.`,
      `Walk ${walk} min to the nearest open road, then ${drive} min by car${via.length ? ` via ${via.join(', ')}` : ''}.`,
      'This route avoids flooded roads.'].join('\n');
  }

  /* Speaker notes, html-slides format {title, script, notes[]}: the words said aloud while the sliders move,
     then the key points. Plain text (the engine escapes it); every number is read from PITCH. */
  function notes() {
    const title = 'Decide before the night';
    if (!ok || LEVELS.length < 4) return { title, script: 'pitch-data.js is missing: run python powerpoint/pitch/build_pitch_data.py', notes: [] };
    const a21 = P.plans[keyOf(0, 0)], a500 = P.plans[keyOf(3, 0)], b500 = P.plans[keyOf(3, 1)];
    const jA = P.johan.plans[keyOf(3, 0)], jB = P.johan.plans[keyOf(3, 1)];
    const about = t => (t >= 50 && t <= 70 ? 'about an hour' : `about ${Math.max(1, Math.round(t))} minutes`);
    const where = j => (!j || !j.shelter ? 'no shelter'
      : /^[A-Z][a-z]+$/.test(j.shelter.title) ? `a ${j.shelter.kind.toLowerCase()} in ${j.shelter.town}` : `the ${j.shelter.title}`);
    const trip = j => (j && j.shelter ? `${fmt(j.total_min, 1)} min to ${j.shelter.title}, ${j.shelter.town}` : 'no route');
    const A = setById('restrictive'), B = setById('generous');
    const script = [
      'This is a decision a district can take before the night: which buildings open as shelters.',
      'Here is the July 2021 flood, with core public buildings only.',
      `Of the ${fmt(a21.to_place)} residents inside the flood, ${pctOf(a21)} percent reach a shelter within 30 minutes.`,
      a21.no_place === 0 ? `Everyone gets a place within the hour, but ${fmt(a21.over30)} people travel longer than 30 minutes.`
        : `${fmt(a21.over30)} people travel longer than 30 minutes.`,
      'Now a 500-year flood, from the EFAS model.',
      `${a500.to_place > a21.to_place ? 'The bar grows, and ' : ''}${fmt(a500.no_place)} people have no place at all.`,
      `This is Johan's phone in that plan. His alert sends him to ${where(jA)}, ${about(jA.total_min)} away.`,
      'Now we open the extended buildings as well.',
      `No place falls to ${fmt(b500.no_place)}, and Johan goes to ${where(jB)}, ${about(jB.total_min)} away.`,
      'Same flood, same roads. What changed is the shelter plan.',
      'Set A and set B are alternative assumption sets, not lower and upper bounds.',
      'The buildings are OpenStreetMap candidates, not designated shelters.',
      'And the phone shows plain cell-broadcast text: no app, no map, and it works on 2G.',
    ].join(' ');
    return {
      title, script,
      notes: [
        `July 2021 flood, core public buildings: ${pctOf(a21)} % of ${fmt(a21.to_place)} residents inside the flood reach a shelter within 30 min; ${fmt(a21.over30)} take longer; no place ${fmt(a21.no_place)}.`,
        `500-year flood (EFAS model): no place ${fmt(a500.no_place)} with core public buildings (set A), ${fmt(b500.no_place)} with + Extended (set B).`,
        `Johan in the 500-year flood: ${trip(jA)} (set A); ${trip(jB)} (set B). Every route avoids closed roads.`,
        `Set A (core public, ${m2(A, '5')} m² per person) and set B (+ extended, ${m2(B, '3.5')} m² per person) are alternative assumption sets, not bounds; the buildings are OpenStreetMap candidates, not designated shelters.`,
        'The alert is plain cell-broadcast text that works on 2G. Residents inside the flood are a GHS-POP 2020 estimate.',
      ],
    };
  }

  function sliderHtml(name, label, stops, extra) {
    return `<div class="s4-slider s4-slider--${name}">
      <span class="kicker s4-sl-label" id="s4-${name}-label">${label}</span>
      <div class="s4-sl-body">
        <input class="s4-range" id="s4-${name}" type="range" min="0" max="${stops.length - 1}" step="1" value="0" aria-labelledby="s4-${name}-label">
        <div class="s4-track" aria-hidden="true"><div class="s4-fill"></div></div>
        <div class="s4-dots" aria-hidden="true">${stops.map(() => '<i></i>').join('')}</div>
        <div class="s4-thumb" aria-hidden="true"><div class="s4-knob"></div></div>
        <div class="s4-stops" aria-hidden="true">${stops.map((s, i) => `<span class="s4-stop${i === 0 ? ' first' : ''}${i === stops.length - 1 ? ' last' : ''}">${s}</span>`).join('')}</div>
        ${extra || ''}
      </div>
    </div>`;
  }

  const ICON_ALERT = '<svg viewBox="0 0 24 24" width="23" height="23" aria-hidden="true"><path d="M12 3.5 2.5 20.5h19z" fill="#fff" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/><path d="M12 9.5v5M12 17.4v.2" stroke="#ff3b30" stroke-width="2.2" stroke-linecap="round"/></svg>';
  const ICON_TORCH = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M8 2.8h8v3l-2 3.4v11.6a1.4 1.4 0 0 1-1.4 1.4h-1.2a1.4 1.4 0 0 1-1.4-1.4V9.2L8 5.8z" fill="none" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/><path d="M12 12.6v2.6" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/></svg>';
  const ICON_CAMERA = '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d="M4 7.6h3.1L8.7 5h6.6l1.6 2.6H20a1.5 1.5 0 0 1 1.5 1.5v8.9a1.5 1.5 0 0 1-1.5 1.5H4A1.5 1.5 0 0 1 2.5 18V9.1A1.5 1.5 0 0 1 4 7.6z" fill="none" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/><circle cx="12" cy="13.2" r="3.5" fill="none" stroke="#fff" stroke-width="1.6"/></svg>';
  const ICON_LOCK = '<svg viewBox="0 0 16 20" width="13" height="17" aria-hidden="true"><rect x="1.5" y="8.5" width="13" height="10" rx="2.4" fill="#fff"/><path d="M4.6 8.6V6.2a3.4 3.4 0 0 1 6.8 0v2.4" fill="none" stroke="#fff" stroke-width="1.8"/></svg>';

  /* Source caption, two lines (the break falls between the data sources and the assumptions). */
  const srcLines = () => {
    const A = setById('restrictive'), B = setById('generous');
    const day = (P.source && P.source.bundle_generated_utc || '').slice(0, 10);
    return ['Kreis Euskirchen + Landkreis Ahrweiler · residents inside the flood: GHS-POP 2020 estimate · buildings: OpenStreetMap candidates, not designated shelters ·',
      `Core public = set A, ${m2(A, '5')} m² per person; + Extended = set B, ${m2(B, '3.5')} m² per person (assumptions) · Smart Shelter System bundle ${day}`];
  };

  const HTML = !ok ? '' : `
    <div class="s4-left">
      <h2 class="h2 s4-title" data-b="0">Decide before the night.</h2>
      <div class="s4-controls" data-b="0">
        ${sliderHtml('level', 'Flood level', LEVELS.map(l => STOP[l.id] || l.id),
          '<div class="s4-subs mono" aria-hidden="true"><span class="s4-sub-mapped">mapped</span><span class="s4-sub-model"><i></i><b>model</b><i></i></span></div>')}
        ${sliderHtml('set', 'Shelter buildings', SETS.map(s => SET_UI[s.id] || s.id))}
      </div>
      <div class="s4-kpi" data-b="0">
        <div class="s4-kpi-n"><span class="num" data-k="kpi">0</span><span class="s4-kpi-u">%</span></div>
        <div class="s4-kpi-l">reach a shelter<br>within 30 min</div>
      </div>
      <div class="s4-chart" data-b="0">
        <div class="s4-bar" role="img">
          ${SEGS.map(s => `<div class="s4-seg ${s[2]}"></div><div class="s4-cap ${s[2]}"></div>`).join('')}
        </div>
        <div class="s4-legend">
          ${SEGS.map(s => `<span class="s4-lg"><i class="s4-sw ${s[2]}" aria-hidden="true"></i><span class="s4-lg-l">${s[1].toLowerCase()}</span><b class="num" data-k="${s[0]}">0</b></span>`).join('')}
        </div>
      </div>
      <div class="s4-tele mono" data-b="0">
        <span>Roads over capacity</span> <b class="num" data-k="roads">0</b><span class="sep">·</span><span>Mean trip</span> <b class="num" data-k="mean">0.0</b> <span>min</span><span class="sep">·</span><span>Residents</span> <b class="num" data-k="res">0</b>
      </div>
    </div>

    <div class="s4-eta glass" aria-label="Johan's trip">
      <div class="s4-eta-n mono"><span class="num" data-k="eta">0.0</span><small>min</small></div>
      <div class="s4-eta-sub mono num" data-k="eta-sub"></div>
      <div class="s4-eta-to"><i aria-hidden="true"></i><span data-k="eta-town"></span></div>
    </div>

    <figure class="s4-phone" aria-label="Johan's phone, demo alert">
      <div class="s4-btn action"></div><div class="s4-btn vol-up"></div><div class="s4-btn vol-dn"></div><div class="s4-btn power"></div>
      <div class="s4-frame"><div class="s4-bezel"><div class="s4-screen">
        <div class="s4-island" aria-hidden="true"></div>
        <div class="s4-status" aria-hidden="true"><span class="sig"><i style="height:4px"></i><i style="height:6.5px"></i><i style="height:9px"></i><i style="height:11.5px;opacity:.35"></i></span><span>2G</span><span class="bat"><span></span></span></div>
        <div class="s4-lock" aria-hidden="true">${ICON_LOCK}</div>
        <div class="s4-date">Saturday 31 October</div>
        <div class="s4-time">06:12</div>
        <div class="s4-card">
          <div class="s4-appicon">${ICON_ALERT}</div>
          <div class="s4-content">
            <div class="s4-row"><span class="t">Emergency Alert</span><span class="w">now</span></div>
            <div class="s4-text"></div>
          </div>
        </div>
        <div class="s4-demo">Demo message, not a real alert</div>
        <div class="s4-qa l" aria-hidden="true">${ICON_TORCH}</div>
        <div class="s4-qa r" aria-hidden="true">${ICON_CAMERA}</div>
        <div class="s4-home" aria-hidden="true"></div>
        <div class="s4-glare" aria-hidden="true"></div>
      </div></div></div>
    </figure>

    <p class="src s4-src">${srcLines().map(esc).join('<br>')}</p>
    <div class="s4-sr" aria-live="polite" data-k="live"></div>
    <div class="s4-sr" data-k="table"></div>`;

  /* ---- runtime ---- */
  let D, root, maxTo = 1, sliders = [], segs = [], N = {}, card, eta, entryTimer = 0, etaTimer = 0;
  const state = { level: 0, set: 0 };

  function table() {
    const head = ['Plan', 'Residents inside the flood', 'Within 30 min', 'Over 30 min', 'No place', 'Share within 30 min', 'Mean trip (min)', 'Roads over capacity', "Johan's trip"];
    const rows = [];
    LEVELS.forEach((lv, li) => SETS.forEach((st, si) => {
      const p = P.plans[keyOf(li, si)], j = P.johan.plans[keyOf(li, si)];
      if (!p) return;
      const trip = j && j.status === 'placed' && j.shelter ? `${fmt(j.total_min, 1)} min to ${j.shelter.title}, ${j.shelter.town}` : 'no route';
      rows.push(`<tr><th scope="row">${esc(LEVEL_TEXT[lv.id] || lv.label)}, ${esc(SET_TEXT[st.id] || st.label)}</th>` +
        [fmt(p.to_place), fmt(p.within30), fmt(p.over30), fmt(p.no_place), pctOf(p) + ' %', fmt(p.mean_min, 1), fmt(p.roads_over), esc(trip)].map(v => `<td>${v}</td>`).join('') + '</tr>');
    }));
    return `<table><caption>Shelter plans for the residents inside the flood, Kreis Euskirchen and Landkreis Ahrweiler (Smart Shelter System bundle)</caption>` +
      `<thead><tr>${head.map(h => `<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table>`;
  }

  /* URL preset ?s4=<level>,<set> (see the header comment). */
  function preset() {
    const q = new URLSearchParams(location.search).get('s4');
    if (!q) return;
    const [l, s] = q.toLowerCase().split(',').map(x => (x || '').trim());
    const lAlias = { '2021': 'obs2021', '1': 'obs2021', '10': 'rp10', '2': 'rp10', '100': 'rp100', '3': 'rp100', '500': 'rp500', '4': 'rp500' };
    const sAlias = { core: 'restrictive', a: 'restrictive', extended: 'generous', b: 'generous' };
    const li = LEVELS.findIndex(x => x.id === (lAlias[l] || l)), si = SETS.findIndex(x => x.id === (sAlias[s] || s));
    if (li >= 0) state.level = li;
    if (si >= 0) state.set = si;
  }

  /* Counters start inside a frame and from the value on screen. Started from an event, the engine's first tick frame
     can carry a timestamp before its start time and paint a negative number for one frame; an interrupted count would
     also restart from its old target. Non-animated updates paint at once. */
  const tickQ = new Map();
  let tickRaf = 0;
  function tickTo(el, to, opt) {
    if (!opt.duration || D.reduced) { tickQ.delete(el); D.tick(el, to, Object.assign({}, opt, { duration: 0 })); return; }
    tickQ.set(el, [to, opt]);
    if (!tickRaf) tickRaf = requestAnimationFrame(() => {
      tickRaf = 0;
      const q = [...tickQ];
      tickQ.clear();
      q.forEach(([e, [v, o]]) => { e._tickVal = undefined; D.tick(e, v, o); });
    });
  }
  function tickStop(el, text) { tickQ.delete(el); cancelAnimationFrame(el._tickRaf); el._tickVal = undefined; el.textContent = text; }

  const live = () => root.classList.contains('is-active');
  const phoneOn = () => live() && root.classList.contains('s1');

  function paintSlider(sl, v) {
    sl.input.value = v;
    const x = (sl.n > 1 ? v / (sl.n - 1) : 0) * (sl.w - THUMB);
    sl.thumb.style.transform = `translate3d(${x}px,0,0)`;
    sl.fill.style.transform = `scaleX(${(THUMB / 2 + x) / sl.w})`;
    sl.stops.forEach((s, i) => s.classList.toggle('on', i === v));
    sl.input.setAttribute('aria-valuetext', sl.text[v]);
  }

  /* Stacked bar: each part is a square body scaled with scaleX plus a 4 px cap that carries the rounded outer end,
     so the corner never distorts while the widths spring. Scale: the largest to_place of the 8 plans = BAR_W. */
  function paintBar(p) {
    const k = (BAR_W - 2 * GAP - MINW) / maxTo;
    let x = 0, last = -1;
    const geo = SEGS.map(([f], i) => {
      const v = p[f] || 0;
      if (v <= 0) return { x, w: 0, v };
      const g = { x, w: Math.max(MINW, v * k), v };
      x = g.x + g.w + GAP; last = i;
      return g;
    });
    const total = SEGS.reduce((t, [f]) => t + (p[f] || 0), 0);
    geo.forEach((g, i) => {
      const s = segs[i], isLast = i === last;
      const body = isLast ? Math.max(0, g.w - CAP) : g.w;
      s.body.style.transform = `translate3d(${g.x}px,0,0) scaleX(${body / BAR_W})`;
      s.cap.style.transform = `translate3d(${g.x + Math.max(0, g.w - CAP)}px,0,0)`;
      s.cap.style.opacity = isLast ? '1' : '0';
      const t = `${SEGS[i][1]}: ${fmt(g.v)} residents (${total ? Math.round(100 * g.v / total) : 0} %)`;
      s.body.title = t; s.cap.title = t;
    });
    N.bar.setAttribute('aria-label', `${fmt(p.to_place)} residents inside the flood: within 30 min ${fmt(p.within30)}, over 30 min ${fmt(p.over30)}, no place ${fmt(p.no_place)}.`);
  }

  /* Crossfade the alert text and let the card arrive with a small drop. */
  function paintAlert(text) {
    const cur = N.text;
    if (cur.textContent === text) return;
    const animate = phoneOn() && !D.reduced;
    card.querySelectorAll('.s4-ghost').forEach(g => g.remove());
    if (!animate) { cur.textContent = text; return; }
    const ghost = cur.cloneNode(true);
    ghost.classList.add('s4-ghost');
    ghost.setAttribute('aria-hidden', 'true');
    ghost.style.top = cur.offsetTop + 'px';
    cur.parentNode.appendChild(ghost);
    cur.textContent = text;
    const out = ghost.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 220, easing: 'linear', fill: 'forwards' });
    out.onfinish = out.oncancel = () => ghost.remove();
    setTimeout(() => ghost.remove(), 700);   // also when the animation clock is paused (hidden tab)
    cur.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 460, delay: 80, easing: 'cubic-bezier(0.2, 0, 0, 1)', fill: 'backwards' });
    card.animate([{ transform: 'translate3d(0,-16px,0) scale(0.975)' }, { transform: 'none' }], { duration: 700, easing: D.SPRING });
  }

  function paintEta(j, animate) {
    const placed = j && j.status === 'placed';
    if (placed) tickTo(N.eta, j.total_min, { decimals: 1, duration: animate ? 900 : 0 });
    else tickStop(N.eta, '–');
    N.etaSub.textContent = placed ? `walk ${fmt(j.walk_min, 1)} · car ${fmt(j.drive_min, 1)}` : (j && j.status === 'no_place' ? 'no place within 1 h' : 'outside the flood map');
    const town = placed && j.shelter ? j.shelter.town : '';
    if (N.town.textContent !== town) {
      N.town.textContent = town;
      if (animate) N.town.animate([{ opacity: 0, transform: 'translate3d(0,6px,0)' }, { opacity: 1, transform: 'none' }], { duration: 500, easing: D.SPRING });
    }
    eta.classList.toggle('no-route', !placed);
  }

  function render(animate) {
    const li = state.level, si = state.set, key = keyOf(li, si);
    const p = P.plans[key], j = P.johan.plans[key];
    if (!p) return;
    const a = animate && live() && !D.reduced;
    const dur = a ? 900 : 0;
    paintSlider(sliders[0], li);
    paintSlider(sliders[1], si);
    tickTo(N.kpi, pctOf(p), { duration: dur });
    paintBar(p);
    SEGS.forEach(([f]) => tickTo(N[f], p[f] || 0, { duration: dur }));
    tickTo(N.roads, p.roads_over, { duration: dur });
    tickTo(N.mean, p.mean_min, { decimals: 1, duration: dur });
    tickTo(N.res, p.to_place, { duration: dur });
    paintAlert(alertText(LEVELS[li].id, j));
    paintEta(j, a && phoneOn());
    N.live.textContent = `${LEVEL_TEXT[LEVELS[li].id] || LEVELS[li].label}, ${SET_TEXT[SETS[si].id] || SETS[si].label}: ${pctOf(p)} % reach a shelter within 30 min, ${fmt(p.no_place)} have no place.` +
      (j && j.status === 'placed' ? ` Johan: ${fmt(j.total_min, 1)} min to ${j.shelter.town}.` : '');
  }

  function set(patch) {
    let changed = false;
    for (const k in patch) if (state[k] !== patch[k]) { state[k] = patch[k]; changed = true; }
    if (changed) render(true);
  }

  function mount(el, _P, Deck) {
    D = Deck; root = el;
    if (!ok) return;
    maxTo = Math.max(...Object.values(P.plans).map(p => p.to_place));
    const q = s => el.querySelector(s);
    el.querySelectorAll('[data-k]').forEach(n => { N[n.dataset.k] = n; });
    N.within30 = q('[data-k="within30"]'); N.over30 = q('[data-k="over30"]'); N.no_place = q('[data-k="no_place"]');
    N.etaSub = N['eta-sub']; N.town = N['eta-town']; N.text = q('.s4-text'); N.bar = q('.s4-bar');
    card = q('.s4-card'); eta = q('.s4-eta');
    N.table.innerHTML = table();
    segs = [...el.querySelectorAll('.s4-seg')].map((body, i) => ({ body, cap: el.querySelectorAll('.s4-cap')[i] }));

    const texts = [LEVELS.map(l => LEVEL_TEXT[l.id] || l.label), SETS.map(s => (SET_UI[s.id] || s.id) + ': ' + (SET_TEXT[s.id] || s.label))];
    sliders = [...el.querySelectorAll('.s4-slider')].map((box, idx) => {
      const sl = {
        key: idx ? 'set' : 'level', input: box.querySelector('.s4-range'), thumb: box.querySelector('.s4-thumb'),
        fill: box.querySelector('.s4-fill'), stops: [...box.querySelectorAll('.s4-stop')], dots: [...box.querySelectorAll('.s4-dots i')],
        w: box.offsetWidth || parseFloat(getComputedStyle(box).width) || 600, text: texts[idx],
      };
      sl.n = sl.stops.length;
      const at = i => THUMB / 2 + (sl.n > 1 ? i / (sl.n - 1) : 0) * (sl.w - THUMB);
      sl.dots.forEach((d, i) => { d.style.left = at(i) + 'px'; });
      sl.stops.forEach((s, i) => { if (i > 0 && i < sl.n - 1) s.style.left = at(i) + 'px'; });
      const sub = box.querySelector('.s4-sub-model');
      if (sub && sl.n > 2) sub.style.left = (at(1) - 26) + 'px';
      sl.input.addEventListener('input', () => set({ [sl.key]: +sl.input.value }));
      // pointer use keeps no focus, so the presenter's arrow keys go back to the deck
      sl.input.addEventListener('pointerdown', () => {
        const release = () => { sl.input.blur(); removeEventListener('pointerup', release); removeEventListener('pointercancel', release); };
        addEventListener('pointerup', release); addEventListener('pointercancel', release);
      });
      return sl;
    });

    Deck.onKey('s4', e => {
      const k = e.key, mine = sliders.find(s => s.input === e.target);
      if (k.length === 1 && k >= '1' && k <= String(Math.min(9, LEVELS.length))) { set({ level: +k - 1 }); return true; }
      if (k === 'b' || k === 'B') { set({ set: state.set ? 0 : 1 }); return true; }
      if (mine && k === 'Escape') { mine.input.blur(); return true; }
      if (mine && (k === 'Home' || k === 'End')) { set({ [mine.key]: k === 'Home' ? 0 : mine.n - 1 }); return true; }
      return false;
    });

    preset();
    render(false);
  }

  /* Entrance: the bar grows from the baseline and the numbers count up once the slide has settled. */
  function enter(el) {
    if (!ok || D.reduced) return;
    clearTimeout(entryTimer);
    el.classList.add('s4-hold');
    segs.forEach(s => { s.body.style.transform = 'translate3d(0,0,0) scaleX(0)'; s.cap.style.transform = 'translate3d(0,0,0)'; s.cap.style.opacity = '0'; });
    [N.kpi, N.within30, N.over30, N.no_place].forEach(n => tickStop(n, '0'));
    el.getBoundingClientRect();
    entryTimer = setTimeout(() => { el.classList.remove('s4-hold'); render(true); }, 320);
  }

  function step(el, n, dir) {
    if (!ok) return;
    const ph = el.querySelector('.s4-phone');
    ph.setAttribute('aria-hidden', n < 1 ? 'true' : 'false');
    eta.setAttribute('aria-hidden', n < 1 ? 'true' : 'false');
    clearTimeout(etaTimer);
    if (n >= 1 && dir > 0 && !D.reduced) {
      // the alert lands after the phone; Johan's trip time counts up as the chip appears
      const j = P.johan.plans[keyOf(state.level, state.set)];
      if (j && j.status === 'placed') {
        tickStop(N.eta, fmt(0, 1));
        etaTimer = setTimeout(() => {
          const now = P.johan.plans[keyOf(state.level, state.set)];
          if (now && now.status === 'placed') tickTo(N.eta, now.total_min, { decimals: 1, duration: 1100 });
        }, 420);
      }
    }
  }

  Deck.register({
    id: 's4', order: 4, title: 'Decide before the night', steps: 2, time: [185, 285],
    notes: notes(), html: HTML, mount, enter, step,
  });
})();
