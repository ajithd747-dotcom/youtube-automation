"""Anime action toolkit (runs INSIDE Blender): cel shading + hull outlines, a posable humanoid hero with lagging hair, desert/sky
environment, energy FX (light shards, laser streaks, petals, debris), roll/whip cameras.

Built from the reference clip analysis (skills: anime-action-speed-lines-and-accent, follow-through-secondary-motion,
colour-script-muted-world-accent-fx, establishing-dark-to-light-reveal). The hero is an ORIGINAL character, not a copy.
World: Z up, metres. Presets are described by dicts so a shot plan can name them (see PRESETS).
"""
import math
import random

import bpy

import scene_lib as L
from scene_lib import STATE, frame, key

D = math.radians
SKIN, SUIT, ARMOR, HAIR, STEEL, MAGENTA = "#c98d6b", "#3b2745", "#8d9096", "#f3a9cb", "#c7ccd4", "#ff2bd6"


# ----------------------------------------------------------------------------- toon material + outline
def toon(color, bands=3, shade=0.55, tint=(0.85, 0.75, 1.0)):
    """Cel-shaded material: Diffuse -> Shader-to-RGB -> constant ColorRamp (shadow / base / light) -> Emission."""
    base = L.rgba(color)
    m = bpy.data.materials.new("toon")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    sh = (base[0] * shade * tint[0], base[1] * shade * tint[1], base[2] * shade * tint[2], 1)
    hi = tuple(min(1.0, c * 1.18 + 0.02) for c in base[:3]) + (1,)
    els = ramp.color_ramp.elements
    els[0].color, els[0].position = sh, 0.0
    els[1].color, els[1].position = base, 0.34
    if bands >= 3:
        e = els.new(0.78)
        e.color = hi
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(diff.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    m.diffuse_color = base
    return m


def flat(color, strength=1.0):
    m = bpy.data.materials.new("flat")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = L.rgba(color)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    m.diffuse_color = L.rgba(color)
    return m


_OUTLINE = None


def outline_mat():
    global _OUTLINE
    if _OUTLINE is None or _OUTLINE.name not in bpy.data.materials:
        _OUTLINE = flat("#120a16")
        _OUTLINE.name = "outline"
        _OUTLINE.use_backface_culling = True
    return _OUTLINE


def add_outline(o, width=0.012):
    """Inverted-hull outline: solidify pushed outward with flipped normals, black emission, back faces only."""
    o.data.materials.append(outline_mat())
    md = o.modifiers.new("Outline", "SOLIDIFY")
    md.thickness, md.offset, md.use_flip_normals, md.material_offset = -width, 1.0, True, 1
    return o


def mesh(kind, color, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), parent=None, outline=0.012, mat=None):
    o = L.part(kind, parent, "#ffffff", loc=loc, scale=scale, rot=rot, flat=False, smooth=True)
    o.data.materials.clear()
    o.data.materials.append(mat or toon(color))
    if outline:
        add_outline(o, outline)
    return o


# ----------------------------------------------------------------------------- hero
JOINTS = ["pelvis", "torso", "neck", "head", "l_sh", "l_el", "r_sh", "r_el", "l_hip", "l_kn", "r_hip", "r_kn"]


def limb(parent, length, r0, r1, color, outline=0.012, k=1.0):
    """Capsule-like limb hanging down (-Z) from its pivot: a cylinder plus a rounded end (knee/elbow/tip), slightly tapered."""
    r0, r1 = r0 * k, r1 * k
    rm = (r0 + r1) / 2
    body = mesh("cylinder", color, loc=(0, 0, -length / 2), scale=(rm * 2, rm * 2, length), parent=parent, outline=outline)
    mesh("sphere", color, loc=(0, 0, -length), scale=(r1 * 2.1,) * 3, parent=parent, outline=outline)
    mesh("sphere", color, loc=(0, 0, 0), scale=(r0 * 2.1,) * 3, parent=parent, outline=outline)
    return body


