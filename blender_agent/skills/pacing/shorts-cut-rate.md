---
id: shorts-cut-rate
name: Cut rate and shot length for shorts vs tutorials
category: pacing
kind: rule
status: reference
applies_to:
- any
when_to_use: Deciding how many shots a video needs and how long each should last.
triggers:
- pacing
- cut rate
- shot length
- shorts
- retention
- editing rhythm
- fast cuts
- how many shots
tags:
- metrics
source:
- video:videoplayback-7
- video:videoplayback-8
- video:blender-grease-pencil-practice-fantasy-anime-scene
- video:can-you-relate-4k-memes-animation-shorts
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe
version: 1
---
## Measured (scene-cut detection + frame-difference motion)
| video | length | shots | mean shot | cuts/min | motion |
|---|---|---|---|---|---|
| videoplayback (7) vertical comedy | 30 s | 12 | 2.5 s (median 1.8) | 22 | 19 |
| videoplayback (8) vertical comedy | 15 s | 8 | 1.8 s (median 1.5) | 29 | 27 |
| anime action clip | 12 s | 5 | 2.3 s | 20 | 33 |
| meme short (one continuous drawn take) | 11 s | 1 | - | 0 | 14 |
| Blender tutorial (screencast) | 588 s | 20 | 29 s (median 10 s) | 1.9 | 4 |

## Rules
- Shorts/comedy: 1.5-2.5 s per shot, alternate wide / close-up; a new visual event every ~2 s.
- Explainers with narration: 4-8 s per shot (the agent uses narration length + 0.35 s).
- Tutorials: hold long, cut on workflow changes.
