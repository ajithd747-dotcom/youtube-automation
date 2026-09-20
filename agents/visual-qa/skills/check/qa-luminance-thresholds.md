---
id: qa-luminance-thresholds
name: Numeric thresholds that flag hazy, dark or clipped shots
category: check
kind: rule
status: verified
applies_to:
- any
when_to_use: 'Judging a still without looking: washed out, too dark, clipped highlights, flat contrast.'
triggers:
- washed out
- hazy
- too dark
- clipped
- overexposed
- flat contrast
- histogram
- milky
- luminance
source:
- 'own-experience: ada_chain_reaction QA findings (2026-09-19)'
version: 1
---
## Rules (calibrated on the ada_chain_reaction shots)
- washed_out: mean luminance > 0.60 and std < 0.14 (the hazy intro: mean 0.84 std 0.135; banner 0.88 / 0.12).
- clipped_highlights: > 10 % of pixels above 0.98 (intro 17 %, domino 23 %).
- too_dark: mean < 0.07 (unless the mood is night/neon by design).
- flat_contrast: p95 - p5 < 0.20.
- Healthy target after fixing: mean 0.30-0.75, std 0.15-0.30, clipped < 8 %, p5 < 0.4.
