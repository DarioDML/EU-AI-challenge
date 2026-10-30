# Pitch: Johan's way out (5 minutes)

Interactive HTML deck for the European AI Challenge pitch. Open `index.html` in Chrome or Edge (works offline from the file; fonts fall back to system fonts without internet). Press F for full screen.

| Key | Action |
|---|---|
| Space, →, PageDown, Enter | next build or slide (clickers work) |
| ←, PageUp, Backspace | back |
| N | speaker notes and clock (rehearsal only: the audience sees it) |
| T | restart the 5-minute pace bar (it also starts on the first key press) |
| 1-4, B | slide 4: flood level, shelter buildings |

`index.html#3.2` opens slide 3 at build 2; `?static` turns transitions off (screenshots).

## Data
Every number on slides 3 and 4 comes from `pitch-data.js`, generated from the Smart Shelter System bundle (`ideas/05-smart-shelter-map/data/bundle.json`, read from `origin/team1-smart-shelter-map` when it is not checked out):

```powershell
python presentation/build_pitch_data.py            # 52 checks; stops on a failure
python presentation/fit_screenshot.py --check figures/generated/pitch/georef_check.png   # only if the map screenshot changes
```

The map is `assets/visualisation busy roates + flooded areas.png` (exact team file name). An SVG of the same view, saved as `assets/visualisation busy roates + flooded areas.svg` or next to the PNG in `powerpoint/`, replaces it automatically. It must show the same extent at the same aspect ratio (1524 × 919), or Johan's route overlay will not line up.

Official FARI and JRC logos are not in the repo; drop the organisers' files as `assets/logos/fari.svg|png` and `assets/logos/jrc.svg|png` and the lockups use them.

Story, sources, allowed claims and open items: `PITCH_BLUEPRINT.md`. Illustrations: `Pitch deck.pptx`.
