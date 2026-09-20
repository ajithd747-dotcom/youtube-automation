---
id: follow-through-secondary-motion
name: 'Overlapping action: hair, cloth, antennas lag behind the body'
category: motion
kind: technique
status: verified
applies_to:
- cinematic
- 3d
- stickman
when_to_use: 'Any character or object that moves fast and stops: hair, capes, tails, antennae, straps should keep
  moving.'
triggers:
- hair
- cape
- tail
- antenna
- follow through
- secondary motion
- overlap
- flowing
- trail
- flutter
tags:
- motion
source:
- video:blender-grease-pencil-practice-fantasy-anime-scene@0:02-0:08
- 'own-experience: anime-clip recreation benchmark (2026-09-19)'
version: 3
---
## Evidence
Anime clip: long pink hair trails opposite to the flight direction and only settles after the body stops (0:02, 0:04, 0:08).

## Procedure
1. Body moves first; appendages start 2-4 frames later (offset the keyframes) and overshoot by 10-20% before settling.
2. For rigged parts use a damped spring: `angle(t) = A e^(-d t) cos(w t)` with d 3-5, w 12-18 rad/s.
3. For cloth/hair use physics (cloth pinned at the root with light gravity, or soft body) rather than hand keys.

## Implemented (verified)
`anime_lib.hair_follow(j, path, fps, lag, gain)`: five spiky hair chains (3-5 pointed cone segments each); every segment rotates against the ROOT velocity (`rx = -vy*6*gain`, `ry = vx*6*gain`, clamped +-70 deg) sampled `i*lag` frames in the past (lag 2), plus a small sine flutter and a constant 12 deg droop. Hair swings back on a dive and settles when the body stops.

## Implemented (verified)
`anime_lib.hair_follow(j, path, fps, lag, gain)`: five spiky hair chains (3-5 pointed cone segments each); every segment rotates against the ROOT velocity (`rx = -vy*6*gain`, `ry = vx*6*gain`, clamped +-70 deg) sampled `i*lag` frames in the past (lag 2), plus a small sine flutter and a constant 12 deg droop. Hair swings back on a dive and settles when the body stops.
