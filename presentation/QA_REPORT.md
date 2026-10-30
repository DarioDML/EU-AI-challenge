# QA report: Johan's way out (pitch deck)

Run: 30 Oct 2026, `python presentation/qa/audit.py` (headless Chrome over the DevTools protocol, 1920x1080, `?static`), then `qa/export_pdf.py`. Screenshots, contact sheet and `audit.json`: `figures/generated/pitch/qa/`. PDF backup: `presentation/johan-pitch-backup.pdf` (20 pages, 2.2 MB, 1920x1080).

Scope: slides 1 (s1), 2 (s2), 3 (s3 map) and 5 (s5), which are stable. The deck now registers six slides, so the state numbers below are the current ones: s1 = 1.x, s2 = 2.x, s2b = 3.x, s3 map = 4.x, s4 = 5.x, s5 = 6.x. s2b and s4 are still placeholders and appear only under findings.

Words = visible words of the build, source captions (`.src`) excluded; the limit is 20. T2 = html-slides Tier 2, pass unless listed. T3 = Tier 3 scores spacing / typography / colour / alignment / overall (1-5), scored from the screenshots.

## Result in one view
- Console: no errors or exceptions. Layer: `div.deck#deck`, six slides with `data-slide` 0..5, exactly one `.active`, `slide-notes` JSON (title, script, notes[]) is the last child of every slide, `goTo`/`next`/`prev` move `.active` correctly, no delivery cues in the notes.
- Forbidden claims: every hit in slides 1, 2, 3 and 5 is negated ("not lower and upper bounds", "does not reroute", "not designated shelters"). No "FAIR" (only a comment in `css/brand.css` that says the organiser is FARI), no lorem or TODO, no purple gradient (s2-pipeline.css uses `magenta` for the building colour only), the range inputs are custom.
- Hand-typed numbers on slides 3 and 4: all hits are SVG geometry or text such as the alert date. No data value is typed by hand on the map slide.
- Map: `route-stress-map.svg` 1244x894 is drawn at exactly 1244x894 px on slide 3 (4.x), not stretched; on slide 2 it is a vector crop at x1.6, aspect kept. Logos: FARI 4980x1791 and JRC 1024x440 render at their own aspect (error under 0.3 %). Both load.
- Gold #FFCC00 as text on white: none found. Contrast is at least 4.5:1 for body text on slides 1, 2, 3 and 5.

## Per state

| State | Slide | Words | New | T2 | Issues | Status | T3 |
|---|---|---|---|---|---|---|---|
| 1.0 | s1 Meet Johan | 10 | 10 | pass | "?" instead of "·" in "11 · Bad Neuenahr-Ahrweiler" | fixed | 4/5/4/4/4 |
| 1.1 | s1 three questions | 15 | 15 | pass | none (scored from the contact sheet) | ok | 4/4/4/4/4 |
| 1.2 | s1 29 % waffle | 17 | 17 | pass | harness false positive "text on text" 29 / received no warning (line boxes of the large numeral) | harness fixed | 4/5/5/4/4 |
| 1.3 | s1 85 % and 46 % | 41 | 41 | pass | over the word limit (see below); "didn?t" glyph; 17 px grid captions | glyph fixed; words open | 4/4/4/4/4 |
| 2.0 | s2 lens 1 | 18 | 18 | pass | 15 px mono source line | open (minor) | 4/4/4/4/4 |
| 2.1 | s2 lens 2 | 29 | 11 | pass | 29 words visible, 11 new | open | 4/4/4/4/4 |
| 2.2 | s2 lens 3 | 40 | 11 | pass | 40 words visible, 11 new; harness flagged `chart_empty` on the phone bars (false positive) | words open; harness fixed | 4/4/4/4/4 |
| 4.0 | s3 map | 12 | 12 | pass | none (contact sheet only) | ok | 4/4/4/4/4 |
| 4.1 | s3 pins | 23 | 11 | pass | 23 words (legend 7, pins 11, title 3, chip) | open | 4/4/4/4/4 |
| 4.2 | s3 route A and HUD | 44 | 26 | pass | 44 words visible, 26 new; 16 px "Model, free-flow" | open | 3/4/4/4/4 |
| 4.3 | s3 route B | 40 | 4 | pass | 40 words visible; route B is only about 60 px long on the map, so the story is carried by the HUD tick (2.4 min) and the Kindergarten label | open (design) | 3/4/4/4/4 |
| 6.0 | s5 Johan | 7 | 7 | pass | none | ok | 4/4/4/4/3 |
| 6.1 | s5 Europe numbers | 30 | 30 | pass | over the word limit; three figures, three captions, open-data line | open | 4/5/4/4/4 |
| 6.2 | s5 three asks | 32 | 32 | pass | over the word limit; Europe map is very faint and the Ahr pin nearly invisible | open | 4/5/4/4/4 |

