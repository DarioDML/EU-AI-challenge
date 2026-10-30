/* Slide 5 · Every valley in Europe (4:15-5:00). Owner: agent 6. */
(function () {
  'use strict';
  const TEAM = 'Team 1';                                   // ← the team name on the closing lockup

  /* Figures from the team policy brief, not from window.PITCH (not re-checked here, see blueprint section 8).
     Printed with their sources in the .src caption of step 1. */
  const FIG = {
    deaths: 230,               // ~230 lives lost, July 2021 floods in BE, DE and NL: brief refs [2], [9], [20]
    damageLo: 32, damageHi: 53, // €32-53 bn damage: brief refs [2], [9], [20]
    roi: 10,                   // ~10× return on early warning: WMO 2022, brief ref [24]
  };
  const PIN = { x: 32.96, y: 58.9 };                        // Ahr valley in europe.png, % of the image box (blueprint 4)
  let timer = 0;

  Deck.register({
    id: 's5', order: 5, title: 'Every valley in Europe', steps: 3, time: [255, 300],

    notes: {
      title: 'Every valley in Europe',
      script: 'Next time, Johan knows where to go: a shelter with room, and a route that avoids flooded roads. ' +
        "Johan's valley is one of many: in July 2021, the floods cost around 230 lives and 32 to 53 billion euros. " +
        'Early warning pays back about ten times its cost. ' +
        'We built this only on open EU-wide data, so the method can be repeated for other valleys. ' +
        'So, to crisis authorities in Belgium, Germany and the Netherlands: designate and publish flood shelters, ' +
        'make every alert answer three questions, and drill the route at school. ' +
        'Next time, Johan knows what to do and where to go.',
      notes: [
        'Outcome: Johan knows where to go, a shelter with room and a route that avoids flooded roads.',
        'Stakes: July 2021 cost ~230 lives and €32-53 bn in BE, DE and NL (team brief refs [2], [9], [20]); early warning returns ~10× (WMO 2022, ref [24]).',
        'Built only on open EU-wide data (Copernicus EMS, EFAS, GHSL, OpenStreetMap), so the method can be repeated elsewhere.',
        'The ask to crisis authorities in BE, DE and NL: designate and publish flood shelters; make every alert answer three questions; drill the route at school.',
      ],
    },

    html: `
      <div class="s5-shelter">
        <figure class="s5-shot">
          <img src="assets/johan/johan-shelter.png" width="2047" height="976" decoding="async"
               alt="Illustration: Johan walking with his phone along a path to a shelter on a hill above the water">
        </figure>
      </div>
      <h1 class="h1 s5-title" data-b="0" data-b-out="1">Next time, Johan<br>knows where to go.</h1>

      <div class="s5-map">
        <img class="s5-europe" src="assets/europe.png" width="2500" height="2166" decoding="async"
             alt="Map of Europe with the Ahr valley in Germany marked">
        <div class="s5-pin" style="left:${PIN.x}%;top:${PIN.y}%">
          <i class="s5-ring"></i><i class="s5-dot"></i>
          <span class="s5-pin-label" data-b="1" data-b-out="2">Ahr valley</span>
        </div>
      </div>

      <div class="s5-stats">
        <div class="s5-stat" data-b="1" data-b-out="2">
          <span class="s5-num num"><span class="s5-dim">~</span><span class="tk" data-to="${FIG.deaths}">${FIG.deaths}</span></span>
          <span class="s5-lbl">lives lost</span>
        </div>
        <div class="s5-stat" data-b="1" data-b-out="2">
          <span class="s5-num num"><span class="s5-cur">€</span><span class="tk" data-to="${FIG.damageLo}">${FIG.damageLo}</span><span class="s5-dash">-</span><span class="tk" data-to="${FIG.damageHi}">${FIG.damageHi}</span><span class="s5-unit">bn</span></span>
          <span class="s5-lbl">damage</span>
        </div>
        <div class="s5-stat" data-b="1" data-b-out="2">
          <span class="s5-num num"><span class="s5-dim">~</span><span class="tk" data-to="${FIG.roi}">${FIG.roi}</span>×</span>
          <span class="s5-lbl">return on early warning</span>
        </div>
      </div>
      <p class="s5-data" data-b="1" data-b-out="2">Built only on open EU-wide data:<span class="s5-data-list">Copernicus EMS · EFAS · GHSL · OpenStreetMap</span></p>
      <p class="src s5-src" data-b="1" data-b-out="2">July 2021 floods in BE, DE and NL. Deaths and damage: team policy brief refs [2], [9], [20]; return on early warning: WMO 2022, ref [24]</p>

      <div class="s5-ask">
        <p class="kicker" data-b="2">To crisis authorities in BE · DE · NL</p>
        <ol>
          <li data-b="2"><span class="s5-an">1</span><span>Designate and publish flood shelters.</span></li>
          <li data-b="2"><span class="s5-an">2</span><span>Make every alert answer three questions.</span></li>
          <li data-b="2"><span class="s5-an">3</span><span>Drill the route at school.</span></li>
        </ol>
      </div>

      <div class="s5-lockup" data-b="2">
        <span class="s5-team">${TEAM}</span>
        <span class="s5-event">European AI Challenge 2026</span>
        <span class="s5-orgs">
          <span class="s5-wm s5-wm-fari" data-wordmark="fari"><span class="s5-wm-text">FARI</span></span>
          <span class="s5-x" aria-hidden="true">×</span>
          <span class="s5-wm s5-wm-jrc" data-wordmark="jrc"><span class="s5-wm-text">Joint Research Centre</span></span>
        </span>
      </div>`,

    mount(el, P, D) {
      // organisers' logo files (assets/logos/), when the engine finds them: replace the typographic wordmarks
      const put = (name, src) => {
        const slot = el.querySelector(`[data-wordmark="${name}"]`);
        if (!slot || !src || slot.classList.contains('has-logo')) return;
        const img = new Image();
        img.alt = slot.textContent.trim();
        img.src = src;
        slot.prepend(img);
        slot.classList.add('has-logo');
      };
      Object.keys((D && D.logos) || {}).forEach(name => put(name, D.logos[name]));
      document.addEventListener('deck:logos', e => put(e.detail.name, e.detail.src));
    },

    step(el, n, dir) {
      clearTimeout(timer);
      if (n !== 1) return;
      const ticks = [...el.querySelectorAll('.s5-stat .tk')];
      if (dir < 0 || Deck.reduced) { ticks.forEach(t => Deck.tick(t, +t.dataset.to, { duration: 0 })); return; }
      ticks.forEach(t => Deck.tick(t, 0, { duration: 0 }));
      timer = setTimeout(() => ticks.forEach(t => Deck.tick(t, +t.dataset.to, { duration: 1500 })), 820);
    },

    leave() { clearTimeout(timer); },
  });
})();
