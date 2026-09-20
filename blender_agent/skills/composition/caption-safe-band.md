---
id: caption-safe-band
name: Reserve the caption band so nothing collides with subtitles
category: composition
kind: rule
status: verified
applies_to:
- any
when_to_use: Laying out any shot that will get burned-in captions.
triggers:
- captions
- subtitles
- safe area
- bottom band
- text overlap
- layout
- portrait
tags:
- layout
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Rules
- Landscape: captions occupy the bottom ~15%; nothing may extend below z = -0.72 (normalised frame). Portrait: bottom ~25%; floor -0.5. ASS font size 5.2% of height (landscape) / 3% (portrait), 2 lines max in landscape.
- Multi-line 3D/2D text: estimate height as `lines * 0.9 * size`; wrap at 26 chars (landscape) / 13 (portrait).
- Portrait 9:16: stack objects vertically, max 5 objects per shot.
