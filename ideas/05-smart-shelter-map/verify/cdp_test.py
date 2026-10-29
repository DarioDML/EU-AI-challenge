"""Real-input browser test of dist/shelter_tool.html (headless Chrome over the DevTools protocol).

Run:  .venv\\Scripts\\python.exe -B -I tool\\verify\\cdp_test.py
Needs the `websocket` (websocket-client) module that is already in the venv. Uses its own Chrome profile.
Real mouse events (Input.dispatchMouseEvent) are used for map and button clicks; the three selects are changed with real key
presses (ArrowDown / Home). Expected numbers are recomputed from data/bundle.json in Python, not read from the page.
"""
import json
import math
import os
import subprocess
import sys
import time
import urllib.request

import websocket

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = os.path.join(os.environ.get("TEMP", HERE), "chrome_cdp_profile")
DL = os.path.join(HERE, "downloads")
PORT = 9333
URL = "file:///" + os.path.join(TOOL, "dist", "shelter_tool.html").replace("\\", "/")
bundle = json.load(open(os.path.join(TOOL, "data", "bundle.json"), encoding="utf-8"))

os.makedirs(DL, exist_ok=True)
for f in os.listdir(DL):
    os.remove(os.path.join(DL, f))
os.makedirs(PROFILE, exist_ok=True)
proc = subprocess.Popen([CH, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}", "--disable-gpu",
                         "--window-size=1440,900", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
results = []   # (name, ok, detail)


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + ((" | " + str(detail)) if detail != "" else ""))


def http(path):
    for _ in range(60):
        try:
            return json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=2))
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("chrome did not start")


class Cdp:
    def __init__(self, url):
        self.ws = websocket.create_connection(url, max_size=None, timeout=60)
        self.n = 0
        self.events = []

    def send(self, method, **params):
        self.n += 1
        mid = self.n
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(method + ": " + json.dumps(msg["error"]))
                return msg.get("result", {})
            self.events.append(msg)

    def drain(self, wait=0.3):
        self.ws.settimeout(wait)
        try:
            while True:
                self.events.append(json.loads(self.ws.recv()))
        except Exception:
            pass
        self.ws.settimeout(60)


