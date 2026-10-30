#!/usr/bin/env python3
"""QA harness for the 5-minute pitch deck (powerpoint/pitch, agent 10).

Opens every slide.step as a fresh page load of index.html?static#S.K in headless Chrome (DevTools protocol,
1920 x 1080, device scale 1), screenshots it and checks what a juror sees:
  * visible words per state: opacity > 0.05, visibility visible, on the stage, not inside .src, aria-hidden or
    visually-hidden nodes; more than --max-words (20, blueprint section 6) is an error
  * html-slides Tier 2 per state: overflow, overlapping, blank, image_broken, chart_empty, text_truncated
  * layout: text cut at the stage edge or by its container, text under other elements or on other text, on the
    brand lockup or the source caption, elements leaving the 1920 x 1080 stage, small type, and contrast measured
    on the screenshot
  * the map <img>: natural size against its rendered box (1:1 at 1080p, aspect kept), overlay SVG alignment
  * console errors and uncaught exceptions (the optional logo and SVG-map probes are marked expected)
  * html-slides presentation layer: div.deck#deck, .slide with data-slide 0..N, exactly one .active,
    script.slide-notes JSON (title, script, notes[]) as each slide's last child, goTo/next/prev, no delivery cues
  * source scan of slides/, css/, js/ and the deck HTML: forbidden claims (blueprint section 8), slop (FAIR,
    lorem, TODO), purple or magenta gradients, unstyled range inputs, and numbers on slides 3-4 typed by hand
    instead of read from window.PITCH (report only)

Run from the repo root (Python 3 with Pillow and numpy; websocket-client is used when installed):
    python powerpoint/pitch/qa/audit.py                  # every state; JSON summary on stdout
    python powerpoint/pitch/qa/audit.py --only 3,4.1     # slide 3 (all steps) and state 4.1
    python powerpoint/pitch/qa/audit.py --offline        # block Google Fonts: test the fallback fonts
    python powerpoint/pitch/qa/audit.py --cli            # also shoot with the plain Chrome CLI and diff
    python powerpoint/pitch/qa/audit.py --deck powerpoint/pitch/johan-pitch.html   # the single-file build
Writes to --out (env PITCH_QA_OUT, else the session scratchpad qa/ folder, else %TEMP%/pitch-qa):
    shots/S.K_<slide>.png, contact_sheet.png, audit.json (every detail). Progress goes to stderr.
Exit code: 0 no errors, 1 errors found, 2 the harness failed.
"""
from __future__ import annotations

import argparse
import base64
import colorsys
import json
import os
import queue
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PITCH_DIR = HERE.parent
CHROME = os.environ.get("PITCH_QA_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").is_file())
W, H = 1920, 1080
EXPECTED_STEPS = {1: 5, 2: 3, 3: 4, 4: 4, 5: 2}                    # blueprint section 7
EXPECTED_FAILS = (r"/assets/logos/", r"visualisation(%20| )busy[^\"' ]*\.svg")  # route-stress-map.svg is the real map now   # optional files the engine probes
TIER2 = ("overflow", "overlapping", "blank", "image_broken", "chart_empty", "text_truncated")


