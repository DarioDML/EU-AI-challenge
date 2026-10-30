"""Export the full-analysis map of one view as a high-resolution PNG (map element only, legend open).
usage: export_map.py OUT.png QUERY LAT LON ZOOM [scale]"""
import base64, json, subprocess, sys, time, urllib.request
import websocket

out, query, lat, lon, zoom = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
scale = float(sys.argv[6]) if len(sys.argv) > 6 else 3
PAGE = "file:///D:/FloodResearch/2026EUFloodChallange/tool/dist/shelter_tool.html"
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9879
prof = out + ".prof"
proc = subprocess.Popen([CH, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={prof}", "--disable-gpu", "--window-size=1800,1150", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(60):
    try:
        pages = [t for t in json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=2)) if t["type"] == "page"]; break
    except Exception:
        time.sleep(0.3)
ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], max_size=None, timeout=120); n = [0]


def send(m, **p):
    n[0] += 1; ws.send(json.dumps({"id": n[0], "method": m, "params": p}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == n[0]:
            return r.get("result", {})


def ev(e):
    return send("Runtime.evaluate", expression=e, returnByValue=True).get("result", {}).get("value")


try:
    send("Page.enable"); send("Runtime.enable")
    send("Emulation.setDeviceMetricsOverride", width=1800, height=1150, deviceScaleFactor=scale, mobile=False)
    send("Page.navigate", url=PAGE + query); time.sleep(9)
    ev(f"__tool.map.setView([{lat},{lon}], {zoom}, {{animate:false}}); 0"); time.sleep(3)
    if '--nolegend' not in sys.argv: ev("(()=>{const b=document.getElementById('legendbar'); if (b && b.hidden) document.getElementById('btnLegend').click(); return 0})()"); time.sleep(1.5)
    ev("(()=>{document.querySelectorAll('.leaflet-control-zoom').forEach(e=>e.style.display='none'); if (%s) { const lb=document.getElementById('legendbar'); if (lb) (lb.closest('.maplegend') || lb.parentElement).style.display='none'; } return 0})()" % ('true' if '--nolegend' in sys.argv else 'false'))
    if '--keep-edge' not in sys.argv:      # leave out the violet edge of the 2021 mapped area (EMS_COL) unless asked for
        ev("(()=>{__tool.map.eachLayer(l=>{ if (l.eachLayer) l.eachLayer(s=>{ if (s.options && String(s.options.color).toUpperCase()==='#5E3C99') l.removeLayer(s); }); }); return 0})()"); time.sleep(1)
    r = ev("(()=>{const r=document.getElementById('map').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]})()")
    data = send("Page.captureScreenshot", format="png", captureBeyondViewport=False, clip={"x": r[0], "y": r[1], "width": r[2], "height": r[3], "scale": 1})["data"]
    open(out, "wb").write(base64.b64decode(data))
    print("map css px", r, "scale", scale, "->", out)
finally:
    proc.kill()
