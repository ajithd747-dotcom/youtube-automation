# Training progress log (tracked; numbers only -- no reference frames)

Each entry: what was tried, on which reference, the score, and what it taught. Scores are `frame_score`
(training/SPEC.md section 1) frame by frame against the real frames. Calibration for reading them is in SPEC.md.

## 2026-09-20 -- ingest of all five references

19,639 frames measured on 12 cores in ~2 minutes; 390 shots (Silent Voice 58, Your Name AMV 149, Garden of Words 38,
Blue Box 82, Fragrant Flower 63). Shot cuts on Fragrant Flower match ffmpeg's detector exactly (63/63). Whisper
(multilingual) transcribed four Japanese-language references; Silent Voice has no speech.
Learned by looking: particle heuristics fail both ways (dappled light, animated logos vs rain), so particles are a
candidate needing visual confirmation; subtitles/logos must be masked in scoring.

## 2026-09-20 -- rung 1 (colour layout) on Fragrant Flower

Measured colour grid -> one vertex-coloured plane in Blender Workbench -> scored. Blender reproduces colours exactly
(200,100,50 -> 200,100,50).

| shot | frames | 6x4 | 16x9 | 32x18 |
|---|---|---|---|---|
| 1 shop sign, static | 27 | 0.478 | 0.542 | 0.581 |
| 4 cake close-up, static | 28 | 0.539 | 0.596 | 0.625 |
| 27 character, static | 57 | 0.538 | 0.591 | 0.630 |

edge_f1 ~ 0 on all: no line work. ~+0.05 per doubling of grid resolution; ceiling of this rung ~0.63, as calibration
predicted (blurred true frame = 0.58-0.62). Skill saved: `exact-colour-vertex-plane-layout` (status reference until a
second video confirms it).

**Next rung (2): line work and silhouettes** -- measured edge/contour polylines as Blender curves or Grease Pencil
strokes over the colour layout, then flat colour regions. Target: edge_f1 from ~0 to >0.4 and frame_score past 0.75.
