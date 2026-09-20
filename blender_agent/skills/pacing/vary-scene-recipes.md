---
id: vary-scene-recipes
name: Do not repeat a scene type in consecutive shots
category: pacing
kind: rule
status: verified
applies_to:
- cinematic
when_to_use: Assigning scene recipes/moods to consecutive script segments.
triggers:
- variety
- repeat
- monotony
- recipe
- next shot
- different look
- sequence
tags:
- director
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Rules
- Pass the list of already used recipes to the director; reject an answer equal to the previous one.
- Alternate mood between neighbours (studio -> day -> sunset -> night -> neon) and alternate calm shots with physics shots.
- Repeat a recipe only after >= 3 other shots and change its mood/title (the ada video reuses `robot_intro` in neon at segment 9).
