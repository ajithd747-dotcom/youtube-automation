# TEST easing-and-overshoot: entrances overshoot ~12-15% then settle to 1.0 (reads springy, not mechanical).
import bpy
r = C.title_3d("Pop", loc=(0, 3, 3), size=0.8, delay=0.0)
vals = [kp.co[1] for fc in L._fcurves(r.animation_data.action) if fc.data_path == "scale" and fc.array_index == 0 for kp in fc.keyframe_points]
assert max(vals) > 1.08 and abs(vals[-1] - 1.0) < 1e-3, f"no overshoot/settle: {vals}"