def build_hero(loc=(0, 0, 0), s=1.0):
    """Original anime-style hero: dark suit, grey armour plates, pink hair (chain that lags), sword. ~1.75 m * s."""
    root = L.empty("hero", None, loc)
    root.scale = (s, s, s)
    j = {"root": root}
    j["pelvis"] = L.empty("pelvis", root, (0, 0, 0.95))
    j["torso"] = L.empty("torso", j["pelvis"], (0, 0, 0.05))
    mesh("sphere", SUIT, loc=(0, 0, 0), scale=(0.32, 0.2, 0.22), parent=j["pelvis"])
    mesh("cone", SUIT, loc=(0, 0, 0.28), scale=(0.44, 0.27, 0.58), rot=(math.pi, 0, 0), parent=j["torso"])
    mesh("cube", ARMOR, loc=(0, -0.11, 0.34), scale=(0.3, 0.05, 0.28), parent=j["torso"], outline=0.008)      # chest plate
    j["neck"] = L.empty("neck", j["torso"], (0, 0, 0.57))
    mesh("cylinder", SKIN, loc=(0, 0, 0.04), scale=(0.09, 0.09, 0.1), parent=j["neck"], outline=0.006)
    j["head"] = L.empty("head", j["neck"], (0, 0, 0.18))
    j["head"].scale = (1.3, 1.3, 1.3)
    mesh("sphere", SKIN, scale=(0.2, 0.22, 0.25), parent=j["head"])
    for sx in (-1, 1):
        mesh("sphere", "#e7fff5", loc=(sx * 0.05, -0.098, 0.015), scale=(0.05, 0.02, 0.065), parent=j["head"], outline=0, mat=flat("#e7fff5"))
        mesh("sphere", "#20d6b4", loc=(sx * 0.05, -0.108, 0.015), scale=(0.03, 0.012, 0.045), parent=j["head"], outline=0, mat=flat("#20d6b4", 1.6))
        mesh("cube", "#2a1a24", loc=(sx * 0.055, -0.1, 0.075), scale=(0.07, 0.008, 0.012), rot=(0, sx * D(-14), 0), parent=j["head"], outline=0, mat=flat("#2a1a24"))
    mesh("cube", "#3a1c1c", loc=(0, -0.106, -0.06), scale=(0.06, 0.008, 0.012), parent=j["head"], outline=0, mat=flat("#3a1c1c"))
    mesh("sphere", HAIR, loc=(0, 0.045, 0.05), scale=(0.24, 0.22, 0.23), parent=j["head"])                         # hair cap (back/top)
    mesh("sphere", HAIR, loc=(0, -0.05, 0.135), scale=(0.235, 0.14, 0.09), rot=(D(-12), 0, 0), parent=j["head"], outline=0.008)   # fringe
    # hair: several spiky chains (centre + sides) so it reads as anime hair clumps; each segment has its own pivot to lag
    j["hair"] = []
    for c, (yaw, spread, n_seg, wid) in enumerate([(0, 0.0, 5, 1.0), (D(28), 0.5, 4, 0.8), (D(-28), -0.5, 4, 0.8), (D(58), 0.9, 3, 0.65), (D(-58), -0.9, 3, 0.65)]):
        prev = j["head"]
        for i in range(n_seg):
            piv = L.empty(f"hair{c}_{i}", prev, (spread * 0.05 if i == 0 else 0, 0.1 if i == 0 else 0, 0.04 if i == 0 else -0.2 * (1.0 - 0.1 * i)))
            piv.rotation_euler = (D(20 if i == 0 else 4), 0, yaw if i == 0 else 0)
            mesh("cone", HAIR, loc=(0, 0, -0.13), scale=(0.2 * wid * (1 - 0.13 * i), 0.13 * wid * (1 - 0.13 * i), 0.36), rot=(math.pi, 0, 0), parent=piv, outline=0.008)
            j["hair"].append(piv)
            prev = piv
    for side, sx in (("l", -1), ("r", 1)):
        j[side + "_sh"] = L.empty(side + "_sh", j["torso"], (sx * 0.22, 0, 0.5))
        mesh("sphere", ARMOR, scale=(0.13, 0.13, 0.13), parent=j[side + "_sh"], outline=0.008)
        limb(j[side + "_sh"], 0.3, 0.06, 0.05, SUIT, k=1.45)
        j[side + "_el"] = L.empty(side + "_el", j[side + "_sh"], (0, 0, -0.3))
        limb(j[side + "_el"], 0.28, 0.05, 0.04, SUIT, k=1.45)
        mesh("sphere", "#22141f", loc=(0, 0, -0.3), scale=(0.085, 0.07, 0.09), parent=j[side + "_el"], outline=0.008)   # glove
        j[side + "_hip"] = L.empty(side + "_hip", j["pelvis"], (sx * 0.1, 0, -0.02))
        limb(j[side + "_hip"], 0.44, 0.09, 0.065, SUIT, k=1.45)
        j[side + "_kn"] = L.empty(side + "_kn", j[side + "_hip"], (0, 0, -0.44))
        limb(j[side + "_kn"], 0.42, 0.065, 0.05, SUIT, k=1.45)
        mesh("cone", ARMOR, loc=(0, -0.02, -0.4), scale=(0.11, 0.2, 0.18), rot=(math.pi, 0, 0), parent=j[side + "_kn"], outline=0.008)  # boot
    sword = L.empty("sword", j["r_el"], (0.02, -0.02, -0.3))
    mesh("cube", "#2a2530", loc=(0, 0, 0), scale=(0.035, 0.035, 0.16), parent=sword, outline=0.006)
    mesh("cube", STEEL, loc=(0, 0, 0.62), scale=(0.03, 0.012, 1.0), parent=sword, outline=0.006)
    sword.rotation_euler = (D(90), 0, 0)
    j["sword"] = sword
    return j


