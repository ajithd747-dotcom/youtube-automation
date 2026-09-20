---
id: title-3d-glow-text
name: Glowing extruded 3D titles that fit and stay readable
category: composition
kind: technique
status: verified
applies_to:
- cinematic
when_to_use: A hook, chapter or ending needs on-screen text inside the 3D scene.
triggers:
- title
- headline
- text
- caption
- on screen text
- label
- 3d text
- logo
- heading
test: tests/text_fit.py
tags:
- text
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
1. `C.title_3d(text, loc, size, delay, width)`: font Arial Bold, extrude 0.08, bevel 0.015, pop-in with overshoot at `delay`.
2. Colours by mood: bright sky (day/sunset) -> dark navy letters `#1a2140`, faint warm emission; dark scenes -> white letters with strong emission (1.6) in an accent glow colour (pink, orange).
3. Fit: measure `dimensions.x` AFTER scaling and a `view_layer.update()`; shrink to fit `width` (default 9 m). Never scale the same text with both its font size and a parent empty.
4. Position: 4-4.5 m high for a standing character, 4.6 m for wide scenes; keep it clear of raised arms; 1-4 words.
5. Non-hero shots only show a small title (0.7 size at y 4): if it must be read, place it in the shot's own layout instead.

## Pitfalls
- White glow text on a bright sky is invisible (the first intro).
- 'Crash!' at size 0.7 was barely legible; give key words size >= 0.9 and a 0.3 s delay.
