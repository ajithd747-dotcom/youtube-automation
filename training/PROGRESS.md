# Training progress log (tracked; numbers only -- no reference frames)

Each entry: what was tried, on which reference, the score, and what it taught. Scores are `frame_score`
(training/SPEC.md section 1) frame by frame against the real frames. Calibration for reading them is in SPEC.md.

## 2026-09-20 -- ingest of all five references

19,639 frames measured on 12 cores in ~2 minutes; 390 shots (Silent Voice 58, Your Name AMV 149, Garden of Words 38,
Blue Box 82, Fragrant Flower 63). Shot cuts on Fragrant Flower match ffmpeg's detector exactly (63/63). Whisper
(multilingual) transcribed four Japanese-language references; Silent Voice has no speech.
Learned by looking: particle heuristics fail both ways (dappled light, animated logos vs rain), so particles are a
candidate needing visual confirmation; subtitles/logos must be masked in scoring.

## 2026-09-20 -- rung 1 (colour layout) on Fragrant Flower

Measured colour grid -> one vertex-coloured plane in Blender Workbench -> scored. Blender reproduces colours exactly
(200,100,50 -> 200,100,50).

| shot | frames | 6x4 | 16x9 | 32x18 |
|---|---|---|---|---|
| 1 shop sign, static | 27 | 0.478 | 0.542 | 0.581 |
| 4 cake close-up, static | 28 | 0.539 | 0.596 | 0.625 |
| 27 character, static | 57 | 0.538 | 0.591 | 0.630 |

edge_f1 ~ 0 on all: no line work. ~+0.05 per doubling of grid resolution; ceiling of this rung ~0.63, as calibration
predicted (blurred true frame = 0.58-0.62). Skill saved: `exact-colour-vertex-plane-layout` (status reference until a
second video confirms it).

**Next rung (2): line work and silhouettes** -- measured edge/contour polylines as Blender curves or Grease Pencil
strokes over the colour layout, then flat colour regions. Target: edge_f1 from ~0 to >0.4 and frame_score past 0.75.

## 2026-09-20 -- rung 2 (line work) on two videos, and the holdout metric

Measured Canny contours -> flat ribbon quads in Blender over the rung-1 colour layout (training/blender_level2.py).
Added `grad_ssim_holdout` to the scorer because rung 2 traces the same Canny edges the scorer measures: without a holdout the
big `edge_f1` gain would have been the metric agreeing with itself. Calibration on the holdout: blur sigma 25 = 0.556, flat
colour = 0.441, unrelated video = 0.320.

| video / shot | rung 1 score / holdout | rung 2 score / holdout | rung 2 edge_f1 | rung 2 ssim vs rung 1 |
|---|---|---|---|---|
| Fragrant Flower 27 (character) | 0.630 / 0.550 | 0.828 / 0.584 | 0.87 | 0.744 -> 0.709 |
| Blue Box 77 (character) | 0.534 / 0.374 | 0.739 / 0.451 | 0.91 | 0.605 -> 0.531 |
| Blue Box 1 (no face) | 0.561 / 0.507 | 0.746 / 0.557 | 0.90 | 0.671 -> 0.588 |

Sweep on Fragrant Flower 27 (canny, min length, half-width): frame_score 0.785 to 0.851, holdout only 0.561 to 0.584. The best
frame_score (canny 90,180 -> 0.851) is the scorer's own Canny thresholds, not a better recreation; the best holdout is the
thinnest line (0.5 px -> 0.584). Chosen: canny 60,120, min length 10, half-width 0.5.

What it taught: line work gives the big edge_f1 gain but ssim FALLS every time (lines a pixel off, ink too dark), and the
remaining gap is flat cel fills and shading, not lines. Skills: `exact-colour-vertex-plane-layout` promoted to verified
(second video confirmed); `measured-edge-ribbon-line-layer` saved as reference.

**Honest scope note:** rungs 1-2 reconstruct what the pixels are (measured colour grid + traced edges). That is the fidelity
baseline, not creation from scratch. The from-scratch part -- the skill the agent must learn -- is reproducing the same look
from parametric Blender constructs driven by the shot script's `blender_directives` (key/fill lights, world, camera path,
depth of field, glare/vignette, particles), with no reference pixels in the loop. Rung 3 should be that, scored by the same
frame metrics plus feature-level checks (camera path, exposure curve, palette).

