---
id: scene-by-scene-production-loop
name: 'Production loop: per scene = visual + motion + voiceover, then assemble'
category: workflow
kind: rule
status: reference
applies_to:
- any
when_to_use: Planning the pipeline for any narrated animated video.
triggers:
- workflow
- pipeline
- storyboard
- shot list
- script to video
- production
- assemble
- parts
tags:
- pipeline
source:
- video:how-to-create-viral-stickman-animations-with-ai-100-free@1:00-8:30
version: 1
---
## Procedure (tutorial 1:00-8:30)
1. Pick topic + length; write the script in parts.
2. Per scene produce three things: a still/visual spec, a motion (animation) spec, and the voiceover text.
3. Generate visuals for all scenes first, check them side by side, then animate each (start-frame -> motion prompt).
4. Voiceover: feed the whole part as ONE paragraph to the TTS (natural prosody); deep, calm, premium voice for psychology content.
5. Import visuals in scene order, lay the voiceover, auto-generate captions ("normal" style), export.

## In this agent
This is `agent.py`: segments -> voiceover -> director shot spec (visual+motion) -> Blender render -> mux + captions. Improvement noted: TTS per whole paragraph then split by word timings keeps prosody continuous.
