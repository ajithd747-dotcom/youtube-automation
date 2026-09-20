"""Runs INSIDE Blender: rebuild frames from a measured colour grid. Rung 1 of the recreation ladder (training/SPEC.md).

    blender -b --python training/blender_level1.py -- job.json

job.json: {"grid": "path/to/grid.npy" (uint8 [n, gh, gw, 3] RGB), "out_dir": "...", "width": 640, "height": 360}
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_layout_common as C  # noqa: E402
import bpy  # noqa: E402

job = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
grid = np.load(job["grid"])
n, gh, gw, _ = grid.shape
W, H = int(job["width"]), int(job["height"])
out = Path(job["out_dir"])
out.mkdir(parents=True, exist_ok=True)

scene, aspect = C.setup_scene(W, H)
mesh, attr = C.build_colour_plane(scene, gw, gh, aspect)
for f in range(n):
    C.set_plane_colours(mesh, attr, grid[f])
    scene.render.filepath = str(out / f"f_{f + 1:05d}.png")
    bpy.ops.render.render(write_still=True)
print(f"LEVEL1_DONE {n} frames -> {out}")