def default_out() -> Path:
    if os.environ.get("PITCH_QA_OUT"):
        return Path(os.environ["PITCH_QA_OUT"])
    return ROOT / "figures" / "generated" / "pitch" / "qa"


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# ----------------------------------------------------------------------------------------------- DevTools plumbing
class MiniWS:
    """Just enough WebSocket (RFC 6455) for the DevTools protocol, used when websocket-client is not installed."""

    def __init__(self, url, timeout=60):
        m = re.match(r"ws://([^/:]+):(\d+)(/.*)", url)
        host, port, path = m.group(1), int(m.group(2)), m.group(3)
        self.sock = socket.create_connection((host, port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("websocket handshake failed")
            buf += chunk
        head, rest = buf.split(b"\r\n\r\n", 1)
        if b" 101" not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError(head.decode(errors="replace")[:200])
        self.buf, self.parts = bytearray(rest), []

    def settimeout(self, t):
        self.sock.settimeout(t)

    @staticmethod
    def _mask(data, mask):
        if not data:
            return b""
        m = (mask * (len(data) // 4 + 1))[:len(data)]
        return (int.from_bytes(data, "big") ^ int.from_bytes(m, "big")).to_bytes(len(data), "big")

    def _send(self, op, data):
        n, head = len(data), bytearray([0x80 | op])
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.sock.sendall(bytes(head) + mask + self._mask(data, mask))

    def send(self, text):
        self._send(1, text.encode("utf-8"))

    def _frame(self):
        b = self.buf                                   # parse without consuming until the whole frame is here,
        if len(b) < 2:                                 # so a timeout in the middle of a frame loses nothing
            return None
        fin, op, masked, n, i = b[0] & 0x80, b[0] & 0x0F, b[1] & 0x80, b[1] & 0x7F, 2
        if n == 126:
            if len(b) < 4:
                return None
            n, i = struct.unpack(">H", b[2:4])[0], 4
        elif n == 127:
            if len(b) < 10:
                return None
            n, i = struct.unpack(">Q", b[2:10])[0], 10
        mask = None
        if masked:
            if len(b) < i + 4:
                return None
            mask, i = bytes(b[i:i + 4]), i + 4
        if len(b) < i + n:
            return None
        payload = bytes(b[i:i + n])
        del b[:i + n]
        return fin, op, (self._mask(payload, mask) if mask else payload)

    def recv(self):
        while True:
            fr = self._frame()
            if fr is None:
                chunk = self.sock.recv(1 << 20)
                if not chunk:
                    raise ConnectionError("websocket closed")
                self.buf += chunk
                continue
            fin, op, payload = fr
            if op == 9:
                self._send(10, payload)
            elif op == 8:
                raise ConnectionError("websocket closed by Chrome")
            elif op in (0, 1, 2):
                self.parts.append(payload)
                if fin:
                    data, self.parts = b"".join(self.parts), []
                    return data.decode("utf-8")

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def ws_connect(url):
    try:
        import websocket  # websocket-client
        return websocket.create_connection(url, timeout=60, suppress_origin=True)
    except ImportError:
        return MiniWS(url)


class Cdp:
    def __init__(self, ws_url):
        self.ws, self.n, self.events = ws_connect(ws_url), 0, []

    def send(self, method, **params):
        self.n += 1
        mid = self.n
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error'].get('message')}")
                return msg.get("result", {})
            if "method" in msg:
                self.events.append(msg)

    def ev(self, expr, await_=False):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=await_)
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            raise RuntimeError("JS: " + ((d.get("exception") or {}).get("description") or d.get("text") or "error")[:600])
        return r.get("result", {}).get("value")

    def drain(self, wait=0.05):
        self.ws.settimeout(wait)
        try:
            while True:
                msg = json.loads(self.ws.recv())
                if "method" in msg:
                    self.events.append(msg)
        except Exception:
            pass
        finally:
            self.ws.settimeout(60)


_NOPROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http_json(port, path, tries=150):
    last = None
    for _ in range(tries):
        try:
            with _NOPROXY.open(f"http://127.0.0.1:{port}{path}", timeout=2) as r:
                return json.load(r)
        except Exception as e:  # Chrome still starting
            last = e
            time.sleep(0.1)
    raise RuntimeError(f"Chrome DevTools did not answer on port {port}: {last}")


class Chrome:
    def __init__(self, exe, profile):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.proc = subprocess.Popen(
            [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--remote-debugging-port={self.port}",
             "--remote-allow-origins=*", f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
             "--disable-extensions", "--mute-audio", "--window-size=1920,1080", "--force-device-scale-factor=1", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        http_json(self.port, "/json/version")
        pages = [t for t in http_json(self.port, "/json/list") if t.get("type") == "page"]
        self.page = Cdp(pages[0]["webSocketDebuggerUrl"])

    def close(self):
        try:
            self.page.ws.close()
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except Exception:
            self.proc.kill()


# ----------------------------------------------------------------------------------------------- in-page scripts
HOOK_JS = r"""
(() => {
  window.__qaDefs = [];
  let real;
  try {
    Object.defineProperty(window, 'Deck', { configurable: true, enumerable: true, get() { return real; },
      set(v) {
        if (v && typeof v.register === 'function' && !v.__qa) {
          const orig = v.register;
          v.register = function (d) {
            try {
              const notes = typeof d.notes === 'string' ? d.notes.replace(/<[^>]+>/g, ' ') : (d.notes && d.notes.script) || '';
              window.__qaDefs.push({ id: d.id, order: d.order, steps: d.steps, title: d.title, time: d.time,
                notesWords: (notes.match(/\S+/g) || []).length });
            } catch (e) {}
            return orig.apply(this, arguments);
          };
          Object.defineProperty(v, '__qa', { value: true });
        }
        real = v;
      } });
  } catch (e) {}
})();
"""

WAIT_JS = r"""
(async () => {
  try { await document.fonts.ready; } catch (e) {}
  const imgs = [...document.images];
  await Promise.all(imgs.map(i => i.complete ? 0 : new Promise(r => {
    i.addEventListener('load', r, { once: true }); i.addEventListener('error', r, { once: true }); setTimeout(r, 4000); })));
  await Promise.all(imgs.filter(i => i.complete && i.naturalWidth).map(i => i.decode().catch(() => 0)));
  return true;
})()
"""

FUNC_JS = r"""
(() => {
  const act = () => { const a = document.querySelectorAll('#deck > .slide.active'); return a.length === 1 ? Number(a[0].dataset.slide) : -1 - a.length; };
  if (typeof goTo !== 'function' || typeof next !== 'function' || typeof prev !== 'function') return { ok: false, why: 'goTo/next/prev missing' };
  const n = document.querySelectorAll('#deck > .slide').length, r = {};
  try {
    goTo(n - 1); r['goTo(last)'] = act() === n - 1;
    prev(); r['prev()'] = act() === Math.max(0, n - 2);
    next(); r['next()'] = act() === n - 1;
    goTo(0); r['goTo(0)'] = act() === 0;
  } catch (e) { return { ok: false, why: String(e) }; }
  return { ok: Object.values(r).every(Boolean), r };
})()
"""

INSPECT_JS = r"""
(async () => {
  const W = 1920;
  const stage = document.getElementById('stage');
  const list = [...new Set(document.querySelectorAll('#deck > .slide, .deck > .slide, #slides > .slide'))];
  const slide = list.find(s => s.classList.contains('is-active')) || list.find(s => s.classList.contains('active')) || null;
  const short = u => { u = u || ''; if (u.startsWith('data:')) return u.slice(0, u.indexOf(',')) + ` (${Math.round(u.length / 1365)} kB)`;
    try { u = decodeURIComponent(u); } catch (e) {} return u.split('/').pop().slice(0, 120); };
  const R = { hash: location.hash, nSlides: list.length, ids: list.map(s => s.id), deck: !!window.Deck,
    current: window.Deck ? window.Deck.current : null, slideIndex: slide ? list.indexOf(slide) + 1 : 0,
    slideId: slide ? slide.id : null, step: slide && slide.dataset.step !== undefined ? Number(slide.dataset.step) : null,
    vw: innerWidth, vh: innerHeight, dpr: devicePixelRatio,
    scroll: [document.documentElement.scrollWidth, document.documentElement.scrollHeight],
    faces: [...(document.fonts || [])].filter(f => /Inter|JetBrains/i.test(f.family)).map(f => `${f.family.replace(/["']/g, '')} ${f.weight} ${f.status}`),
    texts: [], pseudo: [], brandTexts: [], hidden: { nobox: 0, visibility: 0, opacity: 0, clipped: 0 },
    overflow: [], parked: [], spill: [], occluded: [], truncated: [], imgs: [], images: [], canvases: [], charts: [],
    overlays: [], brandImgs: [], ranges: [], srcBoxes: [], brand: null, visuals: 0, layer: null };

  // html-slides presentation layer
  const deckEl = document.getElementById('deck');
  const kids = deckEl ? [...deckEl.children].filter(e => e.classList.contains('slide')) : [];
  R.layer = { deck: !!deckEl && deckEl.tagName === 'DIV' && deckEl.classList.contains('deck'), deckTag: deckEl ? deckEl.tagName.toLowerCase() + '.' + deckEl.className : null,
    globals: { goTo: typeof window.goTo, next: typeof window.next, prev: typeof window.prev },
    generator: (document.querySelector('meta[name=generator]') || {}).content || null, active: [], slides: [] };
  kids.forEach((s, i) => {
    const last = s.lastElementChild, node = s.querySelector(':scope > script.slide-notes');
    let notes = null, err = null;
    if (node) { try { notes = JSON.parse(node.textContent); } catch (e) { err = String(e).slice(0, 140); } }
    R.layer.slides.push({ i, id: s.id, tag: s.tagName.toLowerCase(), dataSlide: s.dataset.slide ?? null,
      lastIsNotes: !!last && last.tagName === 'SCRIPT' && last.type === 'application/json' && last.classList.contains('slide-notes'),
      lastChild: last ? last.tagName.toLowerCase() + (last.className && typeof last.className === 'string' ? '.' + last.className.trim().split(/\s+/).join('.') : '') : null, notes, err });
    if (s.classList.contains('active')) R.layer.active.push(i);
  });
  if (!stage || !slide) return R;

  const S = stage.getBoundingClientRect(), sc = S.width / W || 1;
  R.stage = { left: S.left, top: S.top, width: S.width, height: S.height, scale: sc };
  const B = r => ({ x: +((r.left - S.left) / sc).toFixed(1), y: +((r.top - S.top) / sc).toFixed(1), w: +(r.width / sc).toFixed(1), h: +(r.height / sc).toFixed(1) });
  const cache = new Map();
  const css = el => { let c = cache.get(el); if (!c) { c = getComputedStyle(el); cache.set(el, c); } return c; };
  const opac = el => { let o = 1; for (let a = el; a && a.nodeType === 1; a = a.parentElement) { o *= parseFloat(css(a).opacity); if (o < 1e-3) break; } return o; };
  const shown = el => css(el).visibility === 'visible' && opac(el) > 0.05;
  const ids = new Map(), eid = el => { if (!ids.has(el)) ids.set(el, ids.size + 1); return ids.get(el); };
  const desc = el => { let s = el.tagName.toLowerCase(); if (el.id) s += '#' + el.id;
    const cl = (el.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 3); if (cl.length) s += '.' + cl.join('.');
    for (const k of ['data-b', 'data-b-out']) if (el.hasAttribute(k)) s += `[${k}=${el.getAttribute(k)}]`; return s; };
  const path = el => { const p = []; for (let a = el; a && a !== slide && a !== stage && p.length < 4; a = a.parentElement) p.unshift(desc(a)); return p.join(' > '); };
  const X = (a, b) => { if (!a || !b) return null; const l = Math.max(a.left, b.left), t = Math.max(a.top, b.top), r = Math.min(a.right, b.right), d = Math.min(a.bottom, b.bottom);
    return r > l && d > t ? { left: l, top: t, right: r, bottom: d, width: r - l, height: d - t } : null; };
  const area = rs => rs.reduce((s, r) => s + r.width * r.height, 0);
  const clip = (el, r, upTo) => { let c = r; for (let a = el.parentElement; a && a !== upTo && c; a = a.parentElement) { const s = css(a);
    if (s.overflowX !== 'visible' || s.overflowY !== 'visible') c = X(c, a.getBoundingClientRect()); } return c; };
  const nW = t => (t.match(/\S+/g) || []).filter(w => /[\p{L}\p{N}]/u.test(w)).length;
  const SKIP = 'script,style,template,noscript,title,desc,metadata';
  const DECOR = '[aria-hidden="true"],.sr-only,.visually-hidden,.vh,[hidden]';
  const vhid = el => { for (let a = el; a && a !== slide; a = a.parentElement) { const s = css(a);
    if (s.clip === 'rect(0px, 0px, 0px, 0px)' || /inset\(50%\)/.test(s.clipPath)) return true; } return false; };
  const catOf = el => el.closest('.src, .g-micro, .s2-micro') ? 'src' : el.closest('.s2b-phone, .s4-phone') ? 'artefact' : (el.closest(DECOR) || vhid(el)) ? 'decor' : 'main';
  const scaleOf = el => { let k = 1; for (let a = el; a && a !== stage; a = a.parentElement) { const t = css(a).transform;
    if (t && t !== 'none') { const m = new DOMMatrixReadOnly(t); k *= Math.hypot(m.a, m.b); } } return k; };
  const fontPx = el => { const f = parseFloat(css(el).fontSize) || 0;
    if (el instanceof SVGElement) { const m = el.getScreenCTM && el.getScreenCTM(); return m ? f * Math.hypot(m.a, m.b) / sc : f; } return f * scaleOf(el); };
  const alpha = c => { if (!c || c === 'transparent' || c === 'none') return 0; const m = /rgba?\(([^)]+)\)/.exec(c); if (!m) return 1;
    const p = m[1].split(/[\s,\/]+/).filter(Boolean); return p.length > 3 ? parseFloat(p[3]) : 1; };
  const boxed = a => { if (a instanceof SVGElement) return false; const s = css(a);
    return alpha(s.backgroundColor) > 0.08 || s.backgroundImage !== 'none' || (parseFloat(s.borderTopWidth) > 0 && alpha(s.borderTopColor) > 0.08) || (!!s.backdropFilter && s.backdropFilter !== 'none'); };
  const painted = e => {
    if (e === slide || e === stage || e.contains(slide) || !shown(e)) return false;
    const tag = e.tagName.toLowerCase();
    if (['img', 'video', 'canvas', 'iframe', 'image'].includes(tag)) return true;
    if (e instanceof SVGElement) { if (['svg', 'g', 'foreignobject', 'defs', 'clippath', 'mask', 'a'].includes(tag)) return false; const s = css(e); return alpha(s.fill) > 0.08 || alpha(s.stroke) > 0.08; }
    if (boxed(e)) return true;
    for (const c of e.childNodes) if (c.nodeType === 3 && c.textContent.trim()) return true;
    return false;
  };

  // visible text, one item per text node
  const els = [];
  const collect = (root, sink, ctx, keep) => {
    const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), rg = document.createRange();
    for (let n = tw.nextNode(); n; n = tw.nextNode()) {
      const raw = n.textContent.replace(/\s+/g, ' ').trim();
      if (!raw) continue;
      const el = n.parentElement;
      if (!el || el.closest(SKIP) || vhid(el)) continue;
      rg.selectNodeContents(n);
      const rects = [...rg.getClientRects()].filter(r => r.width > 0.5 && r.height > 0.5);
      let why = !rects.length ? 'nobox' : css(el).visibility !== 'visible' ? 'visibility' : opac(el) <= 0.05 ? 'opacity' : null;
      let inStage = [], vis = [];
      if (!why) { inStage = rects.map(r => X(r, S)).filter(Boolean); vis = inStage.map(r => clip(el, r, ctx)).filter(Boolean); if (!vis.length) why = 'clipped'; }
      if (why) { if (keep) R.hidden[why] += nW(raw); continue; }
      const s = css(el), svg = el instanceof SVGElement;
      sink.push({ t: raw.length > 700 ? raw.slice(0, 697) + '...' : raw, words: nW(raw), cat: catOf(el), el: path(el), eid: eid(el),
        rects: vis.slice(0, 8).map(B), cutStage: +(1 - area(inStage) / area(rects)).toFixed(3), cutClip: +(1 - area(vis) / area(inStage)).toFixed(3),
        fs: +fontPx(el).toFixed(1), fw: parseInt(s.fontWeight, 10) || 400, color: svg ? s.fill : s.color, op: +opac(el).toFixed(3), svg });
      if (keep) els.push([el, vis]);
    }
  };
  collect(slide, R.texts, slide, true);

  // occlusion, text spilling out of its box, ellipsis or clamped text
  const seen = new Set();
  R.texts.forEach((it, i) => {
    const [el, vis] = els[i];
    for (const r of [vis[0], vis[vis.length - 1]]) {
      const x = (r.left + r.right) / 2, y = (r.top + r.bottom) / 2;
      if (x < 0 || y < 0 || x >= innerWidth || y >= innerHeight) continue;
      const stack = document.elementsFromPoint(x, y), k = stack.findIndex(e => e === el || el.contains(e));
      if (k <= 0) continue;
      const by = stack.slice(0, k).find(e => !e.contains(el) && painted(e));
      if (by) { R.occluded.push({ i, t: it.t.slice(0, 70), cat: it.cat, by: path(by) }); break; }
    }
    if (it.cat === 'main') {
      for (let a = el, d = 0; a && a !== slide && d < 5; a = a.parentElement, d++) {
        if (!boxed(a)) continue;
        const c = a.getBoundingClientRect();
        if (vis.some(r => r.left < c.left - 1 || r.right > c.right + 1 || r.top < c.top - 1 || r.bottom > c.bottom + 1)) R.spill.push({ i, t: it.t.slice(0, 70), box: path(a) });
        break;
      }
    }
    if (!seen.has(el)) {
      seen.add(el);
      const s = css(el);
      if (!(el instanceof SVGElement) && el.clientWidth > 0) {
        if (s.textOverflow === 'ellipsis' && el.scrollWidth > el.clientWidth + 1) R.truncated.push({ i, t: it.t.slice(0, 70), why: 'ellipsis', el: path(el) });
        else if ((s.overflowY !== 'visible' || (s.webkitLineClamp && s.webkitLineClamp !== 'none')) && el.scrollHeight > el.clientHeight + 2)
          R.truncated.push({ i, t: it.t.slice(0, 70), why: 'clamped', el: path(el) });
      }
    }
  });

  // CSS generated text
  for (const el of slide.querySelectorAll('*')) {
    if (el instanceof SVGElement || el.closest(SKIP)) continue;
    for (const p of ['::before', '::after']) {
      const ps = getComputedStyle(el, p), c = ps.content;
      if (!c || c[0] !== '"' || ps.display === 'none') continue;
      const t = c.slice(1, -1).replace(/\\[0-9a-f]{1,6}\s?/gi, ' ').trim();
      if (!nW(t)) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 1 || !shown(el) || parseFloat(ps.opacity) <= 0.05 || !X(r, S)) continue;
      R.pseudo.push({ t, words: nW(t), cat: catOf(el), el: path(el) + p });
    }
  }

  // elements leaving the stage (top-most offender only)
  const inside = r => r.left >= S.left - 1 && r.top >= S.top - 1 && r.right <= S.right + 1 && r.bottom <= S.bottom + 1;
  const rep = new Set();
  for (const el of slide.querySelectorAll('*')) {
    if (el.closest(SKIP)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1 || inside(r) || !shown(el)) continue;
    const c = clip(el, r, slide);
    if (!c || inside(c)) continue;
    let a = el.parentElement; while (a && a !== slide && !rep.has(a)) a = a.parentElement;
    if (a && a !== slide) continue;
    rep.add(el);
    const inS = X(c, S);
    (inS ? R.overflow : R.parked).push({ el: path(el), tag: el.tagName.toLowerCase(), box: B(c), text: els.some(([t]) => el === t || el.contains(t)),
      visFrac: inS ? +(area([inS]) / area([c])).toFixed(3) : 0,
      out: { l: Math.round(Math.max(0, S.left - c.left) / sc), r: Math.round(Math.max(0, c.right - S.right) / sc),
             t: Math.round(Math.max(0, S.top - c.top) / sc), b: Math.round(Math.max(0, c.bottom - S.bottom) / sc) } });
  }

  // images, canvases, charts, overlays, sliders, captions, brand
  const MW = (window.PITCH && PITCH.screenshot && PITCH.screenshot.w) || 1524, MH = (window.PITCH && PITCH.screenshot && PITCH.screenshot.h) || 919;
  for (const img of slide.querySelectorAll('img')) {
    const r = img.getBoundingClientRect(), s = css(img), src = img.currentSrc || img.src || '';
    let dec = src; try { dec = decodeURIComponent(src.slice(0, 400)); } catch (e) {}
    R.imgs.push({ src: short(src), complete: img.complete, nw: img.naturalWidth, nh: img.naturalHeight, ow: img.offsetWidth, oh: img.offsetHeight,
      rect: B(r), fit: s.objectFit, pos: s.objectPosition, op: +opac(img).toFixed(3), visible: r.width > 1 && r.height > 1 && shown(img) && !!X(r, S), anc: +scaleOf(img).toFixed(4),
      map: /visualisation|route-stress-map/i.test(dec) || (img.naturalWidth === MW && img.naturalHeight === MH), el: path(img) });
  }
  for (const im of slide.querySelectorAll('image')) {
    const href = (im.href && im.href.baseVal) || im.getAttribute('href') || im.getAttribute('xlink:href') || '', r = im.getBoundingClientRect();
    const nat = await new Promise(res => { const t = new Image(), to = setTimeout(() => res(null), 3000);
      t.onload = () => { clearTimeout(to); res([t.naturalWidth, t.naturalHeight]); }; t.onerror = () => { clearTimeout(to); res([0, 0]); }; t.src = href; });
    let dec = href; try { dec = decodeURIComponent(href.slice(0, 400)); } catch (e) {}
    R.images.push({ src: short(href), nat, rect: B(r), par: im.getAttribute('preserveAspectRatio') || '', visible: r.width > 1 && shown(im) && !!X(r, S),
      map: /visualisation|route-stress-map/i.test(dec) || (!!nat && nat[0] === MW && nat[1] === MH), el: path(im) });
  }
  for (const cv of slide.querySelectorAll('canvas')) { const r = cv.getBoundingClientRect(); if (r.width > 4 && r.height > 4 && shown(cv) && X(r, S)) R.canvases.push({ el: path(cv), rect: B(r) }); }
  const CH = /(^|[-_])(chart|bars?|stacked|graph|plot)([-_]|$)/i, chartEls = [];
  for (const el of slide.querySelectorAll('[class], [id]')) {
    if (![...(el.classList || []), el.id].filter(Boolean).some(t => CH.test(t))) continue;
    // A painted SVG bar is itself a mark, not an empty chart container.
    if (el instanceof SVGGeometryElement) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 20 || r.height < 6 || !shown(el) || chartEls.some(c => c.contains(el))) continue;
    chartEls.push(el);
    let marks = painted(el) && r.width >= 2 && r.height >= 2 ? 1 : 0;
    for (const d of el.querySelectorAll('*')) { const q = d.getBoundingClientRect(); if (q.width >= 2 && q.height >= 2 && painted(d)) marks++; if (marks > 2) break; }
    R.charts.push({ el: path(el), rect: B(r), marks });
  }
  for (const svg of slide.querySelectorAll('svg[viewBox]')) {
    const vb = svg.viewBox.baseVal, m = svg.getScreenCTM();
    if (!vb || !vb.width || !m) continue;
    const p0 = new DOMPoint(vb.x, vb.y).matrixTransform(m), p1 = new DOMPoint(vb.x + vb.width, vb.y + vb.height).matrixTransform(m);
    R.overlays.push({ el: path(svg), vb: [vb.x, vb.y, vb.width, vb.height], visible: shown(svg),
      p0: [(p0.x - S.left) / sc, (p0.y - S.top) / sc], p1: [(p1.x - S.left) / sc, (p1.y - S.top) / sc] });
  }
  for (const i of slide.querySelectorAll('input[type=range]')) { const s = css(i); R.ranges.push({ el: path(i), appearance: s.appearance || s.webkitAppearance || '', visible: shown(i) }); }
  for (const e of slide.querySelectorAll('.src')) { const r = e.getBoundingClientRect(); if (r.width > 1 && shown(e)) R.srcBoxes.push(B(r)); }
  const brand = stage.querySelector('.brand');
  if (brand) { const r = brand.getBoundingClientRect(); R.brand = { box: B(r), visible: r.width > 1 && shown(brand) }; if (R.brand.visible) collect(brand, R.brandTexts, stage, false); }
  R.brandImgs = [...stage.querySelectorAll('.brand img')].map(img => { const r = img.getBoundingClientRect(), s = css(img); return { src: short(img.currentSrc || img.src), complete: img.complete, nw: img.naturalWidth, nh: img.naturalHeight, ow: img.offsetWidth, oh: img.offsetHeight, rect: B(r), fit: s.objectFit, pos: s.objectPosition, visible: r.width > 1 && shown(img), el: path(img), boxed: (() => { for (let a = img; a && a !== stage; a = a.parentElement) if (boxed(a) || css(a).boxShadow !== 'none') return true; return false; })() }; });
  R.visuals = [...slide.querySelectorAll('img, svg, canvas, video, image')].filter(e => { const r = e.getBoundingClientRect();
    return r.width * r.height > 0.03 * S.width * S.height && shown(e) && !!X(r, S); }).length;
  return R;
})()
"""


# ----------------------------------------------------------------------------------------------- source scan
CLAIMS = [  # blueprint section 8 "must not say" (case-insensitive)
    ("real-time", r"real[\s-]?time"),
    ("live data", r"\blive[\s-]+(?:data|traffic|feed|updates?|tracking)\b"),
    ("AI engine", r"\bAI[\s-]+(?:engine|routing|router)\b"),
    ("AI-powered", r"\bAI[\s-]?(?:powered|driven|based)\b"),
    ("balances traffic", r"balanc\w*\s+(?:the\s+)?traffic|traffic[\s-]+balanc\w*|load[\s-]balanc\w*"),
    ("reroute", r"\bre-?rout\w*"),
    ("traffic simulation", r"simulat\w*\s+(?:the\s+)?traffic|traffic\s+simulat\w*"),
    ("verified safe", r"verified[\s-]+safe|guaranteed[\s-]+safe|certified[\s-]+safe"),
    ("designated shelter", r"designated\s+(?:flood\s+|emergency\s+|evacuation\s+)?shelters?"),
    ("official shelter/route", r"official\s+(?:flood\s+|emergency\s+|evacuation\s+)?(?:shelters?|routes?)"),
    ("sets A/B as bounds", r"(?:lower|upper)[\s-]bound|best[\s-]case|worst[\s-]case"),
]
SLOP = [("FAIR (the organiser is FARI)", r"\bFAIR\b", 0), ("lorem ipsum", r"\blorem\b|\bipsum\b", re.I),
        ("TODO/FIXME/TBD", r"\b(?:TODO|FIXME|TBD)\b", re.I)]
NEG = re.compile(r"\b(?:not|no|never|without|nor|cannot)\b|n['\u2019]t\b", re.I)
DELIVERY = re.compile(r"\bpause\b|\bnext slide\b|\bclick(?:s|ed|ing)?\b|\[beat\]|\(beat\)|^\s*say\s*:", re.I | re.M)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\uFE0F]")
NAMED = {"purple": "#800080", "magenta": "#ff00ff", "fuchsia": "#ff00ff", "violet": "#ee82ee", "darkviolet": "#9400d3",
         "darkmagenta": "#8b008b", "blueviolet": "#8a2be2", "mediumpurple": "#9370db", "mediumorchid": "#ba55d3",
         "orchid": "#da70d6", "plum": "#dda0dd", "rebeccapurple": "#663399", "indigo": "#4b0082", "darkorchid": "#9932cc"}
COLOR_RE = re.compile(r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b|rgba?\([^)]*\)|hsla?\([^)]*\)|var\(--[\w-]+[^)]*\)|\b(?:"
                      + "|".join(NAMED) + r")\b", re.I)
GRAD_RE = re.compile(r"(?:repeating-)?(?:linear|radial|conic)-gradient\(", re.I)
NUM_RE = re.compile(r"(?<![\w.#$\\-])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w%]|\.\d|\s*(?:px|ms|deg|em|rem|vh|vw|fr|s)\b)")
REQUIRED = {  # slide order -> phrases a juror or the brief needs on that slide (any build, captions included)
    1: [("warn", "fictional-character note", r"fictional")],
    2: [("warn", "'does not replace official warnings' footer", r"not\s+replace")],
    3: [("warn", "'Demo message, not a real alert'", r"not a real alert|demo message")],
    4: [("warn", "'stress is an indicator, not a forecast'", r"not a forecast"), ("warn", "OpenStreetMap attribution", r"OpenStreetMap")],
    5: [("warn", "'Demo message, not a real alert'", r"not a real alert|demo message")],
}


def to_rgba(c, var=None, depth=0):
    c = c.strip()
    if c.lower().startswith("var("):
        m = re.match(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)$", c, re.I)
        if not m or depth > 4:
            return None
        v = (var or {}).get(m.group(1)) or m.group(2)
        return to_rgba(v, var, depth + 1) if v else None
    if c.lower() in NAMED:
        c = NAMED[c.lower()]
    if c.startswith("#"):
        h = c[1:]
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        try:
            vals = [int(h[i:i + 2], 16) / 255 for i in range(0, len(h), 2)]
        except ValueError:
            return None
        return (*vals[:3], vals[3] if len(vals) > 3 else 1.0)
    m = re.match(r"(rgba?|hsla?)\(([^)]*)\)", c, re.I)
    if not m:
        return None
    parts = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
    try:
        nums = [float(p.rstrip("%deg")) / (100 if p.endswith("%") else 1) for p in parts]
    except ValueError:
        return None
    if len(nums) < 3:
        return None
    a = nums[3] if len(nums) > 3 else 1.0
    if m.group(1).lower().startswith("rgb"):
        rgb = [n if p.endswith("%") else n / 255 for n, p in zip(nums[:3], parts[:3])]
        return (*rgb, a)
    r, g, b = colorsys.hls_to_rgb((nums[0] % 360) / 360, nums[2], nums[1])
    return (r, g, b, a)


def is_purple(rgba):
    if not rgba:
        return False
    h, l, s = colorsys.rgb_to_hls(*rgba[:3])
    return 250 <= h * 360 <= 320 and s >= 0.35 and 0.12 <= l <= 0.92 and rgba[3] >= 0.12


def claim_hits(text):
    hits = []
    for code, pat in CLAIMS:
        for m in re.finditer(pat, text, re.I):
            before = text[max(0, m.start() - 60):m.start()]
            hits.append((code, m.group(0), bool(NEG.search(before))))
    for code, pat, fl in SLOP:
        for m in re.finditer(pat, text, fl):
            hits.append((code, m.group(0), False))
    return hits


def load_pitch(path):
    try:
        t = Path(path).read_text(encoding="utf-8")
        return json.loads(t[t.index("{", t.index("window.PITCH")):t.rindex("}") + 1])
    except Exception as e:
        log(f"pitch-data not read ({e}); the hard-coded-number check is skipped")
        return {}


def pitch_values(P):
    skip = {"source", "screenshot", "overlay", "px", "checks", "zone", "shelter_id", "generated", "share", "destinations",
            "levels", "sets", "assumptions"}
    vals = {}

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k not in skip:
                    walk(v, f"{path}.{k}" if path else k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            if float(o).is_integer():
                if abs(o) >= 10:
                    vals.setdefault(str(int(o)), path)
            elif abs(o) >= 1:
                vals.setdefault(f"{o:.1f}", path)
                if round(o, 2) != round(o, 1):
                    vals.setdefault(f"{o:.2f}", path)
                if abs(o) >= 10:
                    vals.setdefault(str(round(o)), path + " (rounded)")
    walk(P, "")
    for key, p in (P.get("plans") or {}).items():
        tp = p.get("to_place") or 0
        for f in ("within30", "over30", "no_place", "placed"):
            if tp and f in p:
                pct = 100 * p[f] / tp
                vals.setdefault(f"{pct:.1f}", f"plans['{key}'].{f} / to_place, %")
                if pct >= 10:
                    vals.setdefault(str(round(pct)), f"plans['{key}'].{f} / to_place, % (rounded)")
    return vals


def static_scan(deck_dir, index, P):
    files = sorted({*deck_dir.glob("slides/*.js"), *deck_dir.glob("slides/*.css"), *deck_dir.glob("css/*.css"),
                    *deck_dir.glob("js/*.js"), Path(index)})
    files = [f for f in files if f.exists() and f.stat().st_size < 3_000_000]
    texts = {f: f.read_text(encoding="utf-8", errors="replace") for f in files}
    rel = lambda f: f.relative_to(deck_dir).as_posix() if f.is_relative_to(deck_dir) else f.name
    out = []
    var = {}
    for t in texts.values():
        for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;{}]+)", t):
            var.setdefault(m.group(1), m.group(2).strip())
    for f, t in texts.items():
        lines = t.splitlines()
        for n, line in enumerate(lines, 1):
            ctx = (lines[n - 2] if n > 1 else "") + " " + line
            for code, match, neg in claim_hits(line):
                neg = neg or bool(NEG.search(ctx[:len(ctx) - len(line) + max(0, line.lower().find(match.lower()))]))
                out.append({"sev": "warn" if neg else "error", "code": "claim" if code in dict(CLAIMS) else "slop", "file": rel(f),
                            "line": n, "msg": f"'{match}' ({code}{'; negated, check context' if neg else ''}): {line.strip()[:140]}"})
            for m in re.finditer(r"\bAI\b(?![\s-]+Challenge)", line):
                if "European AI Challenge" not in line:
                    out.append({"sev": "info", "code": "ai-mention", "file": rel(f), "line": n, "msg": f"'AI' mention (the engine is not AI): {line.strip()[:140]}"})
        for m in GRAD_RE.finditer(t):
            i, depth = m.end(), 1
            while i < len(t) and depth:
                depth += {"(": 1, ")": -1}.get(t[i], 0)
                i += 1
            body = t[m.start():i]
            bad = [c.group(0) for c in COLOR_RE.finditer(body) if is_purple(to_rgba(c.group(0), var))]
            if bad:
                out.append({"sev": "error", "code": "purple-gradient", "file": rel(f), "line": t.count("\n", 0, m.start()) + 1,
                            "msg": f"purple/magenta gradient stop {', '.join(sorted(set(bad)))}: {body[:120]}"})
        if f.suffix == ".css":
            solid = sorted({c.group(0) for c in COLOR_RE.finditer(t) if not c.group(0).lower().startswith("var(") and is_purple(to_rgba(c.group(0), var))})
            if solid:
                out.append({"sev": "info", "code": "purple-colour", "file": rel(f), "line": 0, "msg": f"purple/magenta colours (not in gradients): {', '.join(solid)}"})
    markup = [f for f, t in texts.items() if f.suffix in (".js", ".html") and re.search(r"type\s*=\s*\\?['\"]?range", t, re.I)]
    styled = any(re.search(r"range[^{}]*\{[^}]*(?:-webkit-)?appearance\s*:\s*none", t, re.I) for f, t in texts.items() if f.suffix in (".css", ".html", ".js"))
    if markup and not styled:
        out.append({"sev": "error", "code": "range-default", "file": ", ".join(rel(f) for f in markup), "line": 0,
                    "msg": "range input without a CSS rule setting appearance: none (default browser slider)"})
    vals = pitch_values(P) if P else {}
    for f, t in texts.items():
        if not vals or f.suffix != ".js" or not re.match(r"s[34]\b|s[34][-_]", f.name):
            continue
        for n, line in enumerate(t.splitlines(), 1):
            for m in NUM_RE.finditer(line):
                tok = m.group(1).replace(",", "")
                key = str(int(float(tok))) if float(tok).is_integer() else tok
                if key in vals:
                    out.append({"sev": "warn", "code": "hardcoded-number", "file": rel(f), "line": n,
                                "msg": f"'{m.group(1)}' equals PITCH {vals[key]}; read it from window.PITCH: {line.strip()[:110]}"})
    return out


# ----------------------------------------------------------------------------------------------- per-state analysis
def lum_image(png):
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(png).convert("RGB"), dtype=np.float32) / 255.0
    a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def css_lum(c):
    rgba = to_rgba(c) if c else None
    if not rgba:
        return None, 0.0
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgba[:3]]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2], rgba[3]


