---
id: studio-softbox-stripe-world
name: Studio / neon environment with procedural softbox stripes
category: lighting
kind: technique
status: verified
applies_to:
- cinematic
- 3d
when_to_use: Glass, gold, chrome, mirror floors or product shots in an empty dark world; neon club looks.
triggers:
- glass
- chrome
- gold
- metal
- reflection
- mirror
- product
- showcase
- studio
- shiny
- neon
- refraction
test: tests/studio_world_stripes.py
exemplar: exemplars/glass_showcase.mp4
tags:
- reflections
- world
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
Reflective and refractive objects finally look like glass/metal because they reflect a structured bright environment.

## Procedure
1. World shader: base dark colour + 2 Wave textures (BANDS, X and Y directions, scale 5 and 3) from Generated coordinates -> ColorRamp (0 at 0.86, colour x gain 3-5 at 0.95) -> ADD-mixed onto the base. Studio stripes white/cool-white; neon stripes magenta `#ff2fb3` / cyan `#22d3ff`.
2. Floor: roughness 0.05, metallic 0.4 (mirror-like) so objects double in the floor.
3. Materials: glass transmission 1.0, IOR 1.5, roughness 0.02; gold metallic 1, roughness 0.15, `#d4af37`; chrome `#e8e8ee` metallic 1 roughness 0.02.
4. Lights: 3 area lights (900 W white key, 350 W cool fill, 600 W warm back).

## Pitfalls
- A black world makes chrome black. Emissive panels placed off-screen do **not** appear in EEVEE Next reflections (screen-space tracing + world probe only), the stripes must live in the *world*.
- Hard black/white stripes read as "test pattern" on glass; keep gains moderate and add a glowing crystal for colour.
