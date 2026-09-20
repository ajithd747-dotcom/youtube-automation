# TEST rigid-body-render-prestep: a rigid body only moves when frames are stepped in order (the viewport depsgraph).
import bpy
C.floor("#404652", rough=0.3)
cube = C.mesh("cube", C.pbr("#ff5555"), loc=(3, 3, 5), scale=(1, 1, 1), name="testcube")
C.rigid_world()
C.rigid(bpy.data.objects["floor"], "PASSIVE")
C.rigid(cube, "ACTIVE", mass=1.0)
sc = bpy.context.scene
for f in range(sc.frame_start, sc.frame_end + 1):
    sc.frame_set(f)
z_end = cube.matrix_world.translation.z
assert z_end < 4.0, f"cube did not fall (z={z_end}); physics did not simulate"
