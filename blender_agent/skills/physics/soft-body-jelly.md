---
id: soft-body-jelly
name: Wobbling translucent jelly (soft body)
category: physics
kind: technique
status: verified
applies_to:
- cinematic
when_to_use: Jelly, gel, rubber, squishy or bouncy blobs that deform on impact.
triggers:
- jelly
- wobble
- squishy
- rubber
- gel
- bouncy
- soft
- blob
- jiggle
test: tests/soft_body_jelly.py
tags:
- soft body
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
An ico-sphere squashes on landing and wobbles back, with a glassy jelly material.

## Procedure
1. `primitive_ico_sphere_add(subdivisions=3, radius=0.75)` (642 verts: enough to deform smoothly; more is slow).
2. Add a SOFT_BODY modifier: mass 1, friction 0.6, `use_goal=False`, `use_edges=True`, pull 0.35, push 0.35, bend 0.6, damping 0.35, self-collision off.
3. The floor needs a **Collision** modifier (in addition to any rigid-body passive setting) or the jelly falls through.
4. Set the soft-body point cache range to the shot length.
5. Material: Principled, transmission 0.85, IOR 1.35, roughness 0.12, small emission 0.6 in the same hue.

## Pitfalls
- Soft bodies do not collide with each other unless self-collision/collision modifiers are set up; keep them apart.
- Extreme deformation from a drop above ~6 m: drop from 2-4 m.
