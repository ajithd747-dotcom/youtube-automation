---
id: render-cost-model
name: What a render costs on this laptop and how to spend it
category: performance
kind: rule
status: verified
applies_to:
- any
when_to_use: Estimating render time, choosing quality, or trying to speed things up.
triggers:
- render time
- slow
- speed
- performance
- cost
- eta
- quality
- fast
- how long
tags:
- performance
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Measured (2 CPU cores, integrated Radeon, EEVEE Next, 1280x720, 24 fps, 'standard' 14 samples + ray tracing)
- Simple shots 3.2 s/frame; glass/mirror 4.6; workshop with spot + fog 5.9; fireworks 2.3-3; cloth 2.5.
- A 55 s video = 1320 frames = 83 min first pass; +42 min for the shots that needed fixes.
- Per-shot fixed cost ~15-60 s (Blender start + shader compile).
- Removing the compositor vignette (blur 260) saved ~3 s/frame; the biggest lever is *resolution* (540p ~ 0.6x). Samples 8 vs 14 saved ~10%. Ray tracing, fog, DOF, motion blur each cost < 10%.
- Two Blender processes do not help (GPU-bound).

## Rules
- Budget = frames x seconds-per-frame; estimate 4 s/frame for cinematic. Use `--quality draft --preview` while iterating.
- Move blur-like post effects (vignette, grain, sharpen) to ffmpeg; keep bloom (cheap) in the compositor.
- Render only what changed (per-shot cache) and review shots as they finish.