def contrast(L, box, color, op):
    """WCAG ratio of a text line box against the ring of pixels around it, measured on the screenshot."""
    import numpy as np
    Hh, Ww = L.shape
    x0, y0 = int(max(0, box[0])), int(max(0, box[1]))
    x1, y1 = int(min(Ww, box[0] + box[2])), int(min(Hh, box[1] + box[3]))
    if x1 - x0 < 4 or y1 - y0 < 6:
        return None
    inner = L[y0:y1, x0:x1].ravel()
    X0, Y0, X1, Y1 = max(0, x0 - 6), max(0, y0 - 6), min(Ww, x1 + 6), min(Hh, y1 + 6)
    mask = np.ones((Y1 - Y0, X1 - X0), bool)
    mask[max(0, y0 - 2 - Y0):min(Y1, y1 + 2) - Y0, max(0, x0 - 2 - X0):min(X1, x1 + 2) - X0] = False
    ring = L[Y0:Y1, X0:X1][mask]
    if ring.size < 30:
        return None
    bg = float(np.median(ring))
    hi, lo = float(np.percentile(inner, 98.5)), float(np.percentile(inner, 1.5))
    cl, ca = css_lum(color)
    lighter = (cl > bg) if (cl is not None and ca * op > 0.2) else (hi - bg) >= (bg - lo)
    fg = hi if lighter else lo
    worst = float(np.percentile(ring, 75 if lighter else 25))
    ratio = lambda a, b: (max(a, b) + 0.05) / (min(a, b) + 0.05)
    return round(ratio(fg, bg), 2), round(ratio(fg, worst), 2)