## 2026-09-21 -- rung 3 (parametric, from the script alone) on two videos

Blender builds the shot from `shots/shot_NN.json` only -- no reference pixels (training/recreate_level3.py, blender_level3.py):
backdrop with the measured top/middle/bottom band colours (new measured script field `colour.regions`, from the 32x18 grid),
an ellipsoid subject proxy at the face/subject box, a point key toward the measured light direction, world fill, camera on the
measured path keyframes, exposure keyed to the measured curve, compositor vignette + bloom. Coordinate descent over 7 light /
compositor parameters minimises the error between the render's features (measured with describe_frames.measure_lighting)
and the script's numbers. frame_score and holdout are computed afterwards and never tuned against.

| video / shot | frame_score untuned -> tuned | holdout | feature error | exposure-curve MAE |
|---|---|---|---|---|
| Fragrant Flower 27 (character) | 0.419 -> 0.456 | 0.505 -> 0.523 | 5.23 -> 1.18 | 0.177 -> 0.029 |
| Blue Box 77 (character) | 0.310 -> 0.418 | 0.280 -> 0.308 | 4.44 -> 1.44 | 0.265 -> 0.003 |
| Blue Box 1 (no face) | 0.284 -> 0.405 | 0.349 -> 0.380 | 4.33 -> 0.78 | 0.258 -> 0.0004 |

~4 min per shot on 12 cores. Checked: key direction round-trips (0/90/180/270 -> 0/90/180/270), camera shift signs and units
(dx 0.1 -> +0.1 width, dy 0.1 -> +0.177 height = 0.1 frame widths), vignette reaches corner/centre 0.66.
What it taught: the lighting half of the script is reproducible from numbers; the gap to rung 2 (0.74-0.83) is shapes. Largest
residuals are vignette, contrast and p95 -- a flat diffuse scene has no small highlights -- and the single pale subject proxy
(face-box colour is wrong for dark-haired characters). Skill: `script-driven-light-and-exposure-matching` (verified, 2 videos).

**Next:** the vision pass to fill `semantic` (setting, characters, props), so the proxy becomes shapes the script names.

## 2026-09-21 -- rung 4 (semantic character proxy) on Fragrant Flower -- mixed

Vision pass filled `semantic` for all 63 Fragrant Flower shots (reference/<slug>/semantic.json, local). When the semantic pass
lists a character AND a face box exists, the single sphere becomes head (skin) + hair + body, colours measured from the grid
around the face box (new script field `colour.regions.character`). Same tuning loop; `--no-character` is the rung-3 ablation.

| shot | rung 3 frame_score / holdout | rung 4 frame_score / holdout |
|---|---|---|
| FF 27 (black-haired boy) | 0.456 / 0.523 | 0.534 / 0.506 |
| FF 50 (dark-purple-haired girl) | 0.379 / 0.414 | 0.431 / 0.395 |
| FF 32 (blond boy) | 0.568 / 0.609 | unchanged: face detector found 0 faces, no proxy built |

What it taught: right colours in roughly the right places lift frame_score (hist, ssim), but the holdout FALLS on both shots --
ellipsoid outlines sit where the real ones are not. Frame_score alone would have called this a win. Next: silhouette
shape (hair outline, shoulders) and the face detector's misses (use semantic characters when detection is empty).

## 2026-09-21 -- rung 5 (character silhouette learned from feedback) -- small gain, ellipsoid ceiling

training/tune_character_shape.py: rung-4 lights fixed, 8 shape parameters of the head/hair/body proxy tuned by coordinate
descent on mean frame_score of 3 probe frames; holdout never used to accept a step.

| shot | before frame_score / holdout | after frame_score / holdout | edge_f1 |
|---|---|---|---|
| FF 27 | 0.534 / 0.506 | 0.560 / 0.513 | 0.149 -> 0.261 |
| FF 50 | 0.431 / 0.395 | 0.444 / 0.394 | 0.089 -> 0.116 |

What it taught: the gain is almost all edge_f1 (outlines moved toward the real ones); holdout +0.007 on 27, flat on 50, so it
is not only fitting the metric, but three ellipsoids have hit their ceiling (~+0.01-0.03). Next shape step needs a richer
silhouette family (hair outline with spikes/bangs, shoulders), not more tuning of ellipsoids.
