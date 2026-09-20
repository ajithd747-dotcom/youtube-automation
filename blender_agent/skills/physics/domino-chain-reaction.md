---
id: domino-chain-reaction
name: Colourful domino chain reaction with a trailing camera
category: physics
kind: recipe
status: verified
applies_to:
- cinematic
when_to_use: The script talks about a chain reaction, one small push causing a cascade, momentum, cause and effect,
  or a row of things falling one after another.
triggers:
- domino
- chain reaction
- one small push
- cascade
- topples
- one after another
- momentum
- ripple effect
- domino effect
uses_recipe: domino_run
exemplar: exemplars/domino_run.mp4
tags:
- rigid body
- recipe
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
A winding row of pastel dominoes toppling in a wave (rigid body), lit by a low sun, with the camera following the fall front.

## Procedure
1. Use recipe `domino_run` (mood `sunset` or `day`, dark floor `#3b414f`, fog <= 0.15).
2. Dominoes: cube scale (0.12, 0.5, 1.0), spacing 0.58 m along an S-curve `y = 1.6 sin(0.42 x)`, hue ramp 0-0.85 across the row, each rotated to the path tangent.
3. Physics: mass 0.25, friction 0.55, bounce 0.05, collision margin 0.0005, world substeps 20, solver iterations 30, time_scale 1.0.
4. Trigger with a red glossy ball (see rigid-body-launch-release) hitting domino 0 at t = 0.9 s.
5. Camera trails the wave: target empty copies a keyed lead empty that reaches the last domino at `1.2 + 0.17 * n` seconds.
6. Pre-step frames before rendering (see rigid-body-render-prestep).

## Parameters that worked (measured)
- The wave travels one domino per ~0.17 s; first domino falls at ~1.7 s. 26 dominoes finish at ~5.7 s, so 26 fits a 7-8 s narration; 34 needs ~9 s.
- Lens 42 mm, f/2.2, camera 5 m from the row at z 1.2-1.7.

## Pitfalls
- White/cream floor + day sun + fog = washed-out, unreadable dominoes; use a dark floor and backlight.
- If the camera schedule is shorter than the fall time the camera ends before the wave does: schedule = measured wave time.
