---
id: simulation-cost-and-bake-rules
name: 'Budget simulation shots: bake once, fewer voxels in draft, keep sims short'
category: performance
kind: rule
status: verified
applies_to:
- any
when_to_use: Adding fluid, smoke, hair or cloth simulations to a plan.
triggers:
- bake
- simulation cost
- mantaflow
- fluid
- resolution
- cache
- simulation time
- fire
- liquid
source:
- 'own-experience: fx recipes (Blender 4.5 Mantaflow / hair particles, 2026-09-19)'
version: 1
tags:
- simulation
---
## Rules
- Bake inside the recipe (build time) - each Blender process re-bakes: keep resolution at 40 for draft/QA, 64 standard, 96 final.
- Domain frames = shot frames (`cache_frame_end = STATE['frames']`); the render then plays the cache.
- Shots longer than ~6 s multiply bake time: cut sims into 4-5 s beats.
- Budget (720p standard): smoke ~3 s/frame + bake 45 s; liquid ~4 s/frame + bake 1-2 min; hair ~1.5x a plain shot.
- QA stills of sim shots take 20-50 s each because of the bake.
