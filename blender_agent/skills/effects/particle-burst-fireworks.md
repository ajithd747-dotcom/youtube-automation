---
id: particle-burst-fireworks
name: 'Fireworks: instanced spark bursts with light flashes and bloom'
category: effects
kind: recipe
status: verified
applies_to:
- cinematic
when_to_use: Fireworks, sparks, explosions of light, celebration at night, a magical finale.
triggers:
- fireworks
- sparks
- burst
- night sky
- celebrate
- explosion
- sparkle
- finale
- magic
uses_recipe: fireworks
test: tests/particle_burst.py
exemplar: exemplars/fireworks.mp4
tags:
- particles
- recipe
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## What it achieves
Several coloured spherical bursts over a dark reflective lake; each burst also flashes a light that illuminates water and fog.

## Procedure
1. Recipe `fireworks`, mood `night`, fog 0.5, mirror floor (`#050810`, roughness 0.03, metallic 0.9).
2. Per burst: hidden spark source (small emissive sphere, emission 14, `hide_render=True`) + emitter icosphere (subdivisions 3, 642 verts) at (x -8..8, y 16-24, z 9-13).
3. Particle settings: count 520, `frame_start = burst frame`, `frame_end = +1` (single-frame emission), lifetime 55 (+-40%), `emit_from="VERT"`, `normal_factor` 9, `factor_random` 1.4, gravity weight 0.25, `render_type="OBJECT"`, `instance_object = spark`, size 1 (+-50%).
4. Hide the emitter with `emitter.show_instancer_for_render = False`.
5. Flash: POINT light energy keyed 0 -> 60000 W at the burst frame -> 0 after 0.35 s.
6. Camera far back: lens 24, f/5, from (0, -10, 1.5) rising to z 2.6, looking at (0, 20, 8).
7. Compositor Glare (bloom) threshold ~1.6 makes the sparks glow.

## Pitfalls
- `ParticleSettings.use_render_emitter` no longer exists in Blender 4.5: use the object property `show_instancer_for_render`.
- 250000 W flashes wash the whole frame purple; 60000 W is enough.
- Stagger bursts across the shot: `t = 0.3 + i * (T - 1.5) / n`, hue steps of 0.19.
