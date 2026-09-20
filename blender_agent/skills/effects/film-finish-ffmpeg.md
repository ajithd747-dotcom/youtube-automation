---
id: film-finish-ffmpeg
name: 'Film look in the final mux: vignette, grade, dip to black (not in the compositor)'
category: effects
kind: technique
status: verified
applies_to:
- any
when_to_use: Every finished shot in cinematic mode; whenever a vignette, colour grade or fade is wanted.
triggers:
- vignette
- cinematic look
- grade
- fade
- film look
- dip to black
- polish
tags:
- performance
- ffmpeg
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
Apply in the per-segment ffmpeg mux, together with captions:
`vignette=PI/5,eq=contrast=1.06:saturation=1.12,fade=t=in:st=0:d=0.18,fade=t=out:st=<dur-0.18>:d=0.18,subtitles=...`

## Why
A compositor vignette (Ellipse mask + Blur size 260) cost ~2.5-3 s **per frame** on this 2-core CPU - it doubled the render time. ffmpeg does the same in milliseconds.

## Pitfalls
- Put the fades before `subtitles` in the filter chain so the captions stay solid while the picture dips to black.
- Bloom is fine in the compositor (cheap); blur-based nodes are not.
