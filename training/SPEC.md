# Training the Blender agent on the reference videos -- spec

Goal (user, 2026-09-20): split every reference video into its individual frames, then train the Blender agent by
recreating each video from scratch, one at a time -- picture, character voice-over and background music -- writing a
detailed per-frame script, comparing every recreated frame with the reference frame, adjusting the script, and saving
the skills learned. Use the whole box (12 cores, 30 GB RAM, CPU only).

The user chose "use your defaults" for the three open questions. The defaults, so nothing is decided by accident:

## 1. What "good" means for a frame (the score)

Per frame, recreation vs reference, both at analysis size (640 px wide):

| Metric | Meaning | Source |
|---|---|---|
| `ssim` | structure similarity on grey (1 = identical) | `recreate/compare.py: score_pair` |
| `dhue` | mean LAB a/b colour distance (0 = same colours) | same |
| `hist` | colour-histogram intersection (1 = same colour mix) | `training/score_recreation.py` |
| `edge_f1` | agreement of edge maps = line work / silhouettes (1 = same) | `training/score_recreation.py` |
| `grad_ssim_holdout` | SSIM of Sobel gradient-magnitude images. **Reported, never tuned against**: a recreation that traces Canny edges to please `edge_f1` cannot fake it | `training/score_recreation.py` |
| `frame_score` | `0.4*ssim + 0.25*hist + 0.25*edge_f1 + 0.10*(1 - min(dhue/20, 1))` | `training/score_recreation.py` |

A number means nothing alone, so **calibration comes first**: `training/calibrate_scores.py` scores known
degradations of a real reference (identical, blurred, flat shot-mean colour, another video) and writes the range a
recreation has to move through. Progress = frame_score rising against the same reference across iterations.
Per shot the loop stops at plateau (gain < 0.01 for 2 iterations) or 6 iterations, whichever first.

## 2. Scope of the first pass

All five references are **ingested** (frames, per-frame table, shots, audio, evidence pack). **Recreation** starts
with one video and grows only when the loop is proven on it, easiest first. Recreation level ladder, each rung
measured before the next is tried:

1. layout: sky / mid / low colour bands, gradients, horizon, light direction
2. silhouettes: characters and large shapes as flat shapes with the right palette and position
3. line work and shading; camera drift; motion cadence (on 1s/2s/3s)
4. voice-over (agents/voice) and music (agents/music) matched by `blender_agent/benchmark/compare.py` audio metrics

## 3. Skill format

Unchanged: `blender_agent/skills/<category>/<skill>.md` with the existing front matter (id, category, kind, status,
triggers, source), authored through the `_author_*.py` pattern. A skill is written **only after it moved a measured
score**, is marked `status: candidate` until a second shot confirms it, and cites the shot and score delta it came from.
Evidence packs from `skill_extract.py` stay in `blender_agent/skills/sources/<slug>/`.

## 4. The per-frame script (what "very detailed" means)

Requested by the user 2026-09-20: physics, lighting, motion "and every other detail" that is in the animated videos.
The script has two layers, and **every value carries the measurement it came from; a value that cannot be measured is
written `NOT MEASURED` -- never guessed and never defaulted** (Rule 8).

**Layer A -- `frames_table.jsonl`, one row per frame, all measured from pixels/audio by `training/describe_frames.py`:**

| Group | Fields |
|---|---|
| lighting | luma mean/std/p5/p50/p95, clipped-highlight and crushed-shadow share, colour-temperature proxy (R/B, LAB a/b), brightest-region centroid + area (light source position), light-gradient vector (key direction), bloom/halo energy, vignette ratio, exposure delta vs previous frame (flash/flicker) |
| colour | 5-colour palette with shares, saturation mean, colourfulness, shadow tint vs highlight tint (grade) |
| camera motion | global affine between frames from optical flow: translation dx/dy, zoom, roll; camera-shake jitter |
| subject motion | residual flow (after removing camera): mean/p95 magnitude, moving-pixel share, dominant direction, 8-bin direction histogram, divergence, curl, flow coherence; drawing cadence (new drawing vs hold) |
| physics | small moving blob count, mean blob velocity vector (gravity/wind direction), fall speed, streakiness (rain) vs roundness (petals/snow/dust), turbulence (flow variance), sudden-change events (impact/flash), sway needs time so it is measured per shot |
| depth / focus | sharpness map by 3x3 grid (depth of field, rack focus), two-layer flow split (parallax), letterbox content rectangle |
| composition | saliency centroid + bbox + area, distance to rule-of-thirds points, dominant line angle (horizon/tilt) |
| characters | anime-face detections (count, bbox, size class => shot scale ECU/CU/MS/WS) |
| transition | hard-cut score, dissolve score (frame ~ blend of neighbours), fade-to/from-black/white score, flash-frame score |
| audio | RMS dB, onset strength, beat flag, spectral centroid, low/mid/high band energy, speech-likelihood, at the frame's time |
| text on screen | `NOT MEASURED` until an OCR pass exists |

