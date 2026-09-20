"""Cinematic recipes that need real simulations: Mantaflow fire/smoke, Mantaflow liquid, particle hair/fur.
Imported at the end of cine_recipes.py (they register themselves in the same RECIPES table)."""
import math
import os
import random

import bpy

import cine_lib as C
import scene_lib as L
from cine_recipes import recipe
from scene_lib import STATE, frame, key


def _cache_dir(tag):
    d = os.path.join(bpy.app.tempdir, f"fluid_{tag}_{os.getpid()}")
    os.makedirs(d, exist_ok=True)
    return d


def _bake(dom):
    bpy.context.view_layer.objects.active = dom
    bpy.ops.fluid.bake_all()


def _domain(dom, kind, res, tag, frames):
    fm = dom.modifiers.new("Fluid", "FLUID")
    fm.fluid_type = "DOMAIN"
    ds = fm.domain_settings
    ds.domain_type, ds.resolution_max = kind, res
    ds.cache_directory = _cache_dir(tag)
    ds.cache_frame_start, ds.cache_frame_end = 1, frames
    return ds


# ----------------------------------------------------------------------------- campfire + smoke (Mantaflow gas)
@recipe("campfire_smoke", "night", fog=0.1, doc="a crackling campfire with real simulated fire and rising smoke, flickering warm light, drifting embers (warmth, night, rest, story, survival, fire)")
def campfire_smoke(p, T):
    C.floor("#12151c", rough=0.7)
    wood = C.pbr("#3a2418", 0.0, 0.8)
    for i in range(6):
        a = i * math.pi / 3
        C.mesh("cylinder", wood, loc=(math.cos(a) * 0.45, 4 + math.sin(a) * 0.45, 0.16), scale=(0.16, 0.16, 1.0), rot=(math.pi / 2 - 0.25, 0, a + math.pi / 2), bevel=0.01)
    for i in range(8):
        a = i * math.pi / 4
        C.mesh("sphere", C.pbr("#585c66", 0, 0.9), loc=(math.cos(a) * 1.0, 4 + math.sin(a) * 1.0, 0.13), scale=(0.34, 0.3, 0.26))
    src = C.mesh("sphere", C.pbr("#ff7a1a", emit=1.0), loc=(0, 4, 0.55), scale=(0.7, 0.7, 0.5), name="flame_src", shadow=False)
    src.hide_render = True
    dom = C.mesh("cube", C.pbr("#ffffff"), loc=(0, 4, 3.4), scale=(5.0, 5.0, 6.8), name="smoke_domain", shadow=False)
    dom.display_type = "WIRE"
    res = {"draft": 40, "standard": 64, "final": 96}.get(C.CFG.get("quality", "standard"), 64)
    ds = _domain(dom, "GAS", res, "fire", STATE["frames"])
    ds.use_noise = False
    ds.beta = 1.6      # buoyancy: a livelier plume
    fl = src.modifiers.new("Fluid", "FLUID")
    fl.fluid_type = "FLOW"
    fs = fl.flow_settings
    fs.flow_type, fs.flow_behavior, fs.flow_source = "BOTH", "INFLOW", "MESH"
    fs.temperature, fs.density, fs.fuel_amount = 2.4, 1.0, 1.0
    m = bpy.data.materials.new("fire_smoke")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = 6.0
    v.inputs["Color"].default_value = L.rgba("#3a3532")
    v.inputs["Blackbody Intensity"].default_value = 1.4
    nt.links.new(v.outputs["Volume"], out.inputs["Volume"])
    dom.data.materials.clear()      # the domain must carry ONLY the volume material (a surface slot renders as a solid box)
    dom.data.materials.append(m)
    lt = C.light("POINT", (0, 3.6, 1.2), 0, "#ff8a3c", 0.4)   # fire light with keyed flicker
    rnd = random.Random(2)
    for f in range(1, STATE["frames"] + 1, 2):
        lt.data.energy = 900 * (0.75 + 0.5 * rnd.random())
        lt.data.keyframe_insert("energy", frame=f)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.3, location=(0, 4, 0.8))
    em = bpy.context.active_object
    em.name = "ember_emit"
    ember = C.mesh("sphere", C.pbr("#ff9a3c", emit=12.0), loc=(0, -60, -5), scale=(0.035,) * 3, shadow=False, name="ember")
    ember.hide_render = True
    ps = em.modifiers.new("ps", "PARTICLE_SYSTEM").particle_system.settings
    ps.count, ps.frame_start, ps.frame_end, ps.lifetime = 90, 1, STATE["frames"], 60
    ps.normal_factor, ps.factor_random = 1.2, 1.2
    ps.effector_weights.gravity = -0.15
    ps.render_type, ps.instance_object, ps.particle_size, ps.size_random = "OBJECT", ember, 1.0, 0.7
    em.show_instancer_for_render = False
    C.camera((0.6, -7.2, 1.6), (-0.3, -6.2, 1.9), (0, 4, 2.2), (0, 4, 2.6), lens=32, fstop=2.8)
    _bake(dom)


