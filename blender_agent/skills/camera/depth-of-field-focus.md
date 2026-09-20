---
id: depth-of-field-focus
name: 'Depth of field: focus object, aperture and when to open it up'
category: camera
kind: rule
status: verified
applies_to:
- cinematic
- 3d
when_to_use: 'Choosing DOF for a shot: intimate/cinematic vs busy background.'
triggers:
- depth of field
- dof
- bokeh
- blur
- focus
- f-stop
- aperture
- background blur
- cinematic
tags:
- camera
- dof
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Rules
- Enable `cam.data.dof.use_dof`, set `focus_object` to the target empty (follows moving subjects), `aperture_fstop`.
- f/2.0-2.6 for hero shots with plain backgrounds (intro, glass, walk); f/3.5-5 when the background has structure or the subject is far (cloth, fireworks f/5).
- The neon stripe world at f/2.4 turned into a blur soup: use f/4+ when the environment is bright and patterned.
- Depth of field in EEVEE Next costs little; the Defocus compositor node is far more expensive.
