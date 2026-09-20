---
id: voice-word-timings-for-sync
name: Use word timings for captions, cuts and pauses
category: sync
kind: technique
status: verified
applies_to:
- any
when_to_use: Synchronising visuals or captions to narration.
triggers:
- word timing
- timestamps
- sync
- lip sync
- align
- captions timing
- cut on the word
- word boundary
source:
- 'own-experience: ada_chain_reaction + reference-clip analysis (2026-09-19)'
version: 1
---
## Procedure
- Kokoro returns per-token start/end (seconds) from the model; edge-tts emits WordBoundary events (offset/duration in 100 ns ticks).
- Store `words=[{text,start,end}]` per clip; shift by the clip's start on the timeline for global timing.
- Cut/emphasise on the word that carries the meaning; start a visual event 0.1-0.2 s before its word.
- Mouth movement: derive open/close from the RMS envelope of the audio (0.05 s frames) or from word spans.
