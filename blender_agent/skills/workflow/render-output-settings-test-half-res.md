---
id: render-output-settings-test-half-res
name: Final output settings and testing at half resolution first
category: workflow
kind: rule
status: verified
applies_to:
- any
when_to_use: 'Before committing to a long render: choose codec/container and test cheaply.'
triggers:
- render
- output
- export
- codec
- h.264
- png sequence
- transparent
- test render
- resolution
- quality
tags:
- render
source:
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe@7:30-9:00
- 'own-experience: tutorial recreation benchmark (2026-09-19)'
version: 2
---
## Procedure (tutorial 7:30-9:00)
1. Output Properties: resolution = target (1920x1080 or 1280x720); output folder; File Format **FFmpeg**, container MPEG-4 (or QuickTime), codec **H.264**, quality preset High.
2. Need transparency for compositing elsewhere -> render a **PNG sequence** instead.
3. Set Start/End frame to cover the animation.
4. Test a single frame (F12), then test the animation at **50% resolution or lower** before the full-quality render (Ctrl+F12 = render animation).
5. EEVEE is fast; Cycles/fancier is slower - pick per shot.

## In this agent
`--preview` (360p, 12 fps, draft quality) is the 50%-test; `--plan-only` reviews the shot list first; per-shot caching means only changed shots re-render.

## Implemented (verified in Blender 4.5)
Recorded live: resolution 1920x1080 at 100 % -> 50 %, File Format FFMPEG, MPEG-4, H.264, constant rate factor HIGH, frame range 1-96, single-frame test render at 25 %.
