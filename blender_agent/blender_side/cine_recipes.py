"""Cinematic scene recipes: each builds a complete physics/lighting scene for one shot (runs inside Blender).

A shot for style "cinematic" looks like:
  {"style":"cinematic","recipe":"domino_run","mood":"sunset","camera":"tracking","title":"Chain reaction","params":{}}
The director (LLM) only chooses recipe / mood / camera / title; the physics setup below is fixed and tested,
so the result is reliable even when the LLM is weak.
"""
import colorsys
import math
import random

import bpy

import cine_lib as C
import scene_lib as L
from scene_lib import STATE, end_t, frame, key

RECIPES = {}
MOODS = ["day", "sunset", "night", "studio", "neon"]


def recipe(name, default_mood, fog=0.0, doc=""):
    def deco(fn):
        RECIPES[name] = dict(fn=fn, mood=default_mood, fog=fog, doc=doc)
        return fn
    return deco


def hsv(h, s=0.75, v=0.95):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def _sun_backlit(mood):
    """Rotate the sky sun behind the subjects for long shadows / rim light / light shafts (call BEFORE setup)."""
    return mood


# ----------------------------------------------------------------------------- 1. robot intro / hook
@recipe("robot_intro", "sunset", fog=0.2, doc="3D robot waves hello on a glossy floor, glowing title floats above (hook / greeting)")
def robot_intro(p, T):
    C.floor("#3a4252", rough=0.1)
    root, j = C.build_robot((0, 0, 0), scale=1.0)
    C.animate_robot(j, p.get("action", "wave"))
    C.mesh("sphere", C.pbr("#ffffff", 0, 0.03, transmission=1.0, ior=1.5), loc=(2.6, 1.0, 0.7), scale=(1.4,) * 3)
    C.mesh("torus", C.pbr("#d4af37", 1.0, 0.18), loc=(-2.8, 1.2, 0.7), scale=(1.9,) * 3, rot=(1.25, 0, 0.5))
    if p.get("title"):
        C.title_3d(p["title"], loc=(0, 2.0, 3.9), size=0.8, delay=0.3)
    C.camera((0.8, -10.5, 1.9), (-0.4, -8.8, 2.1), (0, 0, 1.7), (0, 0, 1.9), lens=30, fstop=2.0)


# ----------------------------------------------------------------------------- 2. robot walking through a workshop
@recipe("workshop_walk", "studio", fog=0.7, doc="robot walks across a moody workshop with lamps and crates, tracking camera (walking / travelling)")
def workshop_walk(p, T):
    C.floor("#2a2e38", rough=0.22)
    C.mesh("cube", C.pbr("#20242e", 0, 0.7), loc=(0, 9, 4), scale=(40, 0.5, 8), name="wall")
    for i, x in enumerate((-7, -3.5, 4, 8)):  # shelves of glowing gadgets
        C.mesh("cube", C.pbr("#3b3f4a", 0.2, 0.5), loc=(x, 8.4, 1.0), scale=(1.6, 0.8, 2.0), bevel=0.04)
        C.mesh("sphere", C.pbr("#22d3ff", 0, 0.2, emit=3.0, emit_color=hsv(0.5 + i * 0.12)), loc=(x, 8.0, 2.3), scale=(0.45,) * 3)
    for i, (x, y) in enumerate(((-5, 4), (5.5, 3), (-1.5, 6.5))):
        C.mesh("cube", C.pbr("#9a6b3f", 0, 0.7), loc=(x, y, 0.5), scale=(1, 1, 1), rot=(0, 0, 0.3 * i), bevel=0.05)
    lamp = C.mesh("sphere", C.pbr("#fff1c9", 0, 0.2, emit=12, emit_color="#ffd9a0"), loc=(1.5, 3.5, 5.6), scale=(0.5,) * 3, shadow=False)
    tgt = C.look_at_empty((0, 0, 0.5))
    C.light("SPOT", (1.5, 3.5, 5.6), 9000, "#ffd9a0", size=0.4, target=tgt, spot=math.radians(50))
    root, j = C.build_robot((-5, 1.5, 0))
    C.animate_robot(j, "walk", walk_from=(-5, 1.5, 0), walk_to=(4.5, 1.5, 0), walk_time=T, plane="side")
    root.rotation_euler = (0, 0, math.pi / 2)  # face +X (walking right, seen in profile)
    C.camera((-2.5, -9.5, 1.5), (1.5, -9.5, 1.6), (-3.0, 1.5, 1.05), (2.8, 1.5, 1.1), lens=34, fstop=2.6)