def rect_inter(a, b):
    x, y = max(a["x"], b["x"]), max(a["y"], b["y"])
    r, d = min(a["x"] + a["w"], b["x"] + b["w"]), min(a["y"] + a["h"], b["y"] + b["h"])
    return (r - x) * (d - y) if r > x and d > y else 0.0


def img_scale(im):
    """Device pixels per image pixel (x, y) and content origin in stage px, honouring object-fit."""
    nw, nh, ow, oh, r = im["nw"], im["nh"], im["ow"], im["oh"], im["rect"]
    if not (nw and nh and ow and oh):
        return None
    fit = (im.get("fit") or "fill").lower()
    if fit == "fill":
        cx, cy = ow / nw, oh / nh
    else:
        s = {"contain": min(ow / nw, oh / nh), "cover": max(ow / nw, oh / nh), "none": 1.0,
             "scale-down": min(1.0, min(ow / nw, oh / nh))}.get(fit, ow / nw)
        cx = cy = s
    tx, ty = r["w"] / ow, r["h"] / oh
    pos = (im.get("pos") or "50% 50%").split()
    def off(p, free):
        return free * float(p[:-1]) / 100 if p.endswith("%") else (float(p[:-2]) if p.endswith("px") else free / 2)
    ox = off(pos[0], ow - nw * cx) if len(pos) > 0 else 0
    oy = off(pos[1], oh - nh * cy) if len(pos) > 1 else 0
    if fit == "fill":
        ox = oy = 0
    return cx * tx, cy * ty, r["x"] + ox * tx, r["y"] + oy * ty


