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
    print(("PASS " if ok else "FAIL ") + name + ((" | " + ascii(detail)) if detail != "" else ""))


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
        return ev(f"(()=>{{const e=document.querySelector({json.dumps(selector)}); if (window.__tool && __tool.revealEl) __tool.revealEl(e); e.scrollIntoView({{block:'center'}}); const r=e.getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2];}})()")

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
    pre = ev("__tool.st.zone")
    r0 = bundle["results"]["obs2021|any|restrictive"]
    pop0 = {z["id"]: z["people"]["obs2021"] for z in bundle["zones"]}
    muni0 = {z["id"]: z["muni"] for z in bundle["zones"]}
    want_pre = max({a[0] for a in r0["assign"] if muni0[a[0]] in ("Schleiden", "Kall")}, key=lambda z: pop0[z])
    check("largest working-case (Schleiden/Kall) zone with a route is preselected on load", pre == want_pre, f"{pre} vs {want_pre}")
    lgr = ev("(()=>{const r=document.querySelector('.maplegend').getBoundingClientRect(), m=document.getElementById('map').getBoundingClientRect(); return [r.left-m.left, m.right-r.right]})()")
    check("legend sits at the bottom right of the map (Eifel working case stays visible)", lgr[0] > lgr[1], lgr)
    boxes = ev("Array.from(document.querySelectorAll('.mlab span')).map(s=>{const r=s.getBoundingClientRect(); return [r.left,r.top,r.right,r.bottom]})")
    ov = sum(1 for i in range(len(boxes)) for j in range(i) if boxes[i][0] < boxes[j][2] and boxes[i][2] > boxes[j][0] and boxes[i][1] < boxes[j][3] and boxes[i][3] > boxes[j][1])
    check("municipality labels do not overlap each other", ov == 0, f"{ov} overlapping pairs of {len(boxes)} labels")
    check("first screen shows a drawn route (panel + selection)", any(w in ev("document.getElementById('selected').innerText") for w in ("The largest group", "All placed")))
    lg = ev("(()=>{const r=document.getElementById('legendbar').getBoundingClientRect(); const m=document.getElementById('map').getBoundingClientRect(); return [r.top,r.bottom,m.bottom,innerHeight]})()")
    check("legend overlay and the whole map end inside the first screen (no scrolling)", lg[1] <= lg[3] and lg[2] <= lg[3] + 1, lg)
    check("municipality labels are on the map at the default zoom", ev("document.querySelectorAll('.mlab').length") >= 5, ev("document.querySelectorAll('.mlab').length"))
    check("no shelter marker is a tab stop", ev("document.querySelectorAll('.leaflet-marker-icon[tabindex]').length") == 0)
    check("initial view fits zone_bounds (not the wider bounds)", ev("(()=>{const b=__tool.map.getBounds(); return [b.getWest(),b.getSouth(),b.getEast(),b.getNorth()]})()")[1] > bundle["meta"]["bounds"][1] + 0.05)
    check("wording: no 'must leave' anywhere", "must leave" not in ev("document.body.innerText") and "must leave" not in ev("document.documentElement.innerHTML"))
    check("MOCK badge hidden on real data", ev("getComputedStyle(document.getElementById('mockBadge')).display") == "none")
    vp = ev("[innerWidth, innerHeight, Math.round(document.getElementById('map').getBoundingClientRect().top), document.documentElement.scrollWidth]")
    visible = (min(vp[1], ev("document.getElementById('map').getBoundingClientRect().bottom")) - vp[2]) / vp[1]
    check("map is about 60% (>= 58%) of viewport height on first screen", visible >= 0.58, f"{visible*100:.0f}% (map top at {vp[2]} px of {vp[1]}); controls/summary bottoms: "
          + str(ev("['.controls','#summary','header.top','#banner'].map(s=>{const e=document.querySelector(s); return e? s+':'+Math.round(e.getBoundingClientRect().bottom):s})")))
    check("no horizontal scroll at 1440", vp[3] <= vp[0], vp)
    banner = ev("document.getElementById('bannerText').textContent")
    check("banner shows Germany only + area", "Germany only" in banner and bundle["meta"]["area"] in banner, banner[:140])
    mid = mouse_click(*el_center("#btnDisc"))
    disc = ev("(()=>{const d=document.getElementById('discBody'); return [d.hidden, d.innerText]})()")
    check("expandable disclaimer lists limits and not-modelled", (not disc[0]) and "Limits" in disc[1] and "Not modelled" in disc[1]
          and any(x in disc[1] for x in (f"{bundle['meta']['outside_hero_area']['rp100']:,}", f"{int(bundle['meta']['outside_hero_area']['rp100'] / 100 + 0.5) * 100:,}")) and "Provenance" in disc[1], f"{len(disc[1])} chars; dict repr gone: {'{' not in disc[1]}")
    shot("t_disc_open")
    mouse_click(*el_center("#btnDisc"))
    ev("window.scrollTo(0,0)")

    # ---------------------------------------------------------------- expected summaries from the bundle
    def fmtR(n):   # mirrors the page: residents rounded (tens below 1,000, hundreds above), JS Math.round = half up
        if n < 0.5:
            return "0"
        if n < 10:
            return "fewer than 10"
        r = int(n / 10 + 0.5) * 10 if n < 1000 else int(n / 100 + 0.5) * 100
        return f"about {r:,}"

    def cardR(n):   # the summary cards use the short form ('~25,600', '<10') so no value is cut at 1280 px (review F3)
        v = fmtR(n)
        return "<10" if v == "fewer than 10" else v.replace("about ", "~")

    def expect_cards(key):
        s = bundle["results"][key]["summary"]
        f = lambda v: f"{round(v):,}"
        return {"People to place (min.)": cardR(s["people_to_place"]), "Placed": cardR(s["placed"]), "UNASSIGNED": cardR(s["unassigned"]),
                "Mean time": f"{s['mean_time_min']:.1f} min", "Walk to open road": f"{s['mean_access_min']:.1f} min",
                "Road detour": f"{s['mean_detour_min']:.1f} min", "Shelter buildings used": f(s["shelters_used"]), "Closed roads": f(s["closed_edges"]),
                "Road segments over assumed capacity": f(s["stress_edges_over_1"])}

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
        want_p = fmtR(pop[zid]) + " (rounded)"
        check(f"{sc}: zone panel shows residents ({want_p}) and {len(zr)} destinations", want_p in panel and panel.count("\n") > 5,
              f"unassigned in bundle: {r['unassigned'].get(str(zid), 0)}")
        shot(f"t_{sc}_zone")
        # shelter click
        used = sorted(r["shelter_load"], key=lambda k: -r["shelter_load"][k])
        ok, tops = False, []
        for sidtxt in used[:8]:
            sid = int(sidtxt)
            x, y = map_point("shelter", sid, 14)
            tops.append(ev(f"(()=>{{const e=document.elementFromPoint({x},{y}); return e ? [e.tagName, String(e.parentElement && e.parentElement.className).slice(0,40), Math.round({y}), innerHeight] : null}})()"))
            mouse_click(x, y)
            if ev("__tool.st.shelter") == sid:
                ok = True
                break
        check(f"{sc}: real mouse click on shelter {sid} selects it", ok, [ev("document.querySelector('#selected h2').textContent"), tops[:2]])
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
    check("CSV button (real click) produced a file named with Set B (no raw id)", got_file == "shelter_plan_rp100_wet_SetB.csv", got_file)
    if got_file:
        import csv as _csv, io
        raw = open(os.path.join(DL, got_file), "rb").read().decode("utf-8")
        check("CSV: BOM, comment row with the disclaimer, then header", (raw.startswith("\ufeff# Planning scenario output") or raw.startswith("\ufeff\"# Planning scenario output")) and "not a live warning" in raw.split("\r\n")[0], raw.split("\r\n")[0][:80])
        rows = list(_csv.reader(io.StringIO(raw.lstrip("\ufeff"))))
        header, body = rows[2], [row for row in rows[3:] if row]
        check("CSV second comment row: people are modelled estimates, not a headcount", rows[1][0].startswith("# People columns are modelled estimates") and "not a headcount" in rows[1][0], rows[1][0][:80])
        want_head = ["scenario", "closure_rule", "capacity_set", "bundle_generated_utc", "zone", "municipality", "zone_total_estimate", "shelter_id", "shelter_lat", "shelter_lon",
                     "shelter_type", "shelter_municipality", "people_estimate", "minutes", "detour_minutes", "unassigned", "population_year"]
        check("CSV header has scenario, closure rule, capacity set, generated_utc, zone_total_estimate, people_estimate, shelter lat/lon", header == want_head, header)
        check("CSV context columns are filled (rp100, closure label, Set B, bundle date)", all(r_[0] == "rp100" and r_[2] == "Set B" and r_[3] == bundle["meta"]["generated_utc"] and r_[1] for r_ in body))
        exp = []
        for z in sorted(pop):
            if pop[z] < 0.5:
                continue
            for a in sorted([a for a in r["assign"] if a[0] == z], key=lambda a: -a[2]):
                sh = next(s_ for s_ in bundle["shelters"] if s_["id"] == a[1])
                exp.append((str(z), str(a[1]), str(int(a[2] + 0.5)) if a[2] >= 0.5 else ("<1" if a[2] > 0 else "0"), round(a[3] / 60, 1), round((a[3] - a[4]) / 60, 1), str(sh["lat"]), str(sh["lon"])))
            un = r["unassigned"].get(str(z), 0)
            if un >= 0.5:
                exp.append((str(z), "", "0", None, None, "", ""))
        got = [(c[4], c[7], c[12], float(c[13]) if c[13] else None, float(c[14]) if c[14] else None, c[8], c[9]) for c in body]
        a_, b_ = sorted(exp, key=str), sorted(got, key=str)
        def same(p_, q_):
            return p_[:3] == q_[:3] and p_[5:] == q_[5:] and all((u is None and v is None) or (u is not None and v is not None and abs(u - v) <= 0.11) for u, v in ((p_[3], q_[3]), (p_[4], q_[4])))
        diff = [(p_, q_) for p_, q_ in zip(a_, b_) if not same(p_, q_)]
        print("differing rows:", ascii(diff[:3]))
        check("CSV rows equal the bundle assignments (zone, shelter, people, minutes, detour, shelter lat/lon)", len(a_) == len(b_) and not diff, f"{len(body)} rows, {len(diff)} differing")
        check("CSV has no decimal people", all("." not in c[6] and "." not in c[12] for c in body))
        unas_csv = sum(int(c[15]) for c in body if c[15].isdigit())
        unas_bundle = sum(int(v + 0.5) for v in r["unassigned"].values() if v >= 0.5)
        check("CSV unassigned column sums to the bundle's unassigned (rounded per zone)", unas_csv == unas_bundle, f"{unas_csv} vs {unas_bundle}")
        print("CSV head:", ascii(raw.split("\r\n")[:4]))

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

    # ---------------------------------------------------------------- round 4 additions
    pop_a = bundle["assumptions"]["population"]
    ev("window.scrollTo(0,0)")
    mouse_click(*el_center("#summary [data-how]"))
    dd = ev("(()=>{const d=document.getElementById('discBody'); return [d.hidden, d.innerText]})()")
    check("'How counted?' link on the People card (real click) opens 'How residents are counted'", (not dd[0]) and "How residents are counted" in dd[1])
    check("counting section renders the bundle's numbers (dropped / window residents / share)", f"{fmtR(pop_a['dropped_no_usable_building'])} of {fmtR(pop_a['window_residents'])} residents ({pop_a['dropped_share']*100:.1f} %)" in dd[1] and "minimums" in dd[1], dd[1][dd[1].find("How residents"):][:200])
    check("counting section has the fifth line 'Reference year and error' from assumptions.population", "Reference year and error" in dd[1] and f"Residents of {pop_a['reference_year']}" in dd[1] and pop_a["error"] in dd[1])
    check("counting section has the four steps from assumptions.population", all(pop_a[k] in dd[1] for k in ("source", "allocation", "flood_test", "aggregation")))
    mouse_click(*el_center("#btnDisc"))
    select_option("selScenario", 0)
    ev(f"__tool.selectZone({want_pre}, false)")
    check("zone tooltip/panel wording: residents inside the flood in this 500 m cell (modelled grid of about 930 x 600 m cells, shared over buildings)", "in this 500 m cell (from a modelled grid of about 930 x 600 m cells, shared over buildings)" in ev("document.getElementById('selected').innerText"))
    # closure rule "mapped": shelters flooded per obs2021_mapped, flood layer without traces
    select_option("selScenario", 0)
    select_option("selClosure", 1)
    select_option("selCapacity", 0)
    n_page = ev("__tool.S.size && Array.from(__tool.S.values()).filter(s=>__tool.isFlooded(s)).length")
    n_bundle = sum(1 for s_ in bundle["shelters"] if s_["flooded"]["obs2021_mapped"])
    check("closure=mapped: flooded shelters follow flooded.obs2021_mapped", n_page == n_bundle, f"{n_page} vs {n_bundle}")
    legend = ev("document.getElementById('legendbar').innerText")
    check("closure=mapped: legend says 'mapped flood only (traces ignored)'", "mapped flood only (traces ignored)" in legend)
    nf = ev("(()=>{let n=0; __tool.map.eachLayer(l=>{ if (l.feature && l.feature.properties && l.feature.properties.kind) n++; }); return n})()")      # the 2021 coverage outline has no kind
    check("closure=mapped: flood layer holds only the mapped-flood feature(s)", nf == sum(1 for f in bundle["floods"]["obs2021"]["features"] if f["properties"].get("kind") == "mapped flood"), nf)
    select_option("selClosure", 0)
    n_page = ev("Array.from(__tool.S.values()).filter(s=>__tool.isFlooded(s)).length")
    check("closure=any: flooded shelters follow flooded.obs2021", n_page == sum(1 for s_ in bundle["shelters"] if s_["flooded"]["obs2021"]), n_page)
    check("closure=any: legend says 'flood and flood-trace extent'", "flood and flood-trace extent" in ev("document.getElementById('legendbar').innerText"))

    # zone panel: top 3 by default, 'show all' by real click
    ev("window.scrollTo(0,0)")
    r = bundle["results"]["obs2021|any|restrictive"]
    pop = {z["id"]: z["people"]["obs2021"] for z in bundle["zones"]}
    many = [z for z in {a[0] for a in r["assign"]} if len([a for a in r["assign"] if a[0] == z]) > 5 and pop[z] > 100]
    zid = many[0]
    x, y = map_point("zone", zid, 13)
    mouse_click(x, y)
    if ev("__tool.st.zone") != zid:
        ev(f"__tool.selectZone({zid}, false)")
    n_all = len([a for a in r["assign"] if a[0] == zid])
    rows_default = ev("document.querySelectorAll('#selected table tbody tr').length")
    check("zone panel lists the top 3 destinations by default", rows_default == 3, rows_default)
    check("zone panel summary line: most people (N, X %) to ..., Z more destinations", f"{n_all - 1} more destination" in ev("document.getElementById('selected').innerText") and "The largest group (" in ev("document.getElementById('selected').innerText"))
    check("zone panel says the allocation is a capacity-driven fill", "capacity-driven fill" in ev("document.getElementById('selected').innerText"))
    mouse_click(*el_center("#btnAll"))
    check(f"'Show all {n_all} destinations' (real click) lists all", ev("document.querySelectorAll('#selected table tbody tr').length") == n_all, ev("document.querySelectorAll('#selected table tbody tr').length"))

    # texts from the new fields
    ev("window.scrollTo(0,0)")
    txt = ev("document.getElementById('summary').innerText")
    sm = bundle["results"]["obs2021|any|restrictive"]["summary"]
    check("summary shows 'over 30 min: N people' and 'N of M at capacity'", f"over 30 min: {fmtR(sm['people_over_30min'])} people" in txt and "rounded est., 2020" in txt and ev("(()=>{const s=document.querySelector('#summary span[title^=rounded],#summary span[data-tip^=rounded]'); return s.title||s.dataset.tip})()") == "rounded; modelled estimate, 2020 population, error not quantified" and f"{sm['shelters_at_capacity']:,} of {sm['shelters_used']:,} at capacity" in txt)
    check("unassigned sub-line uses free_places_total", f"{round(sm['free_places_total']):,} places free further away" in txt)
    check("stress card: title, worst class and the short-link note", "Road segments over assumed capacity" in txt and "short link segments" in txt.lower() or "Short link segments" in txt)
    cap_txt = ev("document.getElementById('capTotal').textContent")
    check("capacity selector shows total assumed places (Set A)", f"{bundle['meta']['total_places']['restrictive']:,}" in cap_txt, cap_txt)
    select_option("selCapacity", 1)
    cap_txt = ev("document.getElementById('capTotal').textContent")
    check("Set B shows its total and 'optimistic supply'", f"{bundle['meta']['total_places']['generous']:,}" in cap_txt and "optimistic" in cap_txt, cap_txt)
    select_option("selCapacity", 0)
    body_txt = ev("document.body.innerText")
    check("no raw capacity ids in visible text", "restrictive" not in body_txt and "generous" not in body_txt)
    comp = ev("document.getElementById('compare').innerText")
    check("compare panel: observed vs modelled not comparable, with computed municipality examples", "not comparable" in comp and "observed" in comp and "vs" in comp, comp[-200:])
    check("compare table is wrapped for horizontal scrolling", ev("getComputedStyle(document.getElementById('compare')).overflowX") == "auto")
    prop = ev("document.getElementById('proposal').innerText")
    check("Proposal (draft) box with next step, no costs", "Proposal (draft)" in prop and "check on the ground" in prop and "Costs, legal powers" in prop, prop[:120])
    check("purpose line is short; the disclaimer names Anna and local authorities", len(ev("document.getElementById('purpose').textContent").split()) <= 10 and "Anna (cross-border crisis coordinator per the challenge brief) and local authorities (to be confirmed)" in ev("document.getElementById('discBody').textContent"))
    banner = ev("document.getElementById('bannerText').textContent")
    check("banner has the area/scope line (Ahr comparison case, Eifel working case, Meuse/Vesdre not covered)", "Ahr valley = comparison case" in banner and "Meuse/Vesdre" in banner)
    check("layers panel groups population and shelter buildings under two headings", ev("Array.from(document.querySelectorAll('#layers h3.grp')).map(h=>h.textContent).join('|')").startswith("Residents inside the flood (population)|Shelter buildings"))
    # dropped selection note
    select_option("selScenario", 3)
    z5 = [z for z in bundle["zones"] if z["people"]["obs2021"] < 0.5 and z["people"]["rp500"] >= 5][0]["id"]
    ev(f"__tool.selectZone({z5}, false)")
    select_option("selScenario", 0)
    note = ev("(()=>{const n=document.getElementById('selNote'); return [n.hidden, n.innerText]})()")
    check("dropped selection shows a visible note", (not note[0]) and "deselected" in note[1], note)
    # population year selector (2020 default, 2025 projection): real key presses, cards from the |pop2025 result, zone people from people_pop2025
    pops = [p_["id"] for p_ in bundle.get("populations", [])]
    if len(pops) > 1:
        select_option("selScenario", 0); select_option("selClosure", 0); select_option("selCapacity", 0)
        check("population year defaults to 2020", ev("__tool.st.pop") == "pop2020")
        select_option("selPop", 1)
        k25 = "obs2021|any|restrictive|pop2025"
        got, exp = read_cards(), expect_cards(k25)
        bad = {k: (got.get(k), v) for k, v in exp.items() if got.get(k) != v}
        check("2025 projection: keyboard select reaches the state, cards equal the |pop2025 summary", ev("__tool.st.pop") == "pop2025" and not bad, bad or "")
        shown = ev("Array.from(document.getElementById('selZone').options).length - 1")
        want = sum(1 for z in bundle["zones"] if z["people_pop2025"]["obs2021"] >= 0.5)
        check("2025 projection: zone list follows people_pop2025", shown == want, f"{shown} vs {want}")
        check("2025 projection is labelled as a projection next to the selector and on the People card", "projection" in ev("document.getElementById('popNote').textContent") and "2025 proj." in ev("document.getElementById('summary').innerText"))
        pc = ev("document.getElementById('compare').innerText")
        s20, s25 = bundle["results"]["obs2021|any|restrictive"]["summary"], bundle["results"][k25]["summary"]
        pct = 100 * (s25["people_to_place"] - s20["people_to_place"]) / s20["people_to_place"]
        check("population comparison table shows both years and the % change", "Population year: how much" in pc and f"{pct:+.1f} %".replace("+-", "-") in pc, [pct, pc[pc.find("Population year"):][:200]])
        select_option("selPop", 0)
        check("back to 2020 restores the default cards", read_cards() == expect_cards("obs2021|any|restrictive"))
    # ---------------------------------------------------------------- profiles (POLICY_TOOL_PLAN.md section 0)
    if bundle.get("munis") and bundle.get("streets"):
        ev("window.scrollTo(0,0)")
        # full state survives a round trip through the other profiles
        select_option("selScenario", 2); select_option("selCapacity", 1)
        before = ev("[__tool.st.sc,__tool.st.cl,__tool.st.cap,__tool.st.pop].join('|')")
        # municipality: real click on the tab, real click on Kall on the map, Add, results equal the bundle sum, Remove empties the list
        mouse_click(*el_center(".profiles [data-profile=municipality]"))
        check("municipality tab (real click) switches the profile and hides the model selectors and cards",
              ev("__tool.pst.profile") == "municipality" and ev("getComputedStyle(document.getElementById('summary')).display") == "none" and ev("getComputedStyle(document.getElementById('selClosure')).display") == "none" or ev("document.getElementById('selClosure').offsetParent") is None)
        kall_lau = next(z["lau"] for z in bundle["zones"] if z["muni"] == "Kall")
        x, y = map_point("zone", 55, 12)
        mouse_click(x, y)
        check("click on the map picks the municipality under the pointer (Kall)", ev("__tool.pst.muniPick") == kall_lau and "Picked: Kall" in ev("document.getElementById('muniPick').innerText"), ev("document.getElementById('muniPick').innerText"))
        mouse_click(*el_center("#btnMuniAdd"))
        kall_p = sum(z["people"]["obs2021"] for z in bundle["zones"] if z["lau"] == kall_lau)
        mr = ev("document.getElementById('muniResult').innerText")
        rnd = lambda n: "0" if n < 0.5 else ("fewer than 10" if n < 10 else f"about {(int(n / 10 + 0.5) * 10 if n < 1000 else int(n / 100 + 0.5) * 100):,}")
        check("Add puts Kall in the list; results = sum of its zones (rounded)", ev("__tool.pst.muniList.length") == 1 and rnd(kall_p) + " residents live inside the flood" in mr, [kall_p, mr[:160]])
        check("municipality results use plain words (no model terms like LP, k, Set A)", all(w not in mr for w in ("LP", "Set A", "k=", "HiGHS", "restrictive")))
        shot("t_profile_municipality")
        mouse_click(*el_center("#muniList [data-rm]"))
        check("Remove empties the list", ev("__tool.pst.muniList.length") == 0 and "Your list is empty" in ev("document.getElementById('muniResult').innerText"))
        # citizen v2: real click on the tab; areas of the citizen plan (one building and one route per area)
        mouse_click(*el_center(".profiles [data-profile=citizen]"))
        check("citizen tab (real click): floating card only, no analysis panels", ev("__tool.pst.profile") == "citizen" and ev("document.getElementById('citCard').offsetParent") is not None and ev("document.getElementById('selected').offsetParent") is None and ev("document.querySelector('.controls').offsetParent") is None)
        cp = bundle["citizen_plan"]
        # since B27 a split cell uses at most 3 buildings, so this simpler plan may leave people without a named building (reason 'plan_rule'); the main plan still places all
        check("citizen plan in the bundle: placed + unassigned = people, at most 3 buildings per area, every unassigned person has a reason, areas present",
              abs(cp["summary"]["placed"] + cp["summary"]["unassigned"] - cp["summary"]["people"]) <= 1 and len(cp["areas"]) > 100 and max(len(a["dest"]) for a in cp["areas"]) <= 3
              and all(a["unassigned_reason"] for a in cp["areas"] if a["unassigned"] >= 0.5), cp["summary"])
        for q_ in ("Hauptstr.", "koelner", "aachener str kall"):
            ev("(()=>{const i=document.getElementById('citSearch'); i.value=''; i.dispatchEvent(new Event('input'))})()")
            ev("document.getElementById('citSearch').focus()"); page.send("Input.insertText", text=q_); time.sleep(0.3)
            n_ = ev("document.querySelectorAll('#citHits button').length")
            check(f"street search finds results for the spelling '{q_}'", n_ > 0, n_)
        check("street search finds 'Aachener Straße, Kall'", any(h.startswith("Aachener Stra") and h.endswith(", Kall") for h in ev("Array.from(document.querySelectorAll('#citHits button')).map(b=>b.textContent)")))
        mouse_click(*el_center("#citHits button"))
        cr = ev("document.getElementById('citResult').innerText")
        check("picking a street selects its area or lists the areas it crosses", "Flooded in July 2021" in cr or "crosses" in cr or "not inside the 2021 flood" in cr, cr[:120])
        # a single-building area in Kall: hover shows its building, a real click shows building 1, its time and the backup
        a1 = max([a for a in cp["areas"] if a["muni"] == "Kall" and len(a["dest"]) == 1 and a.get("backup")], key=lambda a: a["people"])
        pt = ev(f"(()=>{{const a=__tool.CP.areas.find(x=>x.id==={a1['id']}); const g=a.geometry; const ring=(g.type==='Polygon'?g.coordinates:g.coordinates[0])[0];"
                f"for (let i=0;i<ring.length;i++) for (let j=i+1;j<ring.length;j++) {{ const la=(ring[i][1]+ring[j][1])/2, lo=(ring[i][0]+ring[j][0])/2; const ok=[[0,0],[0.0006,0],[-0.0006,0],[0,0.0009],[0,-0.0009]].every(d=>{{const f=__tool.areaAt(la+d[0],lo+d[1]); return f && f.id===a.id;}}); if (ok) return [la,lo]; }} return null}})()")
        ev(f"__tool.map.setView([{pt[0]}, {pt[1]}], 15, {{animate:false}}); 0")
        xy = ev(f"(()=>{{const p=__tool.map.latLngToContainerPoint([{pt[0]},{pt[1]}]), r=document.getElementById('map').getBoundingClientRect(); return [r.left+p.x, r.top+p.y]}})()")
        page.send("Input.dispatchMouseEvent", type="mouseMoved", x=xy[0] + 2, y=xy[1] + 2, button="none"); page.send("Input.dispatchMouseEvent", type="mouseMoved", x=xy[0], y=xy[1], button="none"); time.sleep(0.3)
        tt = ev("Array.from(document.querySelectorAll('.leaflet-tooltip')).map(t=>t.textContent).join(' ')")
        sh1 = next(s_ for s_ in bundle["shelters"] if s_["id"] == a1["dest"][0]["s"])
        check("hover on an area shows its building (tooltip)", tt.startswith("Area in Kall") and sh1["muni"] in tt, tt[:100])
        tipv = ev("(()=>{const t=document.getElementById('tip'); return t && !t.hidden ? [t.textContent, getComputedStyle(t).zIndex] : null})()")
        check("map tooltip text is shown in the top-most help box (above the floating card)", tipv is not None and tipv[0].startswith("Area in Kall") and int(tipv[1]) > 1000, tipv)
        mouse_click(*xy)
        cr = ev("document.getElementById('citResult').innerText")
        mins = max(1, round((a1["dest"][0]["road_s"] + a1["walk_s"][1]) / 60))
        check("click on an area: ONE building (building 1) with its time, the steps and a backup", ev("__tool.pst.area") == a1["id"] and sh1["muni"] in cr and f"about {mins} min" in cr and "Backup 1:" in cr and "Drive along" in cr, [a1["id"], sh1["type"], sh1["muni"], mins, cr[:260]])
        check("citizen answer says candidate building, not designated", "not officially designated" in cr)
        time.sleep(1.3)   # let the glide to the route finish
        shot("t_profile_citizen")
        # an area too large for one building says so
        a2 = next((a for a in cp["areas"] if len(a["dest"]) > 1), None)
        if a2:
            ev(f"__tool.selectArea({a2['id']}, true)")
            cr2 = ev("document.getElementById('citResult').innerText")
            big = max(a2["dest"], key=lambda d: d.get("people", 0)); shn = next(s_ for s_ in bundle["shelters"] if s_["id"] == big["s"])
            check("a shared area: building 1 = the one taking most people, route steps, then Building 2; no 'reserved'", "shared over" in cr2 and "Drive along" in cr2 and "Building 2:" in cr2 and "reserved" not in cr2 and shn["muni"] in cr2.split("Building 2:")[0], [shn["type"], shn["muni"], cr2[:200]])
        # a click on a blank spot while an area is selected clears it and goes back to the earlier view
        time.sleep(1.0); ev(f"__tool.map.stop(); __tool.clearCitizen(); __tool.map.setView([50.55, 6.6], 9, {{animate:false}}); 0"); time.sleep(0.5)
        z0 = ev("__tool.map.getZoom()")
        ev(f"__tool.selectArea({a1['id']}, 'instant', null); 0"); time.sleep(0.3)
        z1 = ev("__tool.map.getZoom()")
        blank = ev("(()=>{const r=document.getElementById('map').getBoundingClientRect(); for (let x=r.right-60; x>r.left+460; x-=37) for (let y=r.top+60; y<r.bottom-60; y+=37) { const ll=__tool.map.containerPointToLatLng([x-r.left, y-r.top]); if (!__tool.areaAt(ll.lat, ll.lng)) return [x, y]; } return null})()")
        mouse_click(*blank); time.sleep(1.2)
        check("selecting an area zooms in to its route; a blank click clears it and zooms to the area itself", z1 > z0 and ev("__tool.pst.area") is None and ev("__tool.map.getZoom()") >= z1, [z0, z1, ev("__tool.map.getZoom()")])
        # two selections, then a blank click: no route, and a close view of the LAST selected area (the area is in view, zoomed in)
        ev("__tool.map.stop(); __tool.clearCitizen(); 0"); time.sleep(0.3)
        a_ids = [a["id"] for a in sorted(cp["areas"], key=lambda a: -a["people"]) if len(a["dest"]) == 1][:2]
        ev(f"__tool.selectArea({a_ids[0]}, 'instant'); 0"); time.sleep(0.4)
        ev(f"__tool.selectArea({a_ids[1]}, 'instant'); 0"); time.sleep(0.4)
        zr = ev("__tool.map.getZoom()")
        blank = ev("(()=>{const r=document.getElementById('map').getBoundingClientRect(); for (let x=r.right-60; x>r.left+530; x-=37) for (let y=r.top+60; y<r.bottom-60; y+=37) { const ll=__tool.map.containerPointToLatLng([x-r.left, y-r.top]); if (!__tool.areaAt(ll.lat, ll.lng)) return [x, y]; } return null})()")
        mouse_click(*blank); time.sleep(1.0)
        inview = ev(f"(()=>{{const a=__tool.CP.areas.find(x=>x.id==={a_ids[1]}); return __tool.map.getBounds().contains(L.geoJSON(a.geometry).getBounds())}})()")
        check("blank click: route closed, nothing selected, close view of the area that was selected", ev("__tool.pst.area") is None and inview and ev("__tool.map.getZoom()") > zr, [zr, ev("__tool.map.getZoom()"), inview])
        check("no focus outline on the citizen answer", ev("getComputedStyle(document.getElementById('citResult')).outlineStyle") in ("none", ""))
        check("citizen card has no red alert boxes", ev("document.querySelectorAll('#citCard .alert').length") == 0)
        ev("__tool.clearCitizen(); 0")
        # taps outside every area: inside the flood (no residents) and outside the flood; never 'safe'
        wetpt = ev("(()=>{for (let la=50.535; la<50.56; la+=0.0004) for (let lo=6.53; lo<6.57; lo+=0.0004) { if (__tool.inFlood2021(la,lo) && !__tool.areaAt(la,lo)) return [la,lo]; } return null})()")
        for ptx, want in ((wetpt, "inside the area flooded in July 2021"), (ev("(()=>{for (let la=50.70; la>50.35; la-=0.01) { if (!__tool.areaAt(la, 6.90) && !__tool.inFlood2021(la, 6.90)) return [la, 6.90]; } return null})()"), "not inside the 2021 flood in our data")):
            if not ptx:
                continue
            ev(f"__tool.map.setView([{ptx[0]}, {ptx[1]}], 16, {{animate:false}}); 0")
            mx_ = ev(f"(()=>{{const p=__tool.map.latLngToContainerPoint([{ptx[0]},{ptx[1]}]), r=document.getElementById('map').getBoundingClientRect(); return [r.left+p.x, r.top+p.y]}})()")
            ev("__tool.clearCitizen(); 0")
            mouse_click(*mx_)
            cr = ev("document.getElementById('citResult').innerText")
            check(f"click outside every area: '{want}'", want in cr and ("does not mean there is no risk" in cr or "no plan was computed" in cr), cr[:120])
        check("the word 'safe' appears nowhere in the visible citizen page", "safe" not in ev("document.body.innerText").lower(), [w for w in ev("document.body.innerText").lower().split() if "safe" in w][:5])
        mouse_click(*el_center(".profiles [data-profile=full]"))
        check("back to Full analysis restores the analyst's flood level, closure rule, capacity set and population year", ev("[__tool.st.sc,__tool.st.cl,__tool.st.cap,__tool.st.pop].join('|')") == before, [before, ev("[__tool.st.sc,__tool.st.cl,__tool.st.cap,__tool.st.pop].join('|')")])
        check("layer checkboxes match the layer state after the round trip", ev("Array.from(document.querySelectorAll('#layers input[data-layer]')).every(i=>i.checked===!!__tool.st.layers[i.dataset.layer])"))
        check("back to Full analysis restores the cards and the selectors", ev("__tool.pst.profile") == "full" and ev("document.getElementById('summary').offsetParent") is not None and ev("document.getElementById('selClosure').offsetParent") is not None)
        select_option("selScenario", 0); select_option("selClosure", 0); select_option("selCapacity", 0)
    # full analysis: panel on the left, resizable by a real drag of the bar
    ev("window.scrollTo(0,0)")
    sl = ev("[document.getElementById('side').getBoundingClientRect().left, document.getElementById('map').getBoundingClientRect().left]")
    check("full analysis: the panel is on the left of the map", sl[0] < sl[1], sl)
    rz = ev("(()=>{const r=document.querySelector('.resizer').getBoundingClientRect(); return [r.left+r.width/2, r.top+80]})()")
    w0 = ev("document.getElementById('side').getBoundingClientRect().width")
    page.send("Input.dispatchMouseEvent", type="mouseMoved", x=rz[0], y=rz[1], button="none")
    page.send("Input.dispatchMouseEvent", type="mousePressed", x=rz[0], y=rz[1], button="left", clickCount=1)
    for k in range(1, 6):
        page.send("Input.dispatchMouseEvent", type="mouseMoved", x=rz[0] + 20 * k, y=rz[1], button="left")
    page.send("Input.dispatchMouseEvent", type="mouseReleased", x=rz[0] + 100, y=rz[1], button="left", clickCount=1)
    time.sleep(0.3)
    w1 = ev("document.getElementById('side').getBoundingClientRect().width")
    check("dragging the bar 100 px to the right widens the panel by about 100 px", 85 <= w1 - w0 <= 115, [w0, w1])
    ev("window.__setW(500); 0")
    # the disclaimer opened by "how?" closes with its close button and with a click outside
    ev("window.scrollTo(0,0)")
    mouse_click(*el_center("#summary [data-how]"))
    op = ev("!document.getElementById('discBody').hidden")
    mouse_click(*el_center("#discBody .discClose"))
    c1 = ev("document.getElementById('discBody').hidden")
    mouse_click(*el_center("#summary [data-how]"))
    mouse_click(*ev("(()=>{const r=document.getElementById('map').getBoundingClientRect(); return [r.left+r.width/2, r.bottom-40]})()"))
    c2 = ev("document.getElementById('discBody').hidden")
    check("disclaimer opened by 'how?' closes by its close button and by a click outside", op and c1 and c2, [op, c1, c2])
    # hover help on a select sits ABOVE it (its list opens below)
    ev("window.scrollTo(0,0)")
    sr = ev("(()=>{const r=document.getElementById('selScenario').getBoundingClientRect(); return [r.left+20, r.top+r.height/2, r.top]})()")
    page.send("Input.dispatchMouseEvent", type="mouseMoved", x=sr[0] + 2, y=sr[1] + 2, button="none"); page.send("Input.dispatchMouseEvent", type="mouseMoved", x=sr[0], y=sr[1], button="none"); time.sleep(0.3)
    tb = ev("(()=>{const t=document.getElementById('tip'); return t && !t.hidden ? t.getBoundingClientRect().bottom : null})()")
    check("hover help of the flood-level selector appears above the selector", tb is not None and tb <= sr[2], [tb, sr[2]])
    page.send("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5, button="none")
    # hover help (real mouse moves): instant help box for cards and legend; resident ring tooltip not hidden by a flooded shelter
    def hover(x, y):
        page.send("Input.dispatchMouseEvent", type="mouseMoved", x=x + 2, y=y + 2, button="none")
        page.send("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y, button="none")
        time.sleep(0.3)
    def tipbox():
        return ev("(()=>{const t=document.getElementById('tip'); return t && !t.hidden ? t.textContent : null})()")
    select_option("selScenario", 0)
    ev("window.scrollTo(0,0)")
    hover(*ev("(()=>{const r=document.querySelector('#summary .card').getBoundingClientRect(); return [r.left+20,r.top+12]})()"))
    check("hover on the People card shows the help box at once", (tipbox() or "").startswith("Residents inside the flood at the selected level"), tipbox())
    hover(*ev("(()=>{const r=document.querySelector('#legendbar span.i').getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]})()"))
    check("hover on a legend entry shows its help", "town chip" in (tipbox() or "").lower() or "chip" in (tipbox() or ""), tipbox())
    hover(5, 5)
    check("help box hides when the pointer leaves", tipbox() is None)
    ev("__tool.st.zone=null; __tool.update()")
    hz = []
    x, y = map_point("zone", 55, 13)   # zone 55 (Kall) has flooded shelter badges near its centre; a used shelter on top would still win, by design
    hover(x, y)
    hz = ev("Array.from(document.querySelectorAll('.leaflet-tooltip')).map(t=>t.textContent).join(' ')")[:40]
    check("zoom 13: hover on a 500 m resident cell shows the residents tooltip, not a flooded shelter", hz.startswith("Zone "), hz)
    # zoom 11: residents are town chips (no cells); a chip shows the town total and zooms in on click
    ev("__tool.map.setView([50.45, 6.75], 11, {animate:false}); 0")   # Kall and Schleiden in the upper left, clear of the legend (bottom right)
    time.sleep(0.4)
    check("zoom 11: no 500 m cells drawn, town chips shown", ev("__tool.zoneLayerCount()") == 0 and ev("document.querySelectorAll('.mchip').length") >= 2, [ev("__tool.zoneLayerCount()"), ev("document.querySelectorAll('.mchip').length")])
    kall = ev("(()=>{const s=Array.from(document.querySelectorAll('.mchip span')).find(e=>e.textContent.startsWith('Kall ')); if(!s) return null; const r=s.getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2, s.textContent]})()")
    kall_p = sum(z["people"]["obs2021"] for z in bundle["zones"] if z["muni"] == "Kall" and z["people"]["obs2021"] >= 0.5)
    check("Kall chip shows the rounded sum of its cells", kall is not None and kall[2] == "Kall ~" + f"{(int(kall_p / 10 + 0.5) * 10 if kall_p < 1000 else int(kall_p / 100 + 0.5) * 100):,}", [kall, kall_p])
    if kall:
        hover(kall[0], kall[1])
        tt = ev("Array.from(document.querySelectorAll('.leaflet-tooltip')).map(t=>t.textContent).join(' ')")
        check("hover on the Kall chip explains it (residents inside the flood, not a shelter)", tt.startswith("Kall:") and "Not a shelter" in tt, tt[:80])
        mouse_click(kall[0], kall[1])
        time.sleep(0.6)
        check("click on a town chip zooms in to its cells (zoom >= 12, cells drawn)", ev("__tool.map.getZoom()") >= 12 and ev("__tool.zoneLayerCount()") > 0, ev("__tool.map.getZoom()"))
    check("no shelter marker has a native title (no double tooltip)", ev("document.querySelectorAll('.leaflet-marker-pane [title]').length") == 0)
    check("page and map background are white", ev("[getComputedStyle(document.body).backgroundColor, getComputedStyle(document.getElementById('map')).backgroundColor].join('|')") == "rgb(255, 255, 255)|rgb(255, 255, 255)",
          ev("[getComputedStyle(document.body).backgroundColor, getComputedStyle(document.getElementById('map')).backgroundColor].join('|')"))
    # keyboard: first Tab stop is the skip link
    # invalid URL parameters: visible note
    page.send("Page.navigate", url=URL + "?scenario=bogus&zone=999999")
    for _ in range(100):
        if ev("document.readyState") == "complete" and ev("!!window.__tool"):
            break
        time.sleep(0.2)
    time.sleep(1.0)
    note = ev("(()=>{const n=document.getElementById('selNote'); return [n.hidden, n.innerText]})()")
    check("invalid URL parameters produce a visible note instead of being ignored silently", (not note[0]) and "Ignored in the link" in note[1], note)
    shot("t_invalid_params")
    press_key("Tab", "Tab", 9)
    check("first Tab stop on a fresh page is the skip link to the list picker", ev("document.activeElement.id") == "skipLink", ev("document.activeElement.id"))
    shot("t_skiplink")

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
