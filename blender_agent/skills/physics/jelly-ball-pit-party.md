---
id: jelly-ball-pit-party
name: Jelly blobs and a rain of colourful balls under neon light
category: physics
kind: recipe
status: verified
applies_to:
- cinematic
when_to_use: Fun, play, party, bounce, energy, colourful chaos, celebration of motion.
triggers:
- party
- bounce
- jelly
- balls
- colourful
- colorful
- playful
- energy
- fun
- wobbling
- bouncing
uses_recipe: jelly_pit
exemplar: exemplars/jelly_pit.mp4
tags:
- recipe
- soft body
- rigid body
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
5 soft-body jellies and 34 rigid balls (radius 0.28-0.5) fall into a pile on a mirror floor lit by magenta/cyan light.

## Procedure
1. Recipe `jelly_pit`, mood `neon` (uses the stripe world, see studio-softbox-stripe-world).
2. Balls: rigid sphere, mass = 2r, friction 0.5, restitution 0.5, spawned at z = 5 + 0.55 i so they rain in sequence; rigid world substeps 10, iterations 20; floor passive with restitution 0.35.
3. Camera 34 mm, f/2.4 from (-6.5, -9, 3) to (6, -9.5, 2.2) looking at (0, 1.5, 1).
4. Pre-step frames (rigid-body-render-prestep) - otherwise the balls never appear.

## Pitfalls
- The neon stripe world is very bright behind the pile: expect a blurry busy backdrop at f/2.4; use f/4+ if the background competes with the action.
