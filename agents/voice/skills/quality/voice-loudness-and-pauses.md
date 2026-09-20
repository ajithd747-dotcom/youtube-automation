---
id: voice-loudness-and-pauses
name: Level, pauses and clean segment edges
category: quality
kind: rule
status: verified
applies_to:
- any
when_to_use: Final QA of narration audio.
triggers:
- loudness
- pauses
- silence
- level
- clipping
- clean
- edges
- gaps
source:
- 'own-experience: ada_chain_reaction + reference-clip analysis (2026-09-19)'
version: 1
---
## Rules
- Narration alone at about -16 LUFS so that voice + ducked music master to -14 LUFS.
- Trim leading silence > 0.15 s; keep 0.25-0.4 s between sentences, 0.6 s between ideas.
- Active-speech ratio 0.75-0.9; below 0.7 the delivery drags.
