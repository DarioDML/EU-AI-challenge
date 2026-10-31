/* Motion layer. Loaded after the slide files and before Deck.start(); it never changes the engine.
   A MutationObserver watches slide class/data-step and emits the existing document events:
     deck:leave {id, el, dir}   deck:enter {id, el, index, dir}   deck:step {id, el, step, dir, enter}
     dir: 1 forward, -1 back, 0 first paint.

   Opt-in attributes, active within the element's/ancestors' data-b and data-b-out window:
     data-stagger="120"   delays per build (max 1.2 s), with data-stagger-delay and order (dom/row/col/random)
     data-tick="1234.5"   count up from 0; data-decimals, prefix, suffix, tick-ms/delay/update-ms
     data-draw            SVG shape/group draws in; data-draw-ms/delay/ease (max 2.4 s); data-draw-lead adds a gold
                          dot with a soft halo riding the drawn tip (the last shape of the group)
     data-at="K" / data-until="K"   build window without build styling (like data-b / data-b-out)
   Legacy data-kenburns, .pulse and flow hooks no longer add cloned elements; .pulse is a CSS halo only.
   Mood metadata and DeckMotion.refresh/current remain available for existing consumers.

   Forward builds reveal once; back restores numbers/visible paths and cancels hidden work.
   ?static, reduced motion and instant jumps settle immediately. Preference changes cancel pending work. */
