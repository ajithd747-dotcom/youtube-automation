---
id: compositor-node-api-45
name: Building compositor chains from Python (nodes, sockets, gotchas)
category: effects
kind: technique
status: verified
applies_to:
- any
when_to_use: 'Creating or animating compositor nodes by script: Glare, Blur, Mix, Lens Distortion, Filter, Defocus,
  Viewer.'
triggers:
- compositor
- node tree
- glare
- lens distortion
- defocus
- mix node
- viewer node
- z pass
- post processing script
source:
- 'own-experience: tutorial recreation benchmark (2026-09-19)'
version: 1
tags:
- compositor
---
## Procedure
- `scene.use_nodes = True` creates Render Layers + Composite in `scene.node_tree`.
- Nodes: `CompositorNodeGlare` (glare_type BLOOM; threshold/size/quality), `CompositorNodeBlur` (size_x/size_y), `CompositorNodeMixRGB` (blend_type COLOR/OVERLAY; inputs[0] = factor), `CompositorNodeLensdist` (use_projector, dispersion input), `CompositorNodeFilter` (filter_type SHARPEN...; inputs[0] = factor), `CompositorNodeDefocus` (use_zbuffer, f_stop keyframeable), `CompositorNodeViewer`, `CompositorNodeRGB`.
- Depth for Defocus: `view_layer.use_pass_z = True`; connect Render Layers `Depth` -> Defocus `Z`.
- Layout: set `node.location`; keep all in view with `bpy.ops.node.view_all()` in a node-editor `temp_override`.
- Animate f-stop: `d.f_stop = 128; d.keyframe_insert('f_stop', frame=1)` then 3.0 at the end.
## Cost
Glare is cheap; Blur/Defocus are CPU-expensive - prefer ffmpeg for blur-like post on long renders (see film-finish-ffmpeg).
