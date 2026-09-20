---
id: camera-impact-shake
name: Decaying camera shake on impact
category: camera
kind: technique
status: verified
applies_to:
- cinematic
- 3d
when_to_use: Collisions, explosions, landings, heavy hits.
triggers:
- impact
- shake
- explosion
- hit
- boom
- crash
- landing
- punch
- earthquake
exemplar: exemplars/crate_smash.mp4
tags:
- camera
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
For `k` frames after the impact frame `f0`: offset the camera position by a random vector in [-a, a]^3 with `a = 0.18 * exp(-k / 6)`, key every frame (LINEAR) for ~0.7 s, then continue the normal move. Total shake amplitude <= 0.2 m at 8 m distance.

## Pitfalls
- Re-key the *whole* camera path in that range (base path + noise), otherwise the shake fights the dolly.
- Do not shake earlier than 1 s into the shot or the setup is lost.
