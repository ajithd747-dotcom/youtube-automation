---
id: physics-timing-calibration
name: Measure the simulation before scheduling cameras and shot lengths
category: physics
kind: rule
status: verified
applies_to:
- cinematic
- 3d
when_to_use: Any physics event whose duration is not obvious (chain reactions, piles, cloth settling).
triggers:
- timing
- calibrate
- measure
- how long
- simulation time
- schedule
- physics timing
tags:
- physics
- qa
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
1. Build the recipe in a probe script with the real parameters; step frames with `frame_set` and record when each object crosses a threshold (e.g. domino height < 0.42 m).
2. Derive: first event time, per-item speed, last event time.
3. Set the camera/lead-empty schedule and the number of items from these numbers (domino: 1.7 s lead, 0.17 s each).
4. Re-measure if substeps, mass, spacing or time_scale change.
