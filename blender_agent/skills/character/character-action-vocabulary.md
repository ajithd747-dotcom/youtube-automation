---
id: character-action-vocabulary
name: Pick the character action from the meaning of the line
category: character
kind: rule
status: verified
applies_to:
- any
when_to_use: Choosing which animation cycle a character performs for a script segment.
triggers:
- action
- gesture
- animation choice
- wave
- think
- point
- celebrate
- sad
- jump
- talk
- run
tags:
- actions
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Rules
| narration says | action | why |
|---|---|---|
| hello, meet, welcome, greeting | `wave` | raised right arm, elbow oscillates 9 rad/s |
| wonder, idea, decide, hmm, question | `think` | hand to chin, small head tilt |
| look, notice, see, this one | `point` | arm horizontal |
| explains, describes, states a fact | `talk` | alternating arm gestures + head nod (default for narration) |
| win, success, thanks, cheers | `celebrate` / `jump` | both arms up, hops |
| fail, tired, bored, stuck | `sad` | head down, torso 8 deg forward |
| rushes, chases, hurries | `run` | larger swing, forward lean |
| goes, travels, arrives | `walk` | with root motion |
Default to `talk` or `idle` when unsure; never repeat the same action for more than two consecutive shots.
