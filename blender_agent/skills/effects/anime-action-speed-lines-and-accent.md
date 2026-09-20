---
id: anime-action-speed-lines-and-accent
name: 'Action shot: speed lines, dutch angle, one saturated accent colour'
category: effects
kind: technique
status: verified
applies_to:
- cinematic
- 3d
- 2d
when_to_use: Fast motion, flying, chase, dive, power-up, impact; anime / high-energy 2D look.
triggers:
- action
- fast
- speed
- dive
- flying
- chase
- anime
- power up
- energy
- rush
- dash
tags:
- anime
- fx
source:
- video:blender-grease-pencil-practice-fantasy-anime-scene@0:01-0:10
- 'own-experience: anime-clip recreation benchmark (2026-09-19)'
version: 3
---
## Evidence (12 s Grease Pencil clip, 5 shots, 20 cuts/min, motion 33)
- Environment is desaturated blue-grey/brown; the *only* saturated colour is the magenta energy (glowing petals, a giant light shard) -> the eye follows the FX.
- Close-up at 0:06: thin dark **radial speed lines** converge on the character; camera is rolled (dutch angle); background terrain streaks.
- Character hair trails behind the motion with overlapping delay (follow-through).
- Cut pattern: dark establishing plunge (0:01) -> tracking medium (0:02) -> pose wide (0:03-0:04) -> speed-line close-up (0:06) -> particles beat (0:07) -> back-view exit (0:08).

## Procedure
1. Pick a muted palette for world/sky, choose ONE accent hue for energy, glow it (additive) and give it particles.
2. Speed lines: 40-80 thin lines radiating from a point behind the subject, random lengths, 2-4 frame life, re-randomised every frame (hold shots 2 frames).
3. Roll the camera 5-12 degrees on close-ups; blur/streak the background along the motion direction.
4. 2-3 s per shot; end on a back view or hold-out pose.

## Implemented (verified)
`blender_side/anime_recipes.py` presets: plunge, aerial_dive, side_lunge, up_shot, crouch_explosion, top_down, smear, speed_close, grin_close, back_leap, ledge_small, hair_close, black. Speed lines: see radial-speed-lines-overlay. FX helpers in `anime_lib.py`: `shard` (magenta triangle prism, emission 7), `laser` (thin emissive streak, hard cut on/off), `petals` (30 keyframed glowing ellipsoids), `debris` (26 grey shards + 9 puffs). Render: 1.4 s/frame at 1080p.
Result vs reference (round 3 benchmark): see work/recreate_anime/compare*/report.json.

## Implemented (verified)
`blender_side/anime_recipes.py` presets: plunge, aerial_dive, side_lunge, up_shot, crouch_explosion, top_down, smear, speed_close, grin_close, back_leap, ledge_small, hair_close, black. Speed lines: see radial-speed-lines-overlay. FX helpers in `anime_lib.py`: `shard` (magenta triangle prism, emission 7), `laser` (thin emissive streak, hard cut on/off), `petals` (30 keyframed glowing ellipsoids), `debris` (26 grey shards + 9 puffs). Render: 1.4 s/frame at 1080p.
Result vs reference (round 3 benchmark): see work/recreate_anime/compare*/report.json.
