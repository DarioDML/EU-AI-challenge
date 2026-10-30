"""Bundle the pitch into one self-contained HTML file (the html-slides rule: one file, no dependencies).

Inlines every local stylesheet and script that index.html links, pitch-data.js, and every image under assets/
as data URIs, so the deck runs from a USB stick, an email attachment or the venue laptop without the folder.
The map uses the team's SVG when one exists (assets/ or next to the PNG in powerpoint/), else the PNG.
Fonts still come from Google Fonts when online; system fonts otherwise.

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

base_map = next((p for p in (HERE / "assets" / f"{MAP}.svg", HERE.parent / f"{MAP}.svg", HERE / "assets" / f"{MAP}.png") if p.exists()))
logos = {p.stem: data_uri(p) for p in sorted((HERE / "assets" / "logos").glob("*")) if p.suffix.lower() in MIME}
inline = "<script>window.DECK_INLINE = " + json.dumps({"map": data_uri(base_map), "logos": logos}) + ";</script>\n"
html = html.replace('<script src="js/deck.js"></script>', inline + '<script src="js/deck.js"></script>')
html = re.sub(r'<script src="((?!https?:)[^"]+)"></script>', js, html)
# the map's own file name may also appear literally (agents' code), raw or URL-encoded
for name in (f"assets/{MAP}.png", "assets/" + MAP.replace(" ", "%20").replace("+", "%2B") + ".png"):
    html = html.replace(name, data_uri(HERE / "assets" / f"{MAP}.png"))

OUT.write_text(html, encoding="utf-8")
left = sorted(set(re.findall(r"(?<![\w:/])assets/[^\"'`)\s]+", html)))
print(f"wrote {OUT.name}: {OUT.stat().st_size / 1e6:.1f} MB; map = {base_map.name}; logos = {sorted(logos) or 'none (typographic lockup)'}")
if missing:
    print("not found (skipped):", ", ".join(missing))
if left:
    print("asset paths still referenced (dynamic or missing):", ", ".join(left[:10]))
