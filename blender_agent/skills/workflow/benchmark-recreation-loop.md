---
id: benchmark-recreation-loop
name: Recreate a reference video and close the gap with measured comparisons
category: workflow
kind: rule
status: verified
applies_to:
- any
when_to_use: The goal is to reproduce (or reach the quality of) an existing video, or to check how good the agent's
  output really is.
triggers:
- recreate
- reference
- benchmark
- compare
- same as
- match the video
- quality gap
- clone the style
- reproduce
tags:
- benchmark
source:
- 'own-experience: anime-clip recreation benchmark (2026-09-19)'
version: 1
---
## Procedure
1. Evidence: `skill_extract.py video <file>` (cuts, motion, loudness, transcript, contact sheets); look at a dense contact sheet (every 0.5 s) to write a shot list with times.
2. Spec: one entry per shot (preset, seconds, params) whose durations sum to the reference length; keep the audio plan (tempo, key, energy curve, hits) from `analyze.py`.
3. Build with the project's tools (Blender presets + FX overlays + music agent + voice agent) and cache each shot.
4. Compare with `benchmark/compare.py ref rec outdir`: duration ratio, cut-alignment F1, motion correlation, SSIM, colour-histogram intersection, mean-colour, brightness correlation, audio score; it also writes a side-by-side video and a contact sheet.
5. Read `per_time` in report.json to find WHERE it fails, fix the largest gap first, re-render only changed shots, repeat. Keep each round's report to prove improvement.
## Pitfalls
- Do not read the aggregate score alone: black frames dominate SSIM/hist averages.
- Always look at the contact sheet: numbers said 'colour worse' when the real cause was a grading filter tinting pure black.
- Match STRUCTURE, TIMING, PALETTE LOGIC and AUDIO CHARACTERISTICS; do not copy the reference's art, character or soundtrack (originals only).