# ----------------------------------------------------------------------------- 3. glass / gold / chrome showcase
@recipe("glass_showcase", "studio", fog=0.5, doc="rotating glass sphere, gold ring, chrome ball and glowing crystal on a mirror floor, orbiting camera (products / treasures / details)")
def glass_showcase(p, T):
    C.floor("#15181f", rough=0.05, metallic=0.4)
    items = [
        ("sphere", C.pbr("#ffffff", 0, 0.02, transmission=1.0, ior=1.5), (-2.4, 0, 1.0), (2.0,) * 3, (0, 0, 0)),
        ("torus", C.pbr("#d4af37", 1.0, 0.15), (0.0, 0.3, 1.1), (2.6,) * 3, (1.3, 0, 0)),
        ("sphere", C.pbr("#e8e8ee", 1.0, 0.02), (2.4, 0, 1.0), (2.0,) * 3, (0, 0, 0)),
    ]
    for kind, mat, loc, sc, rot in items:
        o = C.mesh(kind, mat, loc=loc, scale=sc, rot=rot)
        if kind == "torus":
            key(o, 1, rot=(1.3, 0, 0), interp="LINEAR")
            key(o, STATE["frames"], rot=(1.3, 0, math.pi * 2 * max(1, T / 6)), interp="LINEAR")
    # glowing crystal (icosphere, flat shaded)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.55, location=(0, -1.3, 0.6))
    cr = bpy.context.active_object
    cr.data.materials.append(C.pbr("#22d3ff", 0, 0.1, emit=1.1, transmission=0.6))
    key(cr, 1, rot=(0, 0, 0), interp="LINEAR")
    key(cr, STATE["frames"], rot=(0.4, 0.6, math.pi * 2), interp="LINEAR")
    cr.location = (0, -1.3, 0.75)
    C.light("POINT", (0, -1.3, 0.75), 120, "#22d3ff", size=0.2)
    C.camera((-6.5, -7.5, 2.2), (6.5, -7.5, 2.0), (0, 0, 1.0), (0, 0, 1.0), lens=45, fstop=2.0)


# ----------------------------------------------------------------------------- 4. dominoes (rigid body chain reaction)
@recipe("domino_run", "sunset", fog=0.12, doc="a long winding line of colourful dominoes toppling in a chain reaction (rigid-body physics), tracking camera")
def domino_run(p, T):
    C.floor("#3b414f", rough=0.3)
    n = int(p.get("count", 26))
    pts = []
    x = -9.0
    for i in range(n):
        x += 0.58
        pts.append((x, 1.6 * math.sin(x * 0.42)))
    doms = []
    for i, (x, y) in enumerate(pts):
        nx, ny = pts[min(i + 1, n - 1)]
        px, py = pts[max(i - 1, 0)]
        ang = math.atan2(ny - py, nx - px)
        o = C.mesh("cube", C.pbr(hsv(i / n * 0.85), 0, 0.3, coat=0.5), loc=(x, y, 0.5), scale=(0.12, 0.5, 1.0), rot=(0, 0, ang), bevel=0.012, name=f"dom{i}")
        doms.append(o)
    world = C.rigid_world(substeps=20, iterations=30)
    world.time_scale = 1.0
    C.rigid(bpy.data.objects["floor"], "PASSIVE", friction=0.9)
    for o in doms:
        C.rigid(o, "ACTIVE", mass=0.25, friction=0.55, bounce=0.05, margin=0.0005)
    ball = C.mesh("sphere", C.pbr("#e63946", 0, 0.15, coat=1.0), loc=(pts[0][0] - 5, pts[0][1] + 0.2, 0.42), scale=(0.85,) * 3, name="ball")
    C.rigid(ball, "ACTIVE", mass=3.0, shape="SPHERE", friction=0.4, bounce=0.1)
    t_hit = 0.9
    key(ball, 1, loc=ball.location[:], interp="LINEAR")
    key(ball, frame(t_hit), loc=(pts[0][0] - 0.55, pts[0][1] + 0.05, 0.42), interp="LINEAR")
    C.release_at(ball, t_hit - 0.05)
    lead = C.look_at_empty(pts[0][:2] + (0.5,))
    # camera trails the toppling wave: target follows the fall front
    wave_t = min(T - 0.5, 1.2 + n * 0.17)  # measured: ~0.17 s per domino
    key(lead, 1, loc=(pts[0][0], pts[0][1], 0.5), interp="LINEAR")
    key(lead, frame(0.9), loc=(pts[0][0], pts[0][1], 0.5), interp="LINEAR")
    key(lead, frame(wave_t), loc=(pts[-1][0], pts[-1][1], 0.5), interp="LINEAR")
    key(lead, STATE["frames"], loc=(pts[-1][0], pts[-1][1], 0.5), interp="LINEAR")
    cam, tgt = C.camera((-9, -5.5, 1.3), (pts[-1][0] - 4, -5.5, 1.5), (pts[0][0], pts[0][1], 0.5), (pts[-1][0], pts[-1][1], 0.5), lens=42, fstop=2.2)
    # make the camera target follow `lead` exactly
    tgt.constraints.new("COPY_LOCATION").target = lead
    cam.animation_data_clear()
    key(cam, 1, loc=(pts[0][0] - 3, -5.0, 1.2), interp="LINEAR")
    key(cam, frame(wave_t), loc=(pts[-1][0] - 6, -5.0, 1.6), interp="LINEAR")
    key(cam, STATE["frames"], loc=(pts[-1][0] - 7, -5.2, 1.7), interp="LINEAR")