def analyse_state(st, R, png, args, prev_main):
    issues = []
    add = lambda sev, code, msg: issues.append({"sev": sev, "code": code, "msg": msg})
    t2 = {k: False for k in TIER2}
    res = {"state": f"{st['s']}.{st['k']}", "slide": st["id"], "words": 0, "new_words": 0, "src_words": 0, "decor_words": 0,
           "hidden_words": 0, "tier2": t2, "issues": issues, "shot": str(png) if png and Path(png).exists() else None, "main_texts": []}
    if not R or not R.get("slideId"):
        add("error", "no-slide", "no active slide (engine failed to start or no slide registered)")
        t2["blank"] = True
        return res
    if R["slideIndex"] != st["s"] or R["step"] != st["k"]:
        add("error", "hash", f"#{st['s']}.{st['k']} opened slide {R['slideIndex']} step {R['step']} (hash now {R['hash']})")
    texts = [t for t in R["texts"]]
    main = [t for t in texts if t["cat"] == "main"]
    pseudo_main = [p for p in R["pseudo"] if p["cat"] == "main"]
    res["words"] = sum(t["words"] for t in main) + sum(p["words"] for p in pseudo_main)
    res["src_words"] = sum(t["words"] for t in texts if t["cat"] == "src")
    res["decor_words"] = sum(t["words"] for t in texts if t["cat"] == "decor")
    res["art_words"] = sum(t["words"] for t in texts if t["cat"] == "artefact")
    res["hidden_words"] = sum(R["hidden"].values())
    res["main_texts"] = [t["t"] for t in main] + [p["t"] for p in pseudo_main]
    res["new_words"] = sum(t["words"] for t in main if t["t"] not in prev_main) + sum(p["words"] for p in pseudo_main if p["t"] not in prev_main)
    if res["words"] > args.max_words:
        add("error", "words", f"{res['words']} words visible (max {args.max_words}; {res['new_words']} new in this build)")
    if pseudo_main:
        add("info", "pseudo-text", f"{sum(p['words'] for p in pseudo_main)} words come from CSS ::before/::after")

    # text cut, clipped, truncated, spilling
    for t in texts:
        if t["cutStage"] > 0.02:
            add("error", "text-cut-stage", f"text cut at the stage edge ({t['cutStage']:.0%} hidden): '{t['t'][:60]}' [{t['el']}]")
            t2["overflow"] = True
        elif t["cutClip"] > 0.02:
            add("warn", "text-clipped", f"text clipped by its container ({t['cutClip']:.0%} hidden): '{t['t'][:60]}' [{t['el']}]")
            t2["text_truncated"] = True
    for t in R["truncated"]:
        add("warn", "text-truncated", f"{t['why']}: '{t['t']}' [{t['el']}]")
        t2["text_truncated"] = True
    for s in R["spill"]:
        add("warn", "text-spills", f"text runs outside its box: '{s['t']}' [box {s['box']}]")
    for o in R["overflow"]:
        where = ", ".join(f"{k} {v}px" for k, v in o["out"].items() if v)
        if o["text"]:
            add("error", "off-stage", f"element with text leaves the stage ({where}): {o['el']}")
            t2["overflow"] = True
        else:
            add("warn", "off-stage", f"{o['tag']} leaves the stage ({where}; {o['visFrac']:.0%} visible): {o['el']}")
    for o in R["parked"]:
        add("info", "parked", f"{o['tag']} parked fully off stage: {o['el']}")
    if R["scroll"][0] > R["vw"] + 1 or R["scroll"][1] > R["vh"] + 1:
        add("warn", "scroll", f"document is {R['scroll'][0]}x{R['scroll'][1]} for a {R['vw']}x{R['vh']} viewport")

    # overlaps
    for o in R["occluded"]:
        sev = "warn" if o["cat"] == "decor" else "error"
        add(sev, "occluded", f"text under another element: '{o['t']}' covered by {o['by']}")
        t2["overlapping"] |= sev == "error"
    cand = [t for t in texts if t["rects"]]
    for i, a in enumerate(cand):
        for b in cand[i + 1:]:
            if a["eid"] == b["eid"]:
                continue
            ink = lambda r: {"x": r["x"], "y": r["y"] + 0.2 * r["h"], "w": r["w"], "h": 0.6 * r["h"]}   # glyph ink, not the line box
            best = max((rect_inter(ink(ra), ink(rb)) / max(1.0, min(ra["w"] * ra["h"] * 0.6, rb["w"] * rb["h"] * 0.6)), rect_inter(ink(ra), ink(rb)))
                       for ra in a["rects"] for rb in b["rects"])
            if best[1] > 30 and best[0] > 0.35:
                decor = "decor" in (a["cat"], b["cat"])
                add("warn" if decor else "error", "text-overlap", f"text on text ({best[0]:.0%}): '{a['t'][:40]}' / '{b['t'][:40]}'")
                t2["overlapping"] |= not decor
    if R.get("brand") and R["brand"]["visible"]:
        bb = R["brand"]["box"]
        for t in texts:
            if any(rect_inter(r, bb) > 4 for r in t["rects"]):
                add("error", "brand-overlap", f"text on the brand lockup: '{t['t'][:60]}'")
                t2["overlapping"] = True
    for t in main:
        if any(rect_inter(r, s) > 4 for r in t["rects"] for s in R["srcBoxes"]):
            add("error", "caption-overlap", f"text on the source caption: '{t['t'][:60]}'")
            t2["overlapping"] = True
        elif any(r["y"] + r["h"] > 1020 for r in t["rects"]):
            add("warn", "caption-zone", f"text in the caption zone (y > 1020): '{t['t'][:60]}'")
    margin = [t for t in main if any(r["x"] < 95 or r["x"] + r["w"] > W - 95 for r in t["rects"])]
    if margin:
        add("warn", "margin", f"{len(margin)} text runs inside the 96 px side margins, e.g. '{margin[0]['t'][:50]}'")
    small = [t for t in main if 0 < t["fs"] < args.min_font]
    if small:
        add("warn", "small-type", f"{len(small)} text runs under {args.min_font:g} px, e.g. '{small[0]['t'][:40]}' at {small[0]['fs']} px")

    # images, the map and its overlay
    map_img, map_vector = None, False
    for im in R["imgs"]:
        if im["complete"] and im["nw"] == 0:
            add("error", "image-broken", f"broken image {im['src']} [{im['el']}]")
            t2["image_broken"] |= im["visible"]
            continue
        sc = img_scale(im)
        if not sc or not im["visible"]:
            continue
        sx, sy, ox, oy = sc
        if im["map"]:
            map_img = (sx, sy, ox, oy)
            if abs(im.get("anc", 1) - 1) > 0.002:
                add("error", "map-transform", f"map image sits under a transform scale of {im['anc']} (blurs or resamples the vector)")
            vector = ".svg" in im["src"].lower() or im["src"].startswith("data:image/svg")
            map_vector = vector
            ok11 = abs(sx - 1) <= 0.002 and abs(sy - 1) <= 0.002
            stretch = abs(sx / sy - 1) > 0.002
            msg = (f"map {im['nw']}x{im['nh']} drawn at {im['nw'] * sx:.1f}x{im['nh'] * sy:.1f} device px "
                   f"(scale {sx:.4f} x {sy:.4f}, object-fit {im['fit']}, {'vector' if vector else 'raster'})")
            if stretch:
                add("error", "map-scale", "STRETCHED " + msg)
            elif not ok11 and not vector:
                add("error", "map-scale", "NOT 1:1 " + msg)
            else:
                add("info", "map-scale", msg)
        elif max(sx, sy) > 1.05:
            add("warn", "upscaled", f"image upscaled x{max(sx, sy):.2f} (soft on a projector): {im['src']}")
    for im in R["imgs"] + R.get("brandImgs", []):
        if im["complete"] and im["nw"] and im["visible"] and (im.get("fit") or "fill") in ("fill", "") and im["ow"] and im["oh"]:
            d = (im["rect"]["w"] / im["rect"]["h"]) / (im["nw"] / im["nh"]) - 1
            if abs(d) > 0.01:
                add("error", "aspect-distorted", f"image {im['src']} natural {im['nw']}x{im['nh']} shown in a {im['ow']}x{im['oh']} box ({d:+.1%} aspect error, object-fit fill) [{im['el']}]")
    for im in R.get("brandImgs", []):
        if im["visible"] and im["boxed"]:
            add("error", "logo-box", f"logo {im['src']} sits in a box (background, border or shadow)")
        if im["visible"] and not (im["rect"]["x"] < 500 and im["rect"]["y"] > 950):
            add("error", "logo-place", f"logo {im['src']} is not bottom-left ({im['rect']['x']:.0f}, {im['rect']['y']:.0f})")
        if im["visible"] and im["complete"] and im["nw"] == 0:
            add("error", "image-broken", f"brand logo broken {im['src']}")
    for im in R["images"]:
        if im["nat"] == [0, 0]:
            add("error", "image-broken", f"broken SVG <image> {im['src']} [{im['el']}]")
            t2["image_broken"] |= im["visible"]
        elif im["nat"] and im["visible"]:
            sx, sy = im["rect"]["w"] / im["nat"][0], im["rect"]["h"] / im["nat"][1]
            if im["map"]:
                map_img = (sx, sy, im["rect"]["x"], im["rect"]["y"])
                bad = abs(sx - 1) > 0.002 or abs(sy - 1) > 0.002
                add("error" if bad else "info", "map-scale", f"map SVG <image> {im['nat'][0]}x{im['nat'][1]} drawn at scale {sx:.4f} x {sy:.4f} (preserveAspectRatio '{im['par']}')")
            elif max(sx, sy) > 1.05:
                add("warn", "upscaled", f"SVG image upscaled x{max(sx, sy):.2f}: {im['src']}")
    if map_img:
        sx, sy, ox, oy = map_img
        for ov in ([] if map_vector else R["overlays"]):
            if not ov["visible"] or not (900 <= ov["vb"][2] <= 2000):
                continue
            ex0, ey0 = ox + ov["vb"][0] * sx, oy + ov["vb"][1] * sy
            ex1, ey1 = ox + (ov["vb"][0] + ov["vb"][2]) * sx, oy + (ov["vb"][1] + ov["vb"][3]) * sy
            d = max(abs(ov["p0"][0] - ex0), abs(ov["p0"][1] - ey0), abs(ov["p1"][0] - ex1), abs(ov["p1"][1] - ey1))
            add("error" if d > 1.5 else "info", "overlay-align",
                f"overlay viewBox {' '.join(f'{v:g}' for v in ov['vb'])} sits {d:.1f} px from the map pixels [{ov['el']}]")
    for c in R["charts"]:
        if c["marks"] == 0:
            add("warn", "chart-empty", f"chart-like element with no painted marks: {c['el']}")
            t2["chart_empty"] = True
    for r in R["ranges"]:
        if r["appearance"] != "none":
            add("error", "range-default", f"default browser slider (appearance {r['appearance']}): {r['el']}")

    # visible claims and slop (data-driven text included)
    pool = " | ".join(t["t"] for t in texts) + " | " + " | ".join(p["t"] for p in R["pseudo"])
    for code, match, neg in claim_hits(pool):
        add("warn" if neg else "error", "claim-visible", f"on screen: '{match}' ({code}{'; negated' if neg else ''})")
    if EMOJI.search(pool):
        add("warn", "emoji", f"emoji on screen: {''.join(sorted(set(EMOJI.findall(pool))))}")

    # presentation layer at this state
    L = R.get("layer") or {}
    if L.get("slides"):
        if L["active"] != [st["s"] - 1]:
            add("error", "layer-active", f".slide.active is {L['active']}, expected [{st['s'] - 1}] (exactly one, the current slide)")
        me = L["slides"][st["s"] - 1] if len(L["slides"]) >= st["s"] else None
        if me and not me["lastIsNotes"]:
            add("error", "layer-notes", f"last child of the slide is {me['lastChild']}, not script.slide-notes (moved by mount/step?)")

    # screenshot-based: blank, empty canvases, contrast
    if res["shot"]:
        try:
            import numpy as np
            L_img = lum_image(res["shot"])
            k = L_img.shape[1] / R["vw"] if R.get("vw") else 1.0
            to_px = lambda b: ((R["stage"]["left"] + b["x"] * R["stage"]["scale"]) * k, (R["stage"]["top"] + b["y"] * R["stage"]["scale"]) * k,
                               b["w"] * R["stage"]["scale"] * k, b["h"] * R["stage"]["scale"] * k)
            med = float(np.median(L_img))
            if float(np.mean(np.abs(L_img - med) > 0.04)) < 0.005:
                t2["blank"] = True
            for c in R["canvases"]:
                x, y, w, h = map(int, to_px(c["rect"]))
                reg = L_img[max(0, y):y + h, max(0, x):x + w]
                if reg.size and float(np.std(reg)) < 0.004:
                    add("warn", "chart-empty", f"canvas looks blank on the screenshot: {c['el']}")
                    t2["chart_empty"] = True
            low = []
            for group, items in (("text", [t for t in texts if t["cat"] in ("main", "src")]), ("brand", R.get("brandTexts") or [])):
                for t in items:
                    big = t["fs"] >= 24 or (t["fs"] >= 18.66 and t["fw"] >= 700)
                    need = 3.0 if big else 4.5
                    vals = [contrast(L_img, to_px(r), t["color"], t["op"]) for r in t["rects"][:3]]
                    vals = [v for v in vals if v]
                    if not vals:
                        continue
                    ratio, worst = min(v[0] for v in vals), min(v[1] for v in vals)
                    t["contrast"] = [ratio, worst]
                    if ratio < need:
                        low.append(f"'{t['t'][:36]}' {ratio:.1f}:1 (needs {need:g})")
                    elif worst < 2.0 and t["cat"] == "main":
                        low.append(f"'{t['t'][:36]}' on a busy background, worst {worst:.1f}:1")
            for t in texts:
                if t["cat"] != "decor" and re.search(r"rgba?\(255,\s*204,\s*0", t["color"] or "") and t.get("contrast"):
                    if t["contrast"][0] < 3.0:
                        add("error", "gold-on-light", f"gold #FFCC00 text fails on its background ({t['contrast'][0]}:1): '{t['t'][:40]}' (use --gold-ink #7A5F00)")
            if low:
                add("warn", "contrast", f"{len(low)} low-contrast runs: " + "; ".join(low[:4]))
        except Exception as e:
            add("info", "shot-analysis", f"screenshot analysis skipped: {e}")
    if res["words"] == 0 and res["art_words"] == 0 and R["visuals"] == 0 and not R["pseudo"]:
        t2["blank"] = True
    if t2["blank"]:
        add("error", "blank", "the slide looks blank")
    return res