POSES = {  # joint -> (rx, ry, rz) degrees; sign convention: rx swings limbs forward(-)/back(+) about the body's X axis, ry rolls sideways
    "stand": dict(),
    "dive": dict(torso=(-12, 0, 0), l_sh=(0, 88, 0), r_sh=(0, -88, 0), l_el=(-10, 0, 0), r_el=(-10, 0, 0), l_hip=(4, 0, 0), r_hip=(-4, 0, 0), head=(8, 0, 0)),
    "lunge": dict(torso=(-38, 0, 0), l_sh=(-70, 30, 0), r_sh=(50, -30, 0), l_el=(-40, 0, 0), r_el=(-20, 0, 0), l_hip=(-70, 0, 0), l_kn=(70, 0, 0), r_hip=(35, 0, 0), r_kn=(30, 0, 0), head=(20, 0, 0)),
    "crouch": dict(torso=(-30, 0, 0), l_sh=(-40, 20, 0), r_sh=(-90, -20, 0), l_el=(-50, 0, 0), r_el=(-40, 0, 0), l_hip=(-95, 10, 0), l_kn=(100, 0, 0), r_hip=(-20, -10, 0), r_kn=(80, 0, 0), head=(20, 0, 0)),
    "jump": dict(torso=(-10, 0, 0), l_sh=(-30, 40, 0), r_sh=(-20, -40, 0), l_hip=(-80, 0, 0), l_kn=(100, 0, 0), r_hip=(-60, 0, 0), r_kn=(90, 0, 0), head=(-10, 0, 0)),
    "reach": dict(torso=(-25, 0, 0), l_sh=(-160, 10, 0), r_sh=(-40, -60, 0), r_el=(-30, 0, 0), l_hip=(-30, 0, 0), l_kn=(30, 0, 0), r_hip=(20, 0, 0), r_kn=(50, 0, 0)),
    "glide": dict(torso=(-70, 0, 0), l_sh=(-170, 8, 0), r_sh=(-170, -8, 0), l_hip=(10, 0, 0), r_hip=(10, 0, 0), l_kn=(20, 0, 0), r_kn=(20, 0, 0), head=(50, 0, 0)),
}


def apply_pose(j, name, f, blend=None):
    """Key every joint's Euler rotation for pose `name` at frame f (optionally blended with a second pose (name2, w))."""
    p = POSES[name]
    p2, w = (POSES[blend[0]], blend[1]) if blend else ({}, 0.0)
    for jn in JOINTS:
        a = p.get(jn, (0, 0, 0))
        b = p2.get(jn, (0, 0, 0))
        e = tuple(D(a[i] * (1 - w) + b[i] * w) for i in range(3))
        j[jn].rotation_euler = e
        j[jn].keyframe_insert("rotation_euler", frame=f)


