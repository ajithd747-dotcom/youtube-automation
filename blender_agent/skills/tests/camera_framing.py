# TEST camera-framing-safe-area: the subject (robot head + knee) stays inside the frame for the whole shot.
import bpy
from bpy_extras.object_utils import world_to_camera_view
sc = bpy.context.scene
cam = sc.camera
bad = []
for f in (sc.frame_start, (sc.frame_start + sc.frame_end) // 2, sc.frame_end):
    sc.frame_set(f)
    for name in ("head", "l_kn"):
        o = bpy.data.objects.get(name)
        if o is None:
            continue
        v = world_to_camera_view(sc, cam, o.matrix_world.translation)
        if not (0.02 < v.x < 0.98 and 0.03 < v.y < 0.97):
            bad.append((f, name, round(v.x, 2), round(v.y, 2)))
assert not bad, f"subject leaves the frame: {bad}"
