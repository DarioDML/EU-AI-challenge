"""Export one map view of the built page as a vector SVG: every canvas-drawn line and area in its exact drawing order, plus the
shelter circles and place labels. Layers drawn in a colour listed in --skip-color are left out (default: the violet 2021 mapped-area edge).
usage: export_svg.py OUT.svg QUERY LAT LON ZOOM"""
import json, subprocess, sys, time, urllib.request
import websocket

out, query, lat, lon, zoom = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
SKIP = ["#5E3C99"]
PAGE = "file:///D:/FloodResearch/2026EUFloodChallange/tool/dist/shelter_tool.html"
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9880
proc = subprocess.Popen([CH, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={out}.prof", "--disable-gpu", "--window-size=1800,1150", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(60):
    try:
        pages = [t for t in json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=2)) if t["type"] == "page"]; break
    except Exception:
        time.sleep(0.3)
ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], max_size=None, timeout=180); n = [0]


def send(m, **p):
    n[0] += 1; ws.send(json.dumps({"id": n[0], "method": m, "params": p}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == n[0]:
            return r.get("result", {})


def ev(e):
    r = send("Runtime.evaluate", expression=e, returnByValue=True)
    if "exceptionDetails" in r:
        raise RuntimeError(json.dumps(r["exceptionDetails"])[:600])
    return r.get("result", {}).get("value")


JS = r"""
(() => {
  const SKIP = %s;
  const map = __tool.map, size = map.getSize(), W = size.x, H = size.y;
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const f = v => Math.round(v * 10) / 10;
  // every canvas renderer, bottom pane first
  const rs = new Set(); map.eachLayer(l => { if (l._renderer && l._renderer._drawFirst !== undefined) rs.add(l._renderer); });
  const z = r => Number((r.options.pane && map.getPane(r.options.pane).style.zIndex) || 400);
  const out = [];
  Array.from(rs).sort((a, b) => z(a) - z(b)).forEach(r => {
    for (let o = r._drawFirst; o; o = o.next) {
      const l = o.layer, op = l.options || {};
      if (SKIP.indexOf(String(op.color).toUpperCase()) >= 0) continue;
      if (l._radius != null && l._point) {       // circle markers
        const p = map.layerPointToContainerPoint(l._point);
        out.push('<circle cx="' + f(p.x) + '" cy="' + f(p.y) + '" r="' + f(l._radius) + '" fill="' + (op.fill ? (op.fillColor || op.color) : 'none') + '" fill-opacity="' + (op.fillOpacity == null ? 0.2 : op.fillOpacity) + '" stroke="' + (op.stroke === false ? 'none' : op.color) + '" stroke-width="' + (op.weight || 0) + '" stroke-opacity="' + (op.opacity == null ? 1 : op.opacity) + '"' + (op.dashArray ? ' stroke-dasharray="' + op.dashArray + '"' : '') + '/>');
        continue;
      }
      if (!l._parts || !l._parts.length) continue;
      const closed = !!l._rings && op.fill;
      let d = '';
      l._parts.forEach(part => { part.forEach((pt, i) => { const p = map.layerPointToContainerPoint(pt); d += (i ? 'L' : 'M') + f(p.x) + ' ' + f(p.y); }); if (closed) d += 'Z'; });
      if (!d) continue;
      out.push('<path d="' + d + '" fill="' + (op.fill ? (op.fillColor || op.color) : 'none') + '"' + (op.fill ? ' fill-opacity="' + (op.fillOpacity == null ? 0.2 : op.fillOpacity) + '" fill-rule="evenodd"' : '') +
        ' stroke="' + (op.stroke === false ? 'none' : op.color) + '" stroke-width="' + (op.weight || 0) + '" stroke-opacity="' + (op.opacity == null ? 1 : op.opacity) + '" stroke-linecap="' + (op.lineCap || 'round') + '" stroke-linejoin="' + (op.lineJoin || 'round') + '"' + (op.dashArray ? ' stroke-dasharray="' + op.dashArray + '"' : '') + '/>');
    }
  });
  // DOM markers on top: shelter circles (numbered) and place labels, in the page's own colours
  const mk = [];
  map.eachLayer(l => { if (l._icon && l.getLatLng) mk.push(l); });
  mk.forEach(l => {
    const p = map.latLngToContainerPoint(l.getLatLng()), el = l._icon;
    const c = el.querySelector('.shclu');
    if (c) {
      const cs = getComputedStyle(c), r = c.getBoundingClientRect().width / 2;
      out.push('<circle cx="' + f(p.x) + '" cy="' + f(p.y) + '" r="' + f(r) + '" fill="' + cs.backgroundColor + '" stroke="#ffffff" stroke-width="2"/>' +
        '<circle cx="' + f(p.x) + '" cy="' + f(p.y) + '" r="' + f(r - 1) + '" fill="none" stroke="' + cs.borderTopColor + '" stroke-width="' + parseFloat(cs.borderTopWidth) + '"' + (cs.borderTopStyle === 'dashed' ? ' stroke-dasharray="3 2"' : '') + '/>' +
        '<text x="' + f(p.x) + '" y="' + f(p.y) + '" dy="0.35em" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-weight="700" font-size="' + parseFloat(cs.fontSize) + '" fill="' + cs.color + '">' + esc(c.textContent) + '</text>');
      return;
    }
    const t = (el.innerText || '').trim();
    if (!t) return;
    const b = el.getBoundingClientRect(), m = map.getContainer().getBoundingClientRect(), cs = getComputedStyle(el.querySelector('span') || el);
    const x = b.left - m.left + b.width / 2, y = b.top - m.top + b.height / 2;
    // halo as a separate white copy underneath (many SVG viewers ignore paint-order and would paint the white outline over the letters)
    const ta = '<text x="' + f(x) + '" y="' + f(y) + '" dy="0.35em" text-anchor="middle" font-family="Segoe UI, Arial, Helvetica, sans-serif" font-weight="700" font-size="' + (parseFloat(cs.fontSize) || 13) + '"';
    out.push(ta + ' fill="#ffffff" stroke="#ffffff" stroke-width="3.5" stroke-linejoin="round">' + esc(t) + '</text>' + ta + ' fill="#111111">' + esc(t) + '</text>');
  });
  return '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '"><defs><clipPath id="v"><rect width="' + W + '" height="' + H + '"/></clipPath></defs>' +
    '<rect width="' + W + '" height="' + H + '" fill="#ffffff"/><g clip-path="url(#v)">' + out.join('') + '</g></svg>';
})()
""" % json.dumps([s.upper() for s in SKIP])

try:
    send("Page.enable"); send("Runtime.enable")
    send("Emulation.setDeviceMetricsOverride", width=1800, height=1150, deviceScaleFactor=1, mobile=False)
    send("Page.navigate", url=PAGE + query); time.sleep(9)
    ev(f"__tool.map.setView([{lat},{lon}], {zoom}, {{animate:false}}); 0"); time.sleep(3)
    svg = ev(JS)
    open(out, "w", encoding="utf-8").write(svg)
    print("wrote", out, len(svg), "bytes")
finally:
    proc.kill()