# ----------------------------------------------------------------------------- 5. wrecking ball vs crate tower
@recipe("crate_smash", "sunset", fog=0.5, doc="a heavy steel ball smashes a wall of wooden crates, debris tumbles in slow motion (destruction / impact / climax)")
def crate_smash(p, T):
    C.floor("#3a3f4a", rough=0.3)
    cols, rows = 5, 7
    crates = []
    for r in range(rows):
        for c in range(cols):
            hue_shift = 0.0 if (r + c) % 2 == 0 else 0.03
            o = C.mesh("cube", C.pbr("#a9743f", 0, 0.65), loc=(1.0 + (c - cols / 2) * 0.62, 2.5, 0.31 + r * 0.62),
                       scale=(0.6, 0.6, 0.6), bevel=0.03, name=f"crate{r}_{c}")
            crates.append(o)
    world = C.rigid_world(substeps=15, iterations=25)
    world.time_scale = 0.75
    C.rigid(bpy.data.objects["floor"], "PASSIVE", friction=0.8)
    for o in crates:
        C.rigid(o, "ACTIVE", mass=0.8, friction=0.6, bounce=0.05, margin=0.001)
    ball = C.mesh("sphere", C.pbr("#c9ccd4", 1.0, 0.12), loc=(-9, 2.5, 1.6), scale=(1.5,) * 3, name="wball")
    C.rigid(ball, "ACTIVE", mass=60.0, shape="SPHERE", friction=0.3, bounce=0.05)
    t0, t1 = 0.4, 1.5
    # constant-speed approach (a BEZIER ease-out would leave the ball with ~zero speed when it is released)
    x_c = -1.6  # x where the ball touches the wall
    v = (x_c + 9) / (t1 - t0)
    key(ball, 1, loc=(-9, 2.5, 1.6), interp="LINEAR")
    key(ball, frame(t0), loc=(-9, 2.5, 1.6), interp="LINEAR")
    key(ball, frame(t1 + 0.3), loc=(-9 + v * (t1 + 0.3 - t0), 2.5, 1.6), interp="LINEAR")
    C.release_at(ball, t1 - 0.12)
    C.light("SPOT", (-4, -2, 9), 14000, "#ffe1b8", size=0.6, target=C.look_at_empty((1, 2.5, 1.5)), spot=math.radians(55))
    C.camera((-2.0, -8.0, 1.6), (3.5, -8.5, 2.6), (0.5, 2.5, 1.4), (1.5, 2.5, 1.8), lens=36, fstop=2.4, shake=0.0)
    # impact shake on the camera
    cam = bpy.context.scene.camera
    rnd = random.Random(5)
    base = [cam.location[:]]
    for f in range(frame(t1), frame(t1 + 0.7), 1):
        a = math.exp(-(f - frame(t1)) / 6.0) * 0.18
        t = (f - 1) / STATE["fps"]
        frac = (f - 1) / max(1, STATE["frames"] - 1)
        p0 = [(-2.0 + 5.5 * frac), (-8.0 - 0.5 * frac), (1.6 + 1.0 * frac)]
        key(cam, f, loc=(p0[0] + rnd.uniform(-a, a), p0[1] + rnd.uniform(-a, a), p0[2] + rnd.uniform(-a, a)), interp="LINEAR")


