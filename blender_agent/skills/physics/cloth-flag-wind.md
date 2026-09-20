---
id: cloth-flag-wind
name: Flag / banner rippling in the wind (cloth simulation)
category: physics
kind: recipe
status: verified
applies_to:
- cinematic
when_to_use: 'Flags, banners, curtains, capes, sails, or anything cloth-like moved by wind: victory, pride, unfurling.'
triggers:
- flag
- banner
- wind
- cloth
- fabric
- unfurl
- ripple
- flutter
- victory
- pride
- curtain
- sail
uses_recipe: cloth_banner
test: tests/cloth_wind.py
exemplar: exemplars/cloth_banner.mp4
tags:
- cloth
- wind
- recipe
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
A striped banner pinned to a pole flaps naturally: waves travel along it, the free edge droops and lifts.

## Procedure
1. Recipe `cloth_banner` (mood `day`, fog 0.2).
2. Grid plane 46x26 subdivisions, size 5x3 m; rotate to stand in the XZ plane, then **apply the transform**.
3. Vertex group `pin` with weight 1 on the left edge only (`x < x_min + 0.02`); `cloth.settings.vertex_group_mass = "pin"`.
4. Settings: quality 8, mass 0.15, air_damping 2.5, gravity (0, 0, -3) (lighter than real cloth so it flies), tension = compression stiffness 25, bending 1.2, self-collision off.
5. Wind: `bpy.ops.object.effector_add(type="WIND", rotation=(-pi/2, 0, radians(-70)))` -> blows mostly along +X (along the banner) with a 34% push into it; strength keys 0 -> 260 (0.6 s) -> 420 (mid) -> 300, noise 1.2.
6. Add a Subsurf (level 1) after the Cloth modifier. Wave texture (BANDS, direction **Z**, scale 2.2) -> constant ColorRamp gives the stripes.

## Pitfalls
- An empty has no force field: use `bpy.ops.object.effector_add`; `empty.field` is None otherwise.
- The wind vector is the effector's local **Z** axis. Wind perpendicular to the cloth only inflates it into a sail (y range 4 m, x shrinks to the pole); wind purely along the cloth stretches it flat. 70 deg between them ripples.
- Strength 650+ with mass 0.25 crumples the cloth to the pole; 90-170 with real gravity leaves it hanging like a curtain.
- Stripes direction depends on the plane orientation; on an XZ banner use bands along Z (Y bands give a solid colour).
