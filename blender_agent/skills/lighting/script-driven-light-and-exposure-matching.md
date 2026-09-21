---
id: script-driven-light-and-exposure-matching
name: Match a shot's measured lighting from its script alone - point key, world fill, keyed exposure, compositor vignette/bloom
category: lighting
kind: technique
status: verified
applies_to:
- any
when_to_use: Building a shot from its per-frame script (no reference pixels) and the render's exposure curve, contrast, light
  direction and vignette must match the script's measured lighting numbers.
triggers:
- exposure curve
- key light direction
- match lighting
- recreate shot
- vignette
- from scratch
tags:
- recreation
- lighting
- cycles
- compositor
source:
- 'own-experience: rung 3 of training/SPEC.md on Fragrant Flower shot 27 and Blue Box shots 77 and 1, 2026-09-21 (training/PROGRESS.md)'
version: 1
---
## Procedure

1. Key = POINT light (not sun) placed off-screen toward the script's `lighting.key_direction_screen_deg` (0 = right, 90 = down),
   9 units from a backdrop 10 units from the camera. A sun lights a flat backdrop evenly and cannot produce a screen-space
   gradient; the point light's falloff does. Measured round trip: requested 0/90/180/270 deg -> measured 0/90/180/270.
2. Fill = world background, colour = middle-band colour, strength tuned.
3. Exposure: key `scene.view_settings.exposure` at every `lighting.exposure_luma.keyframes` frame. Correct each key by
   `0.7 * 2.2 * log2(target_luma / rendered_luma)` stops, keep the offsets zero-mean and move the mean into the base exposure.
4. Vignette (Blender 4.5 compositor): Ellipse Mask Size (0.95, 0.95) -> Blur, Size socket = 0.2 x frame size in px -> Mix
   MULTIPLY with Fac = strength. Fac 0.9 gives corner/centre 0.66. In 4.5 the blur size is the `Size` socket, not `factor_x`.
5. Tune key energy, fill strength, key angle, key elevation, exposure, bloom and vignette by coordinate descent (+-step each,
   halve the step when nothing improves), rendering at 320x180 and measuring with `training/describe_frames.measure_lighting`,
   the same function that measured the reference.
6. Camera: `shift_x = -dx`, `shift_y = dy`, lens x (1 + zoom), roll about the view axis. The script's dx/dy are image shifts in
   frame WIDTHS for both axes, which is exactly Blender's shift unit (verified: dy 0.1 moves the image 0.177 of the height at 16:9).

## Evidence

| shot | frame_score untuned -> tuned | holdout | feature error | exposure-curve MAE |
|---|---|---|---|---|
| Fragrant Flower 27 | 0.419 -> 0.456 | 0.505 -> 0.523 | 5.23 -> 1.18 | 0.177 -> 0.029 |
| Blue Box 77 | 0.310 -> 0.418 | 0.280 -> 0.308 | 4.44 -> 1.44 | 0.265 -> 0.003 |
| Blue Box 1 (no face) | 0.284 -> 0.405 | 0.349 -> 0.380 | 4.33 -> 0.78 | 0.258 -> 0.0004 |

frame_score and holdout are never tuned against; both rose.

## Limits

The subject proxy is one ellipsoid coloured from the face box, which is wrong for dark-haired characters (renders pale).
Highlight p95 and vignette stay the largest residuals: a flat diffuse scene has no small bright highlights.
