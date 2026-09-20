---
id: wall-smash-destruction
name: Steel ball smashes a wall of crates in slow motion
category: physics
kind: recipe
status: verified
applies_to:
- cinematic
when_to_use: A climax, impact, crash, collapse, demolition, or 'everything comes crashing down' moment.
triggers:
- smash
- crash
- crashing down
- destroy
- collapse
- wall
- demolish
- impact
- knock down
- tower
- break
uses_recipe: crate_smash
exemplar: exemplars/crate_smash.mp4
tags:
- rigid body
- recipe
- slow motion
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
A 5x7 wall of wooden crates is hit by a heavy steel ball; crates tumble and scatter, camera shakes on impact.

## Procedure
1. Recipe `crate_smash`, mood `sunset` (warm backlight reads best; `night` is too dark).
2. Crates 0.6 m cubes with bevel 0.03, wood PBR (`#a9743f`, roughness 0.65), mass 0.8, friction 0.6, bounce 0.05, margin 0.001; world substeps 15, iterations 25, time_scale 0.75 (slow motion).
3. Ball: 1.5 m diameter chrome (metallic 1, roughness 0.12), 60 kg, launched with constant speed (see rigid-body-launch-release), contact at ~1.5 s.
4. Camera: slow dolly right (-2 -> +3.5 m), lens 36 mm, f/2.4, plus decaying shake `a = 0.18 * exp(-k/6)` over 0.7 s from the impact frame.
5. Pre-step the physics before rendering.

## Pitfalls
- Everything stayed frozen in the first render (no pre-step); see rigid-body-render-prestep.
- Spot light from above (14000 W, 55 deg) gives crisp shadows on the debris; without it the pile is muddy.
- Keep the impact >= 1 s after the start so viewers see the setup, and >= 2.5 s before the end so the scatter can settle.
