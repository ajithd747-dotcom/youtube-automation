---
id: timeline-locked-narration
name: 'Narration that keeps the reference timeline: sentence-level TTS + tempo fit'
category: audio
kind: technique
status: verified
applies_to:
- any
when_to_use: Voice-over must land on fixed timestamps (recreating a video, syncing to a storyboard, matching a screen
  tour).
triggers:
- timeline
- timestamps
- sync narration
- same script
- recreate voiceover
- lock to timeline
- narration timing
- align tts
source:
- 'own-experience: tutorial recreation benchmark (2026-09-19)'
version: 1
tags:
- voice
- sync
---
## Procedure (recreate/tutorial_voice.py)
1. Transcribe the reference (faster-whisper) and split each segment into sentences; distribute each segment's time over its sentences by character count.
2. Fix systematic mis-hearings in the transcript (dictionary of regex fixes: Grease Pencil, EEVEE, grain, chromatic aberration...).
3. Voice agent picks the voice by median pitch (calibrated on a fixed sentence) and sets speed from measured wpm; pitch shift <= +-4 semitones.
4. Synthesize per sentence, place each clip at its original start; if a clip exceeds its slot by > 2 %, `atempo` up to 1.3x; keep word times scaled accordingly.
5. Master: mono files measure 3 dB lower than stereo for the same audio - compare like with like (reference mono -18.0 LUFS = stereo -14.7).
## Result (tutorial, 588 s)
pitch 121.2 Hz vs 119.4 Hz, pace 135 wpm vs 134 wpm, 130 sentences, duration 585.8 s vs 587.7 s. Kokoro on this CPU synthesised 10 minutes of speech in ~17 minutes.
