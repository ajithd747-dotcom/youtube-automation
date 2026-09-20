---
id: pbr-glass-gold-chrome
name: 'PBR material recipes: glass, gold, chrome, coated paint, emissive'
category: materials
kind: technique
status: verified
applies_to:
- cinematic
- 3d
when_to_use: 'Any 3D object that should look real: glass, gold, chrome, painted plastic, glowing parts.'
triggers:
- glass
- gold
- chrome
- metal
- paint
- plastic
- glossy
- material
- emissive
- crystal
tags:
- materials
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Parameters (Principled BSDF)
- Glass: base white, transmission weight 1.0, IOR 1.5, roughness 0.02 (needs ray tracing + a bright environment).
- Gold: `#d4af37`, metallic 1, roughness 0.15-0.18.
- Chrome: `#e8e8ee`, metallic 1, roughness 0.02-0.12.
- Glossy paint: base colour, coat weight 0.5-1.0 (red ball, dominoes).
- Wood crate: `#a9743f`, roughness 0.65.
- Jelly: transmission 0.85, IOR 1.35, roughness 0.12.
- Emission: set `Emission Color` and `Emission Strength` (2-14).

## Pitfalls
- Input names in 4.x: "Transmission Weight", "Coat Weight", "Emission Strength" (older names raise KeyError).
- Enable EEVEE ray tracing for refraction (`use_raytracing`, resolution scale 2, max roughness 0.5).
