/* Keynote-style engine for the 5-minute pitch.
   Slides register themselves (Deck.register); the engine scales the 1920x1080 stage, runs builds and keys,
   keeps the 5-minute pace bar and the speaker notes. No dependencies; works from file://. */
(function () {
  'use strict';
  const SPRING = 'cubic-bezier(0.16, 1, 0.3, 1)';
  const params = new URLSearchParams(location.search);
  const STATIC = params.has('static');                       // screenshots: no transitions, final states at once
  const reduced = STATIC || matchMedia('(prefers-reduced-motion: reduce)').matches;
  const TOTAL_S = 300;
  const MAP_NAME = 'visualisation busy roates + flooded areas';  // exact spelling of the team's file
  const defs = [], keyHandlers = new Map();
  let slides = [], cur = 0, step = 0, started = null, clock = null, stage, notesEl;

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const fmt = (n, d = 0) => Number(n).toLocaleString('en-GB', { minimumFractionDigits: d, maximumFractionDigits: d });

  function register(def) { defs.push(def); }

  /* Number ticker: eases from the value on screen to `to` (easeOutExpo). */
  function tick(el, to, opt = {}) {
    if (!el) return;
    const { decimals = 0, prefix = '', suffix = '', duration = 900 } = opt;
    const from = el._tickVal ?? (parseFloat((el.textContent || '').replace(/[^0-9.\-]/g, '')) || 0);
    el._tickVal = to;
    cancelAnimationFrame(el._tickRaf);
    const paint = v => { el.textContent = prefix + fmt(v, decimals) + suffix; };
    if (reduced || !duration || from === to) { paint(to); return; }
    const t0 = performance.now();
    const frame = now => {
      const t = Math.max(0, Math.min(1, (now - t0) / duration));   // rAF time can precede t0
      paint(t >= 1 ? to : from + (to - from) * (1 - Math.pow(2, -10 * t)));
      if (t < 1) el._tickRaf = requestAnimationFrame(frame);
    };
    el._tickRaf = requestAnimationFrame(frame);
  }

  /* SVG path drawing with stroke-dashoffset; reverse = erase. */
  function draw(path, opt = {}) {
    if (!path) return;
    const { duration = 1600, delay = 0, reverse = false } = opt;
    const len = path.getTotalLength();
    path.style.strokeDasharray = `${len} ${len}`;
    path.style.transition = 'none';
    path.style.strokeDashoffset = reverse ? 0 : len;
    path.getBoundingClientRect();
    path.style.transition = reduced ? 'none' : `stroke-dashoffset ${duration}ms ${SPRING} ${delay}ms`;
    path.style.strokeDashoffset = reverse ? len : 0;
  }

  /* Base map: the file the overlay coordinates were fitted to (PITCH.screenshot.file, written by
     build_pitch_data.py from georef.json). The single-file build puts it in window.DECK_INLINE.map. */
  const INLINE = window.DECK_INLINE || {};
  function mapSrc(img) {
    const file = (window.PITCH && window.PITCH.screenshot && window.PITCH.screenshot.file) || `${MAP_NAME}.png`;
    const list = [INLINE.map, `assets/${encodeURIComponent(file)}`].filter(Boolean);
    let i = 0;
    img.onerror = () => { if (++i < list.length) img.src = list[i]; };
    img.src = list[0];
  }

  /* Official logos are used only if the organisers' files are dropped into assets/logos/ (svg or png). */
  const logos = {};
  function loadLogos() {
    document.querySelectorAll('[data-logo]').forEach(slot => {
      const name = slot.dataset.logo, up = name.toUpperCase();
      const supplied = { fari: 'logo FARI.png', jrc: 'logo JRC.jpg' };
      const exts = [supplied[name], ...['svg', 'png', 'jpg'].flatMap(x => [`${name}.${x}`, `logo ${up}.${x}`])].filter(Boolean);
      let i = 0;
      const img = new Image();
      if (INLINE.logos && INLINE.logos[name]) exts.unshift(null);
      img.alt = slot.textContent.trim();
      img.onload = () => {
        logos[name] = img.src;
        slot.classList.add('has-logo');
        slot.prepend(img);
        document.dispatchEvent(new CustomEvent('deck:logos', { detail: { name, src: img.src } }));
      };
      const url = k => (exts[k] === null ? INLINE.logos[name] : `assets/logos/${encodeURIComponent(exts[k])}`);
      img.onerror = () => { if (++i < exts.length) img.src = url(i); };
      img.src = url(0);
    });
  }

  function fit() {
    const vv = window.visualViewport, w = (vv && vv.width) || innerWidth, h = (vv && vv.height) || innerHeight;
    const s = Math.max(0.05, Math.min(w / 1920, h / 1080));
    stage.style.transform = `translate(-50%, -50%) scale(${s})`;
  }

  /* Visible, tiny failure state: a console error plus a message on the stage instead of a blank screen. */
  const problems = [];
  function report(msg) {
    problems.push(msg);
    console.error('[deck] ' + msg);
    const st = document.getElementById('stage');
    if (!st) return;
    let box = st.querySelector('.deck-problems');
    if (!box) { box = document.createElement('div'); box.className = 'deck-problems'; box.setAttribute('role', 'alert'); st.appendChild(box); }
    box.textContent = problems.join('  |  ');
  }
  addEventListener('error', e => {
    const t = e.target;
    if (t && t !== window && (t.tagName === 'SCRIPT' || t.tagName === 'LINK')) report('failed to load ' + (t.src || t.href).split('/').slice(-2).join('/'));
  }, true);
  addEventListener('unhandledrejection', e => console.error('[deck] unhandled promise rejection', e.reason));

  /* Blackout (. key, the clicker's blank-screen button): the whole viewport fades to black and back. */
  let blackEl = null;
  const isBlack = () => !!blackEl && blackEl.classList.contains('on');
  function blackout(on) {
    if (!blackEl) { blackEl = document.createElement('div'); blackEl.id = 'blackout'; document.body.appendChild(blackEl); }
    blackEl.classList.toggle('on', on === undefined ? !isBlack() : on);
  }

  function setStep(el, k) {
    for (let i = 1; i <= 9; i++) el.classList.toggle('s' + i, i <= k);
    el.dataset.step = k;
  }

  function go(s, k, dir, instant) {
    s = clamp(s, 0, slides.length - 1);
    const S = slides[s];
    k = clamp(k, 0, (S.d.steps || 1) - 1);
    const P = slides[cur];
    if (instant) { stage.classList.add('instant'); requestAnimationFrame(() => requestAnimationFrame(() => stage.classList.remove('instant'))); }
    if (s !== cur || instant) {
      if (P && P !== S) {
        P.el.classList.remove('is-active', 'active');
        try { P.d.leave && P.d.leave(P.el); } catch (e) { console.error(P.d.id, e); }
      }
      slides.forEach(x => { x.el.toggleAttribute('inert', x !== S); x.el.classList.toggle('active', x === S); });
      S.el.classList.add('is-active');
      try { S.d.enter && S.d.enter(S.el); } catch (e) { console.error(S.d.id, e); }
      logNotes(s);
    }
    cur = s; step = k;
    setStep(S.el, k);
    try { S.d.step && S.d.step(S.el, k, dir); } catch (e) { console.error(S.d.id, e); }
    stage.dataset.slide = S.d.id;
    history.replaceState(null, '', `${location.search}#${s + 1}.${k}`);
    pace();
    renderNotes();
  }

  function startClock() {
    if (started !== null) return;
    started = performance.now();
    clearInterval(clock);
    clock = setInterval(() => { pace(); if (!notesEl.hidden) renderNotes(); }, 250);
  }
  function next() {
    startClock();
    const n = slides[cur].d.steps || 1;
    if (step < n - 1) go(cur, step + 1, 1);
    else if (cur < slides.length - 1) go(cur + 1, 0, 1);
  }
  function prev() {
    if (step > 0) go(cur, step - 1, -1);
    else if (cur > 0) go(cur - 1, (slides[cur - 1].d.steps || 1) - 1, -1);
  }

  const elapsed = () => (started === null ? 0 : (performance.now() - started) / 1000);
  function pace() {
    const t = elapsed();
    stage.querySelector('.pace-fill').style.transform = `scaleX(${Math.min(1, t / TOTAL_S)})`;
    const end = (slides[cur] && slides[cur].d.time && slides[cur].d.time[1]) || TOTAL_S;
    stage.classList.toggle('behind', started !== null && t > end + 5);
  }
  function buildTicks() {
    const host = stage.querySelector('.pace-ticks');
    defs.slice(0, -1).forEach(d => {
      if (!d.time) return;
      const i = document.createElement('i');
      i.style.left = (100 * d.time[1] / TOTAL_S) + '%';
      host.appendChild(i);
    });
  }

  const mmss = t => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  /* Speaker notes follow html-slides: {title, script, notes[]}; older HTML-string notes become the script. */
  function noteObj(d) {
    const n = d.notes;
    if (n && typeof n === 'object') return { title: n.title || d.title || d.id, script: n.script || '', notes: n.notes || [] };
    const tmp = document.createElement('div');
    tmp.innerHTML = n || '';
    return { title: d.title || d.id, script: tmp.textContent.replace(/\s+/g, ' ').trim(), notes: [] };
  }
  function renderNotes() {
    if (!notesEl || notesEl.hidden || !slides[cur]) return;
    const d = slides[cur].d, n = noteObj(d), w = d.time ? `${mmss(d.time[0])}-${mmss(d.time[1])}` : '';
    notesEl.innerHTML = `<div class="notes-head"><b>${cur + 1}/${slides.length} · ${esc(n.title)}</b><span>step ${step + 1}/${d.steps || 1}</span>` +
      `<span>target ${w}</span><span class="notes-clock">${mmss(elapsed())} / 5:00</span></div>` +
      `<div class="notes-body"><p>${esc(n.script)}</p>${n.notes.length ? '<ul>' + n.notes.map(x => `<li>${esc(x)}</li>`).join('') + '</ul>' : ''}</div>`;
  }
  /* Presenter view without a second app: open DevTools (F12), detach it to the laptop screen, read the notes there. */
  function logNotes(i) {
    const d = slides[i].d, n = noteObj(d), w = d.time ? ` · ${mmss(d.time[0])}-${mmss(d.time[1])}` : '';
    console.log(`%c${i + 1}/${slides.length} · ${n.title}${w}\n\n%c${n.script}${n.notes.length ? '\n\n• ' + n.notes.join('\n• ') : ''}`,
      'font: 700 15px system-ui; color: #FFCC00', 'font: 400 14px/1.5 system-ui');
  }

  function onKey(e) {
    if (e.metaKey || e.ctrlKey || e.altKey || !slides.length) return;
    const tag = e.target && e.target.tagName;
    if (tag === 'TEXTAREA' || tag === 'SELECT' || (tag === 'INPUT' && !/^(range|button|checkbox|radio)$/.test(e.target.type))) return;
    const nav = [' ', 'ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'PageDown', 'PageUp', 'Enter', 'Backspace', 'Home', 'End'].includes(e.key);
    if (isBlack() && (nav || e.key === 'Escape')) { e.preventDefault(); blackout(false); return; }   // first press only brings the picture back
    const h = keyHandlers.get(slides[cur].d.id);
    if (h && h(e) === true) { e.preventDefault(); return; }
    if (nav) {
      e.preventDefault();                                   // no page scroll, no button or slider activation
      if (e.target && e.target !== document.body && e.target.blur) e.target.blur();   // focus never stays on a control
      if (e.repeat && (e.key === ' ' || e.key === 'Enter')) return;
      startClock();
    }
    switch (e.key) {
      case 'ArrowRight': case 'ArrowDown': case ' ': case 'PageDown': case 'Enter': next(); break;
      case 'ArrowLeft': case 'ArrowUp': case 'PageUp': case 'Backspace': prev(); break;
      case 'Home': go(0, 0, -1); break;
      case 'End': go(slides.length - 1, 0, 1); break;
      case '.': case '>': e.preventDefault(); blackout(); break;
      case 'Escape': notesEl.hidden = true; break;
      case 'f': case 'F':
        if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen().catch(() => {});
        break;
      case 'n': case 'N': notesEl.hidden = !notesEl.hidden; renderNotes(); break;
      case 't': case 'T': started = null; clearInterval(clock); startClock(); pace(); break;
    }
  }

  function parseHash() {
    const m = /^#(\d+)(?:\.(\d+))?/.exec(location.hash);
    return m ? [parseInt(m[1], 10) - 1, parseInt(m[2] || '0', 10)] : [0, 0];
  }

  function start() {
    stage = document.getElementById('stage');
    notesEl = document.getElementById('notes');
    if (STATIC) document.documentElement.classList.add('static');
    const f = params.get('font');                          // test hook: ?font=arial previews fallback metrics
    if (f) document.documentElement.style.setProperty('--font', f);
    fit();
    addEventListener('resize', fit);
    document.addEventListener('fullscreenchange', () => { fit(); setTimeout(fit, 150); });
    if (window.visualViewport) visualViewport.addEventListener('resize', fit);
    if (!window.PITCH) report('pitch-data.js is missing or broken: run python powerpoint/pitch/build_pitch_data.py');
    if (!defs.length) { report('no slide files registered'); return; }
    defs.sort((a, b) => a.order - b.order);
    const host = document.getElementById('deck');
    slides = defs.map((d, i) => {
      const el = document.createElement('section');
      el.className = 'slide';
      el.id = d.id;
      el.dataset.slide = i;
      el.setAttribute('aria-roledescription', 'slide');
      el.setAttribute('aria-label', `${i + 1} of ${defs.length}: ${d.title || d.id}`);
      el.innerHTML = d.html || '';
      host.appendChild(el);
      try { d.mount && d.mount(el, window.PITCH || {}, Deck); } catch (e) { report('slide ' + d.id + ' failed to mount: ' + e.message); }
      const no = document.createElement('div');            // numbered title tag, top right, identical on every slide
      no.className = 'slide-no';
      no.setAttribute('aria-hidden', 'true');
      no.innerHTML = `<b>${String(i + 1).padStart(2, '0')}</b><span>${esc(d.title || d.id)}</span>`;
      el.appendChild(no);
      const notes = document.createElement('script');      // html-slides presentation layer: notes JSON is the slide's last child
      notes.type = 'application/json';
      notes.className = 'slide-notes';
      notes.textContent = JSON.stringify(noteObj(d));
      el.appendChild(notes);
      return { d, el };
    });
    loadLogos();
    buildTicks();
    const [s, k] = parseHash();
    cur = clamp(s, 0, slides.length - 1);
    go(s, k, 0, true);
    addEventListener('keydown', onKey, true);
    addEventListener('keyup', e => { if (e.key === ' ' || e.key === 'Enter') e.preventDefault(); }, true);   // no click on a focused button
    // pointer use must not leave focus on a control: keys keep driving the deck
    document.addEventListener('pointerup', () => setTimeout(() => { const a = document.activeElement; if (a && a.matches && a.matches('input[type=range],button')) a.blur(); }, 0));
    // focus can scroll the overflow:hidden page; put it back
    addEventListener('scroll', () => { scrollTo(0, 0); document.querySelectorAll('#viewport,#stage,#deck,.slide').forEach(n => { n.scrollTop = 0; n.scrollLeft = 0; }); }, true);
    // timers survive blur and tab switches: elapsed time is clock-based; repaint on return
    addEventListener('focus', () => { pace(); renderNotes(); });
    document.addEventListener('visibilitychange', () => { pace(); renderNotes(); });
    if (slides.length < 5) report(`only ${slides.length} slide(s) loaded`);
    addEventListener('hashchange', () => { const [s2, k2] = parseHash(); if (s2 !== cur || k2 !== step) go(s2, k2, 0, true); });
  }

  /* Test hook (?audit, with ?static): visits every slide/build and lists text boxes that overflow themselves or the stage. */
  function audit() {
    const out = [], sr = stage.getBoundingClientRect(), sc = sr.width / 1920;
    slides.forEach((S, i) => {
      for (let k = 0; k < (S.d.steps || 1); k++) {
        go(i, k, 0, true);
        S.el.querySelectorAll('*').forEach(n => {
          if (n.closest('svg') && n.tagName !== 'text') return;
          const cs = getComputedStyle(n), r = n.getBoundingClientRect();
          if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.05 || !r.width) return;
          if (n.closest('[data-b]') && +getComputedStyle(n.closest('[data-b]')).opacity < 0.05) return;
          const x0 = (r.left - sr.left) / sc, x1 = (r.right - sr.left) / sc, y0 = (r.top - sr.top) / sc, y1 = (r.bottom - sr.top) / sc;
          const own = [...n.childNodes].some(c => c.nodeType === 3 && c.textContent.trim());
          const tag = n.id || n.className.baseVal || n.className || n.tagName;
          if (own && (n.scrollWidth > n.clientWidth + 2 || n.scrollHeight > n.clientHeight + 2) && cs.overflow !== 'visible') out.push(`s${i + 1}.${k} clipped text ${tag}: ${n.textContent.trim().slice(0, 30)}`);
          if (own && (x0 < -1 || y0 < -1 || x1 > 1921 || y1 > 1081)) out.push(`s${i + 1}.${k} off-stage ${tag} [${x0 | 0},${y0 | 0},${x1 | 0},${y1 | 0}]: ${n.textContent.trim().slice(0, 30)}`);
          if (own && cs.whiteSpace === 'nowrap' && n.parentElement && n.parentElement.getBoundingClientRect().right + 2 < r.right) out.push(`s${i + 1}.${k} nowrap spills parent ${tag}: ${n.textContent.trim().slice(0, 30)}`);
        });
      }
    });
    const pre = document.createElement('pre'); pre.id = 'audit'; pre.textContent = out.length ? out.join('\n') : 'AUDIT OK';
    document.body.appendChild(pre);
    return out;
  }
  if (params.has('audit')) addEventListener('load', () => setTimeout(audit, 500));

  /* html-slides globals, so its presenter app and tooling can drive this deck (0-based like html-slides). */
  window.goTo = i => go(i, 0, i >= cur ? 1 : -1);
  window.next = () => next();
  window.prev = () => prev();

  window.Deck = {
    register, start, next, prev, go: (s, k = 0) => go(s - 1, k, 0, false),
    tick, draw, fmt, mapSrc, logos, SPRING, reduced,
    onKey: (slideId, fn) => keyHandlers.set(slideId, fn),
    get P() { return window.PITCH || {}; },
    get current() { return { slide: cur + 1, step }; },
  };
})();
