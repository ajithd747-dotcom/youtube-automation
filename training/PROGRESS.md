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

## 2026-09-20 -- rung 2 (line work) on two videos, and the holdout metric

Measured Canny contours -> flat ribbon quads in Blender over the rung-1 colour layout (training/blender_level2.py).
Added `grad_ssim_holdout` to the scorer because rung 2 traces the same Canny edges the scorer measures: without a holdout the
big `edge_f1` gain would have been the metric agreeing with itself. Calibration on the holdout: blur sigma 25 = 0.556, flat
colour = 0.441, unrelated video = 0.320.

| video / shot | rung 1 score / holdout | rung 2 score / holdout | rung 2 edge_f1 | rung 2 ssim vs rung 1 |
|---|---|---|---|---|
| Fragrant Flower 27 (character) | 0.630 / 0.550 | 0.828 / 0.584 | 0.87 | 0.744 -> 0.709 |
| Blue Box 77 (character) | 0.534 / 0.374 | 0.739 / 0.451 | 0.91 | 0.605 -> 0.531 |
| Blue Box 1 (no face) | 0.561 / 0.507 | 0.746 / 0.557 | 0.90 | 0.671 -> 0.588 |

Sweep on Fragrant Flower 27 (canny, min length, half-width): frame_score 0.785 to 0.851, holdout only 0.561 to 0.584. The best
frame_score (canny 90,180 -> 0.851) is the scorer's own Canny thresholds, not a better recreation; the best holdout is the
thinnest line (0.5 px -> 0.584). Chosen: canny 60,120, min length 10, half-width 0.5.

What it taught: line work gives the big edge_f1 gain but ssim FALLS every time (lines a pixel off, ink too dark), and the
remaining gap is flat cel fills and shading, not lines. Skills: `exact-colour-vertex-plane-layout` promoted to verified
(second video confirmed); `measured-edge-ribbon-line-layer` saved as reference.

**Honest scope note:** rungs 1-2 reconstruct what the pixels are (measured colour grid + traced edges). That is the fidelity
baseline, not creation from scratch. The from-scratch part -- the skill the agent must learn -- is reproducing the same look
from parametric Blender constructs driven by the shot script's `blender_directives` (key/fill lights, world, camera path,
depth of field, glare/vignette, particles), with no reference pixels in the loop. Rung 3 should be that, scored by the same
frame metrics plus feature-level checks (camera path, exposure curve, palette).

## 2026-09-21 -- rung 3 (parametric, from the script alone) on two videos

Blender builds the shot from `shots/shot_NN.json` only -- no reference pixels (training/recreate_level3.py, blender_level3.py):
backdrop with the measured top/middle/bottom band colours (new measured script field `colour.regions`, from the 32x18 grid),
an ellipsoid subject proxy at the face/subject box, a point key toward the measured light direction, world fill, camera on the
measured path keyframes, exposure keyed to the measured curve, compositor vignette + bloom. Coordinate descent over 7 light /
compositor parameters minimises the error between the render's features (measured with describe_frames.measure_lighting)
and the script's numbers. frame_score and holdout are computed afterwards and never tuned against.

| video / shot | frame_score untuned -> tuned | holdout | feature error | exposure-curve MAE |
|---|---|---|---|---|
| Fragrant Flower 27 (character) | 0.419 -> 0.456 | 0.505 -> 0.523 | 5.23 -> 1.18 | 0.177 -> 0.029 |
| Blue Box 77 (character) | 0.310 -> 0.418 | 0.280 -> 0.308 | 4.44 -> 1.44 | 0.265 -> 0.003 |
| Blue Box 1 (no face) | 0.284 -> 0.405 | 0.349 -> 0.380 | 4.33 -> 0.78 | 0.258 -> 0.0004 |

~4 min per shot on 12 cores. Checked: key direction round-trips (0/90/180/270 -> 0/90/180/270), camera shift signs and units
(dx 0.1 -> +0.1 width, dy 0.1 -> +0.177 height = 0.1 frame widths), vignette reaches corner/centre 0.66.
What it taught: the lighting half of the script is reproducible from numbers; the gap to rung 2 (0.74-0.83) is shapes. Largest
residuals are vignette, contrast and p95 -- a flat diffuse scene has no small highlights -- and the single pale subject proxy
(face-box colour is wrong for dark-haired characters). Skill: `script-driven-light-and-exposure-matching` (verified, 2 videos).

**Next:** the vision pass to fill `semantic` (setting, characters, props), so the proxy becomes shapes the script names.

## 2026-09-21 -- rung 4 (semantic character proxy) on Fragrant Flower -- mixed

Vision pass filled `semantic` for all 63 Fragrant Flower shots (reference/<slug>/semantic.json, local). When the semantic pass
lists a character AND a face box exists, the single sphere becomes head (skin) + hair + body, colours measured from the grid
around the face box (new script field `colour.regions.character`). Same tuning loop; `--no-character` is the rung-3 ablation.

| shot | rung 3 frame_score / holdout | rung 4 frame_score / holdout |
|---|---|---|
| FF 27 (black-haired boy) | 0.456 / 0.523 | 0.534 / 0.506 |
| FF 50 (dark-purple-haired girl) | 0.379 / 0.414 | 0.431 / 0.395 |
| FF 32 (blond boy) | 0.568 / 0.609 | unchanged: face detector found 0 faces, no proxy built |

