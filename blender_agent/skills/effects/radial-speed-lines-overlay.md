---
id: radial-speed-lines-overlay
name: Manga speed lines as a numpy/PIL RGBA sequence overlaid with ffmpeg
category: effects
kind: technique
status: verified
applies_to:
- any
when_to_use: Fast movement, impact or dramatic close-ups in an anime/comic look.
triggers:
- speed lines
- manga
- action lines
- focus lines
- radial lines
- impact frame
- dash
- burst lines
- anime action
tags:
- fx
- ffmpeg
source:
- 'own-experience: anime-clip recreation benchmark (2026-09-19)'
version: 1
---
## Procedure
- Per frame (re-randomised every 2nd frame = 'drawn on twos'): 46 tapered triangles from radius r0 = 0.38-0.62 H to r1 = r0 + 0.3-0.8 H at random angles around the focus point; width 0.15-0.5% of H; colour (70,68,82) alpha 150; transparent outside the effect windows.
- Write `sl_%04d.png` (RGBA) for the whole duration and composite: `ffmpeg -i video -framerate 24 -i sl_%04d.png -filter_complex "[0:v][1:v]overlay=shortest=1"`.
- Use 0.35-0.6 s windows at the dive, the smear and the speed close-up; keep the centre clear so the subject stays readable.
## Pitfalls
- 90 thick dark lines (alpha 215) covered the subject and looked like a sticker; 46 thin semi-transparent lines matched the reference.
