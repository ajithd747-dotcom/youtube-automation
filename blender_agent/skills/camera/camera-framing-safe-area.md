---
id: camera-framing-safe-area
name: 'Keep the subject fully in frame: distance, lens and a numeric check'
category: camera
kind: rule
status: verified
applies_to:
- any
when_to_use: Every shot with a character or key object; any time a head/feet/prop is cropped.
triggers:
- framing
- cropped
- head cut off
- safe area
- composition
- in frame
- distance
- lens
- subject
test: tests/camera_framing.py
tags:
- qa
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Rules (measured)
- Full-body 1.8 m character: camera distance >= 9 m with a 30-34 mm lens, or >= 5.3 m at 18 mm. 6.2 m at 40 mm cropped the head.
- Leave 10% headroom: target z = 55% of character height.
- Titles above the subject need at least 0.5 m clearance from raised hands.
- QA before a long render: project key points to the camera with `bpy_extras.object_utils.world_to_camera_view` at first/middle/last frame; require 0.02 < x < 0.98 and 0.03 < y < 0.97 (skills/tests/camera_framing.py does this).
- A shot that fails the check should be re-framed, not re-rendered.
