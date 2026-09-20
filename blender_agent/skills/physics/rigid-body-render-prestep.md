---
id: rigid-body-render-prestep
name: Make rigid-body physics actually play in a headless render
category: physics
kind: pitfall
status: verified
applies_to:
- cinematic
- 3d
when_to_use: Any shot with rigid bodies (falling, colliding, toppling, piling objects) rendered with `bpy.ops.render.render(animation=True)`
  in background mode.
triggers:
- rigid body
- physics
- falling
- collide
- topple
- domino
- crash
- pile
- bounce
- drop
- collapse
- gravity
test: tests/rigid_prestep.py
tags:
- headless
- cache
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
Rigid-body objects really move in the rendered video instead of hanging frozen (the ball rolls but nothing it hits ever reacts).

## Procedure
1. Build the scene, add the rigid body world (`C.rigid_world()`), objects (`C.rigid(...)`), keyframes.
2. BEFORE rendering, step every frame once in order, then rewind:
   `for f in range(sc.frame_start, sc.frame_end + 1): sc.frame_set(f)` then `sc.frame_set(sc.frame_start)`.
3. Render the animation as usual: the render reads the physics cache that step 2 filled.
4. For a single still at time t you must also step frames 1..t in order (`frame_set` straight to t shows the initial pose).

## Pitfalls
- Rigid-body simulation only runs in the *active* (viewport) depsgraph; the render depsgraph replays a cache. Without step 2 nothing simulates. Cloth and particle systems were observed to render correctly without it; rigid bodies and soft bodies stayed frozen (jellies hovered in the first jelly render).
- Reading `matrix_world` inside a `render_pre` handler did not show the simulated pose in my tests: judge by the rendered frames.
- This cost me one full re-render of 4 shots (~40 min) - the pre-step costs about 2 s.

## Code
```python
sc = bpy.context.scene
for f in range(sc.frame_start, sc.frame_end + 1):
    sc.frame_set(f)          # fills the rigid-body point cache
sc.frame_set(sc.frame_start)
bpy.ops.render.render(animation=True)
```
