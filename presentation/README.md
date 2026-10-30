# Johan's way out

Five-slide interactive pitch for the European AI Challenge. Open `johan-pitch.html` in Chrome or Edge for the self-contained offline deck, or `index.html` to work on the source. Press **F** for full screen.

The white European editorial theme uses navy text, blue emphasis, original-colour organiser logos at the bottom left, and numbered titles. Johan appears without the house. Transitions are short crossfades with small build movements; route drawings explain the map. System fonts, scripts, styles, maps and logos are available offline in the single-file build.

## Presenting

| Key | Action |
|---|---|
| Space, right arrow, PageDown, Enter | Next build or slide |
| Left arrow, PageUp, Backspace | Back |
| Home / End | First / last slide |
| F | Full screen |
| N | Rehearsal notes and clock (visible to the audience) |
| T | Restart the five-minute pace bar |
| Period | Blackout / restore |

`index.html#3.2` opens slide 3 at build 2. `?static` suppresses motion, as does the operating system's reduced-motion setting.

Opening sequence: Meet Johan, his three questions, the proportion receiving no warning, then two separate shares among warned respondents. The separate dot grids preserve the differing survey denominators.

Slide 5 (`slides/s4-policy.*`) is a guided demo of the policy tool (`policy-tool/`) for Anna in four builds: her question, where the risk is (region view), who gets a shelter (Schleiden, the map pushes in), and her answer with the first step (the tool's "Anna's action" view). The phone alert is slide 3, so this slide shows none. The screens in `assets/tool/` are headless captures of the tool at 1600 × 900, default plan; the Schleiden figures come from `data-analysis/shelter_alert_de_18_summary.json`.

## Build and review

Run from the repository root:

```powershell
python presentation/build_single.py
python presentation/qa/audit.py --offline --max-words 160 --out figures/generated/pitch/qa-final
python scripts/check_data.py
```

On branch `presentation/johan-pitch`, the published source folder is `presentation/`; substitute that prefix for `presentation/` in these commands. The scripts locate the repository through an `AGENTS.md` ancestor.

The audit renders every build and checks navigation, images, layout and errors. Its lexical and screenshot-contrast findings are heuristics and need visual review. The 160-word ceiling preserves the existing demo and source detail during this style-only pass; the original 20-word target is not enforced. Final visual and interaction findings are recorded in `QA_REPORT.md`.

## Map and data

The active map is `assets/route-stress-map.svg` (1244 by 894), derived from the supplied `route-stress_bad-neuenahr-ahrweiler_july-2021_capacity-A.svg` by removing its white background rectangle. The supplied original and the earlier PNG remain unchanged. No panel is painted behind the map. Base map and overlay use the same dimensions and fitted coordinates in `georef.json` / `pitch-data.js`.

The data generator reads the pinned Smart Shelter System bundle and validates its outputs. Do not swap maps without refitting and rebuilding:

```powershell
python presentation/fit_screenshot.py --check figures/generated/pitch/georef_check.png
python presentation/build_pitch_data.py
python presentation/build_single.py
```

Modelled residents, candidate buildings and free-flow trips remain estimates and assumptions, with sources and limitations on the slides and in their notes. Observed EMS evidence and EFAS scenarios remain separate.

Survey source: [Thieken et al. (2023), NHESS 23, 973-990](https://nhess.copernicus.org/articles/23/973/2023/), July 2021 floods, online survey of 1,315 flood-affected respondents. The 29% share is for respondents in Rhineland-Palatinate; 85% and 46% refer to warned respondents across the study. They must not be multiplied together or shown as overlapping subsets of one cohort.

Slide 5's existing impact estimates come from the team brief and retain their visible qualification; they were not independently established by this style pass. See `FACTCHECK.md` and `PITCH_BLUEPRINT.md` for the earlier evidence review and remaining content checks.

## Design references and assets

Visual direction draws on the [European Commission identity guidance](https://commission.europa.eu/resources/european-commission-visual-identity_en) and the team's Annex 6 template, adapted to the requested white editorial style. Supplied `assets/logos/logo FARI.png` and `logo JRC.jpg` retain their original colours and aspect ratios.

The deck preserves the [html-slides](https://github.com/bluedusk/html-slides) presentation conventions already implemented: a single offline HTML file, `.deck` / `.slide` structure, slide-note JSON, and `goTo`, `next`, `prev` controls. It does not require the separate presenter app.
