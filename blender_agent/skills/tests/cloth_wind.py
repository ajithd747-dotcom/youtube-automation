# TEST cloth-flag-wind: pinned cloth + wind mostly along the cloth with a small push into it -> ripples, not a crumpled sail.
import bpy, math
bpy.ops.mesh.primitive_grid_add(x_subdivisions=20, y_subdivisions=12, size=1)
cl = bpy.context.active_object
cl.scale = (4, 2.4, 1); cl.rotation_euler = (math.pi / 2, 0, 0); cl.location = (0, 3, 4)
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
vg = cl.vertex_groups.new(name="pin")
x0 = min(v.co.x for v in cl.data.vertices)
vg.add([v.index for v in cl.data.vertices if v.co.x < x0 + 0.02], 1.0, "REPLACE")
cm = cl.modifiers.new("Cloth", "CLOTH")
s = cm.settings
s.vertex_group_mass = "pin"; s.quality = 6; s.mass = 0.15; s.air_damping = 2.5; s.gravity = (0, 0, -3.0)
s.tension_stiffness = s.compression_stiffness = 25; s.bending_stiffness = 1.2
bpy.ops.object.effector_add(type="WIND", location=(-3, -2, 4), rotation=(-math.pi / 2, 0, math.radians(-70)))
w = bpy.context.active_object
w.field.strength = 260; w.field.noise = 1.2
sc = bpy.context.scene
for f in range(1, 49):
    sc.frame_set(f)
me = cl.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
ys = [v.co.y for v in me.vertices]; xs = [v.co.x for v in me.vertices]
assert max(ys) - min(ys) > 0.25, "cloth did not react to the wind"
assert max(xs) > 1.2, f"cloth crumpled towards the pole (x max {max(xs):.2f})"
