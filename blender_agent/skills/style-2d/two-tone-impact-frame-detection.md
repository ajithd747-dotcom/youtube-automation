---
id: two-tone-impact-frame-detection
name: Detecting two-tone impact frames needs both tone populations, not one
category: style-2d
kind: pitfall
status: verified
applies_to:
- 2d
- anime
- cel
when_to_use: Classifying frames of a 2D reference clip so that stark black-on-white impact
  frames take a different decomposition path from ordinary painted cels.
triggers:
- impact frame
- two-tone
- is_mono
- bimodal
- black and white frame
- silhouette
- flash frame
- line art
- frame classification
- cel decomposition
tags:
- 2d
- classification
- reference-recreation
source:
- 'own-experience: FlipaClip anime-clip recreation (2026-09-20)'
version: 1
---
## Rules
A frame is a two-tone impact frame only when **both** tone populations are heavy. Test the
tails separately, never their sum:

```python
def is_mono(img, sat_max=26.0, bimodal_min=0.75, tail_min=0.12):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    if float(hsv[:, :, 1].mean()) > sat_max:
        return False
    v = hsv[:, :, 2]
    dark = float((v < 70).mean())
    light = float((v > 195).mean())
    return dark + light >= bimodal_min and min(dark, light) >= tail_min
```

## Why the sum alone fails
`((v < 70) | (v > 195)).mean() >= 0.75` is satisfied by any frame that is overwhelmingly
*one* tone, because one tail alone clears the bar. Measured on a real reference:

| content | dark frac | light frac | sum test | correct |
| --- | --- | --- | --- | --- |
| true impact frame | 0.43 | 0.37 | mono | mono |
| true impact frame | 0.21 | 0.57 | mono | mono |
| sketch on white paper | 0.003 | 0.995 | mono | **not mono** |
| near-black fade | 0.96 | 0.002 | mono | **not mono** |

## Consequence of getting it wrong
The two-tone path deliberately skips ink extraction (`strokes = []`) because on a real
impact frame the ink detector fires on everything. Send white-paper line art down it and
you throw away the line layer, which on sketch content *is the entire artwork*. It hit 117
of 121 drawings in one half of a reference and produced blank pages.

## Detection
- Symptom in the data: most drawings in a shot have `ink == []`.
- Symptom on screen: a frame that renders as flat paper.
- Cheap guard: compare each rendered frame's `std` against the reference frame's `std`.
  ssim and mae will *not* catch it - on 95% white paper both stay healthy while the art
  is missing.

## Related
A frame that is almost entirely *dark* also wants the full-frame treatment, but for a
different reason (no ink to extract, no usable plate), so make it a separate predicate
rather than loosening this one - see `flat-tone-frame-full-frame-paint`.
