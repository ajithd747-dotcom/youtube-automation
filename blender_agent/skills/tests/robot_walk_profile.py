# TEST walk-cycle-profile: robot in profile (root rotated +90deg about Z) swings limbs about local X and travels along +X.
import bpy, math
root, j = C.build_robot((0, 3, 0))
root.rotation_euler = (0, 0, math.pi / 2)
C.animate_robot(j, "walk", walk_from=(-2, 3, 0), walk_to=(2, 3, 0), walk_time=1.5, plane="side")
sc = bpy.context.scene
xs, feet = [], []
for f in (1, 6, 12):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    xs.append(root.evaluated_get(dg).matrix_world.translation.x)
    lk, rk = j["l_kn"].evaluated_get(dg).matrix_world.translation, j["r_kn"].evaluated_get(dg).matrix_world.translation
    feet.append(abs(lk.x - rk.x))
assert xs[-1] > xs[0] + 1.0, "robot did not travel"
assert max(feet) > 0.12, f"legs do not swing forward/back (max knee separation {max(feet):.2f})"