(function () {
  'use strict';
  const D = window.Deck;
  const host = document.getElementById('deck') || document.querySelector('.deck') || document.getElementById('slides');
  if (!D || !host) return;
  const stage = document.getElementById('stage') || host.parentElement;
  const STATIC = new URLSearchParams(location.search).has('static');
  const motionQuery = matchMedia('(prefers-reduced-motion: reduce)');
  // Read the live preference; the engine may have cached its value at page load.
  const reduced = () => STATIC || motionQuery.matches;
  const isQuiet = () => reduced() || (stage && stage.classList.contains('instant'));
  const EASE = 'cubic-bezier(0.2, 0, 0.2, 1)';
  if (STATIC) document.documentElement.classList.add('static');
  const MOODS = { s1: 'cinematic', s5: 'cinematic', s2: 'editorial', s3: 'pro', s4: 'pro' };
  const PRIM = '[data-tick], [data-draw]';
  const LIVE_MS = 700;            // matches the slide crossfade
  const DRAW_MS = 900;
  const bounded = (value, max) => Math.max(0, Math.min(max, value));

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
      const vb = n.getAttribute('data-b') ?? n.getAttribute('data-at'), vo = n.getAttribute('data-b-out') ?? n.getAttribute('data-until');
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
      const gap = bounded(attr(box, 'data-stagger', 80), 240), base = bounded(attr(box, 'data-stagger-delay', 0), 1000);
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
          it._mDelay = reduced() ? 0 : bounded(base + i * gap, 1200);
          it.style.setProperty('--m-delay', it._mDelay + 'ms');
        });
      });
    });
  }

  /* Reveal the original SVG geometry once; preserve its build opacity transition. */
  const drawings = new WeakMap();
  const shapes = el => (el instanceof SVGGeometryElement ? [el]
    : Array.from(el.querySelectorAll('path, line, polyline, polygon, circle, ellipse, rect')));
  /* data-draw-lead: a gold dot with a soft halo rides the drawn tip. Same easing and duration as the stroke, so the
     dot sits exactly on the end of the line; Web Animations transform keyframes sampled along the path. */
  const SVGNS = 'http://www.w3.org/2000/svg';
  function stopLead(el) {
    if (el._mLead) { el._mLead.anim && el._mLead.anim.cancel(); el._mLead.anim = null; el._mLead.g.style.opacity = '0'; }
  }
  function startLead(el, opt) {
    stopLead(el);
    const list = shapes(el), path = list[list.length - 1];
    if (!path || typeof path.animate !== 'function') return;
    let len = 0;
    try { len = path.getTotalLength(); } catch (e) { return; }
    if (!(len > 0)) return;
    let lead = el._mLead;
    if (!lead || !lead.g.isConnected) {
      const g = document.createElementNS(SVGNS, 'g');
      g.setAttribute('class', 'm-lead'); g.setAttribute('aria-hidden', 'true'); g.style.opacity = '0';
      g.innerHTML = '<circle class="m-lead-halo" r="17"></circle><circle class="m-lead-core" r="7"></circle>';
      (el.nextSibling ? el.parentNode.insertBefore(g, el.nextSibling) : el.parentNode.appendChild(g));
      lead = el._mLead = { g, anim: null };
    }
    const n = Math.max(24, Math.min(220, Math.round(len / 6))), kf = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n, q = path.getPointAtLength(len * t);
      kf.push({ offset: t, opacity: Math.min(1, t / 0.03, (1 - t) / 0.05), transform: `translate(${q.x}px, ${q.y}px)` });
    }
    lead.anim = lead.g.animate(kf, { duration: opt.ms, delay: opt.delay, easing: opt.ease, fill: 'both' });
    lead.anim.onfinish = () => { lead.g.style.opacity = '0'; lead.anim && lead.anim.cancel(); lead.anim = null; };
  }

  function stroke(el, on, opt) {
    stopLead(el);
    if (on && opt && el.hasAttribute('data-draw-lead') && !isQuiet()) startLead(el, opt);
    shapes(el).forEach(p => {
      let len = 0;
      try { len = p.getTotalLength(); } catch (e) { /* not rendered */ }
      if (!(len > 0)) return;
      // SVG pathLength normalises dash units when it is supplied.
      len = p.pathLength && p.pathLength.baseVal.value > 0 ? p.pathLength.baseVal.value : len;
      let state = drawings.get(p);
      if (!state) {
        state = { original: ['stroke-dasharray', 'stroke-dashoffset'].map(name =>
          [name, p.style.getPropertyValue(name), p.style.getPropertyPriority(name)]), animation: null };
        drawings.set(p, state);
      }
      if (state.animation) { state.animation.cancel(); state.animation = null; }
      const restore = () => state.original.forEach(([name, value, priority]) => {
        if (value) p.style.setProperty(name, value, priority); else p.style.removeProperty(name);
      });
      if (on && !opt) { restore(); return; }
      p.style.strokeDasharray = `${len} ${len}`;
      p.style.strokeDashoffset = on ? '0' : String(len);
      if (!on || !opt) return;
      // A separate animation leaves authored opacity/transform transitions untouched.
      const animation = p.animate([{ strokeDashoffset: String(len) }, { strokeDashoffset: '0' }], {
        duration: opt.ms, delay: opt.delay, easing: opt.ease, fill: 'backwards',
      });
      state.animation = animation;
      animation.onfinish = () => {
        if (state.animation !== animation) return;
        state.animation = null;
        restore();
        animation.cancel();
      };
    });
  }
  const drawOpt = (el, slide) => ({
    ms: bounded(attr(el, 'data-draw-ms', DRAW_MS), 2400),
    delay: bounded(attr(el, 'data-draw-delay', 0) + delayOf(el, slide), 1500),
    ease: el.getAttribute('data-draw-ease') || 'cubic-bezier(0.45, 0, 0.2, 1)',
  });

  /* Keep the actual displayed value so an interrupted update starts where the audience saw it. */
  function tickOpt(el, mode) {
    return {
      decimals: bounded(parseInt(el.getAttribute('data-decimals'), 10) || 0, 20),
      prefix: el.getAttribute('data-prefix') || '',
      suffix: el.getAttribute('data-suffix') || '',
      duration: bounded(attr(el, mode === 'to' ? 'data-tick-update-ms' : 'data-tick-ms', mode === 'to' ? 450 : 1000), 2000),
    };
  }
  function tick(el, mode, slide) {
    clearTimeout(el._mTickT);
    cancelAnimationFrame(el._tickRaf);
    el._mTickT = el._tickRaf = null;
    const to = parseFloat(el.getAttribute('data-tick'));
    if (!Number.isFinite(to)) return;
    const o = tickOpt(el, mode);
    const paint = v => { el._tickVal = v; el.textContent = o.prefix + D.fmt(v, o.decimals) + o.suffix; };
    if (mode === 'final' || isQuiet() || !o.duration) { paint(to); return; }
    slide = slide || el.closest('.slide');
    if (mode === 'up') paint(0);
    const from = Number.isFinite(el._tickVal) ? el._tickVal : to;
    if (from === to) { paint(to); return; }
    const delay = mode === 'up' ? bounded(attr(el, 'data-tick-delay', 0) + delayOf(el, slide), 1500) : 0;
    const live = () => el.isConnected && slide === cur && isOn(slide) && onAt(el, slide, curStep);
    const run = () => {
      el._mTickT = null;
      if (!live()) return;
      if (isQuiet()) { paint(to); return; }
      const start = performance.now();
      const frame = now => {
        el._tickRaf = null;
        if (!live()) return;
        const t = isQuiet() ? 1 : bounded((now - start) / o.duration, 1);
        paint(t === 1 ? to : from + (to - from) * (1 - Math.pow(1 - t, 3)));
        if (t < 1) el._tickRaf = requestAnimationFrame(frame);
      };
      el._tickRaf = requestAnimationFrame(frame);
    };
    if (delay > 0) el._mTickT = setTimeout(run, delay); else run();
  }

  function prepare(slide) {
    if (!slide.dataset.mood) slide.dataset.mood = MOODS[slide.id] || 'editorial';
    stagger(slide);
  }

  function show(p, slide, animate) {
    if (p.hasAttribute('data-draw')) stroke(p, true, animate ? drawOpt(p, slide) : null);
    if (p.hasAttribute('data-tick')) tick(p, animate ? 'up' : 'final', slide);
  }
  function hide(p) {
    if (p.hasAttribute('data-draw')) stroke(p, false, null);
    if (p.hasAttribute('data-tick')) tick(p, 'final');
  }
  function applyStep(slide, step, dir, entering, quiet) {
    const animate = !quiet && dir > 0;                 // builds play forward; going back restores
    slide.querySelectorAll(PRIM).forEach(p => {
      const on = onAt(p, slide, step), was = shown.get(p);
      if (on === was && !entering && !quiet && dir > 0) return;
      shown.set(p, on);
      if (on) show(p, slide, animate);
      else hide(p);
    });
  }

  function enterSlide(el, dir) {
    clearTimeout(el._mLiveT);
    el._mLiveT = null;
    el.classList.remove('m-out', 'm-from');
    el.classList.toggle('m-back', dir < 0);
    el.classList.add('m-live');
    if (stage) stage.dataset.mood = el.dataset.mood || MOODS[el.id] || 'editorial';
    // Let CSS reverse an in-flight fade naturally; never reset a returning slide to opacity zero.
  }
  function leaveSlide(el, dir, quiet) {
    el.classList.add('m-out');
    el.classList.toggle('m-back', dir < 0);
    el.querySelectorAll(PRIM).forEach(p => {
      if (p.hasAttribute('data-draw')) stroke(p, onAt(p, el, +el.dataset.step || 0), null);
      if (p.hasAttribute('data-tick')) tick(p, 'final', el);
      shown.set(p, false);
    });
    clearTimeout(el._mLiveT);
    const stop = () => {
      el._mLiveT = null;
      if (el === cur || isOn(el)) return;
      el.classList.remove('m-live', 'm-out', 'm-back', 'm-from');
      el.querySelectorAll(PRIM).forEach(hide);
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
      const quiet = isQuiet() || !prev;
      cur = el; curIdx = idx; curStep = step;
      el.classList.toggle('m-back', dir < 0);
      if (entering) {
        if (prev) leaveSlide(prev, dir, quiet);
        enterSlide(el, dir);
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
  new MutationObserver(recs => {
    const changed = new Set(recs.filter(r => r.oldValue !== r.target.getAttribute('data-tick')).map(r => r.target));
    changed.forEach(el => tick(el, shown.get(el) === true ? 'to' : 'final'));
  }).observe(host, { subtree: true, attributes: true, attributeFilter: ['data-tick'], attributeOldValue: true });

  function settle() {
    Array.from(host.children).filter(isSlide).forEach(slide => {
      clearTimeout(slide._mLiveT);
      slide._mLiveT = null;
      if (slide !== cur) slide.classList.remove('m-live', 'm-out', 'm-back', 'm-from');
      slide.querySelectorAll(PRIM).forEach(p => {
        const on = slide === cur && onAt(p, slide, curStep);
        shown.set(p, on);
        if (p.hasAttribute('data-draw')) stroke(p, on, null);
        if (p.hasAttribute('data-tick')) tick(p, 'final', slide);
      });
    });
  }
  function settleReducedMotion() {
    if (stage) stage.classList.toggle('motion-reduced', reduced());
    Array.from(host.children).filter(isSlide).forEach(stagger);
    if (isQuiet()) settle();
  }
  // Instant hash jumps can keep a visible primitive in the same build window.
  if (stage) {
    let instant = stage.classList.contains('instant');
    new MutationObserver(() => {
      const next = stage.classList.contains('instant');
      if (next && !instant) settle();
      instant = next;
    }).observe(stage, { attributes: true, attributeFilter: ['class'] });
  }
  motionQuery.addEventListener('change', settleReducedMotion);
  settleReducedMotion();
  sync();

  window.DeckMotion = {
    get reduced() { return reduced(); }, moods: MOODS,
    /* after a slide rebuilt its DOM: re-stagger and play primitives that are new on screen */
    refresh(root) {
      const slide = root || cur;
      if (!slide) return;
      prepare(slide);
      if (slide === cur) applyStep(cur, curStep, 1, false, isQuiet());
    },
    get current() { return cur ? { id: cur.id, step: curStep } : null; },
  };
})();
