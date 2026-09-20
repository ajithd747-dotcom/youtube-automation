---
id: music-reference-matching
name: 'Match a reference track: tempo, key, energy contour, spectrum, loudness'
category: reference-matching
kind: technique
status: verified
applies_to:
- any
when_to_use: Recreating or imitating an existing video's music feel (benchmarking, 'make it sound like this').
triggers:
- reference
- match
- same music
- recreate
- sound like
- imitate
- similar track
- benchmark
source:
- video:blender-grease-pencil-practice-fantasy-anime-scene (audio analysis)
- 'own-experience: anime-clip recreation benchmark (2026-09-19)'
version: 2
---
## Procedure
1. `analyze.describe(ref)`: bpm (halve if > 130), key, centroid, band shares, energy curve per 0.25 s, hits, LUFS, LRA.
2. `plan_from_reference`: bpm, root/scale from key, sections from the energy curve, hits from transients.
3. Render, then `mix.eq_match(band shares)` (per-band gain toward the reference shares) and `mix.match_dynamics(energy curve)`.
4. `loudnorm` to the reference LUFS; `compare()` gives a 0-3 distance (bands, centroid, LUFS, LRA, energy correlation, tempo, key).
5. Iterate `refine_to_reference` (brightness x (ref/ours centroid)^0.6, bass x (ref/ours sub)^-0.4). Stop when the score stops improving.
## Reference values (anime clip, 12 s)
LUFS -14.4, LRA 2.2, ~89 BPM (F major), centroid 1364 Hz, band shares sub 14 % / low 27 % / mid 56 % / high 3 %, energy range 7 dB, 4 impacts.

## Implemented (verified) - result on the anime clip
`MusicAgent.plan_from_reference` + `refine_to_reference(rounds=3)` (FluidSynth strings/choir/bass/arp/kit + numpy risers/impacts, `eq_match`, `match_dynamics`, loudnorm to the reference LUFS): comparison score 0.233 (0 = identical): LUFS -14.4 vs -14.4, LRA 1.8 vs 2.2, energy-curve correlation 0.99, key F major = F major, tempo 90.5 vs 89 (half of the detected 178), centroid 1461 vs 1364 Hz, band-share L1 0.12. Audio score 0.875 in `benchmark/compare.py`.