# ----------------------------------------------------------------------------- 6. cloth banner in the wind
@recipe("cloth_banner", "day", fog=0.2, doc="a large banner/flag on a pole rippling in the wind (cloth simulation), sky and sun (celebration / victory / wind / flag)")
def cloth_banner(p, T):
    C.floor("#5d7a4a", rough=0.85)
    C.mesh("cylinder", C.pbr("#c9ccd4", 1.0, 0.25), loc=(-2.4, 2.0, 3.0), scale=(0.09, 0.09, 6.0), name="pole")
    C.mesh("sphere", C.pbr("#d4af37", 1.0, 0.2), loc=(-2.4, 2.0, 6.1), scale=(0.28,) * 3)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=46, y_subdivisions=26, size=1)
    cloth = bpy.context.active_object
    cloth.name = "banner"
    cloth.scale = (5.0, 3.0, 1.0)
    cloth.rotation_euler = (math.pi / 2, 0, 0)  # grid lies in XY -> stand it up in XZ
    cloth.location = (0.1, 2.0, 4.6)
    bpy.context.view_layer.update()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    vg = cloth.vertex_groups.new(name="pin")
    xs = [v.co.x for v in cloth.data.vertices]
    x_min = min(xs)
    vg.add([v.index for v in cloth.data.vertices if v.co.x < x_min + 0.02], 1.0, "REPLACE")
    # stripes + emblem-ish material
    m = bpy.data.materials.new("banner")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.6
    try:
        b.inputs["Sheen Weight"].default_value = 0.6
    except Exception:
        pass
    tex = nt.nodes.new("ShaderNodeTexWave")
    tex.wave_type, tex.bands_direction = "BANDS", "Z"
    tex.inputs["Scale"].default_value = 2.2
    tex.inputs["Distortion"].default_value = 0.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = L.rgba("#d62839")
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = L.rgba("#fdf0d5")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    cloth.data.materials.append(m)
    cm = cloth.modifiers.new("Cloth", "CLOTH")
    st = cm.settings
    st.vertex_group_mass = "pin"
    st.quality, st.mass, st.air_damping = 8, 0.15, 2.5
    st.gravity = (0, 0, -3.0)  # a lighter-than-real cloth flies more like a flag
    st.tension_stiffness, st.compression_stiffness, st.bending_stiffness = 25, 25, 1.2
    cm.collision_settings.use_self_collision = False
    cm.point_cache.frame_start, cm.point_cache.frame_end = 1, STATE["frames"]
    # gusting wind along +X
    bpy.ops.object.effector_add(type="WIND", location=(-3.5, -3.0, 4.5), rotation=(-math.pi / 2, 0, math.radians(-70)))  # blows +Y (into the banner) and +X
    wind = bpy.context.active_object
    wind.field.strength = 0.0
    wind.field.noise = 1.2
    for t, s in ((0, 0), (0.6, 260), (T * 0.5, 420), (T, 300)):
        wind.field.strength = s
        wind.field.keyframe_insert("strength", frame=frame(t))
    sub = cloth.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = sub.render_levels = 1
    for i, (x, y) in enumerate(((5, 7), (-5, 9), (8, 12))):  # distant trees for depth
        C.mesh("cone", C.pbr("#2f5d34", 0, 0.8), loc=(x, y, 2.0), scale=(2.2, 2.2, 4.0))
    C.camera((3.5, -8.0, 2.0), (1.0, -8.5, 3.6), (0.8, 2.0, 4.4), (0.8, 2.0, 4.6), lens=30, fstop=3.5)


