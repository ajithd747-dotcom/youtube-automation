---
id: calm-deep-narration-voice
name: Choose the narration voice to match the content
category: audio
kind: rule
status: reference
applies_to:
- any
when_to_use: Selecting or configuring text-to-speech for a video.
triggers:
- voice
- narration
- voiceover
- tts
- calm
- deep
- premium
- energetic
- serious
- comedy voice
tags:
- tts
source:
- video:how-to-create-viral-stickman-animations-with-ai-100-free@8:00-8:30
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe@0:00-9:30
version: 1
---
## Procedure
- Psychology / self-improvement / emotional explainers: deep, calm, slow (edge-tts `en-US-ChristopherNeural` or `EricNeural`, rate -5..-10%). The reference asks for "Deep and calm and premium".
- Comedy / stickman jokes: energetic (`en-US-GuyNeural`, rate +0..+8%).
- News / crime: serious (`ChristopherNeural`).
- Aim for 130-160 wpm; leave 0.3-0.4 s of air after each segment (the agent pads 0.35 s).
