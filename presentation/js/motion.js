/* Motion layer (agent 9). Loaded after the slide files and before Deck.start(); it never changes the engine.
   A MutationObserver watches each slide <section> (class, data-step) and drives:

   Events on document, detail:
     deck:leave {id, el, dir}   deck:enter {id, el, index, dir}   deck:step {id, el, step, dir, enter}
     dir: 1 forward, -1 back, 0 first paint or jump.

   Opt-in attributes. Each fires when its element's build is on screen (step >= its data-b, or at once without one):
     data-stagger="100"            container: its [data-b] and [data-stagger-item] descendants get rising delays,
                                   counted per build step (+ data-stagger-delay="ms"; data-stagger-order="row|col|random", default DOM order)
     data-tick="1234.5"            counts up from 0 (data-decimals, data-prefix, data-suffix, data-tick-ms,
                                   data-tick-delay); writing a new data-tick eases to it (data-tick-update-ms)
     data-draw                     SVG shape, or a group of shapes, draws in (data-draw-ms, data-draw-delay,
                                   data-draw-ease); erased when its build is hidden again going back
     data-kenburns                 image wrapper: its picture zooms 1 -> 1.04 over 14 s while the slide is on screen (CSS)
     .pulse                        gold halo ring (CSS ::after; an SVG circle.pulse gets a ring circle)
     .flow[data-path="M0 0 H200"]  HTML gold dot along a path, in its positioned parent's px
     path[data-flow]               SVG gold dot along that path (data-flow-ms, data-flow-delay, data-flow-dots, data-flow-r)
   Moods (light theme): data-mood on each slide (s1, s5 cinematic; s2 editorial; s3, s4 pro; a slide may set its own in mount),
   mirrored on #stage[data-mood] for the faint navy grid (editorial, pro) and a soft spotlight (cinematic).

   Builds animate going forward; going back restores final states at once (draws are erased).
   Under Deck.reduced (prefers-reduced-motion or ?static) everything lands in its final state at once. */