def hair_follow(j, path, fps, lag=2, gain=1.1, spring=0.5):
    """Secondary motion: each hair segment reacts to the ROOT's velocity with an increasing delay and overshoot.
    path: function t(seconds) -> (x, y, z). Hair swings opposite to the direction of travel and settles when the body stops."""
    dt = 1.0 / fps
    frames = STATE["frames"]
    for i, piv in enumerate(j["hair"]):
        for f in range(1, frames + 1, 1):
            t = (f - 1) * dt - i * lag * dt
            a, b = path(max(0, t - dt)), path(max(0, t))
            vel = [(b[k] - a[k]) / dt for k in range(3)]
            # tilt back against travel: rotation about X follows the y-velocity, about Y the x-velocity, plus gravity droop
            rx = D(max(-70, min(70, -vel[1] * 6.0 * gain)) + 6 * math.sin(f * 0.35 + i))
            ry = D(max(-70, min(70, vel[0] * 6.0 * gain)))
            rz = D(4 * math.sin(f * 0.21 + i * 0.7)) * spring
            piv.rotation_euler = (rx * (0.6 + 0.15 * i) + D(12), ry * (0.6 + 0.15 * i), rz)
            piv.keyframe_insert("rotation_euler", frame=f)


# ----------------------------------------------------------------------------- environment
def desert(z=0.0, size=4000):
    """Big terrain plane with banded (toon) desert colours from a Noise texture: orange / brown / grey."""
    o = mesh("plane", "#c98f5a", loc=(0, 0, z), scale=(size, size, 1), outline=0, mat=None)
    m = bpy.data.materials.new("desert")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 16.0
    noise.inputs["Detail"].default_value = 6
    noise.inputs["Roughness"].default_value = 0.62
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    cols = [(0.0, "#6f5a52"), (0.3, "#8a6d5f"), (0.5, "#a98a76"), (0.68, "#bd9f8b"), (0.85, "#a3a2a6")]
    ramp.color_ramp.elements[0].color, ramp.color_ramp.elements[0].position = L.rgba(cols[0][1]), 0.0
    ramp.color_ramp.elements[1].color, ramp.color_ramp.elements[1].position = L.rgba(cols[1][1]), cols[1][0]
    for pos, c in cols[2:]:
        e = ramp.color_ramp.elements.new(pos)
        e.color = L.rgba(c)
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    o.data.materials.clear()
    o.data.materials.append(m)
    return o


def city_ledge(z=0.0, x0=-300, x1=300, y=60, seed=3):
    """Grey blocky structures along a ridge (the bottom-of-frame architecture in the reference)."""
    rnd = random.Random(seed)
    root = L.empty("city", None, (0, 0, z))
    x = x0
    while x < x1:
        w, d, h = rnd.uniform(6, 22), rnd.uniform(6, 30), rnd.uniform(1, 9)
        mesh("cube", "#9a9ea3", loc=(x, y + rnd.uniform(-8, 8), h / 2), scale=(w, d, h), parent=root, outline=0.05)
        x += w * rnd.uniform(0.6, 1.1)
    return root


def sky(top="#a9b9c8", horizon="#dfe4e7"):
    w = bpy.data.worlds.new("sky")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color, ramp.color_ramp.elements[0].position = L.rgba(horizon), 0.42
    ramp.color_ramp.elements[1].color, ramp.color_ramp.elements[1].position = L.rgba(top), 0.72
    nt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    bpy.context.scene.world = w


def clouds(n=14, spread=500, z=90, seed=5):
    rnd = random.Random(seed)
    for _ in range(n):
        p = (rnd.uniform(-spread, spread), rnd.uniform(80, spread * 1.5), z + rnd.uniform(-30, 60))
        mesh("sphere", "#c5ced6", loc=p, scale=(rnd.uniform(50, 130), rnd.uniform(20, 40), rnd.uniform(8, 18)), outline=0, mat=flat("#c9d2d9"))


# ----------------------------------------------------------------------------- FX
def shard(loc, scale, rot, t0, dur=0.7, strength=7.0):
    """Large glowing magenta light shard (flat triangle prism) that snaps in and fades."""
    root = L.empty("shard", None, loc)
    o = L.prism(root, [(-0.5, 0), (0.5, 0), (0.0, -3.0)], 0.02, MAGENTA, flat=True)
    o.data.materials.clear()
    o.data.materials.append(flat(MAGENTA, strength))
    root.rotation_euler = rot
    root.scale = (0.001,) * 3
    f0 = frame(t0)
    key(root, max(1, f0 - 1), scale=(0.001,) * 3, interp="CONSTANT")
    key(root, f0, scale=scale, interp="LINEAR")
    key(root, frame(t0 + dur), scale=(scale[0] * 1.1, scale[1] * 1.3, scale[2]), interp="LINEAR")
    key(root, frame(t0 + dur) + 1, scale=(0.001,) * 3, interp="CONSTANT")
    return root


