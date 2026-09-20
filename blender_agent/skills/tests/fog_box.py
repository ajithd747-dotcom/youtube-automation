# TEST volumetric-fog-box: haze as a bounded volume cube (a world volume renders black in EEVEE Next on this GPU).
import bpy
import numpy as np
box = C.add_fog(0.008)
assert box.data.materials and any(n.bl_idname == "ShaderNodeVolumePrincipled" for n in box.data.materials[0].node_tree.nodes)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 160, 90
sc.render.filepath = bpy.app.tempdir + "fogtest.png"
bpy.ops.render.render(write_still=True)
img = bpy.data.images.load(sc.render.filepath)
px = np.array(img.pixels[:]).reshape(-1, 4)[:, :3]
assert px.mean() > 0.03, f"scene rendered black with fog (mean {px.mean():.3f})"
