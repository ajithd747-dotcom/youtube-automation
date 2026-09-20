---
id: bloom-skip-when-frame-already-bright
name: Skip bloom once most of the frame is already over the threshold
category: effects
kind: pitfall
status: verified
applies_to:
- any
when_to_use: Adding a bloom / glare pass to frames in post (ffmpeg or numpy), especially
  across a sequence whose shots differ in overall brightness.
triggers:
- bloom
- glare
- glow pass
- blown out
- white frame
- overexposed
- screen blend
- post composite
- highlight bleed
tags:
- post
- compositing
- colour
source:
- 'own-experience: FlipaClip anime-clip recreation (2026-09-20)'
version: 1
---
## Rule
Bloom assumes a **localised** bright source with somewhere dark to fall off into. Measure
how much of the frame already exceeds the bloom threshold and skip the pass when it is
most of the picture:

```python
def bright_fraction(img, thresh=185):
    return float((img.max(axis=2) > thresh).mean())

strength = 0.0 if bright_fraction(frame) > 0.5 else base_strength
```

## Why
With most of the frame over threshold the blurred copy is screened back over everything
at once, so there is no falloff and the frame saturates to white. Line art on white paper
is the worst case: the paper is the bloom source.

## Evidence
Tutorial shots (white paper, thin construction lines) composited as **blank white frames**
- rendered `std` 0.08 against the reference's 23 - while still scoring `ssim 0.95`, because
the paper they got right is most of the picture. Gating on bright coverage:

| shot | before | after |
| --- | --- | --- |
| 13 | ssim 0.8693 / mae 13.93 | **0.8908 / 4.64** |
| 14 | ssim 0.9487 / mae 5.37 | **0.9675 / 3.20** |
| 16 | ssim 0.8511 / mae 12.97 | **0.8914 / 4.87** |

## Choosing the threshold
Measure it, do not guess. Bright coverage per shot separated cleanly: shots that genuinely
need bloom peaked at **0.34**, the paper shots started at **0.95**. 0.5 sits in the gap with
margin on both sides.

## Re-tune bloom strength after any change to the glow layer
Bloom strength silently absorbs the errors of whatever feeds it. On this film it had been
tuned to **0.85** while the glow layer was discarding the blown-out cores of its FX (see
`glow-mask-must-include-blown-out-core`) - the bloom was standing in for the missing
cores. Once the cores rendered, that same 0.85 double-counted the light and washed the
saturated halo towards white.

Re-swept afterwards, both metrics improved monotonically as strength came down and
plateaued at 0.12-0.25:

| bloom | shot 9 ssim/mae | shot 7 ssim/mae |
| --- | --- | --- |
| 0.85 | 0.9195 / 8.65 | 0.9261 / 9.44 |
| 0.40 | 0.9215 / 7.63 | 0.9274 / 8.81 |
| 0.25 | 0.9217 / 7.38 | 0.9275 / 8.66 |
| 0.00 | 0.9215 / 7.18 | 0.9273 / 8.56 |

**Take the knee, not the metric minimum.** mae keeps falling all the way to zero bloom
because any spread light that is not perfectly aligned adds error - but at 0.0 the FX
goes visibly flat and loses the reference's soft outer halo, and ssim turns back down.
0.25 is where the picture matches. Always confirm the chosen value on a crop against the
reference; a pixel metric will happily talk you into deleting an effect that is really
there.

## Do not infer it from the frame's class
It is tempting to reuse an existing "is this a flat/mono frame" predicate. That couples
the bloom gate to an unrelated classifier and breaks the moment the classifier is fixed -
which is exactly how this bug surfaced: the paper frames had only ever been spared because
a frame-type test was misfiling them.
