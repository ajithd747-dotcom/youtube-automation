---
id: exact-colour-vertex-plane-layout
name: Exact-colour layout from a measured grid - vertex-coloured plane in Workbench
category: materials
kind: technique
status: reference
applies_to:
- any
when_to_use: Rebuilding the colour layout (sky/mid/low bands, gradients, light falloff) of a reference frame in Blender with
  no invented lighting, as the first rung of a frame-by-frame recreation; or any time colours must come out of Blender exactly.
triggers:
- colour layout
- reference frame
- vertex colour
- exact colour
- workbench flat
- colour grid
- recreate frame
tags:
- recreation
- colour
- workbench
source:
- 'own-experience: rung 1 of training/SPEC.md on the Fragrant Flower trailer, 2026-09-20 (training/PROGRESS.md)'
version: 1
---
## Procedure

1. Measure a colour grid per frame from the reference (mean RGB per cell, letterbox removed): training/measure_colour_grid.py writes 32x18; coarser grids are area-averaged from it.
2. Build ONE plane whose vertices sit at the cell centres plus a border ring at the plane edge carrying the edge cell's colour, so vertex colours interpolate smoothly and the picture reaches the edges.
3. Orthographic camera at z=2 framing the plane exactly (ortho_scale = width/height of the picture); resolution equals the reference analysis size.
4. Render with Workbench, light FLAT, colour type VERTEX, view transform Standard, look None, anti-aliasing off. Nothing is lit, so no lighting is invented.
5. Per frame only overwrite the FLOAT_COLOR point attribute (convert sRGB to linear first) and render; a whole shot renders in seconds.

```python
import bpy
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
shading = scene.display.shading
shading.light, shading.color_type = "FLAT", "VERTEX"
scene.display.render_aa = "OFF"
attr = bpy.context.object.data.color_attributes.new("col", "FLOAT_COLOR", "POINT")
```

## Parameters that worked

Fidelity: a plane painted (200,100,50) and (30,160,220) rendered back as exactly (200,100,50) and (30,160,220). Scores (frame_score, 0..1 against the real frames, training/score_recreation.py), three shots of one trailer, frame-by-frame over 27-57 frames each:
grid 6x4: 0.478 / 0.539 / 0.538;  grid 16x9: 0.542 / 0.596 / 0.591;  grid 32x18: 0.581 / 0.625 / 0.630.
Each doubling of resolution bought about +0.05; edge_f1 stayed ~0 because there is no line work. This matches calibration (blur of the true frame scores 0.58-0.62), so 0.63 is the ceiling of this rung.

## Pitfalls

- Colour-managed views (Filmic/AgX) shift every colour; Standard is required for exact output.
- Vertex colours are scene-linear in FLOAT_COLOR attributes: feed sRGB values through the sRGB-to-linear curve or the picture comes out too bright.
- Burned-in subtitles and logos get averaged into the grid; mask the lower band when scoring (score_recreation.py does when the reference measured subtitles).
- Do not read a rising score as a better recreation of drawing: this rung only reproduces blurred colour. The next gain has to come from edges/silhouettes.

## Evidence

training/PROGRESS.md, entry 2026-09-20 rung 1. Runs: training/runs/<slug>/level1_shotNN_<grid>/ (local, gitignored). Confirmed on three shots (sign, cake close-up, character); needs a second video before promotion to verified.
