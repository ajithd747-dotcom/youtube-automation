---
id: consistent-character-base-prompt
name: Define the character once, repeat it verbatim in every scene
category: workflow
kind: rule
status: reference
applies_to:
- any
when_to_use: A video with a recurring character across many shots/scenes must not change look between shots.
triggers:
- character
- consistent
- same character
- recurring
- mascot
- protagonist
- series
tags:
- consistency
source:
- video:how-to-create-viral-stickman-animations-with-ai-100-free@2:30-3:30
version: 1
---
## Procedure (tutorial 2:30-3:30)
1. Generate a **base prompt/description** first (e.g. "Simple black stickman with a round head, clean smooth lines, minimalist, expressive face, consistent proportions, medium line thickness, flat illustration, white background, soft emotional tone").
2. Paste that base text unchanged into every scene's prompt; only Pose/Action/Expression/Prop/Background vary.
3. Work in parts (about 1 minute of script per part) but reuse the same base block so parts match.
4. Check consistency by putting two scenes side by side before animating.

## In this agent
Keep character parameters in the plan (rig, colour, proportions, accent colour) and pass the same values to every shot: the robot uses `build_robot(color, accent, scale)` with fixed defaults per video; do not randomise per shot.
