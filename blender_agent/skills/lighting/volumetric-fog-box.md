---
id: volumetric-fog-box
name: Haze and light shafts using a bounded volume box
category: lighting
kind: technique
status: verified
applies_to:
- cinematic
- 3d
when_to_use: 'Atmosphere: fog, haze, dusty air, god rays, spotlight beams in a workshop or night scene.'
triggers:
- fog
- haze
- light shaft
- god rays
- beam
- dusty
- atmosphere
- mist
- spotlight
- smoke-filled
test: tests/fog_box.py
tags:
- volumetrics
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
1. Add a large cube (e.g. centre (0, 8, 6), size 46 x 46 x 12), display WIRE, `visible_shadow = False`.
2. Material: Volume output <- Principled Volume, density 0.004-0.012 (`0.01 * fog`), anisotropy 0.3.
3. `scene.eevee.volumetric_end = 70`; quality presets: tile size 8 (draft) / 4 (standard) / 2 (final), 48 samples.
4. A SPOT light (9000-16000 W, 40-55 deg) aimed through the box makes visible cones.

## Pitfalls
- A **world** volume rendered pure black on this iGPU under EEVEE Next. Use the box.
- Density > 0.012 over 46 m washes the frame out; the intro shot looked like milk at 0.8*0.01 with a bright sky.
- Fog adds only a small per-frame cost, but its look differs between draft and final quality: judge it in a still at the target quality.
