---
id: landmark-face-confidence-gate
name: Use a measured face only where the detector is confident - drop landmark keyframes scoring under 0.9
category: character
kind: rule
status: verified
applies_to:
- any
when_to_use: Drawing a character's face from detected facial landmarks (anime-face-detector or similar) in a
  recreation, especially on wide shots, title cards, profiles, backs of heads and hand-over-face shots.
triggers:
- face landmarks
- landmark face
- face detector score
- measured character look
- false face
tags:
- recreation
- character
- measurement
source:
- 'own-experience: Fragrant Flower whole-trailer runs video_measured / video_gated / video_resegmented, 2026-09-22 (training/PROGRESS.md)'
version: 1
---
## Rules

1. A landmark keyframe whose detector box score is below 0.9 is not a measurement: drop it
   (`recreate_video.LANDMARK_MIN_SCORE`). If no keyframe is left, draw the lit proxy, not a guessed face.
2. The flat, unlit body belongs only with a measured face; without one, keep the lit ellipsoid proxy.
3. Score alone cannot tell a real low-confidence face from a false one. Before blaming the detector, check the shot
   boundaries: a keyframe from the other side of a missed cut looks like a confident wrong face
   (see [[detect-missed-shot-cuts]]).
4. A kept keyframe is held for the whole shot. It is only right when the shot really is one picture.

## Evidence

Whole Fragrant trailer, lpips: measured look 0.491, gated 0.493. Fixed a title card (FF 59, score 0.55: 0.484 -> 0.545)
and a profile (FF 46: 0.557 -> 0.597). Cost: FF 18, back of head, all keyframes ~0.77 (0.557 -> 0.473). FF 34 got worse
under the gate (0.595 -> 0.537) because its one passing keyframe came from a close-up on the other side of a missed
cut; after re-cutting the shot it scored 0.618.

## Limits

0.9 was chosen on one trailer. Shots whose every keyframe sits around 0.75-0.85 (backs of heads, small faces) lose a
face that was helping.
