/* Slide 1 · Meet Johan (0:00-0:45), five steps: 0 Johan, 1 three questions, 2 crowd + 29%, 3 85%, 4 46%.
   One crowd of 100 person figures stays in place from step 2 to 4; only the state of the figures changes.
   Illustration of rates per 100 respondents, not 100 real people. Thieken et al. 2023, NHESS 23, 973-990 (online survey,
   n = 1,315): 29% of respondents in Rhineland-Palatinate got no warning (35% in North Rhine-Westphalia); of those who were
   warned, 85% did not expect very severe flooding and 46% reported a lack of knowledge on how to protect themselves.
   The paper does not report how the 85% and 46% overlap, so they are never drawn on the crowd at the same time.
   Johan (first figure, gold raincoat) is one of the 71 warned figures but is not part of any highlighted group. */
(function () {
  'use strict';
  const NO_WARNING = 29, WARNED = 100 - NO_WARNING;                    // 29 / 71
  const N_A = Math.round(WARNED * 0.85), N_B = Math.round(WARNED * 0.46);   // 60 / 33
  const COLS = 10, X0 = 948, DX = 90, Y0 = 168, DY = 78;               // 56 x 72 px figures on the right 55 % of the stage
  const SOURCE = 'Thieken et al. 2023, NHESS 23, 973-990 · online survey, n = 1,315 · 29% in Rhineland-Palatinate (35% in North Rhine-Westphalia)';
  const timers = [];
  const later = (fn, ms) => timers.push(setTimeout(fn, ms));
  const clear = () => { timers.splice(0).forEach(clearTimeout); };

  // fixed, deterministic, scattered groups: a seeded shuffle (mulberry32, fixed seeds) of the 99 other figures, first n taken
  const rng = seed => () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const pick = (ids, seed, n) => { const r = rng(seed), a = ids.slice();
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a.slice(0, n); };
  const others = Array.from({ length: 99 }, (_, i) => i + 1);
  const nw = new Set(pick(others, 2026, NO_WARNING));
  const warned = others.filter(i => !nw.has(i));                      // 70 + Johan = 71
  const gA = new Set(pick(warned, 1030, N_A)), gB = new Set(pick(warned, 1029, N_B));

  const person = () => '<use class="hd" href="#s1-ph"/><use class="bd" href="#s1-pb"/>';
  const badge = (kind, inner) => `<g class="bdg bdg-${kind}" transform="translate(49 9)"><circle r="10.5"/>${inner}</g>`;
  let crowd = '';
  for (let i = 0; i < 100; i++) {
    const r = Math.floor(i / COLS), c = i % COLS;
    const cls = ['pf', i === 0 ? 'johan' : '', nw.has(i) ? 'g-nw' : '', gA.has(i) ? 'g-a' : '', gB.has(i) ? 'g-b' : ''].filter(Boolean).join(' ');
    const layers = `<g class="L base">${person()}</g>` +
      (nw.has(i) ? `<g class="L nw">${person()}${badge('nw', '<rect x="-3.3" y="-5.2" width="6.6" height="10.4" rx="1.5"/><path d="M-7.2 -7.2 7.2 7.2"/>')}</g>` : '') +
      (gA.has(i) ? `<g class="L a">${person()}${badge('a', '<text y="5.2" text-anchor="middle">!</text>')}</g>` : '') +
      (gB.has(i) ? `<g class="L b">${person()}${badge('b', '<text y="5.2" text-anchor="middle">?</text>')}</g>` : '');
    crowd += `<div class="${cls}" style="left:${X0 + c * DX}px;top:${Y0 + r * DY}px;--r:${r};--c:${c}">` +
      `<svg viewBox="0 0 56 72" width="56" height="72" aria-hidden="true">${layers}</svg></div>`;
  }
  const swatch = kind => `<svg viewBox="-2 -2 60 76" width="20" height="26" aria-hidden="true"><g class="sw sw-${kind}">${person()}</g></svg>`;

  Deck.register({
    id: 's1', order: 1, title: 'Meet Johan', steps: 5, time: [0, 45],
    notes: {
      title: 'Meet Johan',
      script: 'This is Johan. He is 11 and lives in Bad Neuenahr-Ahrweiler. Johan is a fictional character; he stands for residents of flood-prone streets. ' +
        'In July 2021, the water came at night. Anyone in his place has three questions. Am I in danger? How serious is it? Where should I go? ' +
        'In a survey, 29% in Rhineland-Palatinate got no warning. ' +
        'Of those who were warned, 85% did not expect very severe flooding, and 46% reported a lack of knowledge on how to protect themselves. ' +
        "Johan doesn't need a generic alert. He needs to know where to go, and which road out is still open.",
      notes: [
        'Johan, 11, is fictional; he stands for residents of flood-prone streets.',
        'A useful alert answers three questions: Am I in danger? How serious is it? Where should I go?',
        'Thieken et al. 2023 (online survey, n = 1,315): 29% of respondents in Rhineland-Palatinate got no warning; the figure was 35% in North Rhine-Westphalia.',
        'Of those who were warned: 85% did not expect very severe flooding; 46% reported a lack of knowledge on how to protect themselves.',
        'The 100 figures illustrate rates per 100 respondents, not real people. The paper does not report how the 85% and 46% overlap, so they are never shown together.',
      ],
    },
    html: `
      <svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>
        <path id="s1-ph" d="M28 3a13 13 0 1 0 .01 0Z"/>
        <path id="s1-pb" d="M3 72V55Q3 33 28 33Q53 33 53 55V72Z"/>
      </defs></svg>
      <div class="s1-art" aria-hidden="true">
        <figure class="s1-fig s1-solo"><img src="assets/johan/johan-solo.png" width="252" height="696" alt=""></figure>
        <figure class="s1-fig s1-think"><img src="assets/johan/johan-thinking-tight.png" width="413" height="1233" alt=""></figure>
      </div>
      <div class="s1-intro" data-b="0" data-b-out="1" data-stagger="170" data-stagger-delay="80">
        <p class="kicker" data-stagger-item>14 July 2021</p>
        <h1 class="h-hero" data-stagger-item>Meet Johan.</h1>
        <p class="lead" data-stagger-item>11 · Bad Neuenahr-Ahrweiler</p>
        <p class="s1-micro" data-stagger-item>Fictional character</p>
      </div>
      <ol class="s1-qs" data-b="1" data-b-out="2" data-stagger="260" data-stagger-delay="120" aria-label="Johan's three questions">
        <li data-stagger-item><span>01</span><h2>Am I in danger?</h2></li>
        <li data-stagger-item><span>02</span><h2>How serious is it?</h2></li>
        <li data-stagger-item><span>03</span><h2>Where should I go?</h2></li>
      </ol>

      <h2 class="h2 s1-title" data-b="2">The water came<br>at night.</h2>
      <div class="s1-stat s1-st-29" data-b="2" data-b-out="3">
        <span class="s1-num num"><span class="tk">29</span><span class="s1-pct">%</span></span>
        <span class="s1-lbl">never got the warning</span>
      </div>
      <div class="s1-stat s1-st-85" data-b="3" data-b-out="4">
        <span class="s1-num num s1-blue"><span class="tk">85</span><span class="s1-pct">%</span></span>
        <span class="s1-lbl">of those warned didn’t expect very severe flooding</span>
      </div>
      <div class="s1-stat s1-st-46" data-b="4">
        <span class="s1-num num s1-goldink"><span class="tk">46</span><span class="s1-pct">%</span></span>
        <span class="s1-lbl">of those warned didn’t know what to do</span>
      </div>

      <p class="s1-per" data-b="2">per 100 respondents</p>
      <div class="s1-crowd" role="img" aria-label="100 person figures, an illustration per 100 respondents. 29 grey: no warning. Of the 71 warned, first 60 who did not expect very severe flooding, then 33 who did not know what to do.">${crowd}</div>
      <ul class="s1-legend">
        <li class="lg-nw" data-b="2" data-b-out="3">${swatch('nw')}no warning</li>
        <li class="lg-slot">
          <span class="lg-a" data-b="3" data-b-out="4">${swatch('a')}didn’t expect</span>
          <span class="lg-b" data-b="4">${swatch('b')}didn’t know</span>
        </li>
      </ul>
      <p class="src s1-src" data-b="2">${SOURCE}</p>`,

    step(el, n, dir) {
      clear();
      const q = s => el.querySelector(s);
      const fin = (node, to) => node && Deck.tick(node, to, { duration: 0 });
      const run = (node, to, ms, delay) => {
        if (!node) return;
        if (dir < 0 || Deck.reduced) { fin(node, to); return; }
        fin(node, 0);
        later(() => Deck.tick(node, to, { duration: ms }), delay);
      };
      const n29 = q('.s1-st-29 .tk'), n85 = q('.s1-st-85 .tk'), n46 = q('.s1-st-46 .tk');
      if (n === 2) run(n29, 29, 1300, 1700); else fin(n29, 29);
      if (n === 3) run(n85, 85, 1400, 600); else fin(n85, 85);
      if (n === 4) run(n46, 46, 1400, 900); else fin(n46, 46);
    },

    leave() { clear(); },
  });
})();
