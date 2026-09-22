---
id: detect-missed-shot-cuts
name: Catch the shot cuts a histogram detector misses - isolated structural or colour jumps, kept past min_len
category: workflow
kind: technique
status: verified
applies_to:
- any
when_to_use: Splitting a reference video into shots before measuring or recreating it, or when one shot's measurements
  look like two different pictures (a close-up face held on a wide shot, lighting that fits neither half).
triggers:
- shot boundaries
- missed cut
- scene detection
- shot segmentation
- cut detection
- min_len
tags:
- recreation
- reference
- measurement
source:
- 'own-experience: Fragrant Flower 1268 / 1698 and Blue Box 613 / 2165 / 2184 / 2201, 2026-09-22 (training/PROGRESS.md)'
version: 1
---
## Procedure

1. Run the usual cut test (mean abs difference > 22 on 192 px frames AND 8x8x8 colour-histogram distance > 0.6), then
   merge_similar (drop cuts < 10 frames after the previous one, and cuts whose two sides share a colour world).
2. Then add back every **isolated** jump: frame difference > 22 while both frame differences on either side stay under
   30 % of it (a hold, then one change, then a hold). Flash runs and fast action are never isolated, so this does not
   re-admit them.
3. An isolated jump is a cut when EITHER the blurred-gray (sigma 2) correlation across it is < 0.3 (the picture's
   structure changed) OR its histogram distance > 0.6 (the colour changed like a raw cut). Isolated cuts bypass
   min_len and the colour-world merge.
4. Look at every added cut (frame before / after) before trusting the rule on a new video.
5. When shots are re-cut after measuring, renumbering shifts every per-shot file: carry unsplit shots over by index,
   re-measure split shots and re-describe them from their own contact sheets (`training/resegment_shots.py`).

Implemented in `training/ingest_reference.detect_isolated_cuts`.

## Evidence

| jump | mad | histogram | correlation | what it is |
|---|---|---|---|---|
| FF 1268 | 55.9 | 0.68 | 0.20 | cut, folded by min_len (9 frames after 1259) |
| FF 1698 | 64.3 | 0.39 | 0.22 | cut, same colours both sides |
| BB 2165 | 44.7 | 1.45 | 0.45 | cut, folded by min_len |
| FF 809 | 28.9 | 0.19 | 0.43 | redrawn close-up inside a shot: rejected |
| FF 1186 | 40.3 | 0.26 | 0.61 | drawing change: rejected |

Adds 11 cuts across 5 references, each confirmed by eye. Splitting FF 34 took its frames from the worst of four runs
(lpips 0.537) to the best (0.618): the wide half had been drawn with the close-up's giant face.

## Limits

A cut inside a flash or fast-action run is not isolated and is still missed. The thresholds were set on two anime
trailers; check a live-action or heavily graded video by eye before trusting them.
