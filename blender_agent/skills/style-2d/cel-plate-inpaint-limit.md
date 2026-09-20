---
id: cel-plate-inpaint-limit
name: Do not inpaint a background plate that was masked in every drawing
category: style-2d
kind: pitfall
status: verified
applies_to:
- 2d
- anime
- cel
when_to_use: Recovering a painted background plate from a 2D shot by taking a per-pixel
  median over the drawings with the character matted out.
triggers:
- background plate
- masked median
- inpaint
- cel matte
- plate recovery
- background reconstruction
- row fill
- sky gradient
- clean plate
tags:
- 2d
- background
- reference-recreation
source:
- 'own-experience: FlipaClip anime-clip recreation (2026-09-20)'
version: 1
---
## Rule
Mirror-inpainting a hole in a plate is only valid when the hole is small enough to have
real background beside it. Gate it on the share of the frame that was masked in **every**
drawing, and above the limit leave the plain unmasked median in place:

```python
frac = float((never > 0).mean())          # never = masked in every drawing
if 0.002 < frac < 0.15:
    bg = _row_fill(bg, never)
```

## Why
A pixel masked in every single drawing is usually one the matte **over-claimed**, not one
the character genuinely never left. At those pixels the plain median is the background,
so it is the better estimate. Mirroring instead reflects whatever is beside the hole into
it - on a seascape that paints the sky down over the water and produces a pale band where
the reference is dark.

## Evidence
Three shots had 59-74% of their plate invented this way; their lower third was the worst
region in the whole film. Adding the gate, with no other change and no re-render:

| shot | before | after |
| --- | --- | --- |
| 5 | ssim 0.8664 / mae 9.70 | **0.9051 / 7.73** |
| 6 | ssim 0.8393 / mae 8.18 | **0.9018 / 5.35** |
| 7 | ssim 0.8839 / mae 22.51 | **0.9252 / 9.77** |
| 8 | ssim 0.8840 / mae 22.87 | **0.9279 / 8.63** |

Bottom-band error fell with it (shot 8 `err_low` 0.173 -> 0.065).

## Why the mask over-claims
Two mechanisms, both worth checking when a plate looks invented:
1. `cel_matte` grows ink and fills the enclosed area, so a **textured background** - sea
   with wave lines, foliage, hatching - reads as dense line work and is taken for cel. One
   shot had 317 of 1080 rows more than 90% matted.
2. A "differs from the current background estimate by more than `tol`" term feeds back:
   a wrong plate makes everything look different, which masks everything, which keeps the
   plate wrong.

## Diagnosis
Write the `never` mask out beside the plate (`shotNN_mask.png`) and look at it. A mask
covering a full-width horizontal band is the tell - a character is a compact blob, a
background band is not. Also print the inpainted percentage per shot; anything over ~30%
means the plate is mostly fiction.
