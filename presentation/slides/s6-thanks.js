/* Slide 6 · Thank you (4:45-5:00). Owner: agent 6.
   Step 0: Johan bounces in (squash and stretch), then hops in a small 2.4 s loop; rain around him.
   Step 1: his gold route draws itself from his feet to an EU-blue pin, the rain clears, confetti floats up, the tagline appears. */
(function () {
  'use strict';
  const TEAM = 'Team 1';                                   // ← the team name on the closing line

  // 24 confetti pieces: seeded (mulberry32), gold and EU blue only, kept in the scene area on the right
  const rng = seed => () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const rnd = rng(606);
  let confetti = '';
  for (let i = 0; i < 24; i++) {
    const x = 930 + rnd() * 890, y = 170 + rnd() * 760, s = 9 + rnd() * 9;
    const round = rnd() < 0.55, gold = i % 2 === 0;
    confetti += `<i class="cf" style="left:${x.toFixed(0)}px;top:${y.toFixed(0)}px;--s:${s.toFixed(0)}px;--d:${(250 + rnd() * 1100).toFixed(0)}ms;--f:${(3.2 + rnd() * 2.4).toFixed(1)}s;--fd:${(-rnd() * 4).toFixed(1)}s;--rot:${(rnd() * 70 - 35).toFixed(0)}deg">` +
      `<b class="${gold ? 'g' : 'b'}${round ? ' r' : ''}"></b></i>`;
  }
  let rain = '';
  for (let i = 0; i < 14; i++) {
    const x = 940 + rnd() * 470, y = 150 + rnd() * 560, l = 34 + rnd() * 24;
    rain += `<line x1="${x.toFixed(0)}" y1="${y.toFixed(0)}" x2="${(x - l * 0.32).toFixed(0)}" y2="${(y + l).toFixed(0)}"/>`;
  }
  const ROUTE = 'M1192 892 C1330 962 1410 806 1500 774 S 1654 694 1716 566';

  Deck.register({
    id: 's6', order: 6, title: 'Thank you', steps: 2, time: [285, 300],
    notes: {
      title: 'Thank you',
      script: 'Thank you. With open data, a clear alert and a route that is practised, next time Johan knows what to do and where to go.',
      notes: [
        'Closing line: next time, Johan knows what to do and where to go.',
        'Team 1, European AI Challenge 2026, organised by FARI and the Joint Research Centre.',
      ],
    },
    html: `
      <div class="s6-left">
        <span class="s6-rule" data-b="0"></span>
        <h1 class="h-hero s6-title" data-b="0">Thank you.</h1>
        <p class="lead s6-tag" data-b="1">Next time, Johan knows where to go.</p>
        <p class="s6-team" data-b="0">${TEAM} · European AI Challenge 2026</p>
      </div>
      <svg class="s6-scene" viewBox="0 0 1920 1080" aria-hidden="true">
        <g class="s6-rain">${rain}</g>
        <path class="s6-route-case" d="${ROUTE}"/>
        <path class="s6-route" d="${ROUTE}"/>
        <g class="s6-pin" transform="translate(1716 566)"><g class="s6-pin-in">
          <path d="M0 0C-22-28-30-42-30-54a30 30 0 1 1 60 0C30-42 22-28 0 0Z"/><circle cx="0" cy="-54" r="11"/>
        </g></g>
      </svg>
      <div class="s6-confetti" aria-hidden="true">${confetti}</div>
      <div class="s6-shadow"></div>
      <figure class="s6-johan"><img src="assets/johan/johan-phone-tight.png" width="535" height="1152" decoding="async"
        alt="Illustration: Johan, a boy in a yellow raincoat, reading the message on his phone"></figure>`,

    mount(el) {
      this.route = el.querySelector('.s6-route'); this.casing = el.querySelector('.s6-route-case');
      this.hide();
    },

    hide() {
      [this.route, this.casing].forEach(p => {
        if (!p) return;
        const len = p.getTotalLength();
        p.style.transition = 'none'; p.style.strokeDasharray = `${len} ${len}`; p.style.strokeDashoffset = len;
      });
    },

    step(el, n) {
      if (n >= 1) {
        Deck.draw(this.casing, { duration: 1700, delay: 250 });
        Deck.draw(this.route, { duration: 1700, delay: 250 });
      } else this.hide();
    },
  });
})();
