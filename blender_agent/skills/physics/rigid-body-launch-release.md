---
id: rigid-body-launch-release
name: Launch a rigid ball with a keyframed approach, then release it to physics
category: physics
kind: technique
status: verified
applies_to:
- cinematic
- 3d
when_to_use: A ball, wrecking ball, bowling ball or projectile must hit dynamic objects at a controlled time and
  speed.
triggers:
- ball
- hits
- launch
- roll
- throw
- wrecking
- projectile
- knocks
- smash
- push
test: tests/rigid_launch_release.py
tags:
- kinematic
- velocity
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
A hand-authored, art-directed hit: the ball arrives exactly when the script says and carries real momentum into the collision.

## Procedure
1. Make the ball an ACTIVE rigid body (`C.rigid(ball, "ACTIVE", mass=..., shape="SPHERE")`).
2. Keyframe its location with **LINEAR** interpolation at constant speed: start hold, then a straight run that continues *past* the contact point.
3. Animate the `rigid_body.kinematic` flag: True until just before contact, then False (`C.release_at(ball, t_contact - 0.12)`).
4. Physics inherits the velocity from the last keyframed motion, so the ball keeps going into the target.

## Parameters that worked
- Steel ball: radius 0.75, mass 60 kg, friction 0.3, ~6.7 m/s (7.6 m in 1.1 s), released 0.12 s before contact.
- Domino trigger ball: radius 0.42, mass 3, released 0.05 s before contact.

## Pitfalls
- BEZIER (ease-out) on the last approach key leaves ~0 velocity at release: the ball stops short and the wall never collapses (this happened in the first crate render).
- Release after the keyframed motion has ended, not on the last key.
- The keyframed end position must lie beyond the target so the velocity estimate is not zero.

## Code
```python
key(ball, 1, loc=start, interp="LINEAR")
key(ball, frame(t0), loc=start, interp="LINEAR")
v = (x_contact - start[0]) / (t_contact - t0)
key(ball, frame(t_contact + 0.3), loc=(start[0] + v * (t_contact + 0.3 - t0), y, z), interp="LINEAR")
C.release_at(ball, t_contact - 0.12)
```
