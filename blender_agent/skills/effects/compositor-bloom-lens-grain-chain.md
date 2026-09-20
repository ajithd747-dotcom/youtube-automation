---
id: compositor-bloom-lens-grain-chain
name: 'Compositor chain: bloom, colour bleed, lens dispersion, film grain, sharpen, defocus'
category: effects
kind: technique
status: verified
applies_to:
- cinematic
- 3d
- any
when_to_use: 'A finished shot should look cinematic or vintage: glow, chromatic edges, grain, animated depth of
  field.'
triggers:
- cinematic
- vintage
- film grain
- chromatic aberration
- lens distortion
- bloom
- depth of field
- defocus
- color bleed
- polish
- compositing
tags:
- compositor
source:
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe@3:30-7:30
- 'own-experience: tutorial recreation benchmark (2026-09-19)'
version: 2
---
## What it achieves
A layered post chain that upgrades any render without re-rendering the 3D.

## Procedure (tutorial 3:30-7:30)
1. Compositing workspace, tick **Use Nodes**. Render Layers -> ... -> Composite. Add a Viewer to preview any socket.
2. **Colour bleed**: Blur (slight) mixed with the original in a Mix node, blend `Color`, small factor.
3. **Bloom**: Filter > Glare, type Bloom; tune threshold, strength, size.
4. **Lens**: Transform > Lens Distortion, Projector mode, a tiny Dispersion -> chromatic aberration.
5. **Grain**: load a grain video/image, Mix with `Overlay`, factor 0.1-0.2.
6. **Sharpen**: Filter > Box Sharpen, small factor (recovers sharpness lost to distortion).
7. **Animated depth of field**: Blur > Defocus; connect the Z/Depth output of Render Layers (enable View Layer > Z pass); keyframe the F-stop.

## Cost on this laptop (measured) - do the cheap ones in ffmpeg
- Glare bloom is cheap (~0.3 s/frame at 720p); Blur/Defocus nodes are not (a 260 px blur cost ~3 s/frame).
- ffmpeg equivalents: chromatic `rgbashift=rh=2:bh=-2`, grain `noise=alls=6:allf=t`, sharpen `unsharp=5:5:0.4`, colour bleed `gblur` + `blend=all_mode=screen:all_opacity=0.25`.

## Pitfalls
- Previewing the compositor in the viewport is CPU heavy (tutorial 5:00).

## Implemented (verified in Blender 4.5)
The chain Blur+Mix(Color) -> Glare(Bloom) -> Lens Distortion(projector, dispersion 0.03) -> grain Mix(Overlay 0.15) -> Filter(Sharpen 0.12) -> Defocus(Z pass, f-stop 128 -> 3) was built live by script and recorded; details in compositor-node-api-45.