What it taught: right colours in roughly the right places lift frame_score (hist, ssim), but the holdout FALLS on both shots --
ellipsoid outlines sit where the real ones are not. Frame_score alone would have called this a win. Next: silhouette
shape (hair outline, shoulders) and the face detector's misses (use semantic characters when detection is empty).

## 2026-09-21 -- rung 5 (character silhouette learned from feedback) -- small gain, ellipsoid ceiling

training/tune_character_shape.py: rung-4 lights fixed, 8 shape parameters of the head/hair/body proxy tuned by coordinate
descent on mean frame_score of 3 probe frames; holdout never used to accept a step.

| shot | before frame_score / holdout | after frame_score / holdout | edge_f1 |
|---|---|---|---|
| FF 27 | 0.534 / 0.506 | 0.560 / 0.513 | 0.149 -> 0.261 |
| FF 50 | 0.431 / 0.395 | 0.444 / 0.394 | 0.089 -> 0.116 |

What it taught: the gain is almost all edge_f1 (outlines moved toward the real ones); holdout +0.007 on 27, flat on 50, so it
is not only fitting the metric, but three ellipsoids have hit their ceiling (~+0.01-0.03). Next shape step needs a richer
silhouette family (hair outline with spikes/bangs, shoulders), not more tuning of ellipsoids.

## 2026-09-21 -- silhouette character style (A) -- no clear gain over ellipsoids

`--style silhouette`: flat back-hair outline (spiked crown + side locks), zigzag bangs in front of the forehead, neck/shoulder
body outline; 13 shape parameters tuned the same way (frame_score on probe frames, holdout untouched).

| shot | ellipsoid tuned: frame_score / holdout | silhouette tuned: frame_score / holdout |
|---|---|---|
| FF 27 | 0.560 / 0.513 | 0.553 / 0.504 |
| FF 50 | 0.444 / 0.394 | 0.456 / 0.379 |

Split verdict, and the holdout sides with the ellipsoids on both. Hand-designed generic outlines do not match specific hair
shapes; the next shape step needs the outline itself measured per character (not generic spikes), or a different family.

## 2026-09-21 -- audio: character voice-over + music (B), Fragrant Flower whole trailer

training/recreate_audio.py: Demucs split -> per-line F0/level on the vocals stem -> Kokoro Japanese voice chosen by F0,
stretched/pitched/levelled per line; music planned from the no-vocals stem (tempo, key, energy, hits) and rendered with
FluidSynth; mixed and scored.

| measure | result | reference point |
|---|---|---|
| voice character accuracy (Whisper small ja) | 0.846 | 0.888 on the reference vocals stem (ceiling) |
| speech envelope correlation | 0.615 | |
| median F0 error per line | 0.41 semitones | |
| music energy-curve correlation | 0.95 | |
| music tempo | 70 bpm vs 140 detected (half-time, bpm_rel 0.007) | |
| music key | planned D minor; measured C major after mastering/impacts | key_match False |
| mix loudness-curve correlation | 0.821 | |
| mix LUFS | -29.8 | -28.3 |

Found and fixed: the music agent's minor progression i-VI-III-VII was HEARD as the relative major (D minor planned -> F major
measured); now i-iv-VII-i, which measures as the planned key for D and A minor alone. In the full trailer render the key still
reads C major after impacts and mastering, so key_match stays False -- the whole-track chroma key detector is fragile.
Skill: `match-reference-character-voice-japanese` (candidate).

## 2026-09-21 -- measured outline, cel shading, and the voice skill confirmed

Measured character outline (training/measure_character_outlines.py: skytnt/anime-seg ISNet ONNX, 3 keyframes per shot,
<= 40-point polygon, NOT MEASURED when foreground < 1% -- wide shots with small figures) drawn as a flat body/hair outline:

| shot | ellipsoid tuned | measured outline tuned | cel (flat emission, measured colours) |
|---|---|---|---|
| FF 27 | 0.560 / 0.513 | 0.541 / 0.506 | 0.436 / 0.495 |
| FF 50 | 0.444 / 0.394 | 0.452 / 0.383 | 0.381 / 0.350 |

(frame_score / holdout.) All three shape families sit within ~0.01: the silhouette is not the bottleneck. Cel shading
collapses `hist` (0.65 -> 0.32): four flat median colours cannot match the broad tone distribution of a real anime frame.
Looking at the renders: what is missing is interior detail -- line art, eyes, hair strands. Lit stays the default.

Voice skill confirmed on Blue Box: character accuracy 0.838 = the Whisper ceiling on the reference vocals (0.838); music key
matched there. `match-reference-character-voice-japanese` -> verified.

## 2026-09-21 -- first whole reference video recreated end to end (Fragrant Flower, 110.5 s)

training/recreate_video.py: all 63 shots through rung 3/4 (scene from the script, lights tuned 6 rounds, character proxy where
the semantic pass + a face box allow), joined with the recreated voice + music, encoded (local only, rule 3). ~2 h on 12 cores.