def check_layer(L, func):
    out = []
    add = lambda sev, code, msg: out.append({"sev": sev, "code": code, "msg": msg})
    if not L:
        add("error", "layer", "presentation layer not inspected")
        return out
    if not L["deck"]:
        add("error", "layer-deck", f'<div class="deck" id="deck"> missing (found {L["deckTag"]})')
    sl = L["slides"]
    if not sl:
        add("error", "layer-slides", "no .slide children in #deck")
        return out
    got = [s["dataSlide"] for s in sl]
    if got != [str(i) for i in range(len(sl))]:
        add("error", "layer-numbering", f"data-slide is {got}, expected 0..{len(sl) - 1}")
    tags = sorted({s["tag"] for s in sl})
    if tags != ["div"]:
        add("info", "layer-tag", f"slides are <{'/'.join(tags)}> (html-slides writes <div>; .slide selectors still work)")
    if len(L["active"]) != 1:
        add("error", "layer-active", f"{len(L['active'])} slides carry .active, expected exactly one")
    for s in sl:
        tag = f"slide {s['i']} ({s['id']})"
        if not s["lastIsNotes"]:
            add("error", "layer-notes", f"{tag}: last child is {s['lastChild']}, not script.slide-notes")
        if s["err"]:
            add("error", "layer-notes", f"{tag}: slide-notes JSON invalid: {s['err']}")
            continue
        n = s["notes"]
        if n is None:
            continue
        if not isinstance(n, dict):
            add("error", "layer-notes", f"{tag}: slide-notes is not a JSON object")
            continue
        bad = [k for k, ok in (("title", isinstance(n.get("title"), str) and n["title"].strip()),
                               ("script", isinstance(n.get("script"), str) and n["script"].strip()),
                               ("notes", isinstance(n.get("notes"), list) and all(isinstance(x, str) for x in n["notes"]))) if not ok]
        if bad:
            add("error", "layer-notes", f"{tag}: slide-notes keys missing or empty: {', '.join(bad)}")
        if isinstance(n.get("notes"), list) and not n["notes"]:
            add("warn", "layer-notes", f"{tag}: notes[] is empty")
        text = " \n".join([str(n.get("title", "")), str(n.get("script", ""))] + [str(x) for x in (n.get("notes") or [])])
        cues = sorted({m.group(0).strip() for m in DELIVERY.finditer(text)})
        if cues:
            add("error", "delivery-cue", f"{tag}: delivery instructions in the notes: {', '.join(cues)}")
        for code, match, neg in claim_hits(text):
            add("warn" if neg else "error", "claim-notes", f"{tag}: spoken notes say '{match}' ({code}{'; negated' if neg else ''})")
    for k, v in L["globals"].items():
        if v != "function":
            add("error", "layer-globals", f"global {k}() missing ({v})")
    if func and not func.get("ok"):
        add("error", "layer-globals", f"goTo/next/prev do not move .active as expected: {func.get('r') or func.get('why')}")
    if not L.get("generator"):
        add("info", "layer-generator", 'no <meta name="generator" content="html-slides vX.Y.Z"> (html-slides spec rule 8)')
    return out


