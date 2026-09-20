---
id: measured-edge-ribbon-line-layer
name: Line work as flat ribbons over a colour layout - measured Canny contours in Workbench
category: style-2d
kind: technique
status: reference
applies_to:
- any
when_to_use: Adding the line art (ink outlines, silhouettes, brick and window lines) of a reference frame on top of an exact colour
  layout in Blender, when recreating an anime or cel-style frame and edge agreement is what is missing.
triggers:
- line work
- ink lines
- edge contours
- outline
- silhouette
- recreate frame
- canny
tags:
- recreation
- lines
- workbench
source:
- 'own-experience: rung 2 of training/SPEC.md on Fragrant Flower and Blue Box, 2026-09-20 (training/PROGRESS.md)'
version: 1
---
## Procedure

1. Measure contours from the reference frame: Canny on the blurred grey frame, drop connected components shorter than 10 px, trace with findContours, simplify with approxPolyDP (epsilon 0.8 px). Mask burned-in subtitles and logos out first: they are overlays, not animation.
2. Give each polyline an ink colour sampled from the frame itself (blurred pixel at the polyline midpoint, multiplied by 0.35) so lines are darker than the fill they sit on.
3. Turn every segment into one flat quad ("ribbon") of half-width 0.5 to 0.75 px, all in ONE mesh with per-vertex colours, 0.01 above the colour plane. Workbench draws it flat; Blender curves are not needed and a per-frame rebuild takes milliseconds.
4. Rebuild only the two meshes per frame and render; a 57-frame shot renders in about a minute.

```python
import numpy as np

def ribbon_corners(a, b, half_width):
    d = b - a
    n = np.stack([-d[:, 1], d[:, 0]], axis=1) / np.hypot(d[:, 0], d[:, 1])[:, None] * half_width
    return np.stack([a + n, a - n, b - n, b + n], axis=1)
```

## Parameters that worked

Rung 1 to rung 2 (frame_score, edge_f1, holdout gradient-SSIM): Fragrant Flower character shot 0.630, 0.03, 0.550 to 0.828, 0.87, 0.584 (half-width 0.5); Blue Box shot 77 0.534, 0.00, 0.374 to 0.739, 0.91, 0.451; Blue Box shot 1 0.561, 0.00, 0.507 to 0.746, 0.90, 0.557. About 1200 to 3100 segments per frame.

## Pitfalls

- frame_score rises mostly through edge_f1, which the scorer computes with Canny (80,160): tracing with Canny (90,180) reached 0.851 by matching the scorer, while the holdout stayed 0.57. Judge line settings by the holdout (grad_ssim_holdout), not by frame_score.
- ssim FELL on every shot (0.744 to 0.700; 0.605 to 0.531; 0.671 to 0.588): thin lines a pixel off the true ones and darker than the true ink cost structure. More or thicker lines make it worse (half-width 1.0 held 0.561 holdout vs 0.584 at 0.5).
- The fills are still blurred colour, not flat cel fills; the biggest remaining gap is the flat regions and shading, not the lines.
- Tracing measured edges is a reconstruction of what is on screen, not creation from scratch: it is a fidelity baseline. The from-scratch skill is building the same look from parametric Blender constructs (lights, materials, camera, particles).

## Evidence

training/PROGRESS.md entries 2026-09-20 rung 2. Runs in training/runs/<slug>/level2_* (local, gitignored). Confirmed on two videos; kept at reference status because the ssim regression is unresolved.