| measure | result |
|---|---|
| frame_score over all 2,649 frames (score_recreation.py) | 0.463 (holdout 0.506) |
| cut alignment F1 (benchmark/compare.py) | 0.941 |
| motion-curve correlation | 0.954 |
| brightness-curve correlation | 0.998 |
| mean colour similarity | 0.976 |
| video_score / audio_score / overall (benchmark) | 0.785 / 0.405 / 0.595 |
| worst shots | S61 0.29 (Netflix streaks), S9 0.29, S41 0.31, S26 0.32, S31 0.33 |

Timing, exposure and colour of the whole trailer are recreated; content is not (backdrop + blobs). Seen in the compare sheet:
close-ups where the face detector found nothing get no character; on non-character shots the saliency "subject" becomes a
stray ellipse (sometimes on a subtitle). Next: drop the saliency blob when the semantic pass lists no character, and use the
anime-seg outline to place characters the face detector misses.

## 2026-09-21 -- parametric anime face features (eyes, lash line, mouth)

`tune_character_shape.py --features`: eyes (white, iris, shine, lash line) and a mouth line placed from the face box, sizes
tuned with the shape; colours are style defaults (the grid cannot resolve eyes).

| shot | shape only: frame_score / holdout | + face features |
|---|---|---|
| FF 27 | 0.560 / 0.513 | 0.585 / 0.507 |
| FF 50 | 0.444 / 0.394 | 0.462 / 0.394 |

+0.02 frame_score, holdout flat -- the gain is edge_f1 (0.26 -> 0.38 on 27). Not enough to call a skill: the holdout, which is
not tuned, does not confirm it. Kept as an option, off by default.

## 2026-09-21 -- second whole reference video recreated end to end (Blue Box, 82 shots, 2,805 frames)

Same driver (training/recreate_video.py, rung 3/4, 6 tuning rounds), run by the new `youtube-recreation-queue` service
(operate/README.md) after a VM reboot killed the first attempt at shot 8; it resumed from the rendered shots.

| measure | Blue Box | Fragrant Flower (for comparison) |
|---|---|---|
| frame_score over all frames | 0.431 | 0.463 |
| grad_ssim_holdout | 0.428 | 0.506 |
| edge_f1 | 0.044 | 0.050 |
| cut alignment F1 (benchmark/compare.py) | 0.869 | 0.941 |
| motion-curve correlation | 0.901 | 0.954 |
| brightness-curve correlation | 0.996 | 0.998 |
| mean colour similarity | 0.968 | 0.976 |
| video_score / audio_score / overall | 0.76 / 0.0 / 0.38 | 0.785 / 0.405 / 0.595 |
| worst shots | S14 0.28, S80 0.28, S25 0.30, S2 0.31, S16 0.33 | |

Timing, exposure and colour transfer to a second video; content still does not (backdrop + proxies), and edge_f1 is ~0.04
on both -- line work is the largest missing component. audio_score 0.0 is a mix-level miss, not voices: the recreation
mix measures -20.5 LUFS, 6.3 dB QUIETER than the reference video (-14.2; lufs_db 6.3), while energy correlation is 0.815 and
tempo matches (bpm_rel 0.007, half-time); key reads F major vs F minor. Next for audio: master to the reference's LUFS.

## 2026-09-21 -- rung 6: parametric line art on the character proxy -- negative, kept off by default

Where edge_f1 is lost (FF 27 / 50, tuned rung-5 renders): 89% / 93% of the reference's edges lie inside the character
outline; the render recalls 30% / 15% of them. The missing ink is interior line work (hair strands, jaw, collar, eyes).

New measured script field `characters.line_art` (training/measure_line_art.py, merged by write_shot_scripts.py): edge
density inside/outside the outline, an 8x8 density grid over the outline's box, ink colour, stroke width, vertical share of
hair strokes -- statistics, never line positions. FF 27: inside 0.060 vs outside 0.011, ink [68,56,55], ~2 px strokes.
Blender: `blender_level3.stroke_paths` -- tapered ink ribbons (bangs strands over a hair fringe, crown strands, side locks,
neck, collar) placed from the face box and proxy shape, in the measured ink colour and width. training/tune_line_art.py
tunes the 6 count/length parameters to the measured line art; frame_score / holdout are never used to accept a step.

| shot | no strokes: frame_score / edge_f1 / holdout | objective = one density | objective = 8x8 grid |
|---|---|---|---|
| FF 27 | 0.560 / 0.261 / 0.513 | 0.539 / 0.272 / 0.488 | 0.535 / 0.262 / 0.500 |
| FF 50 | 0.444 / 0.116 / 0.394 | 0.448 / 0.201 / 0.366 | 0.450 / 0.200 / 0.369 |

The holdout falls in all four runs, and ssim falls 0.04-0.05 each time. With one density number the tuner met the target by
hanging a curtain of side locks over the jacket (n_locks at its limit); the grid objective stopped that on 27 but its error
only fell 0.88 -> 0.73: generic strand templates cannot put ink where THIS character's ink is (on 27 it sits left of the
face box, over the hair fall). Same lesson as rung 2 in reverse: lines in roughly-right places cost ssim and structure more
than they earn in edge_f1. What would move it is measured structure -- where the eyes, jaw, hairline and hair masses are --
not more strokes. Stroke layer stays in the code, off unless spec["line_strokes"].

## 2026-09-21 -- audio mastered to the reference's loudness

