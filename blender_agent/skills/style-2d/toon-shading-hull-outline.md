---
id: toon-shading-hull-outline
name: Cel shading + inverted-hull outlines in EEVEE Next
category: style-2d
kind: technique
status: verified
applies_to:
- cinematic
- 3d
- 2d
- anime
when_to_use: 'An anime / cartoon / cel-shaded 3D look: flat colour bands with black outlines.'
triggers:
- toon
- cel shading
- cel-shaded
- anime
- outline
- cartoon 3d
- flat shading
- ink lines
- comic
tags:
- toon
source:
- 'own-experience: anime-clip recreation benchmark (2026-09-19)'
version: 1
---
## Procedure
1. Material: Diffuse (white) -> Shader to RGB -> ColorRamp (interpolation CONSTANT: 0.0 shadow, 0.34 base, 0.78 highlight) -> Emission. Shadow colour = base x 0.55 with a cool tint (0.85, 0.75, 1.0); highlight = base x 1.18 + 0.02.
2. Outline: a second material slot (black emission, `use_backface_culling=True`) + Solidify modifier: thickness -0.006..-0.05 (scale with object size), offset 1, `use_flip_normals=True`, `material_offset=1`.
3. Render: Standard view transform, sun light 3.0, ray tracing/shadows off, 8 samples: ~1.4 s/frame at 1920x1080 on this laptop (vs 3-6 s for the physically based look).
4. Background/FX use flat Emission materials so they stay unshaded; glowing FX emission 6-8 + compositor Glare threshold 1.4.
## Pitfalls
- Shader-to-RGB only works with EEVEE, and only sees lights that reach the Diffuse node: add a sun.
- Outline thickness in metres: 0.008 for small armour, 0.012 limbs, 0.03-0.05 for buildings.
