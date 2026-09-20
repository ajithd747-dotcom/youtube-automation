---
id: music-duck-under-voice
name: Sidechain duck the music and master to -14 LUFS
category: mixing
kind: rule
status: verified
applies_to:
- any
when_to_use: Mixing music with narration.
triggers:
- duck
- sidechain
- voice over
- narration
- mix
- levels
- loudness
- lufs
- under voice
source:
- video:blender-grease-pencil-practice-fantasy-anime-scene (audio analysis)
- video:can-you-relate-4k-memes-animation-shorts (audio analysis)
- 'own-experience: ada_chain_reaction + reference-clip analysis (2026-09-19)'
version: 1
---
## Procedure
1. ffmpeg `sidechaincompress=threshold=0.02:ratio=8:attack=50:release=350` with the narration as the sidechain, then `amix=inputs=2:normalize=0`.
2. Music sits ~13 dB below the voice while speaking, returns in gaps; in a tutorial keep the bed at -15..-20 dB.
3. Final master: two-pass `loudnorm` I=-14, TP=-1.0, LRA=11 (references measured -14.3, -14.4, -14.7 LUFS).
4. Check with `analyze.py`: LUFS within 1 dB of target, true peak <= -0.3 dB.
