---
id: exposure-and-haze-control
name: 'Avoid washed-out shots: exposure per mood, haze budget, contrast check'
category: lighting
kind: rule
status: verified
applies_to:
- any
when_to_use: Any shot that looks hazy, milky, low-contrast or overexposed; choosing exposure/fog for a mood.
triggers:
- hazy
- washed out
- milky
- low contrast
- overexposed
- too bright
- flat
- foggy
tags:
- qa
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Rules (measured on the ada_chain_reaction render)
- Exposure by mood: sunset -1.5, day -0.5, studio 0, night +0.4, neon +0.3.
- Fog budget: night/workshop up to 0.7, sunset <= 0.2, day <= 0.2. Fog + bright sky + bright floor = milk.
- Floors: dark (`#3b414f`) under bright skies; pale floors only in dark moods.
- QA: render a still; mean luminance should sit around 0.15-0.55 with a max above 0.85 (highlights) and min below 0.05 (blacks). A flat histogram means too much haze.

## Pitfalls
- The intro (sunset + fog 0.5) and the banner (day + fog 0.2, white sky) shots were hazy in the first video: lower fog and darken the ground.
