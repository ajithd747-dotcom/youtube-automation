---
id: camera-follow-target-copy-location
name: Camera that tracks a moving action front
category: camera
kind: technique
status: verified
applies_to:
- cinematic
- 3d
when_to_use: The action travels across the frame (a chain reaction, a walker, a rolling ball) and the camera must
  stay with it.
triggers:
- follow
- track
- tracking shot
- trailing
- chase camera
- dolly
- moves along
- pan with
exemplar: exemplars/domino_run.mp4
tags:
- camera
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
1. Camera object with a TRACK_TO constraint (`TRACK_NEGATIVE_Z`, up `UP_Y`) on a target empty; DOF focus object = the same empty.
2. Key a *lead* empty along the action path with LINEAR interpolation timed to the measured event speed; give the target a COPY_LOCATION constraint to the lead.
3. Key the camera position separately (LINEAR): keep it 5-9 m to the side, lens 34-42 mm, height 1.2-1.7 m.
4. Call `cam.animation_data_clear()` before re-keying if the helper already keyed the camera.

## Pitfalls
- Schedule the lead empty from a **measured** event speed (dominoes: 0.17 s each) - a guessed schedule ends before the action does.
- Perspective foreshortening makes long rows look shorter: trail from behind-left, not straight on.
