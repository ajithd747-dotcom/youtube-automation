# TEST studio-softbox-stripe-world: reflective objects need a bright structured environment; a black world = black metal.
import bpy
import numpy as np
sc = C.setup(320, 180, 12, 2.0, mood="studio", quality="draft")
C.floor("#15181f", rough=0.05, metallic=0.4)
C.mesh("sphere", C.pbr("#e8e8ee", 1.0, 0.02), loc=(0, 0, 1.0), scale=(2, 2, 2))
C.camera((0, -7, 1.5), (0, -7, 1.5), (0, 0, 1.0), None, lens=45, fstop=0)
sc.render.filepath = bpy.app.tempdir + "studio.png"
bpy.ops.render.render(write_still=True)
img = bpy.data.images.load(sc.render.filepath)
px = np.array(img.pixels[:]).reshape(-1, 4)[:, :3]
lum = px.mean(axis=1)
assert lum.mean() > 0.04 and lum.max() > 0.6, f"chrome sphere stays dark (mean {lum.mean():.3f}, max {lum.max():.2f})"