Why the mix was 6.3 dB quiet: nothing normalised it (peak-limit only), and the only reference level on record was the mono
22 kHz analysis copy (-17.9 LUFS) -- the original stereo track the benchmark measures reads -14.2. New
`recreate_audio.master_to_reference`: gain + true-peak limiter (-1 dBFS) to the ORIGINAL reference media's integrated
loudness, with its channel count, measured by the benchmark's own function (analyze.loudness, ffmpeg ebur128), re-measured
and corrected until within 0.3 LU. recreate_video.py now encodes the mastered mix.

| Blue Box audio (benchmark/compare.py) | before | mastered |
|---|---|---|
| mix LUFS (reference -14.2) | -20.5 | -14.3 |
| lufs_db | 6.3 | 0.1 |
| distance score (0 = identical) | 2.012 | 1.018 |
| audio_score | 0.0 | 0.491 |
| energy_corr / bands_l1 / key_match | 0.815 / 0.111 / False | 0.822 / 0.127 / False |

What is left of the distance: key mismatch (0.3), spectral centroid 24% low (0.24), loudness range 2.4 LU narrower (0.24).
Fragrant v2 was already running with the old encoder; its audio gets re-encoded when it finishes.

## 2026-09-21 -- measured face structure: anime face landmarks place the face (first holdout gain from content)

training/measure_face_landmarks.py: hysts/anime-face-detector 0.1.0 (YOLOv3 box + HRNetV2 28 landmarks, plain PyTorch,
~1 s/frame on CPU) on the outline keyframes -> `characters.face_landmarks` in the script. Fragrant: faces in 40 of 63
shots, including S32 (blond boy) where the cascade found none; write_shot_scripts.py now uses the landmark box as the
second fallback for the face box (after the cascade, before the outline-derived box).
Blender (`face_from_landmarks`): a flat skin face on the jaw contour closed just above the brows, eye whites on the hull of
each eye's 6 points, iris + shine inside, ink lash lines, brows, jaw line and mouth through the measured points (ink colour
and width from characters.line_art). Replaces the head ellipsoid; hair/body shape tuned as in rung 5
(`tune_character_shape.py --landmark-face`).

| shot | rung 5 ellipsoid: frame_score / edge_f1 / holdout | landmark face |
|---|---|---|
| FF 27 | 0.560 / 0.261 / 0.513 | 0.589 / 0.383 / 0.516 |
| FF 50 | 0.444 / 0.116 / 0.394 | 0.426 / 0.183 / 0.398 |

Holdout rises on both -- small (+0.003 / +0.004), but every earlier content step (proxy colours, silhouettes, outlines,
parametric eyes, line art) left it flat or lowered it. edge_f1 up on both. frame_score falls on 50 through hist
(0.49 -> 0.41): the flat face plane is lit evenly where the ellipsoid had a gradient, and the girl's face is bright with
blush. Next: cel shading of the face plane from the measured light direction, landmarks animated across keyframes
(mouth, blinks), S32 once Fragrant v2 finishes (its box changes).

## 2026-09-21 -- landmark face: measured face tones + landmarks animated between keyframes

measure_face_landmarks.py now also measures `tones` per face: two LAB clusters inside the face region (minus eyes, mouth,
brows) -> light_rgb (skin), dark_rgb, dark_share, dark_direction_deg. On FF 27 / 50 the dark tone is the bangs over the
forehead (share 0.30-0.38, direction ~275 deg = up), on 32 (short blond hair) only 0.02 -- so the field is named "dark",
not "shadow": the measurement cannot tell skin shadow from hair. Blender paints the face in the light tone and the dark
tone on the measured side at the measured share (face_geometry.shadow_polygon), and re-places every landmark part on
every rendered frame, interpolated between the 3 measured keyframes. Face polygons now live in training/face_geometry.py,
imported by both the measurement and Blender, so the measured region is the drawn region.

| shot | rung 5 ellipsoid: frame_score / hist / edge_f1 / holdout | static landmark face | + tones + animation |
|---|---|---|---|
| FF 27 | 0.560 / 0.652 / 0.261 / 0.513 | 0.589 / 0.653 / 0.383 / 0.516 | 0.604 / 0.701 / 0.390 / 0.513 |
| FF 50 | 0.444 / 0.491 / 0.116 / 0.394 | 0.426 / 0.408 / 0.183 / 0.398 | 0.444 / 0.436 / 0.175 / 0.406 |

Best frame_score on both shots and the best holdout on 50 (+0.012 over rung 5); on 27 the holdout gives back the static
face's +0.003. hist recovers most of what the flat face lost. Tones and animation were changed together -- their separate
contributions are NOT MEASURED. Blinks between keyframes are not captured (3 keyframes per shot).
Candidate skill: `landmark-placed-anime-face` (holdout up on 50, level on 27; needs a third shot -- S32 after Fragrant v2).

## 2026-09-21 -- Fragrant Flower v2 (subject proxy follows the vision pass) + mastered audio

v2 = the whole trailer again with commit c1bd22a (no subject when the vision pass sees no character; head box from the
measured outline when the cascade misses). Re-encoded with the mastered mix.

| measure | v1 | v2 |
|---|---|---|
| frame_score / holdout | 0.463 / 0.506 | 0.462 / 0.503 |
| cut F1 / motion corr / brightness corr | 0.941 / 0.954 / 0.998 | 0.950 / 0.955 / 0.997 |
| audio_score (benchmark) | 0.405 | 0.79 (mastered: -29.8 -> -25.2 LUFS = reference; key matches) |
| overall (benchmark) | 0.595 | 0.788 |

