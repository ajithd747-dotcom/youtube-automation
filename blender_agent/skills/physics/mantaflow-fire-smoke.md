---
id: mantaflow-fire-smoke
name: Real simulated fire + smoke with Mantaflow (campfire recipe)
category: physics
kind: recipe
status: verified
applies_to:
- cinematic
when_to_use: The script has fire, a campfire, flames, smoke, embers, warmth at night, burning.
triggers:
- fire
- campfire
- flames
- smoke
- embers
- burning
- bonfire
- warm
- torch
- cozy
source:
- 'own-experience: fx recipes (Blender 4.5 Mantaflow / hair particles, 2026-09-19)'
version: 1
uses_recipe: campfire_smoke
tags:
- mantaflow
- fire
---
## Procedure (recipe `campfire_smoke`, cine_recipes_fx.py)
1. Domain: cube scaled (5, 5, 6.8) at (0, 4, 3.4) with a Fluid modifier `DOMAIN`, `domain_type='GAS'`, `resolution_max` 40 (draft) / 64 (standard) / 96 (final), `use_noise=False`, `beta=1.6` (buoyancy), `cache_directory` in `bpy.app.tempdir`, cache frames 1..N.
2. **The flow object must lie INSIDE the domain** (a source below the domain floor emits nothing: the first test rendered no smoke). Flow: small ellipsoid, Fluid `FLOW`, `flow_type='BOTH'`, `flow_behavior='INFLOW'`, `flow_source='MESH'`, temperature 2.4, density 1, fuel 1; `hide_render=True`.
3. Domain material: ONLY a volume material (clear the mesh's material slots first): Principled Volume, Density 6, Color `#3a3532`, Blackbody Intensity 1.4.
4. Flicker: point light `#ff8a3c` keyed every 2 frames, energy 900 x (0.75..1.25). Embers: 90 particles from an ico-sphere, instanced emissive sphere (emission 12), gravity weight -0.15.
5. `bpy.ops.fluid.bake_all()` at the end of the recipe (active object = domain). Camera 32 mm f/2.8, slow push in.
## Measured (this laptop)
Bake: res 64 x 96 frames = 44 s; res 40 draft ~20 s; render at 480x270 draft 5.7 s/frame, so a 5 s shot at 720p is ~15 min. Cache 2.8 MB.
## Pitfalls
- A domain that keeps a surface material renders as a solid slab.
- `bpy.ops.object.quick_smoke` does nothing in background mode: set the domain/flow up by hand.