# ----------------------------------------------------------------------------- 7. fireworks over water
@recipe("fireworks", "night", fog=0.5, doc="fireworks bursting over a dark reflective lake with glowing particles and bloom (celebration / night / finale)")
def fireworks(p, T):
    C.floor("#050810", rough=0.03, metallic=0.9)
    spark_mats = []
    bursts = int(p.get("bursts", 5))
    rnd = random.Random(11)
    for i in range(bursts):
        hue = (i * 0.19 + 0.02) % 1.0
        col = hsv(hue, 0.85, 1.0)
        sp = C.mesh("sphere", C.pbr(col, 0, 0.3, emit=14.0), loc=(0, -60, -5), scale=(0.11,) * 3, shadow=False, name=f"spark{i}")
        sp.hide_render = True  # instanced source only
        t = 0.3 + i * (max(1.0, T - 1.5) / bursts)
        pos = (rnd.uniform(-8, 8), rnd.uniform(16, 24), rnd.uniform(9, 13))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.1, location=pos)
        em = bpy.context.active_object
        em.name = f"emit{i}"
        ps_mod = em.modifiers.new("ps", "PARTICLE_SYSTEM")
        ps = ps_mod.particle_system.settings
        ps.count, ps.frame_start, ps.frame_end = 520, frame(t), frame(t) + 1
        ps.lifetime, ps.lifetime_random = 55, 0.4
        ps.emit_from = "VERT"
        ps.normal_factor, ps.factor_random = 9.0, 1.4
        ps.effector_weights.gravity = 0.25
        ps.render_type = "OBJECT"
        ps.instance_object = sp
        ps.particle_size, ps.size_random = 1.0, 0.5
        em.show_instancer_for_render = False
        ps.show_unborn, ps.use_dead = False, False
        fl = C.light("POINT", pos, 0, col, size=0.5)  # flash that lights the water/fog at each burst
        for dt, e in ((-0.02, 0), (0.0, 60000), (0.35, 0)):
            fl.data.energy = e
            fl.data.keyframe_insert("energy", frame=max(1, frame(t + dt)))
    C.camera((0, -10, 1.5), (0, -10, 2.6), (0, 20, 8.0), (0, 20, 9.0), lens=24, fstop=5.0)


# ----------------------------------------------------------------------------- 8. jelly + ball pit (soft body + rigid)
@recipe("jelly_pit", "neon", fog=0.5, doc="translucent jelly blobs wobble (soft body) while colourful balls rain into a pile (rigid bodies) under neon light (fun / bounce / party)")
def jelly_pit(p, T):
    C.floor("#0b0a14", rough=0.08, metallic=0.5)
    fl = bpy.data.objects["floor"]
    fl.modifiers.new("Collision", "COLLISION")
    world = C.rigid_world(substeps=10, iterations=20)
    C.rigid(fl, "PASSIVE", friction=0.7, bounce=0.35)
    rnd = random.Random(4)
    for i in range(5):  # jelly: soft-body ico spheres
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.75, location=(-4.0 + i * 2.0, rnd.uniform(1.5, 3.5), 3.0 + i * 1.6))
        jb = bpy.context.active_object
        jb.name = f"jelly{i}"
        jb.data.materials.append(C.pbr(hsv(0.9 - i * 0.16), 0, 0.12, transmission=0.85, ior=1.35, emit=0.6))
        bpy.ops.object.shade_smooth()
        sb = jb.modifiers.new("Softbody", "SOFT_BODY")
        s = sb.settings
        s.mass, s.friction, s.use_goal = 1.0, 0.6, False
        s.use_edges, s.pull, s.push, s.bend, s.damping = True, 0.35, 0.35, 0.6, 0.35
        s.use_self_collision = False
        sb.point_cache.frame_start, sb.point_cache.frame_end = 1, STATE["frames"]
    for i in range(34):  # ball pit
        r = rnd.uniform(0.28, 0.5)
        o = C.mesh("sphere", C.pbr(hsv(rnd.random()), 0, 0.2, coat=0.8), loc=(rnd.uniform(-5, 5), rnd.uniform(-1.5, 4.5), 5.0 + i * 0.55), scale=(2 * r,) * 3, name=f"pit{i}")
        C.rigid(o, "ACTIVE", mass=r * 2, shape="SPHERE", friction=0.5, bounce=0.5)
    C.camera((-6.5, -9, 3.0), (6.0, -9.5, 2.2), (0, 1.5, 1.0), (0, 1.5, 1.3), lens=34, fstop=2.4)


