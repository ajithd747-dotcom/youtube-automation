---
id: exact-frame-count-per-shot
name: Render exactly round(duration x fps) frames per shot or the timeline drifts
category: workflow
kind: pitfall
status: verified
applies_to:
- any
when_to_use: Concatenating many separately rendered shots that must land on exact times (music hits, cuts, reference
  matching).
triggers:
- timing drift
- frame count
- off by one
- sync
- shot length
- concatenate
- concat
- timeline
- cut times
tags:
- timing
source:
- 'own-experience: anime-clip recreation benchmark (2026-09-19)'
version: 1
---
## Procedure
- The scene builders keep one extra end key frame (`frames = ceil(T fps) + 1`) so animation curves close; set `scene.frame_end = frame_start + round(T * fps) - 1` before rendering (render_shot does this for `anime`).
- Verify: `ffprobe -count_frames` per shot = round(T x fps).
## Pitfalls
- 14 shots x 1 extra frame = 0.58 s of drift: the final black shot began at 10.1 s instead of 9.55 s and every later frame comparison was wrong.
- Physics cinematic shots (`cinematic` style) still carry the extra frame; fix the same way if exact sync matters.