**Layer B -- `shots/<n>.json`, the script proper, built from Layer A by `training/write_shot_scripts.py`:**
camera path with move type and easing; lighting rig (key azimuth/elevation, key:fill ratio, colour temperature, ambient,
rim/backlight, bloom, vignette, exposure keyframes, flicker); physics (particle systems with type/size/speed/direction,
gravity vector, wind vector, turbulence, sway frequency and amplitude, shake profile, impact frames); subject motion
and cadence; composition and depth-of-field plan; palette and grade; transitions in/out; audio (loudness curve, beats,
speech spans with the Whisper text); characters per frame; `semantic` (setting, characters, actions, mood) which stays
`NOT MEASURED` until a vision pass fills it; and `blender_directives` -- concrete Blender settings derived from the above
(light energies/colours/angles, camera keyframes, particle emitter settings, world colour, compositor glare/vignette/
colour balance, DoF), each with `source_metric` and `confidence`.

## Layout

```
training/
  ingest_reference.py      frames + per-frame table + shots + audio, all references, all cores (12 cores: 19,639 frames in ~2 min)
  describe_frames.py       Layer A measurements per frame (lighting, colour, motion, physics, depth, composition, transitions, text)
  describe_audio.py        Layer A audio per frame
  detect_anime_faces.py    characters per frame (OpenCV 4 in tools/cv4; cascade in tools/models)
  write_shot_scripts.py    Layer B: one script per shot + contact sheet for the vision pass
  check_script_completeness.py   audit: groups present, no placeholders, every Blender directive sourced
  check_standard_wiring.py fails if the standard is unwired from CLAUDE.md / skill / agent / Blender agent
  score_recreation.py      per-frame scoring + worst-frame montage
  calibrate_scores.py      what scores do known-bad recreations get
  reference/<slug>/        (gitignored) meta.json frames/f_00001.jpg frames_table.jsonl shots.json audio.wav
  runs/<slug>/<run>/       (gitignored) recreated frames + scores per iteration
```

## Calibration (measured 2026-09-20, Fragrant Flower trailer, 100 frames, `calibrate_scores.py`)

| degradation of the real frame | frame_score | ssim | hist | edge_f1 |
|---|---|---|---|---|
| identical | 1.000 | 1.000 | 1.000 | 1.000 |
| jpeg q15 | 0.891 | 0.912 | 0.797 | 0.947 |
| shifted 3 frames | 0.854 | 0.845 | 0.904 | 0.796 |
| posterised 8 levels | 0.834 | 0.890 | 0.646 | 0.950 |
| blur sigma 2 | 0.814 | 0.891 | 0.962 | 0.474 |
| blur sigma 10 | 0.621 | 0.763 | 0.879 | 0.010 |
| mirrored | 0.600 | 0.537 | 0.986 | 0.313 |
| blur sigma 25 (colour layout only) | 0.581 | 0.737 | 0.784 | 0.010 |
| flat frame / shot mean colour | 0.39 | 0.65 | 0.25 | 0.010 |
| another video, same frame index | 0.253 | 0.368 | 0.160 | 0.117 |

Reading it: getting the colour layout right alone is worth ~0.4-0.6; only line work (edge_f1) and structure carry a
recreation past ~0.8. Anime holds drawings for 2-3 frames, so a 3-frame timing error costs little (0.85).

## Known measurement limits (found by looking at real frames, not assumed)

- Particles: pixel statistics cannot separate particle fields from dappled light or animated logos (false positives) and
  miss rain that merges into large regions (false negative). The script therefore only records a *candidate* with
  `needs_visual_confirmation`; the vision pass decides (`semantic.weather_particles_seen`).
- Faces: the anime cascade misses faces (about half in a two-character frame); 0 detections is not "no character".
- Saliency box is crude; burned-in subtitles and streaming logos contaminate edge/composition numbers. Subtitle
  presence is measured per frame and masked out of scoring; corner logos are masked by fixed regions.

## Hard limits

- Reference videos are other people's copyrighted work. They and everything derived from them stay local
  (gitignored). Recreations exist to measure and train the agent -- never uploaded, never put in the "Created" group.
- Everything lives inside this project (`tools/`, `training/`, HF model cache under `tools/hf`).
- Subagents: at most 5 at once (Rule 1.6); parallelism for rendering and scoring is worker processes, not agents.

## Verification (Rule 0)

- ingest: frame files per video == ffprobe `nb_frames`; table rows == frames; shots cover frames 0..N with no gap.
- score: identical input scores 1.0 on every metric; the degradations order sensibly (identical > blurred > flat >
  another video).
- a recreation iteration counts only if its frames were rendered by Blender and scored in the same run.
