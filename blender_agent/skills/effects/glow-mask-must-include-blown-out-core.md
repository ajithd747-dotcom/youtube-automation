---
id: glow-mask-must-include-blown-out-core
name: A saturation-keyed glow mask throws away the blown-out core
category: effects
kind: pitfall
status: verified
applies_to:
- any
- 2d
when_to_use: Isolating bright FX (energy, magic, neon, explosions) with an HSV mask so
  they can be treated separately from flat paint - banded, bloomed or given their own
  material.
triggers:
- glow mask
- energy effect
- hsv mask
- saturation threshold
- white hot core
- orb
- flat sticker
- fx isolation
- bloom seed
tags:
- colour
- compositing
- fx
source:
- 'own-experience: FlipaClip anime-clip recreation (2026-09-20)'
version: 1
---
## Rules
`(sat > 60) & (val > 150)` finds the coloured rim of an FX blob and **excludes its
middle**, because a blown-out core has desaturated towards white. Measured on an energy
orb: pixels over `val 235` averaged saturation **7.2** against the gate's 60, and only
**3.5%** of them were inside the mask. The orb then rendered as a flat teal sticker with
no bright centre and nothing for the bloom pass to catch.

Add bright pixels back, but only where they are enclosed by real saturated glow, and only
when the enclosed region is small enough to actually *be* a core:

```python
m = ((sat > sat_min) & (val > val_min)).astype(np.uint8) * 255
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k7)
if m.any():
    holes = cv2.subtract(fill_holes(m), m)
    cap = min(float((m > 0).sum()), 0.05 * m.size)     # a core is not bigger than its ring
    n, lbl, stats, _ = cv2.connectedComponentsWithStats((holes > 0).astype(np.uint8), 8)
    keep = np.zeros(n, np.uint8)
    keep[1:] = (stats[1:, cv2.CC_STAT_AREA] <= cap).astype(np.uint8)
    holes = (keep[lbl] * 255).astype(np.uint8)
    core = ((val > core_val).astype(np.uint8) * 255) & holes
    m = cv2.morphologyEx(cv2.bitwise_or(m, core), cv2.MORPH_CLOSE, k7)
```

## Evidence
Core recovered from 3.5% to **79.5%** on the orb and **77.3%** on an explosion, with
unrelated bright content untouched (white sketch paper 1.4-2.0%).

## The cap is not optional
Unbounded hole-filling floods any large bright area that merely happens to be ringed by
saturated marks. On tutorial frames - white paper with teal accents and grid lines - the
glow mask went from 4.6% to **33%** of the frame before the size cap was added. Always
re-measure a mask change across *every* content type in the sequence, not just the shot
you are fixing; print old% / new% / delta per shot and look for the outlier.