(function () {
  'use strict';
  const D = window.Deck;
  const host = document.getElementById('deck') || document.querySelector('.deck') || document.getElementById('slides');
  if (!D || !host) return;
  const stage = document.getElementById('stage') || host.parentElement;
  const REDUCED = !!D.reduced;
  const SPRING = D.SPRING || 'cubic-bezier(0.16, 1, 0.3, 1)';
  const EASE_IO = 'cubic-bezier(0.65, 0, 0.35, 1)';
  const SVGNS = 'http://www.w3.org/2000/svg';
  const MOODS = { s1: 'cinematic', s5: 'cinematic', s2: 'editorial', s3: 'pro', s4: 'pro' };
  const PRIM = '[data-tick], [data-draw], .flow[data-path], [data-flow]';
  const LIVE_MS = 1600;            // a slide that left keeps its loops running while it fades out
  const DRAW_MS = 1200;

  const num = (v, d) => { const n = parseFloat(v); return Number.isFinite(n) ? n : d; };
  const attr = (el, name, d) => num(el.getAttribute(name), d);
  const emit = (name, detail) => document.dispatchEvent(new CustomEvent(name, { detail }));
  const isSlide = n => n.nodeType === 1 && n.classList.contains('slide');
  const isOn = el => el.classList.contains('is-active') || el.classList.contains('active');

  let cur = null, curIdx = -1, curStep = 0;
  const shown = new WeakMap();     // primitive -> on screen at the last sync

  /* Build window of an element: from the highest data-b on it or its ancestors, until the lowest data-b-out. */
  function range(el, slide) {
    let b = 0, out = Infinity;
    for (let n = el; n && n !== slide; n = n.parentElement) {
      const vb = n.getAttribute('data-b'), vo = n.getAttribute('data-b-out');
      if (vb !== null) b = Math.max(b, parseInt(vb, 10) || 0);
      if (vo !== null) out = Math.min(out, parseInt(vo, 10) || 0);
    }
    return [b, out];
  }
  const onAt = (el, slide, step) => { const [b, out] = range(el, slide); return step >= b && step < out; };
  function delayOf(el, slide) {
    for (let n = el; n && n !== slide; n = n.parentElement) if (n._mDelay !== undefined) return n._mDelay;
    return 0;
  }

  /* data-stagger: delays per build step, exposed as --m-delay (read by motion.css on the way in only). */
  function stagger(root) {
    root.querySelectorAll('[data-stagger]').forEach(box => {
      const gap = attr(box, 'data-stagger', 100), base = attr(box, 'data-stagger-delay', 0);
      const order = box.getAttribute('data-stagger-order') || 'dom';          // dom | row | col | random
      const slide = box.closest('.slide') || root, groups = new Map();
      box.querySelectorAll('[data-b], [data-stagger-item]').forEach(it => {
        if (it.parentElement.closest('[data-stagger]') !== box) return;            // a nested container owns it
        if (!it.hasAttribute('data-b')) it.setAttribute('data-b', String(range(it.parentElement, slide)[0]));
        const k = it.getAttribute('data-b');
        if (!groups.has(k)) groups.set(k, []);
        groups.get(k).push(it);
      });
      groups.forEach(list => {
        if (order === 'row' || order === 'col') {
          const r = new Map(list.map(it => [it, it.getBoundingClientRect()])), y = order === 'row';
          list.sort((m, n) => (y ? r.get(m).top - r.get(n).top || r.get(m).left - r.get(n).left
                                 : r.get(m).left - r.get(n).left || r.get(m).top - r.get(n).top));
        } else if (order === 'random') {                                           // seeded: same sweep every run
          let seed = 7;
          const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
          for (let i = list.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [list[i], list[j]] = [list[j], list[i]]; }
        }
        list.forEach((it, i) => {
          it._mDelay = REDUCED ? 0 : base + i * gap;
          it.style.setProperty('--m-delay', it._mDelay + 'ms');
        });
      });
    });
  }

  /* data-draw: stroke-dashoffset, like Deck.draw, plus a short opacity fade and erase from the current length. */
  const shapes = el => (el instanceof SVGGeometryElement ? [el]
    : Array.from(el.querySelectorAll('path, line, polyline, polygon, circle, ellipse, rect')));
  function stroke(el, on, opt) {
    const list = [];
    shapes(el).forEach(p => {
      let len = 0;
      try { len = p.getTotalLength(); } catch (e) { /* not rendered */ }
      if (len > 0) list.push([p, len]);
    });
    if (!list.length) return;
    list.forEach(([p, len]) => {
      p.style.strokeDasharray = `${len} ${len}`;
      p.style.transition = 'none';
      if (!opt) { p.style.strokeDashoffset = on ? 0 : len; return; }
      p.style.strokeDashoffset = opt.fromCurrent ? (parseFloat(getComputedStyle(p).strokeDashoffset) || 0) : (on ? len : 0);
    });
    if (!opt) return;
    list[0][0].getBoundingClientRect();                                          // commit the start state
    const { ms, delay, ease } = opt;
    const fade = on ? `opacity 240ms linear ${delay}ms` : `opacity 160ms linear ${Math.max(0, delay + ms - 160)}ms`;
    list.forEach(([p, len]) => {
      p.style.transition = `stroke-dashoffset ${ms}ms ${ease} ${delay}ms, ${fade}`;
      p.style.strokeDashoffset = on ? 0 : len;
    });
  }
  const drawOpt = (el, slide) => ({
    ms: attr(el, 'data-draw-ms', DRAW_MS),
    delay: attr(el, 'data-draw-delay', 0) + delayOf(el, slide),
    ease: el.getAttribute('data-draw-ease') || SPRING,
  });

  /* data-tick: count up with Deck.tick (easeOutExpo). mode 'up' from 0, 'to' from the shown value, 'final' at once. */
  function tickOpt(el, mode) {
    return {
      decimals: Math.max(0, parseInt(el.getAttribute('data-decimals'), 10) || 0),
      prefix: el.getAttribute('data-prefix') || '',
      suffix: el.getAttribute('data-suffix') || '',
      duration: mode === 'to' ? attr(el, 'data-tick-update-ms', 450) : attr(el, 'data-tick-ms', 1100),
    };
  }
  function tick(el, mode, slide) {
    const to = parseFloat(el.getAttribute('data-tick'));
    if (!Number.isFinite(to)) return;
    const o = tickOpt(el, mode);
    const paint = v => { el._tickVal = v; el.textContent = o.prefix + D.fmt(v, o.decimals) + o.suffix; };
    clearTimeout(el._mTickT);
    cancelAnimationFrame(el._tickRaf);
    if (mode === 'final' || REDUCED) { paint(to); return; }
    if (mode === 'up') paint(0);
    const delay = mode === 'up' ? attr(el, 'data-tick-delay', 0) + delayOf(el, slide) : 0;
    const run = () => D.tick(el, to, o);
    if (delay > 0) el._mTickT = setTimeout(run, delay); else run();
  }

  /* .flow / [data-flow]: dots move with transform keyframes sampled along the path (Web Animations, GPU for HTML). */
  let sampler = null;
  function pathFromD(d) {
    if (!sampler) {
      sampler = document.createElementNS(SVGNS, 'svg');
      sampler.setAttribute('aria-hidden', 'true');
      sampler.style.cssText = 'position:absolute;left:0;top:0;width:0;height:0;overflow:hidden;visibility:hidden;pointer-events:none';
      sampler.appendChild(document.createElementNS(SVGNS, 'path'));
      document.body.appendChild(sampler);
    }
    sampler.firstChild.setAttribute('d', d);
    return sampler.firstChild;
  }
  function frames(path, svg) {
    const len = path.getTotalLength(), n = Math.max(12, Math.min(180, Math.round(len / 8)));
    const out = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n, q = path.getPointAtLength(len * t);
      out.push({
        offset: t,
        opacity: Math.max(0, Math.min(1, t / 0.08, (1 - t) / 0.14)),
        transform: svg ? `translate(${q.x}px, ${q.y}px)` : `translate3d(${q.x}px, ${q.y}px, 0)`,
      });
    }
    return out;
  }
  function svgDots(path, n) {
    let track = path._mTrack;
    if (!track || !track.isConnected) {
      track = document.createElementNS(SVGNS, 'g');
      track.setAttribute('class', 'm-flow-track');
      track.setAttribute('aria-hidden', 'true');
      const tf = path.getAttribute('transform');
      if (tf) track.setAttribute('transform', tf);
      path.after(track);
      path._mTrack = track;
    }
    const r = attr(path, 'data-flow-r', 5);
    while (track.childElementCount < n) {
      const g = document.createElementNS(SVGNS, 'g');
      g.setAttribute('class', 'm-flow-dot');
      g.innerHTML = `<circle class="m-flow-glow" r="${r * 2.6}"></circle><circle r="${r}"></circle>`;
      track.appendChild(g);
    }
    while (track.childElementCount > n) track.lastElementChild.remove();
    return Array.from(track.children);
  }
  function htmlDots(el, n) {
    const list = [el];
    el._mClones = (el._mClones || []).filter(c => c.isConnected);
    while (el._mClones.length < n - 1) {
      const c = el.cloneNode(false);
      ['id', 'data-path', 'data-b', 'data-b-out'].forEach(a => c.removeAttribute(a));
      c.classList.add('m-flow-clone');
      c.setAttribute('aria-hidden', 'true');
      el.after(c);
      el._mClones.push(c);
    }
    el._mClones.forEach((c, i) => { if (i < n - 1) list.push(c); });
    return list;
  }
  function flowStop(el) {
    (el._mFlow || []).forEach(a => a.cancel());
    el._mFlow = null;
  }
  function flowStart(el, slide, withDelay) {
    flowStop(el);
    if (REDUCED || typeof el.animate !== 'function') return;
    const svg = !el.classList.contains('flow');
    const path = svg ? el : pathFromD(el.getAttribute('data-path') || '');
    let kf;
    try { kf = frames(path, svg); } catch (e) { return; }
    const ms = attr(el, 'data-flow-ms', 2400);
    const n = Math.max(1, parseInt(el.getAttribute('data-flow-dots'), 10) || 1);
    let delay = 0;
    if (withDelay) {
      delay = attr(el, 'data-flow-delay', 0) + delayOf(el, slide);
      if (el.hasAttribute('data-draw')) delay += attr(el, 'data-draw-ms', DRAW_MS) + attr(el, 'data-draw-delay', 0);
    }
    const easing = el.getAttribute('data-flow-ease') || (n > 1 ? 'linear' : 'cubic-bezier(0.45, 0, 0.55, 1)');
    const dots = svg ? svgDots(el, n) : htmlDots(el, n);
    el._mFlow = dots.map((dot, i) => dot.animate(kf, { duration: ms, delay: delay + (i * ms) / n, iterations: Infinity, easing, fill: 'backwards' }));
  }

  /* SVG pins: circle.pulse gets a ring behind it (HTML pins use .pulse::after in motion.css). */
  function prepare(slide) {
    if (!slide.dataset.mood) slide.dataset.mood = MOODS[slide.id] || 'editorial';
    stagger(slide);
    slide.querySelectorAll('circle.pulse').forEach(c => {
      if (c._mRing && c._mRing.isConnected) return;
      const ring = c.cloneNode(false);
      ['id', 'data-draw', 'data-flow', 'data-tick'].forEach(a => ring.removeAttribute(a));
      ring.setAttribute('class', 'm-pulse-ring');
      ring.setAttribute('aria-hidden', 'true');
      c.before(ring);
      c._mRing = ring;
    });
  }

  function show(p, slide, animate) {
    if (p.hasAttribute('data-draw')) stroke(p, true, animate ? drawOpt(p, slide) : null);
    if (p.hasAttribute('data-tick')) tick(p, animate ? 'up' : 'final', slide);
    if (p.hasAttribute('data-flow') || p.classList.contains('flow')) flowStart(p, slide, animate);
  }
  function hide(p, slide, erase, entering) {
    if (p.hasAttribute('data-draw')) {
      if (erase) stroke(p, false, { ms: Math.min(700, Math.round(attr(p, 'data-draw-ms', DRAW_MS) * 0.45)), delay: 0, ease: EASE_IO, fromCurrent: true });
      else if (entering) stroke(p, false, null);       // hidden at entry: no stale line
    }
    if (p.hasAttribute('data-tick')) clearTimeout(p._mTickT);
    if (p.hasAttribute('data-flow') || p.classList.contains('flow')) flowStop(p);
  }
  function applyStep(slide, step, dir, entering, quiet) {
    const animate = !quiet && dir > 0;                 // builds play forward; going back restores
    slide.querySelectorAll(PRIM).forEach(p => {
      if (p.classList.contains('m-flow-clone')) return;
      const on = onAt(p, slide, step), was = shown.get(p) === true;
      if (on === was && !(entering && !on)) return;
      shown.set(p, on);
      if (on) show(p, slide, animate);
      else hide(p, slide, !quiet && dir < 0, entering);
    });
  }

  function enterSlide(el, dir, quiet) {
    clearTimeout(el._mLiveT);
    el.classList.remove('m-out');
    el.classList.toggle('m-back', dir < 0);
    el.classList.add('m-live');
    if (stage) stage.dataset.mood = el.dataset.mood || MOODS[el.id] || 'editorial';
    if (quiet) return;
    el.classList.add('m-from');                        // start state with transitions off (motion.css) ...
    void el.offsetWidth;                               // ... committed ...
    el.classList.remove('m-from');                     // ... then the spring takes it to rest
  }
  function leaveSlide(el, dir, quiet) {
    el.classList.add('m-out');
    el.classList.toggle('m-back', dir < 0);
    el.querySelectorAll(PRIM).forEach(p => { shown.set(p, false); clearTimeout(p._mTickT); });
    clearTimeout(el._mLiveT);
    const stop = () => {
      if (el === cur) return;
      el.classList.remove('m-live');
      el.querySelectorAll(PRIM).forEach(flowStop);
    };
    if (quiet) stop(); else el._mLiveT = setTimeout(stop, LIVE_MS);
  }

  function sync() {
    try {
      const list = Array.prototype.filter.call(host.children, isSlide);
      const el = list.find(isOn);
      if (!el) return;
      const step = parseInt(el.getAttribute('data-step'), 10) || 0;
      if (el === cur && step === curStep) return;
      const idx = list.indexOf(el), prev = cur, entering = el !== prev;
      const dir = !prev ? 0 : entering ? Math.sign(idx - curIdx) : Math.sign(step - curStep);
      const quiet = REDUCED || !prev || (stage && stage.classList.contains('instant'));
      cur = el; curIdx = idx; curStep = step;
      if (entering) {
        if (prev) leaveSlide(prev, dir, quiet);
        enterSlide(el, dir, quiet);
      }
      applyStep(el, step, dir, entering, quiet);
      if (entering && prev) emit('deck:leave', { id: prev.id, el: prev, dir });
      if (entering) emit('deck:enter', { id: el.id, el, index: idx, dir });
      emit('deck:step', { id: el.id, el, step, dir, enter: entering });
    } catch (e) { console.error('motion.js', e); }
  }

  const slideObs = new MutationObserver(sync);
  function attach(el) {
    if (el._mAttached) return;
    el._mAttached = true;
    try { prepare(el); } catch (e) { console.error('motion.js', el.id, e); }
    slideObs.observe(el, { attributes: true, attributeFilter: ['class', 'data-step'] });
  }
  new MutationObserver(recs => {
    recs.forEach(r => r.addedNodes.forEach(n => { if (isSlide(n)) attach(n); }));
    sync();
  }).observe(host, { childList: true });
  Array.prototype.filter.call(host.children, isSlide).forEach(attach);

  /* A slide that writes a new data-tick while it is on screen gets an eased update. */
  new MutationObserver(recs => recs.forEach(r => {
    const el = r.target;
    if (r.oldValue !== el.getAttribute('data-tick') && shown.get(el) === true) tick(el, 'to');
  })).observe(host, { subtree: true, attributes: true, attributeFilter: ['data-tick'], attributeOldValue: true });

  sync();

  window.DeckMotion = {
    reduced: REDUCED, moods: MOODS,
    /* after a slide rebuilt its DOM: re-stagger and play primitives that are new on screen */
    refresh(root) {
      const slide = root || cur;
      if (!slide) return;
      prepare(slide);
      if (slide === cur) applyStep(cur, curStep, 1, false, REDUCED);
    },
    get current() { return cur ? { id: cur.id, step: curStep } : null; },
  };
})();
