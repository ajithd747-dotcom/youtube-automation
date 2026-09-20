---
id: gp-shader-effects-glow-rim-blur-colorize
name: 'Grease Pencil effects stack: glow, rim light, soft blur, colorize'
category: style-2d
kind: technique
status: verified
applies_to:
- stickman
- kinetic
- 2d
when_to_use: 'A hand-drawn / 2D Grease Pencil look needs quick polish: warm glow, back-light outline, softened digital
  edges, colour matched to the background.'
triggers:
- grease pencil
- 2d animation
- glow
- rim light
- outline glow
- cartoon
- hand drawn
- anime
- cel
- colorize
- effects
tags:
- grease pencil
source:
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe@0:30-3:00
- 'own-experience: tutorial recreation benchmark (2026-09-19)'
version: 2
---
## What it achieves
Non-destructive polish on a Grease Pencil object in a few clicks, live in EEVEE.

## Procedure (tutorial 0:30-3:00)
1. Select the Grease Pencil object -> Properties -> Effects tab (magic-wand icon). Effects stack like filters and can be reordered/toggled.
2. **Glow**: mode Luminance, blend Add, tune Threshold to catch only the bright highlights, Opacity for strength, Size for spread.
3. **Rim light**: blend Add, pick the rim colour, use Offset to place the back-light, Blur to smooth, Samples for quality.
4. **Blur**: very small size; softens vector-sharp edges for a vintage feel. Too high = mushy.
5. **Colorize**: custom mode, subtle hue matching the scene (the tutorial uses green), Factor slider to dilute; unifies character and background.
6. Extras: Shadow, Pixelate, Wave distortion; Blur in Depth-of-Field mode uses the camera's DOF settings.
7. Order matters: glow -> rim -> blur -> colorize worked best.

## Pitfalls
- In Blender 4.3+ Grease Pencil is the new GPv3 data type and the effects API/UI moved; verify property names on the installed version before scripting.
- Keep glow Threshold high or the whole picture blooms.

## Implemented (verified in Blender 4.5)
Scripted and screen-recorded end to end (glow -> rim -> blur -> colorize, values tweened live): see grease-pencil-effects-python-45 and blender-gui-screen-recording.
