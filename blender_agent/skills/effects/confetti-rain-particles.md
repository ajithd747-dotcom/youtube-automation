---
id: confetti-rain-particles
name: Confetti rain with turbulence and a glowing title finale
category: effects
kind: recipe
status: verified
applies_to:
- cinematic
when_to_use: An ending, thanks, celebration, call to action (like/subscribe), success moment.
triggers:
- thanks
- subscribe
- like
- celebration
- confetti
- ending
- outro
- congratulations
- cheers
- hooray
uses_recipe: finale_confetti
exemplar: exemplars/finale_confetti.mp4
tags:
- particles
- recipe
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
Robot cheers under a glowing 3D title while coloured chips rain down.

## Procedure
1. Recipe `finale_confetti`, mood `night`.
2. Five hidden chip meshes (cube 0.3 x 0.02 x 0.19, emissive 0.6, one hue each). One plane emitter (10 x 6 m) at z 9.5 with 5 particle systems, each: count 150, `frame_start 1`, `frame_end T-1 s`, lifetime 140, `normal_factor -0.8`, random 0.8, gravity weight 0.06 (floaty), rotations on with random angular velocity 6.
3. `bpy.ops.object.effector_add(type="TURBULENCE")` strength 3, size 1.5 above the scene so the chips flutter.
4. Colored rim lights (magenta and cyan area lights) + a top spot make the robot readable in the dark.
5. Title `title_3d(..., loc=(0, 2, 4.5))`; camera pulls back (10.5 -> 8.6 m) with the robot centred at z ~2.

## Pitfalls
- Chips smaller than ~0.15 m vanish at 720p; 0.3 m reads as confetti.
- Title placed at z 3.6 collided with the raised arms; 4.5 clears them.