# ----------------------------------------------------------------------------- 9. celebration finale
@recipe("finale_confetti", "night", fog=0.6, doc="robot cheers under a glowing title while confetti rains down (ending / outro / thanks / celebration)")
def finale_confetti(p, T):
    C.floor("#141827", rough=0.08, metallic=0.3)
    root, j = C.build_robot((0, 0, 0), accent="#ff4fd8")
    C.animate_robot(j, "celebrate")
    C.title_3d(p.get("title") or "Thanks for watching", loc=(0, 2.0, 4.5), color="#ffffff", glow="#ff4fd8", size=0.9, delay=0.2)
    C.light("SPOT", (0, -6, 9), 16000, "#ffffff", size=0.6, target=C.look_at_empty((0, 0, 1.0)), spot=math.radians(40))
    C.light("AREA", (-5, -4, 3), 400, "#22d3ff", 3, C.look_at_empty((0, 0, 1)))
    C.light("AREA", (5, -4, 3), 400, "#ff4fd8", 3, C.look_at_empty((0, 0, 1)))
    # confetti: one emitter plane above the scene shooting coloured chips down
    chips = []
    for i, hue in enumerate((0.0, 0.12, 0.33, 0.55, 0.78)):
        c = C.mesh("cube", C.pbr(hsv(hue, 0.85, 1.0), 0, 0.4, emit=0.6), loc=(0, -80, -5), scale=(0.3, 0.02, 0.19), shadow=False, name=f"chip{i}")
        c.hide_render = True
        chips.append(c)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 1.5, 9.5))
    em = bpy.context.active_object
    em.scale = (10, 6, 1)
    em.name = "confetti_emit"
    for i, c in enumerate(chips):
        pm = em.modifiers.new(f"ps{i}", "PARTICLE_SYSTEM")
        ps = pm.particle_system.settings
        ps.count, ps.frame_start, ps.frame_end = 150, 1, frame(max(1.0, T - 1.0))
        ps.lifetime = 140
        ps.normal_factor, ps.factor_random = -0.8, 0.8
        ps.effector_weights.gravity = 0.06
        ps.render_type, ps.instance_object = "OBJECT", c
        ps.particle_size, ps.size_random = 1.0, 0.6
        ps.use_rotations, ps.rotation_mode, ps.angular_velocity_mode = True, "VEL", "RAND"
        ps.angular_velocity_factor = 6.0
        em.show_instancer_for_render = False
    bpy.ops.object.effector_add(type="TURBULENCE", location=(0, 1.5, 6))
    turb = bpy.context.active_object
    turb.field.strength, turb.field.size = 3.0, 1.5
    C.camera((0.5, -10.5, 2.0), (-0.5, -8.6, 2.4), (0, 0, 2.0), (0, 0, 2.3), lens=32, fstop=2.2)


# ----------------------------------------------------------------------------- dispatcher
def build(shot, width, height, fps, duration, quality="standard"):
    name = shot.get("recipe") if shot.get("recipe") in RECIPES else "robot_intro"
    r = RECIPES[name]
    mood = shot.get("mood") if shot.get("mood") in MOODS else r["mood"]
    p = dict(shot.get("params") or {})
    C.setup(width, height, fps, duration, mood=mood, quality=quality, fog=r["fog"] * float(p.get("fog_scale", 1.0)))
    if p.get("exposure_bias"):  # set by the visual-qa agent
        bpy.context.scene.view_settings.exposure += float(p["exposure_bias"])
    if shot.get("title"):
        p["title"] = shot["title"]
    r["fn"](p, end_t())
    if shot.get("title") and name in ("robot_intro", "finale_confetti"):
        pass
    elif shot.get("title") and name in RECIPES:
        C.title_3d(shot["title"], loc=(0, 4.0, 4.6), size=0.7, delay=0.3)
    return name, mood


import cine_recipes_fx  # noqa: E402,F401  (fire/smoke, liquid, fur recipes register themselves)
import dsl as _dsl  # noqa: E402
assert set(_dsl.RECIPES) == set(RECIPES), f"dsl.RECIPES out of sync: {set(_dsl.RECIPES) ^ set(RECIPES)}"