try:
    ver = http("/json/version")
    pages = [t for t in http("/json") if t["type"] == "page"]
    browser = Cdp(ver["webSocketDebuggerUrl"])
    page = Cdp(pages[0]["webSocketDebuggerUrl"])
    for dom in ("Page", "Runtime"):
        page.send(dom + ".enable")
    page.send("Emulation.setDeviceMetricsOverride", width=1440, height=900, deviceScaleFactor=1, mobile=False)
    page.send("Emulation.setFocusEmulationEnabled", enabled=True)
    browser.send("Browser.setDownloadBehavior", behavior="allow", downloadPath=DL)
    try:
        browser.send("Browser.grantPermissions", permissions=["clipboardReadWrite", "clipboardSanitizedWrite"])
    except Exception as e:
        print("grantPermissions:", e)

    def ev(expr, await_=False):
        r = page.send("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=await_)
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:400])
        return r["result"].get("value")

    def shot(name):
        data = page.send("Page.captureScreenshot", format="png")["data"]
        import base64
        open(os.path.join(HERE, name + ".png"), "wb").write(base64.b64decode(data))

    def mouse_click(x, y):
        for typ in ("mouseMoved", "mousePressed", "mouseReleased"):
            page.send("Input.dispatchMouseEvent", type=typ, x=x, y=y, button="left" if typ != "mouseMoved" else "none", clickCount=1)
        time.sleep(0.25)

    def press_key(k, code, vk):
        for typ in ("keyDown", "keyUp"):
            page.send("Input.dispatchKeyEvent", type=typ, key=k, code=code, windowsVirtualKeyCode=vk, nativeVirtualKeyCode=vk)

    def select_option(sel_id, index):
        """focus the select and press Home, then ArrowDown `index` times (real key events)."""
        ev(f"document.getElementById('{sel_id}').focus()")
        press_key("Home", "Home", 36)
        for _ in range(index):
            press_key("ArrowDown", "ArrowDown", 40)
        time.sleep(0.35)

    def el_center(selector):
        return ev(f"(()=>{{const e=document.querySelector({json.dumps(selector)}); e.scrollIntoView({{block:'center'}}); const r=e.getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2];}})()")

    def map_point(kind, ident, zoom=13):
        # centre the map on the object (programmatic view only), then ask where it is on screen
        return ev(f"""(()=>{{const t=window.__tool; const o=t.{ 'Z' if kind=='zone' else 'S'}.get({ident});
          t.map.setView([o.lat,o.lon],{zoom},{{animate:false}}); window.scrollTo(0,0);
          const p=t.map.latLngToContainerPoint([o.lat,o.lon]); const r=document.getElementById('map').getBoundingClientRect();
          return [r.left+p.x, r.top+p.y];}})()""")

    # ---------------------------------------------------------------- load
    t0 = time.time()
    page.send("Page.navigate", url=URL)
    for _ in range(200):
        if ev("document.readyState") == "complete" and ev("!!window.__tool"):
            break
        time.sleep(0.2)
    load_s = time.time() - t0
    time.sleep(1.5)
    check("page loads, bundle read", ev("!!window.__tool && window.__tool.st.sc") == "obs2021", f"load+init {load_s:.1f} s")
    check("default state obs2021|any|restrictive", ev("[__tool.st.sc,__tool.st.cl,__tool.st.cap].join('|')") == "obs2021|any|restrictive")
    check("MOCK badge hidden on real data", ev("getComputedStyle(document.getElementById('mockBadge')).display") == "none")
    vp = ev("[innerWidth, innerHeight, Math.round(document.getElementById('map').getBoundingClientRect().top), document.documentElement.scrollWidth]")
    visible = (min(vp[1], ev("document.getElementById('map').getBoundingClientRect().bottom")) - vp[2]) / vp[1]
    check("map is >= 60% of viewport height on first screen", visible >= 0.6, f"{visible*100:.0f}% (map top at {vp[2]} px of {vp[1]})")
    check("no horizontal scroll at 1440", vp[3] <= vp[0], vp)
    banner = ev("document.getElementById('bannerText').textContent")
    check("banner shows Germany only + area", "Germany only" in banner and bundle["meta"]["area"] in banner, banner[:140])
    mid = mouse_click(*el_center("#btnDisc"))
    disc = ev("(()=>{const d=document.getElementById('discBody'); return [d.hidden, d.innerText]})()")
    check("expandable disclaimer lists limits and not-modelled", (not disc[0]) and "Limits" in disc[1] and "Not modelled" in disc[1]
          and str(bundle["meta"]["outside_hero_area"]["rp100"]).replace("59504", "59,504") in disc[1], f"{len(disc[1])} chars; dict repr gone: {'{' not in disc[1]}")
    shot("t_disc_open")
    mouse_click(*el_center("#btnDisc"))
    ev("window.scrollTo(0,0)")

    # ---------------------------------------------------------------- expected summaries from the bundle
    def expect_cards(key):
        s = bundle["results"][key]["summary"]
        f = lambda v: f"{round(v):,}"
        return {"People to place (min.)": f(s["people_to_place"]), "Placed": f(s["placed"]), "UNASSIGNED": f(s["unassigned"]),
                "Mean time (walk + road)": f"{s['mean_time_min']:.1f} min", "Walk to open road": f"{s['mean_access_min']:.1f} min",
                "Road detour": f"{s['mean_detour_min']:.1f} min", "Shelters used": f(s["shelters_used"]), "Closed roads": f(s["closed_edges"]),
                "Stress over 1 (indicator)": f(s["stress_edges_over_1"])}

    def read_cards():
        return ev("""Object.fromEntries(Array.from(document.querySelectorAll('#summary .card')).map(c=>[c.querySelector('.l').firstChild.textContent, c.querySelector('.v').textContent]))""")

    def zone_expect(key):
        r = bundle["results"][key]
        sc = key.split("|")[0]
        pop = {z["id"]: z["people"][sc] for z in bundle["zones"]}
        return r, pop

    # ---------------------------------------------------------------- sweep: 4 flood levels x 2 capacity sets (+ the 'mapped' rule)
    scen_ids = [s["id"] for s in bundle["scenarios"]]
    cap_ids = [c["id"] for c in bundle["capacities"]]
    sweep_ms = {}
    first = True
    for si, sc in enumerate(scen_ids):
        for ci, cap in enumerate(cap_ids):
            closures = [c["id"] for c in next(s for s in bundle["scenarios"] if s["id"] == sc)["closures"]]
            for cli, cl in enumerate(closures):
                key = f"{sc}|{cl}|{cap}"
                select_option("selScenario", si)
                select_option("selClosure", cli)
                select_option("selCapacity", ci)
                st = ev("[__tool.st.sc,__tool.st.cl,__tool.st.cap].join('|')")
                exp = expect_cards(key)
                got = read_cards()
                bad = {k: (got.get(k), v) for k, v in exp.items() if got.get(k) != v}
                check(f"{key}: keyboard selects reach the state, summary cards equal bundle summary", st == key and not bad, bad or "")
                # people sums: page-visible zone list vs bundle
                r, pop = zone_expect(key)
                shown = ev("Array.from(document.getElementById('selZone').options).length - 1")
                want = sum(1 for v in pop.values() if v >= 0.5)
                check(f"{key}: zone list = zones with >=1 resident", shown == want, f"{shown} vs {want}")
    # timing of ONE real key press that changes the flood level, to the second frame after it (no sleeps inside the timed part)
    timing = {}
    for si in range(len(scen_ids)):
        for cap_i in (0, 1):
            select_option("selCapacity", cap_i)
            start = si - 1 if si > 0 else 1          # neighbour level, reached with untimed presses
            select_option("selScenario", start)
            ev("document.getElementById('selScenario').focus(); window.__t0=performance.now()")
            if si > 0:
                press_key("ArrowDown", "ArrowDown", 40)
            else:
                press_key("ArrowUp", "ArrowUp", 38)
            ms = ev("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r(performance.now()-window.__t0))))", True)
            ok_state = ev("__tool.st.sc") == scen_ids[si]
            timing[f"{scen_ids[si]}|{cap_ids[cap_i]}"] = (round(ms), ok_state)
    print("one key press changing the flood level -> ms until 2nd frame:", timing)
    check("every timed key press reached the intended level", all(v[1] for v in timing.values()))

    # ---------------------------------------------------------------- zone + shelter clicks, per flood level (restrictive, first closure rule)
    for si, sc in enumerate(scen_ids):
        select_option("selScenario", si)
        select_option("selClosure", 0)
        select_option("selCapacity", 0)
        key = f"{sc}|{bundle['scenarios'][si]['closures'][0]['id']}|{cap_ids[0]}"
        r = bundle["results"][key]
        # a zone with a clear route and a few hundred residents
        cand = sorted({a[0]: 0 for a in r["assign"]}.keys())
        pop = {z["id"]: z["people"][sc] for z in bundle["zones"]}
        zid = max(cand, key=lambda z: pop[z])
        x, y = map_point("zone", zid, 14)
        top = ev(f"(()=>{{const e=document.elementFromPoint({x},{y}); return e? e.className + ' ' + e.tagName : null}})()")
        mouse_click(x, y)
        got = ev("__tool.st.zone")
        h2 = ev("document.querySelector('#selected h2').textContent")
        if got != zid:   # a shelter icon may sit on top of the zone: nudge by a few pixels around the point
            for dx, dy in ((4, 0), (-4, 0), (0, 4), (0, -4), (6, 6), (-6, -6)):
                mouse_click(x + dx, y + dy)
                if ev("__tool.st.zone") == zid:
                    got = zid
                    break
        check(f"{sc}: real mouse click on zone {zid} selects it and draws a route", got == zid and ev("__tool.st.zone") == zid,
              f"top element at point: {top}; panel: {ev('document.querySelector(\"#selected h2\").textContent')}")
        zr = [a for a in r["assign"] if a[0] == zid]
        panel = ev("document.getElementById('selected').innerText")
        want_p = f"{int(pop[zid] + 0.5):,}"
        check(f"{sc}: zone panel shows residents ({want_p}) and {len(zr)} destinations", want_p in panel and panel.count("\n") > 5,
              f"unassigned in bundle: {r['unassigned'].get(str(zid), 0)}")
        shot(f"t_{sc}_zone")
        # shelter click
        used = sorted(r["shelter_load"], key=lambda k: -r["shelter_load"][k])
        ok = False
        for sidtxt in used[:8]:
            sid = int(sidtxt)
            x, y = map_point("shelter", sid, 14)
            mouse_click(x, y)
            if ev("__tool.st.shelter") == sid:
                ok = True
                break
        check(f"{sc}: real mouse click on shelter {sid} selects it", ok, ev("document.querySelector('#selected h2').textContent"))
        panel = ev("document.getElementById('selected').innerText")
        check(f"{sc}: shelter panel says candidate, not designated", "not an officially designated shelter" in panel)
        shot(f"t_{sc}_shelter")
    ev("__tool.map.fitBounds([[50.3,6.3],[50.78,7.45]]); 0")

    # ---------------------------------------------------------------- zero-resident zones
    select_option("selScenario", 0)
    zero = [z for z in bundle["zones"] if z["people"]["obs2021"] < 0.5 and z["people"]["rp500"] >= 0.5]
    zid = zero[0]["id"]
    ev("__tool.st.zone=null; __tool.update()")
    x, y = map_point("zone", zid, 14)
    mouse_click(x, y)
    check("obs2021: click on a zone with no residents selects nothing", ev("__tool.st.zone") is None, f"zone {zid}")
    ev(f"__tool.selectZone({zid})")
    check("selectZone() refuses a zone with no residents", ev("__tool.st.zone") is None)
    check("zero-resident zone is not in the zone list", ev(f"Array.from(document.getElementById('selZone').options).every(o=>o.value!=='{zid}')"))
    select_option("selScenario", 3)           # rp500: now it has residents
    x, y = map_point("zone", zid, 14)
    mouse_click(x, y)
    sel = ev("__tool.st.zone")
    check("rp500: the same zone is clickable (has residents)", sel == zid)
    select_option("selScenario", 0)           # back to obs2021: no residents -> selection dropped
    check("switching to a level where the zone has none clears the selection", ev("__tool.st.zone") is None)
    txt = ev("document.getElementById('selected').innerText")
    check("no 'No shelter place is planned' wording anywhere in the page", "No shelter place is planned" not in ev("document.body.innerText"))

    # ---------------------------------------------------------------- CSV via the real button
    select_option("selScenario", 2)   # rp100
    select_option("selClosure", 0)
    select_option("selCapacity", 1)   # generous
    key = "rp100|wet|generous"
    r = bundle["results"][key]
    pop = {z["id"]: z["people"]["rp100"] for z in bundle["zones"]}
    muni = {z["id"]: z["muni"] for z in bundle["zones"]}
    sh = {s["id"]: s for s in bundle["shelters"]}
    zid = max({a[0] for a in r["assign"]}, key=lambda z: pop[z])
    x, y = map_point("zone", zid, 14)
    mouse_click(x, y)
    for f in os.listdir(DL):
        os.remove(os.path.join(DL, f))
    mouse_click(*el_center("#btnCsv"))
    got_file = None
    for _ in range(40):
        fs = [f for f in os.listdir(DL) if f.endswith(".csv")]
        if fs:
            got_file = fs[0]
            break
        time.sleep(0.25)
    check("CSV button (real click) produced a file", got_file == "shelter_plan_rp100_wet_generous.csv", got_file)
    if got_file:
        raw = open(os.path.join(DL, got_file), "rb").read().decode("utf-8")
        lines = raw.split("\r\n")
        rows = [l.split(",") for l in lines[1:] if l]
        exp = []
        for z in sorted(pop):
            if pop[z] < 0.5:
                continue
            for a in [a for a in r["assign"] if a[0] == z]:
                exp.append((str(z), str(a[1]), str(int(a[2] + 0.5)) if a[2] >= 0.5 else ("<1" if a[2] > 0 else "0"), f"{a[3]/60:.1f}", f"{(a[3]-a[4])/60:.1f}"))
            un = r["unassigned"].get(str(z), 0)
            if un >= 0.5:
                exp.append((str(z), "", "0", "", ""))
        got = [(c[0], c[3], c[6], c[7], c[8]) for c in rows]
        # compare as multisets with 0.1 tolerance on minutes (JS and Python round half cases differently)
        def norm(t):
            return (t[0], t[1], t[2], round(float(t[3]), 1) if t[3] else None, round(float(t[4]), 1) if t[4] else None)
        a_, b_ = sorted(map(norm, exp), key=str), sorted(map(norm, got), key=str)
        print('differing rows:', [(p, q) for p, q in zip(a_, b_) if p != q][:4])
        diff = sum(1 for p, q in zip(a_, b_) if p != q and not (p[:3] == q[:3] and abs((p[3] or 0) - (q[3] or 0)) <= 0.11 and abs((p[4] or 0) - (q[4] or 0)) <= 0.11))
        check("CSV rows equal the bundle assignments (zone, shelter, people, minutes, detour)", len(a_) == len(b_) and diff == 0, f"{len(rows)} rows, {diff} differing")
        check("CSV has BOM, header, no decimal people", raw.startswith("\ufeffzone,municipality,people_to_place") and all("." not in c[2] and "." not in c[6] for c in rows))
        unas_csv = sum(int(c[9]) for c in rows if c[9].isdigit())
        unas_bundle = sum(int(v + 0.5) for v in r["unassigned"].values() if v >= 0.5)
        check("CSV unassigned column sums to the bundle's unassigned (rounded per zone)", unas_csv == unas_bundle, f"{unas_csv} vs {unas_bundle}")
        print("CSV head:", lines[:4])

    # ---------------------------------------------------------------- clipboard via the real button
    mouse_click(*el_center("button[data-copy=msgEN]"))
    time.sleep(0.5)
    stat = ev("document.getElementById('copyStat') ? document.getElementById('copyStat').textContent : null")
    clip = None
    try:
        clip = ev("navigator.clipboard.readText()", True)
    except Exception as e:
        clip = "ERR " + str(e)[:120]
    want = ev("document.getElementById('msgEN').textContent")
    check("copy English button (real click) reports success", stat == "Copied.", stat)
    check("clipboard content equals the English draft (Windows turns \n into \r\n)", (clip or "").replace("\r\n", "\n") == want, (clip or "")[:60])
    mouse_click(*el_center("button[data-copy=msgDE]"))
    time.sleep(0.4)
    try:
        clip = ev("navigator.clipboard.readText()", True)
    except Exception as e:
        clip = "ERR " + str(e)[:120]
    check("clipboard content equals the German draft", (clip or "").replace("\r\n", "\n") == ev("document.getElementById('msgDE').textContent") and "ENTWURF" in clip and "für" in clip)
    shot("t_message")

    # ---------------------------------------------------------------- stress layer toggle by real click, closed/routes, all-shelters toggle
    ev("window.scrollTo(0,0); __tool.st.zone=null; __tool.update(); __tool.map.fitBounds([[50.3,6.3],[50.78,7.45]]); 0")
    mouse_click(*el_center("input[data-layer=stress]"))
    check("stress layer toggle (real click) turns the layer on", ev("__tool.st.layers.stress") is True)
    mouse_click(*el_center("input[data-layer=allshelters]"))
    check("all-candidate-shelters toggle (real click)", ev("__tool.st.layers.allshelters") is True)
    ev("window.scrollTo(0,0)")
    time.sleep(0.8)
    shot("t_stress_all")

    page.drain(1.0)
    errs = []
    for e in page.events:
        if e.get("method") == "Runtime.exceptionThrown":
            errs.append(json.dumps(e["params"]["exceptionDetails"])[:300])
        if e.get("method") == "Runtime.consoleAPICalled" and e["params"]["type"] in ("error", "warning"):
            errs.append(e["params"]["type"] + ": " + " ".join(str(a.get("value", a.get("description", ""))) for a in e["params"]["args"])[:300])
    check("no console errors/warnings and no uncaught exceptions during the whole run", not errs, errs[:5])
finally:
    try:
        proc.terminate()
    except Exception:
        pass

bad = [r for r in results if not r[1]]
print(f"\n{len(results) - len(bad)} passed, {len(bad)} failed")
sys.exit(1 if bad else 0)
