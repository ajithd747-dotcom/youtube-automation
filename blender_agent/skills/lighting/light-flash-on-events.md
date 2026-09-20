---
id: light-flash-on-events
name: Flash a light at bursts and impacts
category: lighting
kind: technique
status: verified
applies_to:
- cinematic
- 3d
when_to_use: Explosions, fireworks, camera flashes, lightning, magic zaps.
triggers:
- flash
- burst
- explosion
- lightning
- zap
- firework
- illuminate
- spark
exemplar: exemplars/fireworks.mp4
tags:
- lighting
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
POINT light at the event; key `light.data.energy`: 0 at t-0.02 s, peak at t, 0 at t+0.35 s (frames via `frame(t)`). Peak 60000 W for a burst 20 m away over a mirror lake; scale with distance squared. The flash lights fog and water, which sells the size of the burst.

## Pitfalls
- 250000 W washed the whole frame purple.
