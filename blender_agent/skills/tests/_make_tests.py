"""Regenerates the skill test snippets (each runs inside Blender after a small scene is built; an AssertionError = FAIL)."""
from pathlib import Path

T = {}

T["rigid_prestep"] = '''# TEST rigid-body-render-prestep: a rigid body only moves when frames are stepped in order (the viewport depsgraph).
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
'''

T["rigid_launch_release"] = '''# TEST rigid-body-launch-release: constant-speed keyframed approach, then free flight keeps the velocity.
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
'''

T["cloth_wind"] = '''# TEST cloth-flag-wind: pinned cloth + wind mostly along the cloth with a small push into it -> ripples, not a crumpled sail.
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
'''

T["soft_body_jelly"] = '''# TEST soft-body-jelly: an ico-sphere soft body dropped on a floor with a Collision modifier squashes on impact.
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
'''

T["particle_burst"] = '''# TEST particle-burst-fireworks: one-frame emission from a vertex emitter gives hundreds of instanced particles.
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
'''

T["fog_box"] = '''# TEST volumetric-fog-box: haze as a bounded volume cube (a world volume renders black in EEVEE Next on this GPU).
import bpy
import numpy as np
box = C.add_fog(0.008)
assert box.data.materials and any(n.bl_idname == "ShaderNodeVolumePrincipled" for n in box.data.materials[0].node_tree.nodes)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 160, 90
sc.render.filepath = bpy.app.tempdir + "fogtest.png"
bpy.ops.render.render(write_still=True)
img = bpy.data.images.load(sc.render.filepath)
px = np.array(img.pixels[:]).reshape(-1, 4)[:, :3]
assert px.mean() > 0.03, f"scene rendered black with fog (mean {px.mean():.3f})"
'''

T["studio_world_stripes"] = '''# TEST studio-softbox-stripe-world: reflective objects need a bright structured environment; a black world = black metal.
import bpy
import numpy as np
sc = C.setup(320, 180, 12, 2.0, mood="studio", quality="draft")
C.floor("#15181f", rough=0.05, metallic=0.4)
C.mesh("sphere", C.pbr("#e8e8ee", 1.0, 0.02), loc=(0, 0, 1.0), scale=(2, 2, 2))
C.camera((0, -7, 1.5), (0, -7, 1.5), (0, 0, 1.0), None, lens=45, fstop=0)
sc.render.filepath = bpy.app.tempdir + "studio.png"
bpy.ops.render.render(write_still=True)
img = bpy.data.images.load(sc.render.filepath)
px = np.array(img.pixels[:]).reshape(-1, 4)[:, :3]
lum = px.mean(axis=1)
assert lum.mean() > 0.04 and lum.max() > 0.6, f"chrome sphere stays dark (mean {lum.mean():.3f}, max {lum.max():.2f})"
'''

T["text_fit"] = '''# TEST text fitting: measure AFTER scaling + update, and never scale text twice (parent AND font size).
import bpy
root = empty("t", None, (0, 0, 0))
t = text_part(root, "A very long headline that must fit inside the frame width", "#ffffff", height=1.0, max_width=8.0, wrap=20)
bpy.context.view_layer.update()
assert t.dimensions.x <= 8.02, f"text too wide: {t.dimensions.x:.2f}"
'''

T["camera_framing"] = '''# TEST camera-framing-safe-area: the subject (robot head + knee) stays inside the frame for the whole shot.
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
'''

T["robot_walk_profile"] = '''# TEST walk-cycle-profile: robot in profile (root rotated +90deg about Z) swings limbs about local X and travels along +X.
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
'''

T["pop_in_overshoot"] = '''# TEST easing-and-overshoot: entrances overshoot ~12-15% then settle to 1.0 (reads springy, not mechanical).
import bpy
r = C.title_3d("Pop", loc=(0, 3, 3), size=0.8, delay=0.0)
vals = [kp.co[1] for fc in L._fcurves(r.animation_data.action) if fc.data_path == "scale" and fc.array_index == 0 for kp in fc.keyframe_points]
assert max(vals) > 1.08 and abs(vals[-1] - 1.0) < 1e-3, f"no overshoot/settle: {vals}"
'''

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    for name, code in T.items():
        (here / f"{name}.py").write_text(code, encoding="utf-8")
    print("wrote", len(T), "tests")