The subject change is a wash on the picture: 40 shots moved, all of them outline-derived head boxes -- gains up to +0.10
(S11, S26, S33), losses down to -0.10 (S38, S32, S34, S14, mostly the blond boy the cascade cannot see). The overall jump
is the audio mastering. Scripts are now rebuilt with the landmark box ahead of the outline guess: the face-box source for
the 63 shots is now face_landmarks 27, face_track 14, silhouette_outline 3, saliency 2, none 17.

## 2026-09-21 -- landmark face, third shot (FF 32, blond boy): NOT confirmed

S32 had no character before (the cascade found no face); the landmark box now gives it one.

| FF 32 | frame_score | holdout |
|---|---|---|
| no character (rung 3) | 0.568 | 0.609 |
| rung 4 ellipsoid, lights tuned | 0.528 | 0.587 |
| rung 5 ellipsoid, shape tuned | 0.587 | 0.543 |
| landmark face, default shape | 0.552 | 0.569 |
| landmark face, shape tuned | 0.622 | 0.511 |

Every character variant has a lower holdout than no character at all, and shape tuning lowers it further on both styles
(hist 0.64 -> 0.89 while the hair ellipsoid grows to fill the close-up: frame_score fitting the colour histogram). Seen in
the renders: the landmark face is placed right (eyes, brows, mouth on the measured points) but clips to white -- the flat
face plane sits nearer the key light than the ellipsoid the lights were tuned with. So `landmark-placed-anime-face` stays
unconfirmed. Fix being tried: draw the landmark face as emission in the measured colours, divided by the frame's exposure,
so it displays at the measured colour whatever the lighting.

## 2026-09-21 -- landmark face in measured colours (emission, exposure-compensated); the shape tuner fits hist

`blender_level3.make_measured_flat`: the landmark face parts are unlit emission whose strength is keyed to 2^-exposure on
the exposure curve, so they display exactly the measured colours (checked: rendered skin at the nose = measured light_rgb,
[225,208,180] on 27 and [248,218,208] on 50). Lit, the face plane had clipped white on 32.

| shot | no character | lit face: default shape / tuned | measured-colour face: default shape / tuned |
|---|---|---|---|
| FF 27 | -- | -- / 0.604, 0.513 | 0.579, 0.508 / 0.594, 0.514 |
| FF 50 | -- | -- / 0.444, 0.406 | 0.481, 0.395 / 0.482, 0.397 |
| FF 32 | 0.568, 0.609 | 0.552, 0.569 / 0.622, 0.511 | 0.587, 0.569 / 0.647, 0.517 |

(frame_score, holdout.) Measured colours raise frame_score on 50 (+0.04, hist 0.44 -> 0.57) and 32; the holdout does not
move with them. The bigger finding is the shape tuner itself: on 32 it grows the hair ellipsoid until hist reaches 0.962
while the holdout falls 0.569 -> 0.517 -- frame_score's 0.25 hist weight rewards painting the frame the right colours in the
wrong shapes. On a close-up that is the whole frame. The landmark face is still not confirmed: on 32 no character keeps the
best holdout. Next: tune the proxy shape against the measured silhouette (characters.silhouette_outline IoU), not frame_score.

## 2026-09-21 -- proxy shape tuned to the measured silhouette (outline IoU): silhouette fit does not move the holdout

`tune_character_shape.py --objective outline`: the proxy's screen silhouette computed from the same geometry Blender uses
(union of hair/head/body ellipses + landmark face polygon; camera motion ignored -- static on these shots), coordinate
descent on IoU with characters.silhouette_outline over the outline keyframes, no rendering in the loop (seconds). Checked
against a render: the silhouettes coincide; a render-difference mask adds the proxy's cast shadow and misses dark hair on
a dark backdrop, which is why its IoU with the computed mask read only 0.44-0.75.

| shot | outline IoU | frame_score / holdout, default shape | outline-tuned | frame_score-tuned (previous entry) |
|---|---|---|---|---|
| FF 27 | 0.612 -> 0.738 | 0.579 / 0.508 | 0.557 / 0.500 | 0.594 / 0.514 |
| FF 50 | 0.617 -> 0.939 | 0.481 / 0.395 | 0.480 / 0.394 | 0.482 / 0.397 |
| FF 32 | 0.645 -> 0.811 | 0.587 / 0.569 | 0.585 / 0.542 | 0.647 / 0.517 |

On 50 the proxy covers 94% of the measured silhouette and the holdout does not move; on 32 a better silhouette LOWERS it.
Together with the rung-5 finding (three shape families within ~0.01) this settles it: the outer silhouette is not what the
holdout measures. The holdout is SSIM of gradient-magnitude maps -- it rewards gradients where the reference has them and
flatness where it is flat. A lit ellipsoid puts smooth shading gradients across areas the reference paints flat (anime cel
fills), and the bigger the proxy, the more of them -- which is why no character at all still scores best on 32 (0.609).
Next candidates, both about interior gradients rather than outline: flat (unlit, measured-colour) hair and body proxies
like the landmark face; then interior structure (hair masses, clothing folds) where the reference has edges.

