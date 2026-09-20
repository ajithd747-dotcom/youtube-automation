---
id: narration-driven-shot-length
name: Shot length = narration length + padding; make the physics fit
category: pacing
kind: rule
status: verified
applies_to:
- any
when_to_use: Deciding how long each shot lasts and whether an event fits inside it.
triggers:
- duration
- timing
- shot length
- narration
- sync
- length
- seconds
- fit
- pace
tags:
- timing
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Rules
- Shot duration = audio duration + 0.35 s (agent default). Speech rate ~2.6 words/s.
- Sim events must finish inside the shot: domino wave 0.17 s per domino (+1.7 s lead-in), crate impact at ~1.5 s with >= 2.5 s of aftermath, fireworks bursts spread over `T - 1.5 s`, cloth needs ~0.6 s wind ramp.
- Size scenes to the duration: `count = (T - 2) / 0.17` dominoes (26 for 7.5 s).
- Typical ada video: 10 segments, 4.2-7.5 s each = 55 s.
