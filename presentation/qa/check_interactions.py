#!/usr/bin/env python3
"""Bounded local interaction QA using audit.py's Chrome/CDP helper.

Run from the repository root:
    python powerpoint/pitch/qa/check_interactions.py
    python powerpoint/pitch/qa/check_interactions.py --deck powerpoint/pitch/johan-pitch.html

Only writes the requested JSON report and a temporary browser profile under data/raw.
No screenshots, deck mutations, builds, network resources, or dataset dumps.
Exit codes: 0 pass, 1 functional failure, 2 harness error or source changed during run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
from audit import CHROME, HOOK_JS, WAIT_JS, Chrome  # noqa: E402

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file())
# Includes legacy slide-specific counter delays; checks measure settled behavior.
SETTLE = {'s1': 4.1, 's2': 3.0, 's3': 1.7, 's4': 1.9, 's5': 1.2}

PROBE_JS = r"""
(() => {
  const nativeRAF = window.requestAnimationFrame.bind(window);
  window.__interaction = { raf: 0, mutations: 0 };
  window.requestAnimationFrame = callback => nativeRAF(t => {
    window.__interaction.raf++; callback(t);
  });
  addEventListener('DOMContentLoaded', () => {
    const deck = document.querySelector('#deck');
    if (deck) new MutationObserver(rs => { window.__interaction.mutations += rs.length; })
      .observe(deck, {subtree: true, attributes: true, childList: true, characterData: true});
  });
})();
"""

SNAPSHOT_JS = r"""
(() => {
  const slides = [...document.querySelectorAll('#deck > .slide')];
  const active = slides.filter(s => s.classList.contains('active'));
  const slide = active[0];
  const visible = el => {
    if (!el || !el.getClientRects().length || el.closest('[aria-hidden="true"]')) return false;
    let opacity = 1;
    for (let n = el; n; n = n.parentElement) {
      const c = getComputedStyle(n);
      if (c.display === 'none' || c.visibility !== 'visible') return false;
      opacity *= Number(c.opacity);
    }
    return opacity > .05;
  };
  const texts = [];
  if (slide) {
    const walker = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const n = walker.currentNode, el = n.parentElement;
      if (el.closest('script,.s4-sr') || !visible(el)) continue;
      const text = n.textContent.replace(/\s+/g, ' ').trim();
      if (text) texts.push(text);
    }
  }
  const describe = el => el ? el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
    '.' + String(el.getAttribute('class') || '').trim().replace(/\s+/g, '.') : '(unknown)';
  const animations = document.getAnimations().filter(a => a.playState === 'running' || a.pending)
    .map(a => {
      const target = a.effect && a.effect.target;
      const t = a.effect && a.effect.getTiming();
      return {target: describe(target), pace: !!(target && target.closest('#pace')),
        infinite: !!t && t.iterations === Infinity,
        duration_ms: t && typeof t.duration === 'number' ? t.duration : null};
    });
  const builds = slide ? [...slide.querySelectorAll('[data-b]')].map((el, i) =>
    [i, visible(el), Number(getComputedStyle(el).opacity) > .99]) : [];
  const routes = slide ? [...slide.querySelectorAll('.s3-route path')].map(el =>
    Math.abs(parseFloat(getComputedStyle(el).strokeDashoffset) || 0) < .1) : [];
  const errors = [];
  if (active.length !== 1) errors.push('active slide count: ' + active.length);
  if (slides.filter(s => s.classList.contains('is-active')).length !== 1) errors.push('is-active count');
  if (slides.some(s => s.inert === (s === slide))) errors.push('inert state disagrees with active slide');
  if (slide && (Number(slide.dataset.slide) + 1 !== Deck.current.slide ||
      Number(slide.dataset.step) !== Deck.current.step)) errors.push('DOM/current mismatch');
  if (window.DeckMotion && slide && (DeckMotion.current.id !== slide.id ||
      DeckMotion.current.step !== Deck.current.step)) errors.push('motion/current mismatch');
  if (document.querySelector('.deck-problems')) errors.push('deck load/mount problem');
  if (!texts.length) errors.push('blank visible text');
  const broken = [...document.images].filter(i => !i.complete || !i.naturalWidth);
  if (broken.length) errors.push('broken images: ' + broken.length);
  return {hash: location.hash, current: window.Deck && Deck.current, errors,
    signature: {texts, builds, routes}, animations,
    raf: __interaction.raf, mutations: __interaction.mutations,
    notesHidden: document.querySelector('#notes').hidden};
})();
"""

CONTROL_JS = r"""
(() => {
  const li = +document.querySelector('#s4-level').value;
  const si = +document.querySelector('#s4-set').value;
  const lv = PITCH.levels[li], st = PITCH.sets[si];
  const key = `${lv.id}|${lv.closure}|${st.id}`;
  const p = PITCH.plans[key], j = PITCH.johan.plans[key];
  const fmt = (v, d=0) => Number(v).toLocaleString('en-GB', {minimumFractionDigits:d,maximumFractionDigits:d});
  const want = {kpi: fmt(Math.round(100*p.within30/p.to_place)), within30: fmt(p.within30),
    over30: fmt(p.over30), no_place: fmt(p.no_place), roads: fmt(p.roads_over),
    mean: fmt(p.mean_min, 1), res: fmt(p.to_place)};
  if (j && j.status === 'placed') want.eta = fmt(j.total_min, 1);
  const mismatches = Object.entries(want).filter(([k, v]) =>
    document.querySelector(`#s4 [data-k="${k}"]`).textContent.trim() !== v).map(([k]) => k);
  const text = document.querySelector('#s4 .s4-text').textContent;
  const severity = {obs2021:'as in July 2021',rp10:'a 1-in-10-year flood',
    rp100:'a 1-in-100-year flood',rp500:'a 1-in-500-year flood'};
  if (!text.includes(severity[lv.id])) mismatches.push('alert level');
  if (j && j.status === 'placed' && !text.includes(j.shelter.title)) mismatches.push('alert destination');
  if (![...document.querySelectorAll('#s4 input[type=range]')].every(n => n.getAttribute('aria-valuetext')))
    mismatches.push('range aria-valuetext');
  return {level: li, set: si, key, mismatches};
})();
"""


def relative_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Paths must remain inside the repository')
    return path


def source_hashes(deck: Path) -> dict:
    paths = [deck]
    if deck.name == 'index.html':
        paths += [deck.parent / 'pitch-data.js']
        for folder in ('js', 'css', 'slides'):
            paths += sorted(p for p in (deck.parent / folder).glob('*') if p.suffix in ('.js', '.css'))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


class Check:
    def __init__(self, cdp, deck, report, skip):
        self.cdp, self.deck, self.report = cdp, deck, report
        self.token = 0
        self.baseline = {}
        self.runtime_errors = set()
        self.external_requests = set()
        self.external_responses = set()
        self.skip = set(skip)
        self.states = []
        self.slides = []

    def record(self, name, failures=None, **details):
        failures = failures or []
        self.report['checks'].append({'name': name, 'status': 'fail' if failures else 'pass',
                                      **details, **({'failures': failures[:24]} if failures else {})})
        print(f"{name}: {'FAIL' if failures else 'pass'}", flush=True)

    def collect_errors(self):
        for event in self.cdp.events:
            method, p = event.get('method'), event.get('params', {})
            if method == 'Runtime.exceptionThrown':
                d = p.get('exceptionDetails', {})
                self.runtime_errors.add(((d.get('exception') or {}).get('description') or d.get('text', 'exception'))[:240])
            elif method == 'Runtime.consoleAPICalled' and p.get('type') in ('error', 'assert'):
                self.runtime_errors.add(' '.join(str(a.get('value', a.get('description', ''))) for a in p.get('args', []))[:240])
            elif method in ('Network.requestWillBeSent', 'Network.responseReceived'):
                url = (p.get('request') or p.get('response') or {}).get('url', '')
                if url.startswith(('http://', 'https://')):
                    host = urlsplit(url).netloc
                    (self.external_requests if method == 'Network.requestWillBeSent' else self.external_responses).add(host)
        self.cdp.events.clear()

    def load(self, state=(1, 0), static=False, reduced=False):
        self.collect_errors()
        self.token += 1
        self.cdp.send('Emulation.setEmulatedMedia', features=[{'name': 'prefers-reduced-motion',
                      'value': 'reduce' if reduced else 'no-preference'}])
        url = f"{self.deck.as_uri()}?interaction_qa={self.token}{'&static' if static else ''}#{state[0]}.{state[1]}"
        self.cdp.send('Page.navigate', url=url)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                if self.cdp.ev(f"location.search.includes('interaction_qa={self.token}') && document.readyState === 'complete' && !!window.DeckMotion"):
                    break
            except RuntimeError:
                pass
            time.sleep(.05)
        else:
            raise RuntimeError('Deck did not load within 15 seconds')
        self.cdp.ev(WAIT_JS, await_=True)
        time.sleep(.12)

    def snap(self):
        result = self.cdp.ev(SNAPSHOT_JS)
        self.collect_errors()
        return result

    def settle(self, state):
        time.sleep(SETTLE.get(self.slides[state[0]-1]['id'], 1.8))

    def key(self, key):
        codes = {'ArrowRight':39, 'ArrowLeft':37, 'Home':36, 'End':35, 'Escape':27, ' ':32,
                 'PageDown':34, 'PageUp':33, 'Enter':13, 'Backspace':8}
        code = codes.get(key, ord(key.upper()) if len(key) == 1 else 0)
        for kind in ('keyDown', 'keyUp'):
            self.cdp.send('Input.dispatchKeyEvent', type=kind, key=key, windowsVirtualKeyCode=code)

    def compare(self, state, snapshot, baseline=True):
        label = f'{state[0]}.{state[1]}'
        problems = list(snapshot['errors'])
        if snapshot['hash'] != '#' + label or snapshot['current'] != {'slide':state[0], 'step':state[1]}:
            problems.append('wrong navigation destination')
        if baseline and snapshot['signature'] != self.baseline[state]:
            parts = [k for k in snapshot['signature'] if snapshot['signature'][k] != self.baseline[state][k]]
            problems.append('differs from fresh static state: ' + ', '.join(parts))
        return [{'state': label, 'issue': p} for p in problems]

    def run(self):
        self.load(static=True)
        self.slides = self.cdp.ev("""[...document.querySelectorAll('#deck > .slide')].map((el,i)=>{
          const d=__qaDefs.find(d=>d.id===el.id);return {slide:i+1,id:el.id,steps:d.steps};})""")
        self.report['slides'] = self.slides
        self.report['builds'] = sum(s['steps'] for s in self.slides)
        self.report['skipped_slide_ids'] = sorted(self.skip)
        self.states = [(s['slide'], k) for s in self.slides if s['id'] not in self.skip for k in range(s['steps'])]
        if not self.states:
            raise RuntimeError('No states selected')
        ids = {s['id']:s['slide'] for s in self.slides}
        states = self.states
        first_state, last_state = states[0], states[-1]
        failures = []
        for state in states:
            self.load(state, static=True)
            snap = self.snap()
            self.baseline[state] = snap['signature']
            failures += self.compare(state, snap, baseline=False)
        counts = [s['steps'] for s in self.slides]
        self.record('structure_and_static_baselines', failures, slides=len(counts), builds=sum(counts), steps=counts,
                    selected_builds=len(states), expectation='discovered registered slides, per updated user direction')

        self.load(first_state)
        failures, idle_failures, animation_samples = [], [], 0
        sequence = states + list(reversed(states[:-1]))
        for i, state in enumerate(sequence):
            if i:
                self.key('ArrowRight' if i < len(states) else 'ArrowLeft')
                time.sleep(.07)
                animation_samples += sum(not a['pace'] for a in self.snap()['animations'])
            self.settle(state)
            snap = self.snap()
            failures += self.compare(state, snap)
            if i < len(states):
                time.sleep(.45)
                end = self.snap()
                anims = [a for a in end['animations'] if not a['pace']]
                if anims or end['raf'] != snap['raf'] or end['mutations'] != snap['mutations']:
                    idle_failures.append({'state': f'{state[0]}.{state[1]}', 'animations': anims[:5],
                        'raf_callbacks': end['raf']-snap['raf'], 'deck_mutations':end['mutations']-snap['mutations']})
            if i % 8 == 3:
                print(f'  animated traversal {i+1}/{len(sequence)}', flush=True)
        if not animation_samples:
            failures.append({'issue': 'normal-motion navigation produced no observed animation'})
        self.record('animated_forward_backward', failures, visited_states=len(sequence), animation_samples=animation_samples)
        self.record('idle_no_continuous_deck_animation', idle_failures, states=len(states), sample_ms=450,
                    excludes='intentional #pace timer/transition; notes hidden', includes='hidden slide animations and requestAnimationFrame callbacks')
        first = []
        if first_state == (1,0):
            self.key('ArrowLeft')
            time.sleep(.1)
            first = self.compare(first_state, self.snap())
        self.cdp.ev(f'Deck.go({last_state[0]}, {last_state[1]})')
        self.settle(last_state)
        self.key('ArrowRight')
        self.record('navigation_boundaries', first + self.compare(last_state, self.snap()), first_boundary_tested=first_state==(1,0))

        failures = []
        for state in states:
            self.load(state)
            self.settle(state)
            failures += self.compare(state, self.snap())
        hash_cases = [(f'#{s}.{k}', (s,k)) for s,k in [states[len(states)//2],first_state,last_state]]
        hash_cases += [(f'#{last_state[0]}',(last_state[0],0)), ('#999.99',last_state)]
        if first_state == (1,0):
            hash_cases.append(('#0.99',(1,self.slides[0]['steps']-1)))
        for raw, state in hash_cases:
            self.cdp.ev(f'location.hash = {json.dumps(raw)}')
            self.settle(state)
            failures += self.compare(state, self.snap())
        self.record('direct_hash_and_live_hashchange', failures, fresh_loads=len(states), live_changes=len(hash_cases))

        failures = []
        bursts = [(list(reversed(states))+[states[len(states)//2]], states[len(states)//2]),
                  (states+[first_state],first_state), (states[::2]+[last_state],last_state)]
        for burst, final in bursts:
            self.cdp.ev('(()=>{' + ''.join(f'Deck.go({s},{k});' for s,k in burst) + '})()')
            self.settle(final)
            failures += self.compare(final, self.snap())
        spaced = states[::3]+[first_state]
        self.cdp.ev('(async()=>{for(const [s,k] of '+json.dumps(spaced)+'){Deck.go(s,k);await new Promise(r=>setTimeout(r,40));}})()', await_=True)
        self.settle(first_state)
        failures += self.compare(first_state, self.snap())
        self.record('rapid_go', failures, synchronous_bursts=3, spaced_burst_ms=40)

        failures = []
        self.load(first_state,reduced=True)
        for state in states:
            self.cdp.ev(f'Deck.go({state[0]},{state[1]})')
            time.sleep(.12)
            snap = self.snap()
            failures += self.compare(state, snap)
            if any(not a['pace'] for a in snap['animations']):
                failures.append({'state': f'{state[0]}.{state[1]}', 'issue':'animation under reduced motion'})
        self.record('reduced_motion_at_load', failures, states=len(states))

        failures = []
        map_slide = ids['s3']
        self.load((map_slide,1))
        self.key('ArrowRight')
        time.sleep(.08)
        self.cdp.send('Emulation.setEmulatedMedia', features=[{'name':'prefers-reduced-motion','value':'reduce'}])
        time.sleep(.15)
        snap = self.snap()
        failures += self.compare((map_slide,2), snap)
        time.sleep(.15)
        after = self.snap()
        if after['raf'] > snap['raf']:
            failures.append({'issue':'ticker callbacks continue after live reduced-motion change',
                             'raf_callbacks':after['raf']-snap['raf']})
        self.record('live_reduced_motion_change', failures, settled_after_change_ms=150)

        self.load(first_state,static=True)
        self.key('n')
        failures = []
        for state in states:
            self.cdp.ev(f'Deck.go({state[0]},{state[1]})')
            notes = self.cdp.ev("""(() => {
              const s=document.querySelector('.slide.active'), n=JSON.parse(s.querySelector('script.slide-notes').textContent);
              const panel=document.querySelector('#notes'), head=panel.querySelector('.notes-head').textContent;
              return !panel.hidden && !!n.title && !!n.script && Array.isArray(n.notes) &&
                s.lastElementChild.matches('script.slide-notes') && head.includes(n.title) &&
                head.includes('step '+(Deck.current.step+1)+'/') && panel.querySelector('.notes-body').textContent.includes(n.script);
            })()""")
            if not notes:
                failures.append({'state':f'{state[0]}.{state[1]}', 'issue':'notes missing or stale'})
        self.key('n')
        if not self.snap()['notesHidden']:
            failures.append({'issue':'N did not close notes'})
        self.key('n')
        self.key('Escape')
        if not self.snap()['notesHidden']:
            failures.append({'issue':'Escape did not close notes'})
        self.record('notes', failures, states=len(states))

        self.load((ids['s4'],1))
        self.settle((ids['s4'],1))
        failures, plans = [], []
        for si in range(2):
            if si:
                self.key('b')
            for li in range(4):
                self.key(str(li+1))
                time.sleep(1.2)
                actual = self.cdp.ev(CONTROL_JS)
                plans.append(actual['key'])
                if actual['level'] != li or actual['set'] != si or actual['mismatches']:
                    failures.append(actual)
        # Exercise native pointer input and confirm the next deck key is not swallowed.
        box = self.cdp.ev("(()=>{const r=document.querySelector('#s4-level').getBoundingClientRect();return {x:r.left+8,y:r.top+r.height/2};})()")
        for kind in ('mousePressed','mouseReleased'):
            self.cdp.send('Input.dispatchMouseEvent', type=kind, x=box['x'], y=box['y'], button='left', clickCount=1)
        time.sleep(1.2)
        pointer = self.cdp.ev(CONTROL_JS)
        if pointer['level'] != 0 or pointer['mismatches']:
            failures.append({'issue':'native range pointer control', **pointer})
        self.key('ArrowRight')
        self.settle((ids['s5'],0))
        failures += self.compare((ids['s5'],0), self.snap())
        self.record('slide4_existing_controls', failures, plans_checked=plans,
                    checked='1-4, B, native range pointer, values/ETA versus PITCH.plans, alert level/destination, aria labels, navigation after pointer')
        self.record('runtime_errors', sorted(self.runtime_errors))
        self.record('offline_network', [{'issue':'external resource received','host':h} for h in sorted(self.external_responses)],
                    offline_emulation=True, blocked_url_patterns=['http://*','https://*'],
                    external_request_hosts=sorted(self.external_requests), external_response_hosts=sorted(self.external_responses))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deck', default='powerpoint/pitch/index.html')
    parser.add_argument('--out', default='figures/generated/pitch/interaction_check.json')
    parser.add_argument('--chrome', default=CHROME)
    parser.add_argument('--skip-slide', action='append', default=[], help='slide ID temporarily excluded, e.g. s1')
    args = parser.parse_args()
    deck, out = relative_path(args.deck), relative_path(args.out)
    before = source_hashes(deck)
    start = time.monotonic()
    report = {'schema':1, 'deck':deck.relative_to(ROOT).as_posix(),
              'when_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'scope':'local interaction QA; visual/layout audit and analytical validation belong to main',
              'viewport':[1920,1080], 'external_resources_blocked':True, 'offline_emulation':True, 'checks':[]}
    chrome = None
    cache = ROOT / 'data' / 'raw' / 'pitch-interaction-qa'
    cache.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='chrome-', dir=cache, ignore_cleanup_errors=True) as profile:
            try:
                chrome = Chrome(args.chrome, profile)
                cdp = chrome.page
                for domain in ('Page','Runtime','Network'):
                    cdp.send(domain+'.enable')
                cdp.send('Network.setBlockedURLs', urls=['http://*','https://*'])
                cdp.send('Network.emulateNetworkConditions', offline=True, latency=0, downloadThroughput=0, uploadThroughput=0)
                cdp.send('Emulation.setDeviceMetricsOverride', width=1920, height=1080, deviceScaleFactor=1, mobile=False)
                cdp.send('Page.addScriptToEvaluateOnNewDocument', source=HOOK_JS+'\n'+PROBE_JS)
                report['browser'] = cdp.send('Browser.getVersion')['product']
                Check(cdp, deck, report,args.skip_slide).run()
            finally:
                if chrome:
                    chrome.close()
    except Exception as exc:
        report['harness_error'] = str(exc)[:600]
    after = source_hashes(deck)
    changed = [p for p in set(before)|set(after) if before.get(p) != after.get(p)]
    skipped_changes = [p for p in changed if any(Path(p).name.startswith(s+'-') for s in args.skip_slide)]
    relevant_changes = [p for p in changed if p not in skipped_changes]
    report['source_fingerprint_sha256'] = hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest()
    report['changed_source_files_during_run'] = sorted(changed)
    report['changed_skipped_source_files'] = sorted(skipped_changes)
    report['seconds'] = round(time.monotonic()-start,1)
    failed = [c['name'] for c in report['checks'] if c['status'] == 'fail']
    report['status'] = 'incomplete' if report.get('harness_error') or relevant_changes else 'fail' if failed else 'pass'
    report['failed_checks'] = failed
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'failed_checks':failed,
                      'harness_error':report.get('harness_error'),'changed_source_files':changed,
                      'report':out.relative_to(ROOT).as_posix(),'seconds':report['seconds']}))
    return 2 if report['status'] == 'incomplete' else 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
