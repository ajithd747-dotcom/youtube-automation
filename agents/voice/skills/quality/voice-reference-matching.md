---
id: voice-reference-matching
name: Match a reference narrator's pitch and pace (never clone a person)
category: quality
kind: technique
status: verified
applies_to:
- any
when_to_use: Making narration sound like the same kind of voice as a reference video (benchmarks, house style).
triggers:
- reference voice
- same voice
- match voice
- sound like
- pitch
- narrator
- recreate
- voice over same
source:
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe
- 'own-experience: tutorial recreation benchmark (2026-09-19)'
version: 2
---
## Procedure
1. Measure the reference: median f0 (autocorrelation, voiced frames), p10/p90, wpm from its transcript, LUFS.
2. `calibrate_voices()`: synthesise a fixed sentence with every candidate voice, cache f0 + wpm.
3. Choose the voice with the nearest f0; speed = ref wpm / voice wpm; pitch shift = 12 log2(ref f0 / voice f0) semitones (clamped +-4) with ffmpeg `asetrate + atempo`.
4. Re-measure and iterate; loudness to the reference LUFS.
## Ethics
This matches *characteristics* with a stock TTS voice. Do not clone a real person's voice from their videos without their consent.

## Implemented (verified) - tutorial narrator
Reference: median f0 119.4 Hz, 134 wpm overall. Chosen: Kokoro `am_adam` speed 1.035, +0.26 semitones -> measured 121.2 Hz, 135 wpm.
