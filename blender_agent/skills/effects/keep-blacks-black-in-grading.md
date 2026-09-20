---
id: keep-blacks-black-in-grading
name: Colour grading must not lift pure black
category: effects
kind: pitfall
status: verified
applies_to:
- any
when_to_use: Applying an ffmpeg/Blender colour grade to footage that contains black frames, fades or letterboxing.
triggers:
- grade
- colorbalance
- tint
- black frame
- fade
- lifted blacks
- eq filter
- color correction
- histogram
tags:
- ffmpeg
- colour
source:
- 'own-experience: anime-clip recreation benchmark (2026-09-19)'
version: 1
---
## Procedure
- Tint only mids/highlights: `colorbalance=rm=0.02:bm=0.03:rh=0.02:bh=0.04`; never use the shadow terms (`rs/gs/bs`) on footage with black.
- `eq=saturation=0.82:contrast=1.04:gamma=1.02` keeps 0 -> 0.
- Check: `mean` of a known black frame must stay 0.0 after the grade.
## Evidence
Adding `bs=0.05` turned black frames into dark blue and collapsed the histogram-intersection metric from 1.0 to 0.0 on every black frame.