## 2026-09-21 -- flat (unlit, measured-colour) hair and body proxies: mixed, hypothesis only half right

`--flat-proxy`: hair/head/body ellipsoids use the same exposure-compensated emission as the landmark face
(blender_level3.measured_colour_material). Scored at the default shape, landmark face on, no tuning (`--rounds 0`).

| shot | lit proxies: frame_score / holdout | flat proxies | no character |
|---|---|---|---|
| FF 27 | 0.579 / 0.508 | 0.573 / 0.499 | -- |
| FF 50 | 0.481 / 0.395 | 0.477 / 0.375 | -- |
| FF 32 | 0.587 / 0.569 | 0.631 / 0.596 | 0.568 / 0.609 |

Flat helps the blond close-up (32: holdout +0.027, frame_score +0.044) and hurts both dark-haired shots (-0.009, -0.020).
So the previous entry's explanation ("lit shading adds gradients where anime is flat") holds only where the reference hair
IS flat: 32's short blond hair is a few flat tones, while 27/50 have dense strand lines -- there the lit ellipsoid's
shading gradient was standing in (badly) for the reference's hair detail, and removing it removes gradient where the
reference has plenty. The holdout rewards matching the gradient distribution, not flatness. On 32 no character still wins.
Stays off by default. What the numbers point at: the proxies need interior detail that follows the measured
characters.line_art density (dense in hair, sparse on skin) -- rung 6 tried generic strokes and lost; the difference now
would be placing hair masses from the landmarks/outline, not strands from templates.

## 2026-09-21 -- rung 7: hair as measured masses -- negative on the holdout (all three shots)

New measurement `hair_tones` per face (measure_face_landmarks.py: two LAB tones inside the measured outline above the chin,
minus the face). Blender (`hair_masses`): the hair ellipsoid is replaced by the measured outline above the chin in the
majority tone, split into locks fanning from a crown point (face_geometry.hair_locks), the minority tone on its measured
share of the locks, ink along the lock boundaries. training/tune_hair_masses.py picks the lock count whose rendered line-art
grid is closest to characters.line_art (frame_score / holdout never used to choose). The renders visibly take each
character's own hair shape (27 spiky, 50 long side locks, 32 short blond spikes).

| shot | landmark face + ellipsoid hair: frame_score / edge_f1 / holdout | hair masses | locks chosen |
|---|---|---|---|
| FF 27 | 0.579 / 0.298 / 0.508 | 0.489 / 0.295 / 0.475 | 10 |
| FF 50 | 0.481 / 0.164 / 0.395 | 0.515 / 0.201 / 0.361 | 8 |
| FF 32 | 0.587 / 0.214 / 0.569 | 0.652 / 0.337 / 0.536 | 16 |

Holdout -0.033 / -0.034 / -0.033. The render's line density stays at a third of the reference's (0.022 vs 0.060 on 27)
at every lock count, so the grid objective is choosing among uniformly wrong options.

Pattern over rungs 4-7 (colours, silhouettes, outline fit, parametric eyes, line art, flat fills, hair masses): the only
content change that raised the holdout on more than one shot is the landmark face -- structure placed on MEASURED points.
Anything placed plausibly but not measured (templates, wedges, strokes, tuned ellipsoids) lowers it, by 0.01-0.05, even
when it looks closer to the reference. grad_ssim_holdout is an unforgiving judge: SSIM on gradient maps blurred at sigma
1.2 px, so an edge a few pixels off counts as a missing edge AND a false one. Off by default.

## 2026-09-21 -- a second holdout: LPIPS (perceptual) -- and it reverses most of rungs 4-7's verdicts

Added `lpips_holdout` = 1 - LPIPS(alex) to score_recreation.py (reported, never tuned against; subtitles/logos masked by
copying reference pixels; <= 300 sampled frames per run, ~0.15 s/frame on CPU; weights in tools/torch). Calibration on
Fragrant (60 frames, calibrate_scores.py, two new degradations):

| degradation | frame_score | grad_ssim_holdout | lpips_holdout |
|---|---|---|---|
| identical | 1.000 | 1.000 | 1.000 |
| offset 4 px (right drawing, misplaced) | 0.780 | **0.568** | **0.925** |
| mean-shift simplified redraw | 0.928 | 0.830 | 0.893 |
| blur sigma 2 / 10 / 25 | 0.819 / 0.628 / 0.589 | 0.846 / 0.589 / 0.556 | 0.791 / 0.581 / 0.540 |
| flat shot colour | 0.392 | 0.441 | 0.444 |
| another video | 0.245 | 0.320 | 0.308 |

Ordering check passes. grad_ssim_holdout scores a correct drawing 4 px off as low as blur sigma 25; LPIPS scores it near
identical while keeping blur, flat colour and unrelated frames low. So the gradient holdout could not tell "roughly right
shapes" from "mush" -- exactly the regime rungs 4-7 operate in.

Every earlier run re-scored without re-rendering (training/rescore_perceptual.py), same scene before vs after each change:

