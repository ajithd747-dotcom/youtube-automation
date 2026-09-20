---
id: hook-promise-agenda-opening
name: Open with a question, a promise, then the agenda (first 30 s)
category: pacing
kind: rule
status: verified
applies_to:
- any
when_to_use: Writing or structuring the first seconds of an explainer / tutorial video.
triggers:
- intro
- hook
- opening
- explainer
- tutorial
- what if
- welcome
- today we
- agenda
- curious
tags:
- script
source:
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe@0:00-0:30
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe@9:00-9:40
- 'own-experience: tutorial recreation benchmark (2026-09-19)'
version: 2
---
## Procedure (tutorial 0:00-0:30, ~134 wpm)
1. 0-7 s: a curiosity question that promises a transformation ("What if a few clever tweaks could transform your animation into a cinematic masterpiece? Curious how? Stick around.").
2. Next ~10 s: "Welcome back ... today we are wrapping up X by doing Y".
3. Next ~10 s: agenda in one sentence: "We'll cover A for quick polish, B for advanced tweaks like C, D, then E".
4. Visual during the hook: the *finished result* (character in the final scene) with bold outlined 2-3 word captions; only then switch to the working screen.
5. A single soft call to action mid-way (sponsor/membership at ~3:00) and a subscribe ask at the end (9:30).

## Numbers
Speech rate 134 wpm (tutorial 1) vs 197 wpm (tutorial 2, rushed); calm explainers sit near 130-160 wpm.

## Implemented (verified)
Recreation intro: 38 s reel of the agent's own anime clip with 2-3 word huge yellow outlined captions timed to the narration words (voice agent `captions.write_ass(style='hook')`), then a 3 s 'Get the source files' card.