def laser(p0, p1, t0, dur=0.35, width=0.5, strength=8.0):
    """Thin emissive streak between two points, visible for dur seconds (hard cut on/off like a drawn effect)."""
    from mathutils import Vector
    a, b = Vector(p0), Vector(p1)
    mid, d = (a + b) / 2, (b - a)
    root = L.empty("laser", None, tuple(mid))
    o = mesh("cube", MAGENTA, scale=(width, d.length, width * 0.4), parent=root, outline=0, mat=flat(MAGENTA, strength))
    root.rotation_euler = d.to_track_quat("Y", "Z").to_euler()
    root.scale = (0.001,) * 3
    key(root, max(1, frame(t0) - 1), scale=(0.001,) * 3, interp="CONSTANT")
    key(root, frame(t0), scale=(1, 1, 1), interp="CONSTANT")
    key(root, frame(t0 + dur), scale=(1, 1, 1), interp="CONSTANT")
    key(root, frame(t0 + dur) + 1, scale=(0.001,) * 3, interp="CONSTANT")
    return root


def petals(center, t0, n=26, life=1.6, spread=3.0, seed=2):
    """Glowing magenta petals/blobs drifting away from a point (particle burst done with keyframes: deterministic + cheap)."""
    rnd = random.Random(seed)
    for i in range(n):
        v = (rnd.uniform(-1, 1) * spread, rnd.uniform(-1, 1) * spread * 0.4, rnd.uniform(-0.3, 1.2) * spread)
        s = rnd.uniform(0.05, 0.22)
        root = L.empty("petal", None, center)
        mesh("sphere", MAGENTA, scale=(s * 1.6, s * 0.5, s), parent=root, outline=0, mat=flat(MAGENTA, 6.0))
        st = t0 + rnd.uniform(0, 0.35)
        key(root, max(1, frame(st) - 1), loc=center, scale=(0.001,) * 3, interp="CONSTANT")
        for k in range(0, 5):
            tt = k / 4.0
            pos = tuple(center[c] + v[c] * tt * life - (0.5 * 2.0 * (tt * life) ** 2 if c == 2 else 0) for c in range(3))
            sc = (1, 1, 1) if k < 4 else (0.001,) * 3
            key(root, frame(st + tt * life), loc=pos, scale=sc, rot=(rnd.uniform(0, 3), rnd.uniform(0, 3), 0), interp="LINEAR")


def debris(center, t0, n=26, life=1.8, size=1.0, seed=4):
    """Grey shard/smoke burst (impact explosion): shards fly outward, arc and fall, puffs swell then fade by shrinking."""
    rnd = random.Random(seed)
    for i in range(n):
        ang = rnd.uniform(-0.9, 0.9)
        sp = rnd.uniform(6, 22) * size
        v = (math.sin(ang) * sp, rnd.uniform(-2, 4), math.cos(ang) * sp * rnd.uniform(0.5, 1.3))
        s = rnd.uniform(0.6, 2.4) * size
        root = L.empty("debris", None, center)
        kind = "ico" if False else "cube"
        mesh("cube", "#8d9096", scale=(s * rnd.uniform(0.5, 1.4), s * 0.6, s * rnd.uniform(0.6, 1.6)), parent=root, outline=0.03 * size)
        key(root, max(1, frame(t0) - 1), loc=center, scale=(0.001,) * 3, interp="CONSTANT")
        for k in range(0, 6):
            tt = k / 5.0
            T = tt * life
            pos = (center[0] + v[0] * T, center[1] + v[1] * T, center[2] + v[2] * T - 0.5 * 9.8 * T * T * 0.5)
            key(root, frame(t0 + T), loc=pos, rot=(T * rnd.uniform(-4, 4), T * rnd.uniform(-4, 4), 0), scale=(1, 1, 1) if k < 5 else (0.001,) * 3, interp="LINEAR")
    for i in range(9):  # smoke puffs
        root = L.empty("puff", None, (center[0] + random.uniform(-3, 3), center[1], center[2] + random.uniform(0, 2)))
        s = random.uniform(3, 6) * size
        mesh("sphere", "#a9aeb3", scale=(s, s * 0.7, s * 1.2), parent=root, outline=0, mat=flat("#b7bcc1"))
        key(root, max(1, frame(t0) - 1), scale=(0.001,) * 3, interp="CONSTANT")
        key(root, frame(t0 + 0.25), scale=(1, 1, 1), interp="BEZIER")
        key(root, frame(t0 + life * 1.4), scale=(1.5, 1.5, 1.5), interp="BEZIER")
        key(root, frame(t0 + life * 1.4) + 1, scale=(0.001,) * 3, interp="CONSTANT")


