"""Builds tool/dist/shelter_tool.html: src/app.html + Leaflet 1.9.4 (inlined) + the bundle JSON (inlined).

Usage:  .venv\\Scripts\\python.exe -B -I tool\\build.py [bundle.json]     (default: tool/data/bundle.json if present, else mock_bundle.json)
Leaflet is downloaded ONCE from cdnjs into tool/vendor/ (SHA-256 printed) and reused afterwards.
The result opens from file:// with no server; only the optional basemap tiles need the network.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "vendor")
BASE = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/"
FILES = ["leaflet.js", "leaflet.css"]
# 1x1 transparent gif: replaces Leaflet's relative image urls (layers.png, marker icons) that we never use
PIXEL = "url(data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==)"


def fetch_vendor():
    os.makedirs(VENDOR, exist_ok=True)
    for name in FILES:
        path = os.path.join(VENDOR, name)
        if not os.path.exists(path):
            print("downloading", BASE + name)
            with urllib.request.urlopen(BASE + name, timeout=60) as r:
                data = r.read()
            with open(path, "wb") as f:
                f.write(data)
        with open(path, "rb") as f:
            print("SHA-256", name, hashlib.sha256(f.read()).hexdigest())


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    # default: the real bundle if the pipeline has written one, else the synthetic mock
    real = os.path.join(HERE, "data", "bundle.json")
    mock = os.path.join(HERE, "data", "mock_bundle.json")
    bundle_path = sys.argv[1] if len(sys.argv) > 1 else (real if os.path.exists(real) else mock)
    fetch_vendor()
    js = read(os.path.join(VENDOR, "leaflet.js"))
    js = re.sub(r"//# sourceMappingURL=\S+", "", js)
    css = re.sub(r"url\((?:\"|')?images/[^)]*\)", PIXEL, read(os.path.join(VENDOR, "leaflet.css")))
    css = re.sub(r"/\*# sourceMappingURL=.*?\*/", "", css)
    assert "</script" not in js.lower(), "unexpected </script in leaflet.js"

    with open(bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)  # fails early if the file is not valid JSON
    text = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
    # keep the JSON from closing the script element or opening an HTML comment; U+2028/9 break old JS parsers
    text = text.replace("</", "<\\/").replace("<!--", "<\\!--").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")

    html = read(os.path.join(HERE, "src", "app.html"))
    for marker, value in (("/*__LEAFLET_CSS__*/", css), ("/*__LEAFLET_JS__*/", js), ("/*__BUNDLE__*/null", text)):
        assert html.count(marker) == 1, "marker missing or repeated in app.html: " + marker
        html = html.replace(marker, value)  # str.replace: no regex escaping problems

    out_dir = os.path.join(HERE, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "shelter_tool.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", out, round(os.path.getsize(out) / 1024), "KB (%.1f MB) from bundle" % (os.path.getsize(out) / 1048576), bundle_path)


if __name__ == "__main__":
    main()
