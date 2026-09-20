---
id: particle-hair-fur
name: Fur and hair with particle hair (fuzzy creature recipe)
category: physics
kind: recipe
status: verified
applies_to:
- cinematic
when_to_use: Fur, fluffy animals, pets, hair, grass-like strands, soft cute characters.
triggers:
- fur
- fluffy
- hair
- pet
- cute
- animal
- furry
- soft
- creature
- strands
- fuzzy
source:
- 'own-experience: fx recipes (Blender 4.5 Mantaflow / hair particles, 2026-09-19)'
version: 1
uses_recipe: fuzzy_creature
tags:
- hair
- particles
---
## Procedure (recipe `fuzzy_creature`)
1. Emitter mesh (sphere body) + particle system `type='HAIR'`: count 1800 (draft) / 4500, `hair_length` 0.34, `child_type='INTERPOLATED'`, `child_percent` 4, `rendered_child_count` 8, `child_radius` 0.12, `clump_factor` 0.45, `roughness_1` 0.06, `root_radius` 0.012, `tip_radius` 0, `use_close_tip`, `render_type='PATH'`.
2. Names differ from older tutorials: it is `child_percent` (not `child_nbr`).
3. Fur colour = the body's Principled material (`#ffb45a`, roughness 0.55); eyes are glossy spheres; ears/feet ovals.
4. Life: squash & stretch bounce keyed every 0.25 s (scale z 0.88..1.05) + a WIND effector (strength 4, noise 1.5).
5. Camera 45 mm f/2.4 at 4.2 m.
## Pitfalls
- Hair looks like a fuzzy sphere unless the light rakes across it: use a backlight/rim; the day mood washed it out in the first test (QA agent: exposure -0.6).
