---
name: frame-script-standard
description: The mandatory standard for writing a script, storyboard or shot plan for an animated video in this project -- every frame/shot must record lighting, camera and subject motion, physics, composition, colour, transitions, audio and characters, each backed by a measurement or marked NOT MEASURED. Use whenever asked to write, extend, review or recreate a video script, a shot list, a per-frame script, or to recreate a reference video in Blender.
---

# Per-frame script standard

Owner's rule (2026-09-20): a script for a video is not a paragraph of intent. It is a **measured, per-frame description**
of what the video actually does, detailed enough that Blender can recreate it and a score can say how close it got.

**The one rule that decides everything: a value is either measured or it says `NOT MEASURED`.** No estimates from
imagination, no "typical anime lighting", no defaults filled in to make the table look complete. A complete-looking
table with invented numbers is worse than a sparse honest one, because the recreation loop will trust it.

## What every script covers

The canonical field list is `training/SPEC.md` section 4 -- read it, do not work from memory. In short:
lighting, colour, camera motion, subject motion, physics, depth/focus, composition, characters, transitions, audio,
and on-screen text (`NOT MEASURED` until an OCR pass exists). Units: positions are fractions of the frame (x right, y
down), speeds are frame-widths per frame, angles are degrees with 0 = right and 90 = down, luma is 0..1.

Two layers:
- **Layer A** `training/reference/<slug>/frames_table.jsonl`: one measured row per frame (`training/describe_frames.py`).
- **Layer B** `training/reference/<slug>/shots/<n>.json`: the script proper, built from Layer A per shot
  (`training/write_shot_scripts.py`): camera path, lighting rig, physics, motion, composition, palette and grade,
  transitions, audio, characters, `semantic`, and `blender_directives` (concrete Blender settings, each with
  `source_metric` and `confidence`).

## Procedure

1. Ingest the reference if it is not ingested: `.venv/bin/python training/ingest_reference.py --only <slug>`.
   This splits the video into every frame, measures Layer A on all cores, detects shots, extracts audio.
2. Build Layer B: `.venv/bin/python training/write_shot_scripts.py <slug>`. Read the output for the shot you were asked about.
3. Fill `semantic` (setting, characters, actions, mood, on-screen text) by **looking at the frames**: open the shot's
   contact sheet / key frames with the Read tool as images. Describe only what is visible. Anything you cannot see stays
   `NOT MEASURED`.
4. Check completeness: `.venv/bin/python training/check_script_completeness.py <slug>` lists every empty or unbacked
   field. A script is not done until that list is empty or each remaining item is deliberately `NOT MEASURED`.
5. Only then hand it to the Blender build. After a render, score it (`training/score_recreation.py`) and change the
   script in the direction the worst frames point -- one change per iteration so the score delta means something.

## Never

- Write a script from the video's title, thumbnail or your knowledge of the film.
- Put a guessed number in a measured field. Use `null` / `NOT MEASURED`.
- Copy reference frames into a recreation. Recreate from the measured description.
- Publish or upload anything derived from a reference video.
