"""Runs INSIDE Blender: colour layout (rung 1) plus measured line work as thin flat ribbons. Rung 2 of the ladder.

    blender -b --python training/blender_level2.py -- job.json

job.json: {"grid": grid.npy [n,gh,gw,3], "lines": lines.npz, "out_dir", "width", "height", "half_width_px": 0.75}
lines.npz holds, per frame f: a_f, b_f ([S,2] pixel coords), c_f ([S,3] uint8 ink colours).
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
lines = np.load(job["lines"])
n, gh, gw, _ = grid.shape
W, H = int(job["width"]), int(job["height"])
out = Path(job["out_dir"])
out.mkdir(parents=True, exist_ok=True)

scene, aspect = C.setup_scene(W, H)
plane, attr = C.build_colour_plane(scene, gw, gh, aspect)
line_mesh = C.make_line_object(scene)
for f in range(n):
    C.set_plane_colours(plane, attr, grid[f])
    C.set_line_ribbons(line_mesh, lines[f"a_{f}"], lines[f"b_{f}"], lines[f"c_{f}"], W, H, aspect, float(job["half_width_px"]))
    scene.render.filepath = str(out / f"f_{f + 1:05d}.png")
    bpy.ops.render.render(write_still=True)
print(f"LEVEL2_DONE {n} frames -> {out}")
