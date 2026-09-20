---
id: voice-speaking-rate-targets
name: Speaking-rate targets and how to hit them
category: prosody
kind: rule
status: verified
applies_to:
- any
when_to_use: Setting narration speed or checking that it is neither rushed nor slow.
triggers:
- speed
- pace
- wpm
- words per minute
- rate
- slow
- fast
- rushed
- tempo of speech
source:
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe (134 wpm)
- video:how-to-create-viral-stickman-animations-with-ai-100-free (197 wpm)
version: 1
---
## Targets (measured on the references)
Tutorial narrator 134 wpm; calm psychology 120-140; explainer 140-160; comedy 160-180; a stumbling-fast 197 wpm sample (stickman tutorial) is too fast to follow.
## Procedure
1. Synthesize, `measure.stats(path, words=words)` -> wpm_speaking (words / speech time, pauses excluded).
2. New speed = old speed x target/measured; Kokoro accepts 0.7-1.4.
3. Add 0.35 s of air after every segment.