# ----------------------------------------------------------------------------- camera / render
def cam_rig(keys, lens=35, roll=None, shake=0.0, seed=1):
    """keys: [(t, pos, target)]; roll: [(t, degrees)] about the view axis; shake: metres of handheld noise.
    Rig empty tracks the target; the camera is its child so its local Z rotation is a true roll."""
    rig = L.empty("cam_rig", None, keys[0][1])
    tgt = L.empty("cam_t", None, keys[0][2])
    c = rig.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    cd = bpy.data.cameras.new("cam")
    cd.lens, cd.clip_end = lens, 30000
    cam = L._link(bpy.data.objects.new("cam", cd))
    cam.parent = rig
    bpy.context.scene.camera = cam
    for t, p, tg in keys:
        key(rig, frame(t), loc=p, interp="BEZIER")
        key(tgt, frame(t), loc=tg, interp="BEZIER")
    for t, deg in (roll or [(0, 0)]):
        cam.rotation_euler = (0, 0, D(deg))
        cam.keyframe_insert("rotation_euler", frame=frame(t))
    if shake:
        rnd = random.Random(seed)
        for f in range(1, STATE["frames"] + 1, 2):
            t = (f - 1) / STATE["fps"]
            base = [sum(k[1][i] * w for k, w in zip(keys, _weights(keys, t))) for i in range(3)]
            key(rig, f, loc=tuple(base[i] + rnd.uniform(-shake, shake) for i in range(3)), interp="LINEAR")
    return cam, tgt


def _weights(keys, t):
    """Linear interpolation weights of `keys` at time t (for adding shake on top of the keyed path)."""
    ts = [k[0] for k in keys]
    if t <= ts[0]:
        return [1.0] + [0.0] * (len(keys) - 1)
    if t >= ts[-1]:
        return [0.0] * (len(keys) - 1) + [1.0]
    for i in range(len(ts) - 1):
        if ts[i] <= t <= ts[i + 1]:
            u = (t - ts[i]) / (ts[i + 1] - ts[i])
            w = [0.0] * len(keys)
            w[i], w[i + 1] = 1 - u, u
            return w
    return [1.0] + [0.0] * (len(keys) - 1)


def setup(width, height, fps, duration, samples=8, motion_blur=False, bloom=True, exposure=0.0, sky_top="#a9b9c8", sky_hor="#dfe4e7"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    STATE.update(fps=fps, frames=max(2, int(math.ceil(duration * fps)) + 1), aspect=width / height, style="anime", flat=True)
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = width, height, 100
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = 1, STATE["frames"]
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = name
            break
        except TypeError:
            continue
    sc.eevee.taa_render_samples = samples
    sc.eevee.use_raytracing = False
    sc.eevee.use_shadows = False
    sc.render.use_motion_blur = motion_blur
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = exposure
    sky(sky_top, sky_hor)
    sun = L._link(bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")))
    sun.data.energy = 3.0
    sun.rotation_euler = (D(50), D(20), D(-40))
    sc.use_nodes = True
    nt = sc.node_tree
    nt.nodes.clear()
    rl, comp = nt.nodes.new("CompositorNodeRLayers"), nt.nodes.new("CompositorNodeComposite")
    last = rl.outputs["Image"]
    if bloom:
        gl = nt.nodes.new("CompositorNodeGlare")
        try:
            gl.glare_type = "BLOOM"
        except Exception:
            gl.glare_type = "FOG_GLOW"
        for a, v in (("threshold", 1.4), ("size", 6), ("quality", "MEDIUM")):
            try:
                setattr(gl, a, v)
            except Exception:
                pass
        nt.links.new(last, gl.inputs["Image"])
        last = gl.outputs["Image"]
    nt.links.new(last, comp.inputs["Image"])
    return sc
