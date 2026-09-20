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
