# TEST particle-burst-fireworks: one-frame emission from a vertex emitter gives hundreds of instanced particles.
import bpy
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.1, location=(0, 8, 6))
em = bpy.context.active_object
spark = C.mesh("sphere", C.pbr("#ffcc55", emit=10), loc=(0, -60, -5), scale=(0.1,) * 3, shadow=False, name="spark")
spark.hide_render = True
pm = em.modifiers.new("ps", "PARTICLE_SYSTEM")
ps = pm.particle_system.settings
ps.count, ps.frame_start, ps.frame_end, ps.lifetime = 300, 3, 4, 50
ps.emit_from = "VERT"; ps.normal_factor, ps.factor_random = 9.0, 1.4
ps.render_type = "OBJECT"; ps.instance_object = spark
em.show_instancer_for_render = False
sc = bpy.context.scene
for f in range(1, 12):
    sc.frame_set(f)
n = len(em.evaluated_get(bpy.context.evaluated_depsgraph_get()).particle_systems[0].particles)
assert n >= 100, f"only {n} particles alive"
