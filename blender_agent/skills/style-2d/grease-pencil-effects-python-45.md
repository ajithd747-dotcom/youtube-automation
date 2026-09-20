---
id: grease-pencil-effects-python-45
name: Grease Pencil objects and shader effects from Python (Blender 4.5)
category: style-2d
kind: technique
status: verified
applies_to:
- 2d
- stickman
- any
when_to_use: 'Scripting Grease Pencil (2D) objects and their Effects: glow, rim light, blur, colorize, shadow, pixelate,
  wave.'
triggers:
- grease pencil
- shader effect
- fx_glow
- fx_rim
- fx_blur
- fx_colorize
- 2d animation python
- gpencil
- monkey
source:
- 'own-experience: tutorial recreation benchmark (2026-09-19)'
version: 1
tags:
- grease pencil
---
## Procedure
- Object: `bpy.ops.object.grease_pencil_add(type='MONKEY'|'STROKE'|'EMPTY'|'LINEART_SCENE'...)`; recolour via `mat.grease_pencil.color`, `.fill_color`, `.show_fill`.
- Effects: `obj.shader_effects.new(name, 'FX_GLOW')`; types FX_BLUR, FX_COLORIZE, FX_FLIP, FX_GLOW, FX_PIXEL, FX_RIM, FX_SHADOW, FX_SWIRL, FX_WAVE.
  - Glow: `mode='LUMINANCE'`, `threshold` (lower = more glows), `opacity`, `size=(x,y)`, `samples`, `glow_color`.
  - Rim: `mode='ADD'`, `rim_color`, `offset=(x,y)` px, `blur=(x,y)` px.
  - Blur: `size=(x,y)`, `samples`, `use_dof_mode`.
  - Colorize: `mode='CUSTOM'`, `low_color`, `factor`.
  - Toggle with `fx.show_viewport` / `show_render`.
- Brightness matters: glow on LUMINANCE finds nothing on dark strokes - use bright strokes on a dark background.
- Stack order used in the tutorial: glow -> rim -> blur -> colorize.
