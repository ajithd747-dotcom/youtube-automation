---
id: per-frame-script-standard
name: Per-frame script standard - measured lighting, motion, physics, composition, colour, transitions, audio, characters
category: workflow
kind: rule
status: reference
always: true
applies_to:
- any
when_to_use: Writing or planning any script, storyboard, shot plan or per-frame description of an animated video,
  especially when recreating a reference video in Blender.
triggers:
- script
- storyboard
- shot plan
- per-frame
- recreate reference video
- lighting
- physics
- camera motion
- composition
- transition
tags:
- workflow
- script
- standing-rule
source:
- 'owner rule 2026-09-20 (training/SPEC.md section 4, CLAUDE.md rule 2)'
version: 1
---
## Rules

1. Every value in a script is MEASURED (from training/reference/<slug>/frames_table.jsonl or shots/<n>.json) or the text NOT MEASURED. Never guess, never default, never write from the title.
2. Every frame/shot records: lighting (key direction, contrast, colour temperature, bloom, vignette, exposure), camera motion (dx, dy, zoom, roll, shake), subject motion (speed, direction, cadence on 1s/2s/3s), physics (particles, gravity/wind vector, turbulence, sway, impacts), composition (subject box, thirds, horizon tilt, depth of field), colour (palette, grade), transitions (cut/dissolve/fade/flash), audio (loudness, beats, speech), characters (count, size, position).
3. Blender settings come only from the measured values, each with its source metric and a confidence; unmeasured means the build leaves that setting neutral and says so.
4. Units: positions are frame fractions (x right, y down), speeds are frame-widths per frame, angles in degrees with 0 = right and 90 = down, luma 0..1.
5. One change per iteration, then re-score against the reference, so a score delta can be attributed.

## Evidence

Canonical field list: training/SPEC.md section 4. Procedure and never-list: .claude/skills/frame-script-standard/SKILL.md.