# ----------------------------------------------------------------------------------------------- outputs
def contact_sheet(rows, out_png, title):
    from PIL import Image, ImageDraw, ImageFont

    def font(size, bold=False):
        for name in (("segoeuib.ttf", "arialbd.ttf") if bold else ("segoeui.ttf", "arial.ttf")):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                pass
        return ImageFont.load_default(size=size)
    tw, th, lab, pad = 480, 270, 30, 14
    by = {}
    for r in rows:
        by.setdefault(r["s"], []).append(r)
    ncol = max(len(v) for v in by.values())
    sheet = Image.new("RGB", (pad + ncol * (tw + pad), 52 + len(by) * (lab + th + pad) + pad), (16, 18, 24))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 14), title, fill=(235, 238, 245), font=font(20, True))
    y = 52
    f1, f2 = font(17, True), font(16, True)
    for s in sorted(by):
        for c, r in enumerate(sorted(by[s], key=lambda r: r["k"])):
            x = pad + c * (tw + pad)
            col = (224, 69, 94) if r["n_err"] else (207, 127, 18) if r["n_warn"] else (30, 156, 110)
            d.text((x, y + 5), f"{s}.{r['k']}  {r['id']}", fill=(235, 238, 245), font=f1)
            d.text((x + tw, y + 6), f"{r['words']} w   {r['n_err']} err  {r['n_warn']} warn", fill=col, font=f2, anchor="ra")
            try:
                im = Image.open(r["shot"]).convert("RGB").resize((tw, th), Image.LANCZOS)
            except Exception:
                im = Image.new("RGB", (tw, th), (60, 10, 20))
            sheet.paste(im, (x, y + lab))
            d.rectangle([x - 2, y + lab - 2, x + tw + 1, y + lab + th + 1], outline=col, width=2)
        y += lab + th + pad
    sheet.save(out_png)


def cli_shots(chrome, base_url, items, outdir, workers=4):
    """The plain Chrome CLI screenshot (one process per state, virtual time budget), for comparison."""
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="cli-", dir=outdir))
    pool = queue.Queue()
    for i in range(workers):
        pool.put(tmp / f"p{i}")

    def one(item):
        s, k, png = item
        prof = pool.get()
        try:
            subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1920,1080",
                            "--force-device-scale-factor=1", "--virtual-time-budget=3000", f"--user-data-dir={prof}",
                            "--no-first-run", f"--screenshot={png}", f"{base_url}?static#{s}.{k}"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        finally:
            pool.put(prof)
        return png if Path(png).exists() else None
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, items))
    shutil.rmtree(tmp, ignore_errors=True)
    return res


def is_expected(text, url, offline):
    blob = f"{url} {text}"
    if any(re.search(p, blob) for p in EXPECTED_FAILS):
        return True
    return offline and "fonts.g" in blob


def parse_only(spec):
    out = []
    for part in filter(None, (p.strip() for p in spec.split(","))):
        s, _, k = part.partition(".")
        out.append((int(s), int(k) if k else None))
    return out


