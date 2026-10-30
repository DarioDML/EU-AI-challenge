/* Slide 1 · Meet Johan (0:00-0:45). Owner: agent 6.
   Copy is fixed by the blueprint (section 7). The two survey figures are external (not in window.PITCH):
   Thieken et al. 2023, NHESS 23, 973-990, printed in the .src caption of step 1. */
(function () {
  'use strict';
  let timer = 0;

  Deck.register({
    id: 's1', order: 1, title: 'Meet Johan', steps: 3, time: [0, 45],

    notes: {
      title: 'Meet Johan',
      script: 'This is Johan. He is 11 and lives by the river in Bad Neuenahr-Ahrweiler. ' +
        'Johan is a fictional character; he stands for residents of flood-prone streets. ' +
        'On 14 July 2021, the water came at night. In a survey of 1,315 affected residents, 85% of those who were warned ' +
        "didn't expect severe flooding, and 46% didn't know what to do. " +
        'So Johan is left with three questions. Am I in danger? How serious is it? Where should I go? ' +
        'Every warning should answer all three. ' +
        "Johan doesn't need a generic alert. He needs to know where to go, and which road out is still open.",
      notes: [
        'Johan, 11, is fictional; he stands for residents of flood-prone streets.',
        '14 July 2021: the water came at night.',
        "Being warned was not enough: 85% of those warned didn't expect severe flooding, 46% didn't know what to do (Thieken et al. 2023, n = 1,315).",
        'A useful alert answers three questions: Am I in danger? How serious is it? Where should I go?',
      ],
    },

    html: `
      <div class="s1-scene">
        <figure class="s1-shot s1-home"><div class="s1-plate"></div><div class="s1-frame">
          <img src="assets/johan/johan-home.png" width="2047" height="1819" decoding="async"
               alt="Illustration: Johan, a boy in a yellow raincoat, standing next to his house by a river">
        </div></figure>
        <figure class="s1-shot s1-night"><div class="s1-frame">
          <img src="assets/johan/johan-night.png" width="1842" height="2047" decoding="async"
               alt="Illustration: Johan's house at night in heavy rain, water rising, Johan worried at the lit window">
        </div></figure>
        <figure class="s1-shot s1-think"><div class="s1-glow"></div><div class="s1-frame">
          <img src="assets/johan/johan-thinking.png" width="1111" height="1722" decoding="async"
               alt="Illustration: Johan looking worried, thinking">
        </div></figure>
      </div>

      <div class="s1-copy s1-c0">
        <p class="kicker" data-b="0" data-b-out="1">14 July 2021</p>
        <h1 class="h-hero" data-b="0" data-b-out="1">Meet Johan.</h1>
        <p class="lead" data-b="0" data-b-out="1">11 · Bad Neuenahr-Ahrweiler</p>
        <p class="s1-micro" data-b="0" data-b-out="1">Fictional character</p>
      </div>

      <div class="s1-copy s1-c1">
        <h2 class="s1-h2" data-b="1" data-b-out="2">The water came<br>at night.</h2>
        <div class="s1-stat" data-b="1" data-b-out="2">
          <span class="s1-num num"><span class="tk" data-to="85">85</span><span class="s1-pct">%</span></span>
          <span class="s1-lbl">of those warned didn’t expect severe flooding</span>
        </div>
        <div class="s1-stat" data-b="1" data-b-out="2">
          <span class="s1-num num"><span class="tk" data-to="46">46</span><span class="s1-pct">%</span></span>
          <span class="s1-lbl">didn’t know what to do</span>
        </div>
      </div>
      <p class="src s1-src" data-b="1" data-b-out="2">Thieken et al. 2023, Natural Hazards and Earth System Sciences 23, 973-990 · online survey, n = 1,315, North Rhine-Westphalia and Rhineland-Palatinate</p>

      <ol class="s1-qs" aria-label="Johan's three questions">
        <li class="s1-q" data-b="2"><span class="s1-qn">01</span><span class="s1-qt">Am I in danger?</span></li>
        <li class="s1-q" data-b="2"><span class="s1-qn">02</span><span class="s1-qt">How serious is it?</span></li>
        <li class="s1-q s1-q-gold" data-b="2"><span class="s1-qn">03</span><span class="s1-qt">Where should I go?</span></li>
      </ol>`,

    step(el, n, dir) {
      clearTimeout(timer);
      if (n !== 1) return;
      const ticks = [...el.querySelectorAll('.s1-stat .tk')];
      if (dir < 0 || Deck.reduced) { ticks.forEach(t => Deck.tick(t, +t.dataset.to, { duration: 0 })); return; }
      ticks.forEach(t => Deck.tick(t, 0, { duration: 0 }));
      timer = setTimeout(() => ticks.forEach((t, i) => Deck.tick(t, +t.dataset.to, { duration: 1300 + 200 * i })), 420);
    },

    leave() { clearTimeout(timer); },
  });
})();
