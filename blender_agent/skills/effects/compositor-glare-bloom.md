---
id: compositor-glare-bloom
name: Bloom / glow via the compositor Glare node (and its NaN trap)
category: effects
kind: technique
status: verified
applies_to:
- cinematic
- 3d
when_to_use: 'Anything that should glow: neon, lamps, sparks, magic, emissive text, sun highlights.'
triggers:
- glow
- bloom
- neon
- glowing
- light
- shine
- halo
- radiant
- lamp
tags:
- compositor
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
1. `scene.use_nodes = True`; Render Layers -> Glare -> Composite. Glare type `BLOOM` (fallback `FOG_GLOW`), quality MEDIUM.
2. Threshold ~1.6 (only genuinely bright pixels), size 7, strength 0.7 (set via the node input `Strength`).
3. Make the glowing objects emissive with strength 2-14 in the shader; sparks 14, title text 0.5-1.6, eyes/chest glow 6.
4. Set EEVEE `clamp_surface_direct = 30`, `clamp_surface_indirect = 8`.

## Cost
Bloom is cheap (~0.3 s/frame at 720p on this laptop).

## Pitfalls
- A sun disc reflected in a glossy floor is astronomically bright: bloom turned it into a checkerboard of artefact squares (probably inf/NaN pixels). Clamping direct/indirect light (step 4) and keeping the sun energy at 2-3.5 removed them.
- Threshold 0.9 blooms the whole bright sky and hazes the picture.
