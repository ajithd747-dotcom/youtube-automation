---
id: camera-rig-with-roll-and-relative-framing
name: 'Camera rig: track target, true roll, offsets relative to the subject'
category: camera
kind: technique
status: verified
applies_to:
- cinematic
- 3d
- anime
when_to_use: Dutch angles / rolling camera, or any shot where the subject moves and the framing must stay guaranteed.
triggers:
- dutch angle
- roll
- tilt
- camera roll
- framing
- follow
- close-up
- relative camera
- rolled camera
- whip
tags:
- camera
source:
- 'own-experience: anime-clip recreation benchmark (2026-09-19)'
version: 1
---
## Procedure
1. `rig` empty with a TRACK_TO constraint (`TRACK_NEGATIVE_Z`, up `UP_Y`) to a `target` empty; the camera is the rig's CHILD at local (0,0,0). Roll = the camera's local Z rotation (`cam.rotation_euler = (0, 0, radians(deg))`), keyed over time.
2. Key rig and target positions per shot (BEZIER); add handheld shake by keying small random offsets every 2 frames (LINEAR).
3. Frame relative to the subject: `cam_pos(t) = subject_pos(t) + offset`, `look(t) = subject_pos(t) + look_offset`. Typical offsets for a 1.75 m hero: full body (0,-4,0.9) lens 40; low angle (0,-3,-1.7) looking up; close-up face (0.05,-1.2,1.72) lens 50; top-down (0,0.3,6) roll 25-40 deg.
## Pitfalls
- A Track-To camera cannot roll by itself; rolling the rig instead breaks the track. Use the child camera.
- Absolute camera positions rot when the subject path changes; relative offsets do not.