| change | FF 27 lpips | FF 50 lpips | FF 32 lpips | grad holdout said |
|---|---|---|---|---|
| no character -> rung 4 ellipsoid proxy | 0.523 -> 0.561 | 0.377 -> 0.411 | 0.406 -> 0.397 | worse on all |
| rung 5 shape tuning (frame_score) | 0.561 -> 0.565 | 0.411 -> 0.417 | 0.397 -> 0.373 | mixed |
| landmark face (vs rung 5) | 0.565 -> 0.578 | 0.417 -> 0.448 | 0.373 -> 0.459 | +, +, n/a |
| line-art strokes (rung 6) | 0.565 -> 0.575 | 0.417 -> 0.468 | -- | worse on both |
| flat measured-colour proxies | 0.586 -> 0.586 | 0.453 -> 0.464 | 0.459 -> 0.536 | 2 of 3 worse |
| hair masses (rung 7) | 0.586 -> 0.590 | 0.453 -> **0.518** | 0.459 -> 0.514 | worse on all |

By LPIPS: the landmark face, hair masses and flat proxies each help on every shot (or hold), the character proxy helps
where the character is large, and the best S32 is the flat-proxy landmark face (0.536) -- not "no character" (0.406), which
the gradient holdout preferred. The renders agree with LPIPS: hair masses LOOK like each character's hair.
The two holdouts now disagree often, so neither decides alone: a change is a clear win when frame_score and lpips_holdout
rise and grad_ssim_holdout does not fall by more than calibration noise; when they split, look at the frames. Next:
combine the pieces LPIPS favours (landmark face + hair masses + flat proxies) and test on 27/50/32, then on whole videos.

## 2026-09-21 -- combined measured character (landmark face + hair masses + flat body) on FF 27 / 50 / 32

`tune_hair_masses.py --flat-proxy` (lights from level4, default proxy shape; before = landmark face with lit ellipsoid
hair/body). recreate_level3.render_and_score now also returns lpips_holdout.

| shot | before: frame_score / grad holdout / lpips | combined | locks |
|---|---|---|---|
| FF 27 | 0.579 / 0.508 / 0.586 | 0.490 / 0.477 / 0.585 | 10 |
| FF 50 | 0.481 / 0.395 / 0.453 | **0.515** / 0.361 / **0.518** | 8 |
| FF 32 | 0.587 / 0.569 / 0.459 | **0.652** / 0.536 / **0.514** | 16 |

50 and 32: clear wins on frame_score and lpips (+0.065, +0.055); the gradient holdout falls its usual ~0.03. 27 fails on
frame_score (hist 0.69 -> 0.50) with lpips flat, and the cause is the measurement: anime-seg merged the hanging cloth and
the lavender brick wall into 27's "character" (outline spans x 0.05-0.92), so the hair region is a tent and its measured
light tone [86,83,103] is the wall. `face_geometry.hair_region` now limits hair to 1.3 face widths either side of the face
centre and 1.5 face heights above the brows -- too loose to fix 27 (unchanged at 0.490), kept as a guard; no per-shot
fitting. Verdict left to the whole trailer: recreate_video.py --look measured (face / hair / body from measurements
where the script has them, lights tuned with those parts in place, 10 locks).

## 2026-09-22 -- whole trailer with the measured character look: a win on character shots, three failure modes

`recreate_video.py fragrant --rounds 6 --look measured` (queue job video_fragrant_measured, 1 h 43 min) vs video_v2
(same pipeline, ellipsoid proxy). lpips_holdout on all 2649 frames for both (rescore_perceptual.py; it now reads frames/
for whole-video runs -- before, it silently wrote 0.0 per frame when rendered/ was absent, and now it exits instead).

| shots | frames | v2 frame_score / grad / lpips | measured |
|---|---|---|---|
| whole trailer | 2649 | 0.462 / 0.503 / 0.470 | **0.486** / 0.480 / **0.491** |
| 43 with measured parts | 1662 | 0.471 / 0.462 / 0.471 | **0.509** / 0.426 / **0.505** |
| 20 without character | 987 | 0.446 / 0.571 / 0.469 | unchanged |

lpips rose on 34 of the 43 shots (largest S14 +0.209, S32 +0.144, S50 +0.111). The gradient holdout fell by 0.036, about
calibration noise for "right shapes, a few px off". Split verdict, so I looked at the frames (compare/v2_vs_measured.jpg,
middle frame of S59/46/49/14/32/31). On face shots the measured look is plainly closer: eyes, brows, hair colour and
mass in the right places. Kept as the whole-video look. Three failure modes, each a measurement fault, not a rendering one:
- **S59 title card (lpips -0.063)**: a tiny character with a face was placed on a watercolour title card that has no
  character in it. Character detection gives a false positive on text/texture shots.
- **S49 (grad -0.160)**: face landmarks rotated and the hair region fanned out as radial wedges across the frame; the
  character is half off-screen, hand over face.
- **S46 profile (lpips -0.040)**: no landmarks on a side view, so it falls back to the flat proxy, which is worse than
  the lit ellipsoid there.
Next: gate measured parts on detection confidence (face score, outline area vs. frame), fall back to the v2 proxy below
it, then re-run the trailer.

## 2026-09-22 -- landmark score gate (>= 0.9) on the whole trailer: a wash overall, fixes two shots, breaks two

video_gated = video_measured + two rules in apply_character_look: landmark keyframes scoring < 0.9 dropped (none left ->
lit proxy), flat body only with a measured face. lpips on all 2649 frames for all three runs.