# ----------------------------------------------------------------------------- water splash (Mantaflow liquid)
@recipe("water_splash", "studio", fog=0.0, doc="drops of water falling into a pool with a glassy, refractive liquid splash in slow motion (water, rain, splash, drink, ocean, calm, liquid)")
def water_splash(p, T):
    C.floor("#1b2029", rough=0.25, metallic=0.2)
    dom = C.mesh("cube", C.pbr("#ffffff"), loc=(0, 4, 1.5), scale=(4.4, 4.4, 3.0), name="liquid_domain", shadow=False)
    dom.display_type = "WIRE"
    res = {"draft": 40, "standard": 56, "final": 80}.get(C.CFG.get("quality", "standard"), 56)
    ds = _domain(dom, "LIQUID", res, "water", STATE["frames"])
    ds.use_mesh = True
    ds.time_scale = 0.8     # slow motion
    pool = C.mesh("cube", C.pbr("#ffffff"), loc=(0, 4, 0.45), scale=(4.2, 4.2, 0.9), name="pool", shadow=False)
    pool.hide_render = True
    objs = [pool]
    for i, (x, y, z) in enumerate(((0.0, 4.0, 2.4), (0.7, 3.6, 2.0), (-0.6, 4.4, 1.7))):
        d = C.mesh("sphere", C.pbr("#ffffff"), loc=(x, y, z), scale=(0.5, 0.5, 0.5), name=f"drop{i}", shadow=False)
        d.hide_render = True
        objs.append(d)
    for o in objs:
        m = o.modifiers.new("Fluid", "FLUID")
        m.fluid_type = "FLOW"
        fs = m.flow_settings
        fs.flow_type, fs.flow_behavior, fs.flow_source = "LIQUID", "GEOMETRY", "MESH"
    dom.data.materials.clear()
    dom.data.materials.append(C.pbr("#cfe8ff", 0.0, 0.03, transmission=1.0, ior=1.33))
    C.light("AREA", (-3, -2, 5), 700, "#ffffff", 3, C.look_at_empty((0, 4, 1)))
    C.light("AREA", (4, 1, 3), 400, "#9ec5ff", 3, C.look_at_empty((0, 4, 1)))
    C.camera((-1.5, -2.8, 1.5), (1.5, -2.8, 1.3), (0, 4, 1.1), (0, 4, 1.0), lens=38, fstop=3.2)
    _bake(dom)


# ----------------------------------------------------------------------------- furry creature (particle hair)
@recipe("fuzzy_creature", "day", fog=0.0, doc="a soft furry creature with thousands of hair strands bouncing in a breeze (fur, hair, cute, pet, animal, soft, fluffy)")
def fuzzy_creature(p, T):
    C.floor("#8fb37a", rough=0.9)
    root = L.empty("critter", None, (0, 4, 0))
    fur = C.pbr("#ffb45a", 0.0, 0.55)
    body = C.mesh("sphere", fur, loc=(0, 0, 1.0), scale=(1.7, 1.5, 1.6), parent=root, name="body")
    ps = body.modifiers.new("fur", "PARTICLE_SYSTEM").particle_system.settings
    ps.type, ps.count, ps.hair_length = "HAIR", 1800 if C.CFG.get("quality") == "draft" else 4500, 0.34
    ps.child_type = "INTERPOLATED"
    ps.child_percent, ps.rendered_child_count = 4, 8
    ps.child_radius, ps.child_roundness = 0.12, 0.5
    ps.clump_factor, ps.roughness_1, ps.root_radius, ps.tip_radius = 0.45, 0.06, 0.012, 0.0
    ps.use_close_tip = True
    ps.render_type = "PATH"
    for sx in (-1, 1):
        C.mesh("sphere", C.pbr("#ffffff", 0, 0.2), loc=(sx * 0.42, -0.62, 1.45), scale=(0.36, 0.2, 0.44), parent=root)
        C.mesh("sphere", C.pbr("#101216", 0, 0.05), loc=(sx * 0.42, -0.74, 1.45), scale=(0.2, 0.09, 0.26), parent=root)
        C.mesh("sphere", C.pbr("#ffb45a", 0, 0.8), loc=(sx * 0.4, 0.2, 0.15), scale=(0.5, 0.4, 0.26), parent=root)
    C.mesh("sphere", C.pbr("#3a1d20", 0, 0.3), loc=(0, -0.78, 1.05), scale=(0.22, 0.14, 0.14), parent=root)
    t = 0.0
    while t <= T + 0.5:      # bounce with squash & stretch
        up = abs(math.sin(t * 3.0))
        key(root, frame(t), loc=(0, 4, up * 0.45), scale=(1 + 0.08 * (1 - up), 1 + 0.08 * (1 - up), 1 - 0.12 * (1 - up) + 0.05 * up), interp="BEZIER")
        t += 0.25
    bpy.ops.object.effector_add(type="WIND", location=(-4, 3.5, 1.4), rotation=(0, math.pi / 2, 0))
    wind = bpy.context.active_object
    wind.field.strength, wind.field.noise = 4.0, 1.5
    C.camera((-1.2, -4.2, 1.6), (1.2, -3.6, 1.4), (0, 4, 1.4), (0, 4, 1.5), lens=45, fstop=2.4)
