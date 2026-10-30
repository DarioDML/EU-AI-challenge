/* Slide 1 · Meet Johan (0:00-0:45), four steps. Owner: agent 6.
   External figures (not in window.PITCH): Thieken et al. 2023, NHESS 23, 973-990, online survey, n = 1,315.
   29% got no warning (Rhineland-Palatinate; 35% in North Rhine-Westphalia). Of those WARNED, 85% didn't expect severe
   flooding and 46% didn't know what to do (paper abstract). The 10 x 10 waffle shows the rates per 100 respondents:
   an illustration, not 100 real people. The paper does not report how the two groups overlap, so the dots do not claim it. */
(function () {
  'use strict';
  const NO_WARNING = 29;
  const WARNED = 100 - NO_WARNING;                                   // 71
  const N_EXPECT = Math.round(WARNED * 0.85);                         // 60
  const N_KNOW = Math.round(WARNED * 0.46);                           // 33
  const timers = [];
  const later = (fn, ms) => timers.push(setTimeout(fn, ms));
  const clear = () => { timers.splice(0).forEach(clearTimeout); };

  // k-th of 71 warned dots is picked when the running quota ticks over: evenly spread, no hidden overlap pattern
  const spread = (k, n) => Math.floor((k + 1) * n / WARNED) > Math.floor(k * n / WARNED);
  const spreadShifted = (k, n) => spread((k + 23) % WARNED, n);

  let dots = '';
  for (let i = 0; i < 100; i++) {
    const k = i - NO_WARNING;
    const nw = i < NO_WARNING;
    const fl = !nw && spread(k, N_EXPECT);
    const rg = !nw && spreadShifted(k, N_KNOW);
    dots += `<i class="dot${nw ? ' nw' : ''}${fl ? ' fl' : ''}${rg ? ' rg' : ''}" style="--i:${i};--k:${Math.max(k, 0)}">` +
      `<b class="l-base"></b>${nw ? '<b class="l-nw"></b>' : ''}${fl ? '<b class="l-fl"></b>' : ''}${rg ? '<b class="l-rg"></b>' : ''}</i>`;
  }

  Deck.register({
    id: 's1', order: 1, title: 'Meet Johan', steps: 4, time: [0, 45],

    notes: {
      title: 'Meet Johan',
      script: 'This is Johan. He is 11 and lives in Bad Neuenahr-Ahrweiler. Johan is a fictional character; he stands for residents of flood-prone streets. ' +
        'In July 2021, the water came at night. Anyone in his place has three questions. Am I in danger? How serious is it? Where should I go? ' +
        'Those are the questions a warning must answer, and the chain often failed to. ' +
        'In a survey of 1,315 residents, 29% in Rhineland-Palatinate got no warning. ' +
        'Of those who were warned, 85% did not expect very severe flooding, and 46% reported a lack of knowledge on how to protect themselves. ' +
        "Johan doesn't need a generic alert. He needs to know where to go, and which road out is still open.",
      notes: [
        'Johan, 11, is fictional; he stands for residents of flood-prone streets.',
        'A useful alert answers three questions: Am I in danger? How serious is it? Where should I go?',
        'Thieken et al. 2023 (n = 1,315): 29% in Rhineland-Palatinate got no warning; the figure was 35% in North Rhine-Westphalia.',
        "Of those warned: 85% did not expect very severe flooding; 46% reported a lack of knowledge on how to protect themselves. The dots show rates per 100 respondents, an illustration.",
      ],
    },

    html: `
      <div class="s1-art">
        <figure class="s1-fig s1-solo"><img src="assets/johan/johan-solo.png" width="252" height="696" decoding="async"
          alt="Illustration: Johan, a boy in a yellow raincoat"></figure>
        <figure class="s1-fig s1-think"><img src="assets/johan/johan-thinking-tight.png" width="413" height="1233" decoding="async"
          alt="Illustration: Johan looking worried, thinking"></figure>
      </div>

      <div class="s1-col s1-c0">
        <span class="s1-rule" data-b="0" data-b-out="1"></span>
        <p class="kicker" data-b="0" data-b-out="1">14 July 2021</p>
        <h1 class="h-hero" data-b="0" data-b-out="1">Meet Johan.</h1>
        <p class="lead" data-b="0" data-b-out="1">11 · Bad Neuenahr-Ahrweiler</p>
        <p class="s1-micro" data-b="0" data-b-out="1">Fictional character</p>
      </div>

      <div class="s1-col s1-c1">
        <h2 class="h2 s1-h2" data-b="2" data-b-out="3">The water came<br>at night.</h2>
        <div class="s1-big" data-b="2" data-b-out="3">
          <span class="s1-num num"><span class="tk" data-to="${NO_WARNING}">${NO_WARNING}</span><span class="s1-pct">%</span></span>
          <span class="s1-lbl">never got the warning</span>
        </div>
      </div>

      <div class="s1-col s1-c2">
        <h2 class="h2 s1-h2" data-b="3">Of those warned:</h2>
        <div class="s1-stat s1-st-a" data-b="3">
          <span class="s1-num num s1-blue"><span class="tk" data-to="85">85</span><span class="s1-pct">%</span></span>
          <span class="s1-lbl">didn’t expect very severe flooding</span>
        </div>
        <div class="s1-stat s1-st-b" data-b="3">
          <span class="s1-num num s1-goldink"><span class="tk" data-to="46">46</span><span class="s1-pct">%</span></span>
          <span class="s1-lbl">didn’t know what to do</span>
        </div>
      </div>

      <div class="s1-waffle-wrap" data-b="2">
        <p class="s1-per">per 100 respondents</p>
        <div class="s1-waffle" role="img" aria-label="100 dots. 29 hollow: no warning. Of those warned, 60 are shaded blue: didn't expect very severe flooding. 33 carry a gold ring: didn't know what to do.">${dots}</div>
        <ul class="s1-legend">
          <li class="lg-a" data-b="2"><i class="sw sw-nw"></i>No warning</li>
          <li class="lg-b" data-b="3"><i class="sw sw-fl"></i>Didn’t expect</li>
          <li class="lg-c" data-b="3"><i class="sw sw-rg"></i>Didn’t know</li>
        </ul>
      </div>
      <p class="src s1-src" data-b="2">Thieken et al. 2023, NHESS 23, 973-990 · online survey, n = 1,315 · 29% in Rhineland-Palatinate (35% in North Rhine-Westphalia)</p>

      <ol class="s1-qs" aria-label="Johan's three questions">
        <li class="s1-q" data-b="1" data-b-out="2"><span class="s1-qn">01</span><span class="h1 s1-qt">Am I in danger?</span></li>
        <li class="s1-q" data-b="1" data-b-out="2"><span class="s1-qn">02</span><span class="h1 s1-qt">How serious is it?</span></li>
        <li class="s1-q s1-q-gold" data-b="1" data-b-out="2"><span class="s1-qn">03</span><span class="h1 s1-qt">Where should I go?</span></li>
      </ol>`,

    step(el, n, dir) {
      clear();
      const q = s => el.querySelector(s);
      const tk = (node, to, ms, delay, from) => {
        if (!node) return;
        if (dir < 0 || Deck.reduced) { Deck.tick(node, to, { duration: 0 }); return; }
        Deck.tick(node, from, { duration: 0 });
        later(() => Deck.tick(node, to, { duration: ms }), delay);
      };
      const fin = (node, to) => node && Deck.tick(node, to, { duration: 0 });
      if (n === 2) tk(q('.s1-c1 .tk'), NO_WARNING, 1200, 950, 0);   // 29 %, with the grey sweep
      else fin(q('.s1-c1 .tk'), NO_WARNING);
      if (n === 3) {
        tk(q('.s1-st-a .tk'), 85, 1500, 450, 0);                    // 85 %, with the blue sweep
        tk(q('.s1-st-b .tk'), 46, 1500, 2150, 0);                   // 46 %, with the gold-ring sweep
        tk(q('.tk-w'), WARNED, 900, 150, 100);                      // 100 → 71
      } else {
        fin(q('.s1-st-a .tk'), 85); fin(q('.s1-st-b .tk'), 46); fin(q('.tk-w'), WARNED);
      }
    },

    leave() { clear(); },
  });
})();
