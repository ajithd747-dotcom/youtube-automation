---
id: robot-character-rig
name: 3D robot character rigged from empties, greeting / celebrating on a glossy floor
category: character
kind: recipe
status: verified
applies_to:
- cinematic
- 3d
when_to_use: The narration introduces a character, greets the viewer, or celebrates; a friendly 3D mascot is needed.
triggers:
- meet
- introduce
- hello
- welcome
- robot
- mascot
- character
- hero
- greeting
- wave
- cheer
uses_recipe: robot_intro
test: tests/camera_framing.py
exemplar: exemplars/robot_intro.mp4
tags:
- rig
- recipe
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
A 1.8 m stylised robot (white coated body, dark joints, glowing eyes/chest/antenna) that can wave, walk, celebrate and think - no armature needed.

## Procedure
1. `root, j = C.build_robot(loc, color="#e8edf5", accent="#22d3ff", scale=1.0)` builds a hierarchy of empties (pelvis, torso, neck, head, l/r shoulder, elbow, hip, knee); meshes are parented to the joints.
2. `C.animate_robot(j, action)` keys the joint rotations every 2 frames from the shared pose functions (`idle walk run wave jump celebrate think point talk sad`) plus pelvis bob.
3. Frontal view (facing the camera at -Y): plane="front" (swing about local Y). Profile view (walking sideways): rotate `root` +90 deg about Z (faces +X) and use plane="side" (swing about local X).
4. Camera for a standing shot: 30-32 mm, distance 9-10.5 m, target z 1.7-2.0 so the head, raised arm and a title above all fit.
5. Recipe `robot_intro` adds a gold ring and a glass sphere either side and a floating title.

## Pitfalls
- Title at z 3.3 collided with the head/antenna; use z >= 3.9 (4.5 when arms are raised).
- Change of accent colour (`accent="#ff4fd8"`) recolours the glow parts only - keep the body colour constant across shots for consistency.
