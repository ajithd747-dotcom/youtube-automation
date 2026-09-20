# TEST rigid-body-launch-release: constant-speed keyframed approach, then free flight keeps the velocity.
import bpy
C.floor("#404652", rough=0.3)
ball = C.mesh("sphere", C.pbr("#ff5555"), loc=(-6, 6, 0.5), scale=(1, 1, 1), name="testball")
C.rigid_world()
C.rigid(bpy.data.objects["floor"], "PASSIVE", friction=0.2)
C.rigid(ball, "ACTIVE", mass=2.0, shape="SPHERE", friction=0.1)
key(ball, 1, loc=(-6, 6, 0.5), interp="LINEAR")
key(ball, 12, loc=(-3, 6, 0.5), interp="LINEAR")
key(ball, 20, loc=(-1.4, 6, 0.5), interp="LINEAR")
C.release_at(ball, (9 - 1) / STATE["fps"])
sc = bpy.context.scene
xs = {}
for f in range(1, 24):
    sc.frame_set(f)
    xs[f] = ball.matrix_world.translation.x
assert xs[22] > xs[14] + 0.3, f"ball stopped after release ({xs[14]:.2f} -> {xs[22]:.2f})"
