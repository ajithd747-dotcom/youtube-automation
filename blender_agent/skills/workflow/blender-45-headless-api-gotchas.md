---
id: blender-45-headless-api-gotchas
name: Blender 4.5 headless API facts that broke scripts
category: workflow
kind: pitfall
status: verified
applies_to:
- any
when_to_use: Writing or debugging bpy code that runs with `blender -b`.
triggers:
- bpy
- api
- error
- attributeerror
- keyerror
- headless
- blender 4.5
- script
- exception
- traceback
tags:
- api
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure (facts, each one cost a failed run)
- Engine ids: `BLENDER_EEVEE_NEXT` (4.2-4.5), `BLENDER_EEVEE` (5.x), `BLENDER_WORKBENCH`.
- Principled inputs: `Transmission Weight`, `Coat Weight`, `Emission Color`, `Emission Strength`.
- `ParticleSettings.use_render_emitter` is gone: `obj.show_instancer_for_render = False`.
- Empties have no `.field`: `bpy.ops.object.effector_add(type=...)`.
- `FCurves`: `action.fcurves` in 4.x, layered actions in 5.x (`scene_lib._fcurves` handles both).
- `text.dimensions` is stale until `view_layer.update()` and excludes the parent's scale at creation time.
- `bpy.ops.mesh.primitive_*_add` links to the active collection: unlink then link to `scene.collection` when parenting manually.
- A world **volume** rendered black (EEVEE Next, this GPU): use a volume box.
- `bpy.ops.wm.read_factory_settings(use_empty=True)` gives a clean scene and keeps the addon-free environment.
- `image.pixels` + numpy reads a rendered PNG for QA (luminance checks).
- Use the API dump (`python blender_agent/knowledge/kb.py search "<name>"`) before guessing names.