Scored at full size: 1.0, 1.2, 1.3, 2.2, 4.2, 4.3, 6.1, 6.2. The others were scored on the contact sheet.

## Word limit (20 per build): the main open item
Seven states of the four stable slides exceed 20. The audit counts everything visible except `.src`. Cuts that would bring them under:
- 1.3 (41): drop both "Share among warned respondents" (8 words), move "Each grid represents a separate percentage. Overlap between the groups is not shown." (13) into the source caption, drop the subtitle (5). About 15 left.
- 2.1 and 2.2 (29, 40): only 11 words are new per build, so the stage reads as 3 words per lens; the total is the three lens titles, three subtitles and the footer. Acceptable if the limit is read as new words per build.
- 4.2 and 4.3 (44, 40): the legend (7 words) and the three HUD labels (about 18) stay on screen. Shorten the HUD labels ("Closed roads on route", "Sent to other districts") and hide the legend after build 1.
- 6.1 (30): shorten the WMO line to "WMO: early warning returns about 10x its cost" and drop "lives lost, roughly" to "lives lost".
- 6.2 (32): 3 asks (14 words) plus the "To crisis authorities" line, "TEAM 1" and the title; the title is the only line that can go.
I did not cut copy myself: it is the speaker's wording and the Thieken caveat on slide 1 matters.

## Fixed
- `slides/s1-johan.js`: two literal "?" characters replaced by "·" (line 33) and "’" (line 58, "didn’t"). The file had lost them in an earlier write.
- Harness: text on text threshold (a numeral and its caption are not an overlap), contrast "busy background" no longer counts neighbouring text, captions are no longer cut at 160 characters (the required-phrase check missed "not a forecast" and OpenStreetMap), chart detection counts the element itself, logo aspect uses the true rendered box.

## Findings for others (not edited)
- `slides/s2b-message.*` (3.x): still unstyled. Headline numbers overlap the questions, the alert text runs from x = 0, the map `img.s2b-base` leaves the stage (r 1110 px, b 1624 px, 16 % visible), 78 words visible, "Alertnow" is run together in the alert header. Re-run the audit once its CSS lands.
- `slides/s4-policy.*` (5.x): 36 words at 5.0 and 99 at 5.1 earlier; 17 px captions; one "?" in the source (`x?x` pattern) to check for a lost glyph; `.s4-sr` text was reported as cut at the stage edge (probably a screen-reader node the harness does not skip).
- `index.html`: no `<meta name="generator" content="html-slides v0.9.4">` (html-slides spec rule 8); slides are `<section>` (html-slides writes `<div>`; selectors still work).
- Slide times run 0 to 300 s without a gap now that s2b exists (80-125 s).
- Johan's town is Bad Neuenahr-Ahrweiler here and Gemünd in `policy-tool/DEMO.md` (blueprint item 1).
- Audit fonts: the web fonts did not load in the audit run, so the screenshots use the fallback face; check once in Chrome with internet before presenting.
