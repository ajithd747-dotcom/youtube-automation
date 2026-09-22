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
- contrast grade
- render looks flat
- no dark shadows
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
version: 3
---
## Procedure

1. Key = POINT light (not sun) placed off-screen toward the script's `lighting.key_direction_screen_deg` (0 = right, 90 = down),
   9 units from a backdrop 10 units from the camera. A sun lights a flat backdrop evenly and cannot produce a screen-space
   gradient; the point light's falloff does. Measured round trip: requested 0/90/180/270 deg -> measured 0/90/180/270.
2. Fill = world background, colour = NEUTRAL GREY at the middle-band colour's Rec. 709 luma (`blender_level3.neutral_of`),
   strength tuned. Never tint the fill with the measured colour: every surface it lights already carries a measured
   colour, so a tinted fill applies it twice -- renders came out 1.48x the script's chroma on Blue Box (81 of 86 shots),
   1.24x on Fragrant. Neutral fill: 1.10x / 1.15x, hue error -10 %, holdouts unchanged (2026-09-22).
3. Exposure: key `scene.view_settings.exposure` at every `lighting.exposure_luma.keyframes` frame. Correct each key by
   `0.7 * 2.2 * log2(target_luma / rendered_luma)` stops, keep the offsets zero-mean and move the mean into the base exposure.
4. Vignette (Blender 4.5 compositor): Ellipse Mask Size (0.95, 0.95) -> Blur, Size socket = 0.2 x frame size in px -> Mix
   MULTIPLY with Fac = strength. Fac 0.9 gives corner/centre 0.66. In 4.5 the blur size is the `Size` socket, not `factor_x`.
5. Contrast: grade LUMINANCE ONLY -- RGB-to-BW, then `pivot * (luma / pivot) ** gamma`, and multiply the image by
   `graded / luma`. Pivot = the shot's measured median luma (converted to linear), so the grade leaves the exposure curve
   alone and only the tails move. Never gamma the channels: a per-channel power raises the channel ratios, which is
   saturation -- on Blue Box 46 it fixed tone (luma_std error 2.62 -> 0.29) while pushing lab_b error 3.02 -> 8.25, worse
   overall. Luminance-only moved lab_b the right way (3.02 -> 2.43) for the same tone gain.
6. Tune key energy, fill strength, key angle, key elevation, exposure, bloom, vignette and contrast by coordinate descent (+-step each,
   halve the step when nothing improves), rendering at 320x180 and measuring with `training/describe_frames.measure_lighting`,
   the same function that measured the reference.
   PAIR each contrast move with the exposure fit that answers it, and judge the pair. A contrast move shifts the mean
   luma, and the exposure-curve term (double weight, scale 0.03) punishes that before the exposure fit gets its own turn:
   greedy single moves left contrast at 1.0 on 13 of 14 probe shots. Any two parameters coupled this way need the same
   treatment -- the search is greedy, so a move that only pays off after a second move is never taken.
7. Camera: `shift_x = -dx`, `shift_y = dy`, lens x (1 + zoom), roll about the view axis. The script's dx/dy are image shifts in
   frame WIDTHS for both axes, which is exactly Blender's shift unit (verified: dy 0.1 moves the image 0.177 of the height at 16:9).

## Evidence

| shot | frame_score untuned -> tuned | holdout | feature error | exposure-curve MAE |
|---|---|---|---|---|
| Fragrant Flower 27 | 0.419 -> 0.456 | 0.505 -> 0.523 | 5.23 -> 1.18 | 0.177 -> 0.029 |
| Blue Box 77 | 0.310 -> 0.418 | 0.280 -> 0.308 | 4.44 -> 1.44 | 0.265 -> 0.003 |
| Blue Box 1 (no face) | 0.284 -> 0.405 | 0.349 -> 0.380 | 4.33 -> 0.78 | 0.258 -> 0.0004 |
| Blue Box 2, contrast 1.56 | - | - | 2.40 -> 1.62 | - |
| Blue Box 46, contrast 1.56 | - | - | 2.06 -> 1.73 | - |

frame_score and holdout are never tuned against; both rose.

## Limits

The subject proxy is one ellipsoid coloured from the face box, which is wrong for dark-haired characters (renders pale).
Highlight p95 and vignette stay the largest residuals: a flat diffuse scene has no small bright highlights.
The tuner has no colour parameter: lab_a/lab_b are in the feature error but no tuned value can move them, so colour is
only as right as the measured material colours and a neutral fill make it.

The contrast grade closes only 16-26% of the tone gap (14 Blue Box shots, 2026-09-22): luma_std gap -0.062 -> -0.052,
p5 +0.096 -> +0.079, dark share -0.053 -> -0.039, holdout flat at 0.4201. The tuner is at its own optimum, not stuck --
a sweep on BB 46 put the best at 1.4 and it chose 1.5625 -- because `top_minus_bottom` error climbs as the grade
stretches the vertical lighting gradient. The darks that are still missing are ink strokes the scene has no geometry
for: a tone curve can imitate line art but cannot draw it. Expect the rest of this gap from line art, not from lighting.
