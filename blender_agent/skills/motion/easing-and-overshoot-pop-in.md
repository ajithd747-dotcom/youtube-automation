---
id: easing-and-overshoot-pop-in
name: 'Springy entrances: overshoot 12-15% then settle'
category: motion
kind: technique
status: verified
applies_to:
- any
when_to_use: 'Anything appearing on screen: titles, props, characters, icons.'
triggers:
- appear
- pop in
- entrance
- overshoot
- spring
- bounce in
- reveal
- easing
- ease
test: tests/pop_in_overshoot.py
tags:
- easing
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
- Scale from ~0 (hold at 0.001 until the delay) -> 1.12-1.15 over ~60% of the entrance -> 1.0 by frame +14 (0.55 s at 24 fps), BEZIER.
- Slide-ins: start off-screen 0.7 x frame width/height away, ease to the target in 0.55 s.
- Use LINEAR for anything that must carry constant speed into a physics release (see rigid-body-launch-release) and for camera dollies.
- Stagger multiple objects by 0.3-0.4 s so each gets its own beat.

## Code
```python
key(root, 1, scale=(0.001,) * 3, interp="CONSTANT")
key(root, f0 + 8, scale=(1.12,) * 3, interp="BEZIER")
key(root, f0 + 14, scale=(1, 1, 1), interp="BEZIER")
```
