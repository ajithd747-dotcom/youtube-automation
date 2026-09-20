---
id: walk-cycle-profile
name: Walk cycle in profile with a tracking camera (workshop walk)
category: motion
kind: recipe
status: verified
applies_to:
- cinematic
- 3d
when_to_use: 'A character travels from A to B: walking to work, journey, morning routine.'
triggers:
- walk
- walks
- walking
- journey
- travel
- morning
- workshop
- route
- goes
- heads to
- commute
uses_recipe: workshop_walk
test: tests/robot_walk_profile.py
exemplar: exemplars/workshop_walk.mp4
tags:
- walk
- recipe
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
A readable walk in profile: legs scissor forward/back with knee bend on the trailing leg, arms counter-swing, torso leans slightly, pelvis bobs.

## Procedure
1. Recipe `workshop_walk` (mood `studio`, fog 0.7): dark wall, shelves with glowing orbs, crates, a warm SPOT lamp (9000 W, 50 deg) casting a visible cone.
2. Pose numbers (from `_pose`): hip swing +-30 deg (run 50), knee bend 35 deg (run 70) only on the trailing leg (`max(0, sin(w t + 0.6))`), arm swing 0.9 x hip swing, elbows -25/+25 deg, torso -4 deg (run -14), bob 0.012 x |sin|, w = 6 rad/s (walk) / 9.5 (run).
3. Face +X: `root.rotation_euler = (0, 0, +pi/2)`; use `animate_robot(..., plane="side")`; travel with root keyframes LINEAR from `walk_from` to `walk_to` over the shot duration.
4. Camera 34 mm at distance ~9.5 m (x from -2.5 to +1.5), height 1.5-1.6, target follows the robot (z ~1.05), f/2.6.

## Pitfalls
- Robot facing -X walks backwards: +90 deg about Z faces +X, -90 deg faces -X.
- Camera at 6.2 m with 40 mm cropped the head; 9.5 m / 34 mm framed the full body (see camera-framing-safe-area).
- Frontal-plane swing on a robot in profile makes the legs scissor toward the camera - always use the side plane.