| run | frame_score | grad holdout | lpips |
|---|---|---|---|
| video_v2 (proxy) | 0.462 | 0.503 | 0.470 |
| video_measured | **0.486** | 0.480 | 0.491 |
| video_gated | 0.483 | 0.480 | **0.493** |

Only the 13 shots the gate changed differ (others within 0.0016 frame_score). On those 570 frames lpips
v2 0.495 / measured 0.483 / gated 0.490, so the gate recovers most of the measured look's loss on low-confidence shots
but not all of it. Per shot (lpips, measured -> gated): S59 title card 0.484 -> 0.545, S46 profile 0.557 -> 0.597, S30
0.439 -> 0.439, S38 0.412 -> 0.426 -- fixed. S18 0.557 -> 0.473 (back of head, all keyframes ~0.77: the measured face
was a jumble of shards and still beat the ball proxy), S34 0.595 -> 0.537 -- worse. Frames: compare/gated.jpg.
S34 is a gate fault, not noise: its only passing keyframe is frame 0 (score 0.999, face box 0.30 x 0.66 of the frame),
the tail of the previous close-up, while the booth shot's real face is the 0.625 keyframe at frame 31 (box 0.06 x 0.14).
Keeping the passing keyframe and holding it for 64 frames placed a giant face on a wide shot. Score alone cannot tell
a real low-confidence face from a false one. Gate kept (whole-trailer lpips holds, the two visible faults are gone),
not a clear win. Next: reject keyframes whose face box disagrees with the shot's other keyframes and with
colour.regions.subject_bbox (cut-boundary spill), and only apply a keyframe to frames near it instead of holding one
keyframe for the whole shot.

## 2026-09-22 -- missed cuts fixed (isolated structural cuts), all references resegmented; Fragrant re-run

S34's regression under the score gate was not a detection fault: S34 was two shots. The cut at 1268 (profile close-up
-> wide booth shot) was detected raw but folded away by merge_similar's min_len (9 frames after the cut at 1259), and
1698 (stairwell -> corridor, same colours) failed the histogram test (0.39 < 0.6) despite the largest frame jump in the
trailer. ingest_reference.detect_isolated_cuts now keeps any jump with mad > 22 whose neighbours stay under 30 % of it
and whose blurred-gray correlation is < 0.3 (real missed cuts measured <= 0.22, a redrawn close-up 0.43). It adds 9
cuts across 4 references -- FF 1268, 1698; Blue Box 613, 2184, 2201; Silent Voice 704; Garden of Words 1182 -- each
checked by eye; FF 809 (drawing change) is rejected, Blue Box 2165 (ncc 0.45) is still missed.
training/resegment_shots.py carried per-shot files over (unsplit shots verified identical to the backups in
<reference>/backup_pre_resegment_20260922/), split shots were re-measured (outlines, landmarks, line art) and
re-described from their own contact sheets. Shot indices after the first new cut differ from all earlier runs.

Fragrant, --look measured with the score gate, frame ranges (lpips on all frames):

| frames | v2 fs / grad / lpips | measured | gated | resegmented |
|---|---|---|---|---|
| whole trailer | 0.462 / 0.503 / 0.470 | 0.486 / 0.480 / 0.491 | 0.483 / 0.480 / 0.493 | 0.484 / 0.481 / **0.495** |
| 1259-1267 (profile close-up) | 0.524 / 0.541 / 0.549 | 0.547 / 0.522 / 0.606 | 0.578 / 0.505 / 0.614 | **0.630 / 0.647 / 0.677** |
| 1268-1322 (wide booth) | 0.531 / 0.692 / 0.579 | 0.517 / 0.659 / 0.593 | 0.489 / 0.601 / 0.525 | 0.531 / 0.658 / **0.609** |
| 1680-1716 (stairwell, corridor) | 0.456 / 0.398 / 0.375 | same | same | 0.459 / 0.377 / 0.389 |

Old S34's frames go from the worst of the four runs to the best on all three metrics; the wide shot now carries its own
small face instead of the close-up's giant one (compare/resegmented.jpg). Best whole-trailer lpips so far. Open: the
profile face is crude, and the empty corridor (new S46) shows a stray pink sphere in every run. Not the character proxy (its spec
has character=None); origin not yet traced, to look at next.

## 2026-09-22 -- the pink sphere on FF 46 (empty corridor): a cascade false face became the subject proxy

Traced: blender_level3 places a generic "subject" ellipsoid whenever colour.regions has a subject box. For FF 46 that
box came from characters.face_track -- lbpcascade reports a "face" on 100 % of frames, on the sink taps (box x 0.18,
y 0.62; compare/s46_sphere.jpg). write_shot_scripts.py had the rule "vision pass saw no character -> no subject proxy",
but after the face-track branch, so it never ran when the cascade fired. Now checked first. Only FF 46 changes in the
five references (diffed every shot script before/after; Blue Box, mid-run, unchanged). The Sparkle scripts were stale
(written before colour.regions existed) and are now current -- no Sparkle run is affected.
Same tuned lights, sphere removed: frame_score 0.456 -> 0.452, lpips 0.289 -> 0.273 on 19 frames. The sphere scored
slightly better by accident, standing in for the pale sinks under it; kept the fix, since a character proxy on a shot
with no character is not a measurement of anything. Scene props (sinks, windows) are the real gap on empty shots.
