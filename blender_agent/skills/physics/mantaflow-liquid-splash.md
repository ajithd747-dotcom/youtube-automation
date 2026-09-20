---
id: mantaflow-liquid-splash
name: Liquid splash into a pool with refraction (water recipe)
category: physics
kind: recipe
status: verified
applies_to:
- cinematic
when_to_use: Water, drops, splashes, a pool, drinks, rain, ocean-like calm liquid.
triggers:
- water
- splash
- liquid
- drop
- pool
- rain
- drink
- wave
- pour
- ocean
- puddle
source:
- 'own-experience: fx recipes (Blender 4.5 Mantaflow / hair particles, 2026-09-19)'
version: 1
uses_recipe: water_splash
tags:
- mantaflow
- liquid
---
## Procedure (recipe `water_splash`)
1. Domain cube (4.4, 4.4, 3.0) at (0, 4, 1.5), `domain_type='LIQUID'`, `resolution_max` 40/56/80, `use_mesh=True` (the surface mesh is what renders), `time_scale=0.8` for slow motion.
2. Initial fluid = flow objects with `flow_type='LIQUID'`, `flow_behavior='GEOMETRY'`: a slab (pool, 4.2 x 4.2 x 0.9) and three spheres (drops) above it; all `hide_render=True`.
3. Material on the domain (the liquid mesh): Principled transmission 1, IOR 1.33, roughness 0.03, tint `#cfe8ff` - clear the other slots first.
4. Studio-stripe world + 2 area lights so the refraction has something to bend; camera low and to the side (lens 38, f/3.2) moving 3 m.
5. `bpy.ops.fluid.bake_all()`. Measured: draft bake + still ~51 s.
## Pitfalls
- Needs ray tracing for refraction; drops at 0.5 m in a 4.4 m domain at res 56 give ~8 cm voxels - splashes are soft; use res 80 for hero shots.
- Fewer than 2 s of simulation looks like a static pool: give the drops 1.7-2.4 m of fall.
