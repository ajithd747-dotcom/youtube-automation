---
id: silent-failures-in-image-pipelines
name: The failures that matter in an image pipeline do not raise
category: workflow
kind: rule
status: verified
applies_to:
- any
when_to_use: Building or extending a multi-stage image/video pipeline that is scored
  against a reference, especially when adding a new kind of source content.
triggers:
- ssim
- mae
- quality metric
- silent failure
- blank frame
- verify
- regression
- pipeline stage
- scoring
- benchmark
tags:
- workflow
- testing
- metrics
source:
- 'own-experience: FlipaClip anime-clip recreation (2026-09-19..20)'
version: 1
---
## Rule
Every expensive bug in this pipeline produced a **plausible frame, not an exception**. Build
the checks that catch those, and never treat a headline metric as proof of correctness.

## Checks worth having
- **Per-frame `std` against the reference frame's `std`.** Catches blank/featureless output
  that ssim and mae both rate highly. A frame at `std` 0.08 against a reference at 23 scored
  `ssim 0.95`, because the flat paper it got right was most of the picture.
- **Hue error (mean |a,b| difference in Lab), reported per shot.** Catches channel-order
  bugs and palette collapse that luminance-based ssim is blind to by construction.
- **Empty-layer counts.** `ink == []` on most drawings of a shot means a classifier sent
  them down a path that discards the line layer.
- **Coverage/inpaint percentages per stage.** A plate that is 74% invented is a fact worth
  printing next to the shot's score.
- **Alpha-empty render check.** A fully transparent cel render composites to a clean plate
  and looks deliberate.

## Rules of thumb
- A stage that cannot produce its output should **fail loudly**. A crash that a driver
  script reports only as "skipped" nearly dropped 91 frames from a finished cut.
- When adding a new content type, re-measure every threshold that was tuned on the old
  one. Thresholds are fitted to the content that was in front of you at the time.
- Prefer measuring a quantity over inferring it from a classifier. Gates keyed on "what
  kind of frame is this" break silently when the classifier is later corrected; gates keyed
  on "what is actually in this frame" do not.
- **Look at the pictures.** Two of the six bugs here were invisible in the numbers and
  obvious in a contact sheet of reference-vs-output-vs-error-map.

## Know the metric's ceiling before chasing it
Measure what a *perfect-but-approximate* result would score on the content in hand. On
fractal two-tone art: the reference shifted 1px against **itself** scores 0.851, blurred
3px scores 0.729, a flat fill scores 0.256. A 0.75 gate is unreachable there by any
polygon approximation, so judge that content on mae/hue and gate ssim per content type
rather than lowering the bar globally.
