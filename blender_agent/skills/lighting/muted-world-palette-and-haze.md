---
id: muted-world-palette-and-haze
name: Desaturate the environment and add haze so the subject and FX pop
category: lighting
kind: rule
status: verified
applies_to:
- any
when_to_use: A landscape or backdrop looks garish next to the character or effects; matching a muted anime/painterly
  reference.
triggers:
- muted
- desaturated
- haze
- atmosphere
- painterly
- background too saturated
- garish
- environment colour
- terrain
tags:
- colour
source:
- 'own-experience: anime-clip recreation benchmark (2026-09-19)'
version: 1
---
## Procedure
- Terrain bands (toon, noise scale ~16 on the plane's object coordinates): `#6f5a52, #8a6d5f, #a98a76, #bd9f8b, #a3a2a6`; sky `#a9b9c8` -> horizon `#dfe4e7`; clouds flat `#c9d2d9`.
- Grade: `eq=saturation=0.82:contrast=1.04` + a slight pink-cool tint in mids/highlights only.
- The only saturated colour in frame is the FX (magenta emission 6-8 + bloom).
## Measured
The first, saturated brown/orange desert scored histogram-intersection 0.44; the reference terrain is a desaturated pink-brown.
