---
id: force-fields-wind-turbulence
name: Wind / turbulence force fields need the effector operator
category: physics
kind: pitfall
status: verified
applies_to:
- cinematic
- 3d
when_to_use: Any simulation (cloth, particles, smoke) that should be pushed by wind, gusts or turbulence.
triggers:
- wind
- gust
- turbulence
- breeze
- blow
- force field
- swirl
- air
tags:
- effector
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
1. Create with `bpy.ops.object.effector_add(type="WIND"|"TURBULENCE"|"VORTEX", location=..., rotation=...)`, then use `bpy.context.active_object.field`.
2. Animate `field.strength` with `field.keyframe_insert("strength", frame=...)` for gusts (ramp in over ~0.6 s).
3. Direction of a WIND field is its local +Z axis: choose the rotation so Z points where the air should go.

## Pitfalls
- `L.empty(...)` objects have `field = None`; setting `.field.type` raises AttributeError.
- Wind acts on cloth/particles/soft bodies, not on rigid bodies unless their effector weights allow it.
