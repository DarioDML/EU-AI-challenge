# Design review, pitch deck (screenshots 2026-10-30 12:45-12:49, 1920x1080, `?static#N.K`)

Note: `s3-map.css` header already says "light European theme" and was being edited, so slide 3 shots (dark glass) may be stale. Re-shoot after agent 7 lands. Hash format is `#N.K` (not `#S.K`; the `S` form renders slide 1 every time).
Not individually viewed: s2-1, s3-1, s3-2, s4-1, s5-1 (intermediate steps).

## Scores (1-5: hierarchy / whitespace / alignment / colour / contrast / 3-sec legibility)
| State | H | W | A | C | Ct | L | Verdict |
|---|---|---|---|---|---|---|---|
| s1.0 Meet Johan | 4 | 4 | 4 | 3 | 5 | 5 | cartoon in circle = childish |
| s1.1 three questions | 4 | 4 | 4 | 3 | 4 | 5 | gold text OK (#7A5F00); same cartoon |
| s1.2 29% dots | 5 | 4 | 4 | 5 | 4 | 5 | best slide; footer source 11px |
| s1.3 85/46 | 4 | 4 | 3 | 4 | 4 | 4 | gold rings on blue dots busy |
| s2.0 (1 of 3) | 3 | 3 | 3 | 4 | 4 | 3 | empty 2/3 of slide, map not centred in column |
| s2.2 full | 3 | 3 | 3 | 2 | 4 | 4 | magenta houses, phone, map clipped; icon-row feel |
| s3.0 map | 2 | 2 | 2 | 2 | 2 | 3 | dark glass legend, title collides, footer under map |
| s3.3 HUD | 1 | 1 | 1 | 2 | 1 | 2 | overlaps, see defects |
| s4 demo | 4 | 4 | 4 | 3 | 4 | 4 | clean; green/amber/red not tokens |
| s5.0 | 3 | 4 | 3 | 2 | 4 | 4 | clip-art hill scene, off-edge |
| s5.2 close | 4 | 4 | 4 | 4 | 5 | 4 | good; logos big here, tiny elsewhere |

## Defects (pixel coordinates at 1920x1080)
- s3: legend dark glass box (14,14)-(202,112) collides with title left edge x=217; title baseline y~80 vs other slides y~190. Slide number "03 THE MAP" (1690,55) hidden behind HUD tile (1540,59)-(1904,127) in s3.3. HUD tiles dark navy-grey with unreadable labels (contrast ~1.5:1). Callouts "Johan"/"Kindergarten" dark boxes; "3.8x road capacity" (1090,768) label text washed out. Bottom pill "Polch 28 min" (1160,985) near-invisible. Map card (215,140)-(1704,1033) is a grey rounded rectangle with heavy shadow, not transparent; the bottom 1033 edge runs into footer. FARI/JRC logos (96,1010) overlapped by map card; JRC logo cut at x~232. Footer text (424,1055) clipped under map and by attribution box (1637,1005)-(1920,1080), a dark box bleeding off canvas.
- s2: map thumbnail (198,390)-(498,653) is offset 100px right of its column (96..600) and hard-cropped at right and bottom (visible rectangle edge); arrows at y=540 not aligned to phone centre y=540 (ok) but gap map->arrow 30px vs arrow->icon 0px. Magenta houses #C2185B clash with palette. Disclaimer (640,1027) starts at x=640, not on the 96 left margin or right-aligned; it competes with logos.
- s1: avatar circle (1090,240)-(1710,860) with shadow = default-looking. Footer citation 11px mono at (708,1027) too small. Gold hairline under title absent but blue rule at (96,373) while s2/s5 use gold rule (96,124)/(96,145): inconsistent accent colour and y position.
- s5.0: scene (360,397)-(1820,1048) is cut flat at x=360 and y=1048 and x=1820; sun, flag, house, hill = childish scene.
- Titles: s1 130px bold, s2 ~65px regular, s3 ~58px bold, s4 ~58px bold, s5.0 ~95px regular. Weight flips between bold and regular; no scale.
- Logos: 30px tall on s1-s4 (illegible subtext) vs ~75px on s5. No box (good).
- Progress bar at y=1077 shows tick marks only; barely visible (fine).

## Fixes (max 20), by owner

### Agent 6: slides 1/5 + brand
1. `s1-johan.css` avatar circle: remove border and box-shadow, background none; scale figure to 560px tall, centre in right half (x 1100-1800). Drop the circle entirely.
2. `s5-europe.css` / scene SVG: delete the hill/sun/house scene; replace step 0 with a single line map (Europe outline, gold dot on Ahr) or a big type-only statement. No flag, sun, or hill.
3. `s1-johan.css` rule (96,373): use `--eu-blue` 56x3px on s1; make the same accent rule on all slides EU blue, gold only as a 6px dot at the data point.
4. `brand.css` `.brand-logo img`: height 30px -> 40px on all slides; keep gap 40px; bottom 40px, left 96px. Same height on s5 or intentionally larger (56px) only on closing.
5. Slide 1 source line `.s1-source` (708,1027): 11px -> 15px, colour `--ink-2`; wrap at 2 lines max, right edge x=1824.
6. `s1` step 3: gold ring (#FFCC00) on blue dots: use navy ring 3px for "didn't know", keep gold off the chart; gold only in the "46" via #7A5F00.
7. `s5` step 2: close layout fine; align `TEAM 1` baseline with the logos bottom (y 915).

### Agent 7: slides 2/3
8. `s2-pipeline.css` `.s2-col`: centre the artwork in the column (map left 96 -> centre at 348 of 96..600); remove hard crop with `clip-path: inset(0 round 12px)` or fade mask `mask-image: radial-gradient`, 300x263 -> 440x330.
9. `s2` house icons: `--building` #C2185B -> `#003399` fill with white glyph; shelter chosen pin gold ring only.
10. `s2` footer disclaimer: left=96, bottom=96, 15px; or move under the title as a subtitle. Remove from the logo row.
11. `s2` step reveal: step 0 should show 3 faint column rules with the first active, so the slide is never 2/3 empty.
12. `s3-map.css` legend: replace dark box with no-box white-text-free legend: 15px navy text, no background, at (96,150) under title; or put inside the map bottom-left at (240,960) with 90% white.
13. `s3` title: top 124 as s2 (y~190 baseline), single title position across slides; map card moves down to y=250, height 720, left 96 right 1824, background transparent, no shadow, radius 0.
14. `s3` HUD tiles (1540,59): white 96% bg, 1px #D6E0F2 border, navy numbers 56px, gold only as 3px left bar; position inside map top-right (1580,270), never overlapping the section label (1690,55).
15. `s3` callouts and `.s3-call-home`: white bg, navy text 22px, 1px navy hairline leader; remove dark pills. Capacity label contrast >= 7:1.
16. `s3` attribution box (1637,1005): remove dark box; right aligned 12px `--ink-2` at x=1824,y=1040. Footer text "Smart Shelter System bundle..." same style, not behind map.

### Engine/shared (main)
17. `deck.css` `.title`: define scale 72px/1.05 weight 700 for all slide titles at top 140; s1 hero 120, s5 80. Remove regular-weight variants.
18. `deck.css` logo row: reserve `bottom: 40px; height: 40px` safe band; nothing else below y=1030 except the progress bar.
19. `brand.css`: add tokens `--ok:#1B7F5C`, `--warn:#B45309`, `--bad:#B42318` for s4 bar; remove hard-coded green/amber. Add `--shelter:#003399`.
20. `deck.js` hash: accept `#S2.1` as alias; document `?static#N.K` in README.

## Three keynote polish moves
1. One locked grid and one title position (x 96, y 140, 72px bold) across slides, so cuts feel like a keynote: only content changes.
2. Replace cartoon scenes with one hero image: the real flood-extent map at full bleed, thin white type overlay (Apple-style), and a single 140px number per beat.
3. Add a continuous motion thread: the Ahr river line from slide 1 dot grid morphs into the s2 map and s3 route (shared-element transition, 600ms ease-out), ending on the Europe dot in s5.
