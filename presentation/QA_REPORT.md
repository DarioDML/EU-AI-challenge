# QA report: Johan's way out (pitch deck), final audit

Run 30 Oct 2026 13:19 on the deck as it stood then: `python presentation/qa/audit.py` (headless Chrome over the DevTools protocol, 1920x1080, `?static`, plus a live pass with real transitions and a device-scale-2 pass). Screenshots, contact sheet, `audit.json`: `figures/generated/pitch/qa/`. PDF backup: `presentation/johan-pitch-backup.pdf` (20 pages, 2.3 MB, 1920x1080; regenerate with `python presentation/qa/export_pdf.py --refresh`).

Deck now: s1 Meet Johan (5 steps), s2 How it works (3), s2b The message (4), s3 The map (4), s4 Decide before the night (2, teammate's placeholder), s6 Thank you (2). The Europe slide is gone. Slides s3, s4 and s6 were still being edited during the audit; re-run `qa/audit.py` once they settle.

Words = visible words of the build, excluding source captions (`.src`, `.s2-micro`, `.g-micro`) and the phone screen (`.s2b-phone`, `.s4-phone`, which is the alert itself). Limit 20. T3 = spacing / typography / colour / alignment / overall.

## Checks that pass
- Console: no errors or exceptions, static (21 loads) and live (stepping the whole deck forward and back with transitions).
- html-slides layer: `div.deck#deck`, six `.slide` with `data-slide` 0..5, exactly one `.active`, `script.slide-notes` last child with valid title, script and notes[], `goTo`/`next`/`prev` move `.active`, no delivery cues. The generator meta tag is now in `index.html`.
- Logos: FARI 4980x1791 and JRC 1024x440 render at their own aspect, bottom left, no box, background or shadow.
- Map: `route-stress-map-hd.svg` on slide 4 is drawn 1244x894 CSS px at 1:1, vector, with no transform above it; at device scale 2 the screenshot is 3840x2160 and the scale stays 1.0000. On slides 2 and 3 it is a vector crop at x1.6 and x2.1, so it stays sharp.
- Claims: every hit for "reroute", "designated shelters", "upper bound" and "traffic simulation" is negated. No FAIR for FARI, lorem or TODO, no purple gradient, no default slider. Hand-typed numbers on the map slide: none (hits are SVG geometry).
- Contrast on the light theme at least 4.5:1 for body and 3:1 for large text, except the intentional dimmed items below. No gold text on white (`--gold-ink` used for the 46 %).

## Per state

| State | Slide | Words | New | Issues | Status | T3 |
|---|---|---|---|---|---|---|
| 1.0 | s1 | 10 | 10 | none | ok | 4/5/4/4/4 |
| 1.1 | s1 | 15 | 15 | none | ok | 4/4/4/4/4 |
| 1.2 | s1 | 15 | 15 | "per 100 respondents" 17 px | open (minor) | 4/5/5/4/4 |
| 1.3 | s1 | 19 | 11 | was 21: legend "no warning" now leaves at this build | fixed | 4/4/4/4/4 |
| 1.4 | s1 | 19 | 11 | was 21 | fixed | 4/4/4/4/4 |
| 2.0 | s2 | 10 | 10 | none | ok | 4/4/4/4/4 |
| 2.1 | s2 | 15 | 5 | was 29 | fixed | 4/4/4/4/4 |
| 2.2 | s2 | 20 | 5 | was 40 | fixed | 4/4/4/4/4 |
| 3.0 | s2b | 0 | 0 | phone only | ok | 4/4/4/4/4 |
| 3.1 | s2b | 5 | 5 | none | ok | 4/5/4/4/4 |
| 3.2 | s2b | 10 | 5 | dimmed "01" numeral 2.2:1 | open (minor) | 4/5/4/4/4 |
| 3.3 | s2b | 15 | 5 | same; the dimmed questions now pass 3:1 (opacity .38 to .55) | fixed | 4/5/4/4/5 |
| 4.0 | s3 map | 12 | 12 | none | ok | 4/4/4/4/4 |
| 4.1 | s3 map | 23 | 11 | over 20 | open | 4/4/4/4/4 |
| 4.2 | s3 map | 44 | 26 | over 20; "Model, free-flow" 16 px | open | 3/4/4/4/4 |
| 4.3 | s3 map | 40 | 4 | over 20; route B is only about 60 px long on the map | open | 3/4/4/4/4 |
| 5.0 | s4 | 36 | 36 | teammate's slide, not edited | open | not scored |
| 5.1 | s4 | 43 | 6 | same, 17 px captions | open | not scored |
| 6.0 | s6 | 20 | 20 | 17 px tool list | open (minor) | 4/4/4/4/4 |
| 6.1 | s6 | 27 | 7 | over 20; "Tool built in two days." 2.4:1 (dimmed) | open | 4/4/3/4/4 |

I looked at every state in the contact sheet and at full size at 1.4, 3.3 and 6.1 (old Thank-you layout). Tier 2 (overflow, overlapping, blank, image_broken, chart_empty, text_truncated) passes on every state.

## Fixed in this run
- `index.html`: generator meta tag added.
- `slides/s1-johan.js`: legend "no warning" leaves at build 3 (21 to 19 words); speaker script cut from 120 to 97 words ("In a survey" without the n, "He has three questions", "lacked knowledge on how to protect themselves").
- `slides/s2-pipeline.js`: step numerals are `aria-hidden`; title "From flood map to one message."; "shelter with room"; "three plain-text answers"; script 99 to 75 words.
- `slides/s2b-message.js`: script 117 to about 94 words (the 500-year sentence is dropped; its figure is still on screen).
- `slides/s2b-message.css`: dimmed past questions at opacity .55 instead of .38.
- Harness: caption and phone exemptions, glyph-ink overlap test, speaking-time check, live pass, device-scale-2 map pass, logo box and place checks, map transform check.

## Speaking time at 130 wpm (script words against the window)
s1 97 words = 45 s (window 45 s); s2 75 = 35 s (35 s); s2b about 94 = 43 s, now 113 = 52 s in the latest edit (45 s window, over); s3 169 = 78 s (60 s window, over by 18 s); s4 168 = 78 s (window now 80 s); s6 25 = 12 s (15 s). The s3 script needs about 40 words cut, or give s3 about 15 s from s4.

## Open
- Word limit on the map slide: 4.1 (23), 4.2 (44), 4.3 (40). The legend (8 words) and three HUD labels stay on screen; shortening them ("Closed roads on route", "Sent to other districts") and hiding the legend after build 1 brings them to about 28. Not edited because slide 3's route content was changing.
- s4 (5.x) is the teammate's: 36 and 43 words, 17 px captions, 3.2:1 on two glyphs, "designated shelters" appears in a negated sentence only.
- s6 (6.1): 27 words; the dimmed first line is 2.4:1.
- Slide times: s4 ends at 265 s and s6 starts at 285 s (20 s gap); check the windows.
- s6 says "AI built it fast"; fine as a statement about how the tool was made, but keep it away from the routing engine, which is not AI.
- Web fonts did not load in the audit browser (system fallback); check once online before presenting.
- Johan's town is Bad Neuenahr-Ahrweiler here and Gemünd in `policy-tool/DEMO.md`.
