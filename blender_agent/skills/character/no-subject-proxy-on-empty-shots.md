---
id: no-subject-proxy-on-empty-shots
name: The vision pass decides whether a shot has a character - a detector's face on an empty shot is not a subject
category: character
kind: pitfall
status: verified
applies_to:
- any
when_to_use: Writing a shot script or building a Blender scene for a shot with no character in it (empty rooms,
  corridors, landscapes, title cards), or when a stray ball or blob appears in a recreation of an empty shot.
triggers:
- subject proxy
- empty shot
- stray sphere
- false positive face
- no character
tags:
- recreation
- character
- measurement
source:
- 'own-experience: Fragrant Flower shot 46 (empty school corridor), 2026-09-22 (training/PROGRESS.md)'
version: 1
---
## Rules

1. When the vision pass lists no characters (`semantic.characters == []`), the shot gets no subject box and no subject
   proxy -- check this BEFORE any detector-derived box, not after.
2. A face cascade reporting a face on 100 % of frames is not evidence of a character: on FF 46 lbpcascade found one on
   the sink taps of an empty corridor, and the shot script turned it into a pink ellipsoid.
3. Do not keep an invented subject because it scores slightly better. On FF 46 the ball scored lpips 0.289 against
   0.273 without it, only because it stood in for the pale sinks underneath. The missing thing is the scene's props.

## Evidence

`training/write_shot_scripts.py` had the "no character seen -> no subject" branch after the face-track branch, so it
never ran when the cascade fired. Moving it first changed exactly one shot script across five references (FF 46).