# ----------------------------------------------------------------------------------------------- main
def run(args):
    index = Path(args.deck).resolve()
    deck_dir = index.parent
    out = Path(args.out)
    shots = out / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    only = parse_only(args.only)
    if not only:
        for f in shots.glob("*.png"):
            f.unlink()
    P = load_pitch(Path(args.pitch_data))
    static = static_scan(deck_dir, index, P)
    log(f"source scan: {len(static)} findings in {deck_dir}")
    profile = Path(tempfile.mkdtemp(prefix="chrome-", dir=out))
    base = index.as_uri()
    console, captured, hidpi = {}, [], []
    chrome = Chrome(args.chrome, profile)
    try:
        cdp = chrome.page
        for dom in ("Page", "Runtime", "Log"):
            cdp.send(dom + ".enable")
        cdp.send("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=False)
        cdp.send("Page.addScriptToEvaluateOnNewDocument", source=HOOK_JS)
        if args.offline:
            cdp.send("Network.enable")
            cdp.send("Network.setBlockedURLs", urls=["*fonts.googleapis.com*", "*fonts.gstatic.com*"])
        token = [0]

        def load(s, k):
            token[0] += 1
            t = token[0]
            cdp.send("Page.navigate", url=f"{base}?static&qa={t}#{s}.{k}")
            end = time.time() + 25
            while time.time() < end:
                try:
                    if cdp.ev(f"document.readyState === 'complete' && location.search.indexOf('qa={t}') >= 0"):
                        break
                except RuntimeError:
                    pass
                time.sleep(0.05)
            else:
                raise RuntimeError(f"page did not finish loading: #{s}.{k}")
            for _ in range(2):
                cdp.ev(WAIT_JS, await_=True)
            time.sleep(args.settle)
            cdp.ev("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r(true))))", await_=True)

        def collect_events(state):
            cdp.drain(0.05)
            for m in cdp.events:
                meth, p, item = m.get("method"), m.get("params", {}), None
                if meth == "Runtime.exceptionThrown":
                    d = p.get("exceptionDetails", {})
                    text = ((d.get("exception") or {}).get("description") or d.get("text") or "exception").strip()
                    item = ("exception", text.splitlines()[0], d.get("url", ""), d.get("lineNumber"))
                elif meth == "Runtime.consoleAPICalled" and p.get("type") in ("error", "assert", "warning"):
                    parts = []
                    for a in p.get("args", []):
                        v = str(a.get("value", a.get("description", ""))).strip()
                        parts.append(v.splitlines()[0] if v else "")
                    fr = ((p.get("stackTrace") or {}).get("callFrames") or [{}])[0]
                    item = (p["type"], " ".join(parts), fr.get("url", ""), fr.get("lineNumber"))
                elif meth == "Log.entryAdded" and p.get("entry", {}).get("level") in ("error", "warning"):
                    e = p["entry"]
                    item = (e["level"], e.get("text") or "", e.get("url", ""), e.get("lineNumber"))
                if item:
                    level, text, url, line = item
                    short = url
                    if url.startswith("file:"):
                        short = urllib.request.url2pathname(url.split("?")[0].split("#")[0][5:]).lstrip("\\/")
                        try:
                            short = Path(short).resolve().relative_to(deck_dir).as_posix()
                        except ValueError:
                            short = Path(short).name
                    c = console.setdefault((level, text[:300], short), {"level": level, "text": text[:300], "url": short, "line": line,
                                                                         "states": [], "expected": is_expected(text, url, args.offline)})
                    if state not in c["states"]:
                        c["states"].append(state)
            cdp.events.clear()

        load(1, 0)
        defs = cdp.ev("window.__qaDefs || []") or []
        R0 = cdp.ev(INSPECT_JS, await_=True)
        func = cdp.ev(FUNC_JS) if R0["nSlides"] else None
        collect_events("load")
        by_id = {d.get("id"): d for d in defs}
        slides = []
        for i, sid in enumerate(R0["ids"], 1):
            d = by_id.get(sid, {})
            steps = d.get("steps")
            if not steps:                     # no hook data: let the engine clamp the step and read the hash
                load(i, 99)
                m = re.match(r"#\d+\.(\d+)", cdp.ev("location.hash") or "")
                steps = int(m.group(1)) + 1 if m else 1
                collect_events("probe")
            slides.append({"n": i, "id": sid, "title": d.get("title"), "steps": int(steps or 1), "time": d.get("time"),
                           "notes_words": d.get("notesWords")})
        log(f"{len(slides)} slides, {sum(s['steps'] for s in slides)} states: " + ", ".join(f"{s['n']}:{s['id']}x{s['steps']}" for s in slides))
        states = [{"s": s["n"], "k": k, "id": s["id"]} for s in slides for k in range(s["steps"])]
        if only:
            states = [st for st in states if any(st["s"] == s and (k is None or st["k"] == k) for s, k in only)]
        if not states:
            png = shots / "0.0_empty.png"
            if not args.no_shots:
                png.write_bytes(base64.b64decode(cdp.send("Page.captureScreenshot", format="png")["data"]))
            captured.append(({"s": 0, "k": 0, "id": "(none)"}, R0, png))
        for st in states:
            load(st["s"], st["k"])
            R = cdp.ev(INSPECT_JS, await_=True)
            png = shots / f"{st['s']}.{st['k']}_{re.sub(r'[^A-Za-z0-9_-]+', '-', st['id'] or 'slide')}.png"
            if not args.no_shots:
                png.write_bytes(base64.b64decode(cdp.send("Page.captureScreenshot", format="png", fromSurface=True)["data"]))
            collect_events(f"{st['s']}.{st['k']}")
            captured.append((st, R, png))
            log(f"  {st['s']}.{st['k']} {st['id']}: {sum(t['words'] for t in R['texts'] if t['cat'] == 'main')} words")
        # live pass: real transitions (no ?static), stepping through the whole deck forward and back
        if not only and not args.no_live:
            cdp.send("Page.navigate", url=f"{base}?qa=live#1.0")
            time.sleep(2.0)
            n_states = sum(s["steps"] for s in slides)
            for _ in range(n_states - 1):
                cdp.ev("Deck.next()")
                time.sleep(0.45)
            for _ in range(6):
                cdp.ev("Deck.prev()")
                time.sleep(0.3)
            time.sleep(1.0)
            collect_events("live")
        # hi-dpi pass: the map at device scale 2 (vector must stay 1:1 in CSS px with no transform above it)
        if not only and not args.no_hidpi:
            cdp.send("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=2, mobile=False)
            for st in states:
                load(st["s"], st["k"])
                Rh = cdp.ev(INSPECT_JS, await_=True)
                if any(i.get("map") and i["visible"] for i in Rh["imgs"] + Rh["images"]):
                    png2 = shots.parent / "shots2x" / f"{st['s']}.{st['k']}_{st['id']}@2x.png"
                    png2.parent.mkdir(exist_ok=True)
                    png2.write_bytes(base64.b64decode(cdp.send("Page.captureScreenshot", format="png", fromSurface=True)["data"]))
                    hidpi.append((st, Rh, png2))
            cdp.send("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=False)
    finally:
        chrome.close()
        shutil.rmtree(profile, ignore_errors=True)

    # analysis
    results, prev = [], {}
    for st, R, png in captured:
        r = analyse_state(st, R, png if not args.no_shots else None, args, prev.get(st["s"], set()) if st["k"] else set())
        prev[st["s"]] = set(r["main_texts"])
        results.append((st, R, r))
    glob = []
    gadd = lambda sev, code, msg: glob.append({"sev": sev, "code": code, "msg": msg})
    for f in static:
        gadd(f["sev"], f["code"], f"{f['file']}:{f['line']} {f['msg']}" if f["line"] else f"{f['file']}: {f['msg']}")
    glob += check_layer(R0.get("layer"), func) if R0.get("nSlides") else [{"sev": "error", "code": "no-slides", "msg": "no slide registered (missing slide files?)"}]
    for c in console.values():
        sev = "info" if c["expected"] else ("error" if c["level"] in ("error", "exception", "assert") else "warn")
        gadd(sev, "console", f"{c['level']}: {c['text'][:220]} ({c['url']}{':' + str(c['line']) if c['line'] is not None else ''}; states {', '.join(c['states'][:6])}{' ...' if len(c['states']) > 6 else ''})")
    for s in slides:
        exp = EXPECTED_STEPS.get(s["n"])
        if exp and exp != s["steps"]:
            gadd("info", "steps", f"slide {s['n']} ({s['id']}) has {s['steps']} steps; the storyboard says {exp}")
        if not s.get("notes_words"):
            gadd("warn", "notes", f"slide {s['n']} ({s['id']}) has no speaker notes")
    times = [s["time"] for s in slides if s.get("time")]
    if slides and len(times) == len(slides):
        gaps = [f"{a[1]}->{b[0]}" for a, b in zip(times, times[1:]) if a[1] != b[0]]
        if times[0][0] != 0 or times[-1][1] != 300 or gaps:
            gadd("warn", "timing", f"slide times {times} do not run 0-300 s without gaps")
    if not only:
        for n, phrases in REQUIRED.items():
            pool = " ".join(t["t"] for st, R, r in results if st["s"] == n for t in (R.get("texts") or []) + (R.get("pseudo") or []))
            if n <= len(slides):
                for sev, what, pat in phrases:
                    if not re.search(pat, pool, re.I):
                        gadd(sev, "required", f"slide {n}: {what} not found on screen")
    faces = sorted({f for st, R, r in results for f in (R.get("faces") or [])})
    loaded = sorted({f.rsplit(" ", 2)[0] for f in faces if f.endswith("loaded")})
    gadd("info", "fonts", f"web fonts loaded: {', '.join(loaded) or 'none (system fallback)'}")

    from PIL import Image as _Im
    for st, Rh, png2 in hidpi:
        for im in Rh["imgs"]:
            if not (im.get("map") and im["visible"]):
                continue
            sx = im["rect"]["w"] / im["nw"] if im["nw"] else 0
            vec = ".svg" in im["src"].lower()
            ok = abs(im.get("anc", 1) - 1) <= 0.002 and Rh["dpr"] == 2 and (vec or abs(sx - 1) <= 0.002) and (abs(sx - 1) <= 0.002 or im["rect"]["w"] < 1100)
            size = _Im.open(png2).size
            gadd("info" if ok and size == (3840, 2160) else "error", "map-hidpi",
                 f"{st['s']}.{st['k']}: map {im['src']} at device scale {Rh['dpr']}: {im['nw']}x{im['nh']} CSS px drawn at scale {sx:.4f}, ancestor transform {im.get('anc')}, screenshot {size[0]}x{size[1]}")
    # speaking time: script words at 130 wpm against the slide's time window
    notes_by = {s["id"]: s for s in (R0.get("layer") or {}).get("slides", [])}
    for s in slides:
        n = (notes_by.get(s["id"]) or {}).get("notes") or {}
        words = len(re.findall(r"\S+", n.get("script", "")))
        win = (s["time"][1] - s["time"][0]) if s.get("time") else None
        if win:
            sec = words / 130 * 60
            sev = "error" if sec > win else "warn" if sec < 0.6 * win else "info"
            gadd(sev, "speaking-time", f"slide {s['n']} ({s['id']}): script {words} words = {sec:.0f} s at 130 wpm; window {win} s ({sec / win:.0%})")
    # CLI comparison shots
    if args.cli and not args.no_shots:
        import numpy as np
        from PIL import Image
        items = [(st["s"], st["k"], str(out / "shots_cli" / Path(r["shot"]).name)) for st, R, r in results if r["shot"]]
        log(f"Chrome CLI shots: {len(items)} states")
        made =cli_shots(args.chrome, base, items, out / "shots_cli")
        for (s, k, cli_png), got in zip(items, made):
            r = next(x[2] for x in results if x[0]["s"] == s and x[0]["k"] == k)
            if not got:
                r["issues"].append({"sev": "warn", "code": "cli-shot", "msg": "Chrome CLI screenshot failed"})
                continue
            a = np.asarray(Image.open(r["shot"]).convert("RGB"), dtype=np.int16)
            b = np.asarray(Image.open(got).convert("RGB"), dtype=np.int16)
            if a.shape != b.shape:
                r["issues"].append({"sev": "warn", "code": "cli-shot", "msg": f"CLI shot is {b.shape[1]}x{b.shape[0]}, CDP shot {a.shape[1]}x{a.shape[0]}"})
                continue
            frac = float(np.mean(np.abs(a - b).max(axis=2) > 24))
            r["cli_diff"] = round(frac, 4)
            if frac > 0.01:
                r["issues"].append({"sev": "warn", "code": "cli-shot", "msg": f"CLI and CDP renders differ on {frac:.1%} of pixels (fonts or timing)"})

    # summary
    n_err = sum(1 for g in glob if g["sev"] == "error") + sum(1 for st, R, r in results for i in r["issues"] if i["sev"] == "error")
    n_warn = sum(1 for g in glob if g["sev"] == "warn") + sum(1 for st, R, r in results for i in r["issues"] if i["sev"] == "warn")
    rows = [{"s": st["s"], "k": st["k"], "id": st["id"], "words": r["words"], "shot": r["shot"],
             "n_err": sum(i["sev"] == "error" for i in r["issues"]), "n_warn": sum(i["sev"] == "warn" for i in r["issues"])} for st, R, r in results]
    sheet = None
    if not args.no_shots and rows:
        sheet = out / "contact_sheet.png"
        contact_sheet(rows, sheet, f"{index.name}  {datetime.now():%Y-%m-%d %H:%M}  {len(rows)} states  {n_err} errors  {n_warn} warnings"
                      + ("  [fonts blocked]" if args.offline else ""))
    summary = {
        "deck": str(index), "out": str(out), "when": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "offline": args.offline,
        "slides": slides,
        "states": [{"state": r["state"], "slide": r["slide"], "words": r["words"], "new_words": r["new_words"], "src_words": r["src_words"],
                    "tier2_fail": [k for k, v in r["tier2"].items() if v],
                    "errors": [i["msg"] for i in r["issues"] if i["sev"] == "error"],
                    "warnings": [i["msg"] for i in r["issues"] if i["sev"] == "warn"],
                    **({"cli_diff": r["cli_diff"]} if "cli_diff" in r else {}),
                    "shot": r["shot"]} for st, R, r in results],
        "global": {sev: [g["msg"] for g in glob if g["sev"] == sev] for sev in ("error", "warn", "info")},
        "totals": {"states": len(results), "errors": n_err, "warnings": n_warn,
                   "over_word_limit": [r["state"] for st, R, r in results if r["words"] > args.max_words],
                   "tier2_fail": {k: [r["state"] for st, R, r in results if r["tier2"][k]] for k in TIER2}},
        "contact_sheet": str(sheet) if sheet else None, "details": str(out / "audit.json"),
    }
    detail = {**summary, "global_issues": glob, "console": list(console.values()), "func_test": func,
              "layer": R0.get("layer"), "per_state": [{**r, "dom": R} for st, R, r in results]}
    (out / "audit.json").write_text(json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary, n_err


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deck", default=str(PITCH_DIR / "index.html"), help="deck HTML (default: index.html next to qa/)")
    ap.add_argument("--out", default=str(default_out()), help="output folder for shots, contact sheet and audit.json")
    ap.add_argument("--chrome", default=CHROME, help="Chrome executable (env PITCH_QA_CHROME)")
    ap.add_argument("--only", default="", help="states to audit, e.g. '3' (all of slide 3) or '3,4.1'")
    ap.add_argument("--settle", type=float, default=0.8, help="seconds to wait after load, fonts and images (default 0.8)")
    ap.add_argument("--offline", action="store_true", help="block Google Fonts to test the system-font fallback")
    ap.add_argument("--cli", action="store_true", help="also shoot each state with the plain Chrome CLI and compare")
    ap.add_argument("--no-live", action="store_true", help="skip the live (non-static) console pass")
    ap.add_argument("--no-hidpi", action="store_true", help="skip the device-scale-2 map pass")
    ap.add_argument("--no-shots", action="store_true", help="skip screenshots (no contrast, blank or contact sheet)")
    ap.add_argument("--max-words", type=int, default=20)
    ap.add_argument("--min-font", type=float, default=18.0, help="smallest comfortable type in px (source captions exempt)")
    ap.add_argument("--pitch-data", default=str(PITCH_DIR / "pitch-data.js"))
    args = ap.parse_args(argv)
    t0 = time.time()
    try:
        summary, n_err = run(args)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(json.dumps({"harness_error": repr(e)}))
        return 2
    summary["seconds"] = round(time.time() - t0, 1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
