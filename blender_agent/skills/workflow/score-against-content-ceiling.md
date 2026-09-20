---
id: score-against-content-ceiling
name: Judge a shot against its content's ceiling, not a fixed threshold
category: workflow
kind: technique
status: verified
applies_to:
- any
when_to_use: Deciding whether a shot that scores badly is actually broken, or is simply
  made of content no approximation could score well on - and therefore whether to keep
  working on it or to accept it.
triggers:
- ssim threshold
- quality gate
- shot failing
- is this good enough
- metric ceiling
- hard content
- benchmark
- verify threshold
- false alarm
tags:
- workflow
- metrics
- testing
source:
- 'own-experience: FlipaClip anime-clip recreation (2026-09-20)'
version: 1
---
## Procedure
Measure what a near-perfect but not pixel-exact result could score **on that shot's own
content**, then compare the actual score to it:

```python
g = cv2.cvtColor(cv2.imread(ref_frame), cv2.COLOR_BGR2GRAY)
ceiling = ssim(g, np.roll(g, 1, axis=1))     # the reference against itself, shifted 1px
relative = shot_ssim / ceiling
```

Sample 3 frames per shot. Report `ssim`, `ceiling` and `relative` side by side.

## Why
An absolute gate is fitted to whatever content was in front of you when you chose it.
Fine detail collapses ssim even when the picture is right, so a shot of fractal smoke and
a shot of flat sky are not on the same scale at all. Measured ceilings on one film ranged
from **0.896 to 0.994** between shots.

## What it tells you
Actual example, where a shot was failing a fixed 0.75 gate:

| shot | ssim | ceiling | relative |
| --- | --- | --- | --- |
| median shot | 0.951 | 0.99 | **0.951** |
| worst ordinary shot | 0.905 | 0.979 | 0.925 |
| the failing shot | 0.723 | 0.896 | **0.807** |

The relative column is the answer. Had it come out near 0.95, the shot would have been as
good as the rest and the gate would have been the thing at fault. It came out at 0.807 -
a genuine outlier - so the shot really was the weakest and deserved more work, which then
took it from 0.647 to 0.730.

## Use it honestly
This is a tool for deciding **where to spend effort**, not for excusing a bad result. Run
it *before* concluding "the metric is unfair", because a single-frame ceiling estimate can
easily be off - on this film one frame suggested a ceiling of 0.851 where the shot average
was 0.896, which was almost enough to wrongly write the shot off as unfixable. If you do
conclude a gate is miscalibrated, change it per content type with the measurement written
down next to it, and never quietly lower it to make a report look clean.
