"""Runs INSIDE Blender: rebuild frames from a measured colour grid. Rung 1 of the recreation ladder (training/SPEC.md).

    blender -b --python training/blender_level1.py -- job.json

job.json: {"grid": "path/to/grid.npy" (uint8 [n, gh, gw, 3] RGB), "out_dir": "...", "width": 640, "height": 360}
One quad-mesh plane with one vertex per grid cell (vertex colours interpolate smoothly between cell centres), an
orthographic camera that frames it exactly, Workbench flat shading (no lighting invented), Standard view transform so
Blender does not tone-map the colours. Each frame only updates the vertex colours and renders.
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

job = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
grid = np.load(job["grid"])
n, gh, gw, _ = grid.shape
W, H = int(job["width"]), int(job["height"])
out = Path(job["out_dir"])
out.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = W, H, 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.display_settings.display_device = "sRGB"
shading = scene.display.shading
shading.light, shading.color_type, shading.show_specular_highlight = "FLAT", "VERTEX", False
scene.display.render_aa = "OFF"

# vertices at cell centres, plus a border ring at the plane edge carrying the edge cell's colour
aspect = W / H
xs = np.concatenate([[0.0], (np.arange(gw) + 0.5) / gw, [1.0]])
ys = np.concatenate([[0.0], (np.arange(gh) + 0.5) / gh, [1.0]])
verts = [((x - 0.5) * aspect, (0.5 - y), 0.0) for y in ys for x in xs]     # row 0 = top of the picture
nx, ny = gw + 2, gh + 2
faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]
mesh = bpy.data.meshes.new("layout")
mesh.from_pydata(verts, [], faces)
mesh.update()
attr = mesh.color_attributes.new("col", "FLOAT_COLOR", "POINT")
obj = bpy.data.objects.new("layout", mesh)
scene.collection.objects.link(obj)

cam_data = bpy.data.cameras.new("cam")
cam_data.type, cam_data.ortho_scale = "ORTHO", aspect
cam = bpy.data.objects.new("cam", cam_data)
cam.location = (0, 0, 2)
scene.collection.objects.link(cam)
scene.camera = cam


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


for f in range(n):
    cells = grid[f].astype(np.float32) / 255.0
    padded = np.pad(cells, ((1, 1), (1, 1), (0, 0)), mode="edge")          # [gh+2, gw+2, 3]
    lin = srgb_to_linear(padded).reshape(-1, 3)
    rgba = np.concatenate([lin, np.ones((len(lin), 1), np.float32)], axis=1).ravel()
    attr.data.foreach_set("color", rgba)
    mesh.update()
    scene.render.filepath = str(out / f"f_{f + 1:05d}.png")
    bpy.ops.render.render(write_still=True)
print(f"LEVEL1_DONE {n} frames -> {out}")
