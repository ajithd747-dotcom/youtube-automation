# TEST soft-body-jelly: an ico-sphere soft body dropped on a floor with a Collision modifier squashes on impact.
import bpy
fl = bpy.data.objects.get("floor") or C.floor("#404652")
fl.modifiers.new("Collision", "COLLISION")
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.75, location=(3, 3, 2.0))
jb = bpy.context.active_object
sb = jb.modifiers.new("Softbody", "SOFT_BODY")
s = sb.settings
s.mass, s.friction, s.use_goal = 1.0, 0.6, False
s.use_edges, s.pull, s.push, s.bend, s.damping = True, 0.35, 0.35, 0.6, 0.35
sc = bpy.context.scene
heights = []
for f in range(1, 31):
    sc.frame_set(f)
    me = jb.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    zs = [v.co.z for v in me.vertices]
    heights.append(max(zs) - min(zs))
assert min(heights) < heights[0] * 0.97, "jelly never deformed on impact"
