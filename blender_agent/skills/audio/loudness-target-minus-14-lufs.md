---
id: loudness-target-minus-14-lufs
name: Master to about -14 LUFS
category: audio
kind: rule
status: reference
applies_to:
- any
when_to_use: Every final mix; tutorials/shorts that sound too quiet or too loud.
triggers:
- loudness
- volume
- quiet
- loud
- lufs
- normalize
- audio level
- mix
tags:
- ffmpeg
source:
- video:can-you-relate-4k-memes-animation-shorts
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe
- video:blender-grease-pencil-practice-fantasy-anime-scene
- video:how-to-create-viral-stickman-animations-with-ai-100-free
version: 1
---
## Evidence (measured with ffmpeg ebur128)
Meme short -14.3 LUFS, Blender tutorial -14.7, anime clip -14.4 (social-ready), stickman tutorial -22.0 (noticeably quiet).

## Procedure
Final mix: `loudnorm=I=-14:TP=-1.5:LRA=11` (single pass is fine for narration) after concatenation, so every segment has one consistent level. With music, duck it ~12-15 dB under the voice.
