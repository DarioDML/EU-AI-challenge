"""Bundle the pitch into one self-contained HTML file (the html-slides rule: one file, no dependencies).

Inlines every local stylesheet and script that index.html links, pitch-data.js, and every image under assets/
as data URIs, so the deck runs from a USB stick, an email attachment or the venue laptop without the folder.
The map comes from the same pitch-data.js metadata used by the live deck, preserving overlay alignment.
System fonts and embedded organiser logos work offline without external requests.

    python powerpoint/pitch/build_single.py      ->  powerpoint/pitch/johan-pitch.html
"""
import base64
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "johan-pitch.html"
MAP = "visualisation busy roates + flooded areas"
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".webp": "image/webp"}


def data_uri(path):
    return f"data:{MIME[path.suffix.lower()]};base64," + base64.b64encode(path.read_bytes()).decode()


def inline_images(text):
    """Replace literal asset paths (relative to index.html or ../ from css/ and slides/) with data URIs."""
    def swap(m):
        path = HERE / m.group(2)
        return data_uri(path) if path.exists() else m.group(0)
    return re.sub(r"((?:\.\./)?)(assets/[\w./-]+?\.(?:png|jpe?g|svg|webp))", swap, text)


html = (HERE / "index.html").read_text(encoding="utf-8")
missing = []


def css(m):
    path = HERE / m.group(1)
    if not path.exists():
        missing.append(m.group(1))
        return ""
    return "<style>\n" + inline_images(path.read_text(encoding="utf-8")) + "\n</style>"


def js(m):
    path = HERE / m.group(1)
    if not path.exists():
        missing.append(m.group(1))
        return ""
    return "<script>\n" + inline_images(path.read_text(encoding="utf-8")).replace("</script", "<\\/script") + "\n</script>"


html = re.sub(r'<link rel="stylesheet" href="((?!https?:)[^"]+)">', css, html)

data_text = (HERE / "pitch-data.js").read_text(encoding="utf-8")
pitch = json.loads(data_text.split("window.PITCH =", 1)[1].strip().rstrip(";"))
base_map = HERE / "assets" / pitch["screenshot"]["file"]
if not base_map.is_file():
    raise FileNotFoundError(f"The georeferenced map is missing: {base_map.name}")
if base_map.suffix.lower() == ".svg" and re.search(r'<rect width="\d+" height="\d+" fill="#fff(?:fff)?"\s*/>', base_map.read_text(encoding="utf-8")):
    raise ValueError(f"{base_map.name} still has a white background rect; use the transparent derived assets/route-stress-map.svg")
logos = {}
for key, supplied in {"fari": "logo FARI.png", "jrc": "logo JRC.jpg"}.items():
    candidates = [HERE / "assets" / "logos" / supplied]
    candidates += [HERE / "assets" / "logos" / f"{key}{ext}" for ext in MIME]
    found = next((p for p in candidates if p.is_file()), None)
    if found:
        logos[key] = data_uri(found)
inline = "<script>window.DECK_INLINE = " + json.dumps({"map": data_uri(base_map), "logos": logos}) + ";</script>\n"
html = html.replace('<script src="js/deck.js"></script>', inline + '<script src="js/deck.js"></script>')
html = re.sub(r'<script src="((?!https?:)[^"]+)"></script>', js, html)
# the map's own file name may also appear literally (agents' code), raw or URL-encoded
for name in (f"assets/{MAP}.png", "assets/" + MAP.replace(" ", "%20").replace("+", "%2B") + ".png"):
    html = html.replace(name, data_uri(base_map))

if missing:
    raise FileNotFoundError("Cannot build the deck; missing dependencies: " + ", ".join(missing))
OUT.write_text(html, encoding="utf-8")
left = sorted(set(re.findall(r"(?<![\w:/])assets/[^\"'`)\s]+", html)))
print(f"wrote {OUT.name}: {OUT.stat().st_size / 1e6:.1f} MB; map = {base_map.name}; logos = {sorted(logos) or 'none (typographic lockup)'}")
if left:
    print("asset paths still referenced (dynamic or missing):", ", ".join(left[:10]))
