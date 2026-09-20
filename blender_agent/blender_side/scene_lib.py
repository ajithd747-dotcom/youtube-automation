"""Helper library that runs INSIDE Blender (bpy). It turns a declarative "shot" dict into a
keyframed scene: stickman rigs, text, icons, primitives, camera moves, background.

Everything is placed in a normalized frame: pos = [x, z] in [-1, 1] (x right, z up), size = fraction
of frame height. World units: frame height is always H = 10, width W = 10 * aspect. Objects are built
in the XZ plane and the camera looks along +Y, so 2D styles use an orthographic camera and the
"3d" style uses a slowly orbiting perspective camera.

The same functions are exposed to LLM-written custom code (see coder.py) so generated code can reuse
them instead of re-deriving low-level bpy calls.
"""
import math
import os
import textwrap

import bpy

from dsl import ACTIONS, ICONS, SHAPES  # noqa: F401  (shared with the director)

H = 10.0  # world height of the frame
STATE = {"fps": 24, "frames": 24, "aspect": 16 / 9, "style": "kinetic", "flat": True}


# ----------------------------------------------------------------------------- basics
def W():
    return H * STATE["aspect"]


def frame(t):
    """Seconds -> frame number."""
    return 1 + int(round(t * STATE["fps"]))


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgba(hex_color, alpha=1.0):
    h = str(hex_color).lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        r, g, b = 0.5, 0.5, 0.5
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


def make_material(color, flat=None, name="mat"):
    flat = STATE["flat"] if flat is None else flat
    col = rgba(color)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = col  # what the Workbench engine shows
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if flat:
        sh = nt.nodes.new("ShaderNodeEmission")
        sh.inputs["Color"].default_value = col
    else:
        sh = nt.nodes.new("ShaderNodeBsdfPrincipled")
        sh.inputs["Base Color"].default_value = col
        sh.inputs["Roughness"].default_value = 0.55
    nt.links.new(sh.outputs[0], out.inputs["Surface"])
    return m


def _link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def empty(name="node", parent=None, loc=(0, 0, 0)):
    e = _link(bpy.data.objects.new(name, None))
    e.empty_display_size = 0.1
    if parent is not None:
        e.parent = parent
    e.location = loc
    return e


def _paint(obj, color, flat=None, smooth=True):
    obj.data.materials.clear()
    obj.data.materials.append(make_material(color, flat))
    if smooth and hasattr(obj.data, "polygons"):
        obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
        obj.data.update()
    return obj


def _mesh_obj(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    return _link(bpy.data.objects.new(name, me))


def part(kind, parent, color, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), flat=None, smooth=True):
    """Add a unit primitive (height/diameter 1) as a child. kind: cube|sphere|cylinder|cone|torus|plane."""
    ops = bpy.ops.mesh
    if kind == "sphere":
        ops.primitive_uv_sphere_add(radius=0.5, segments=32, ring_count=16)
    elif kind == "cylinder":
        ops.primitive_cylinder_add(radius=0.5, depth=1, vertices=32)
    elif kind == "cone":
        ops.primitive_cone_add(radius1=0.5, radius2=0, depth=1, vertices=32)
    elif kind == "torus":
        ops.primitive_torus_add(major_radius=0.4, minor_radius=0.1, major_segments=40, minor_segments=16)
    elif kind == "plane":
        ops.primitive_plane_add(size=1)
    else:
        ops.primitive_cube_add(size=1)
    o = bpy.context.active_object
    for c in list(o.users_collection):
        c.objects.unlink(o)
    _link(o)
    o.parent = parent
    o.location, o.scale, o.rotation_euler = loc, scale, rot
    return _paint(o, color, flat, smooth and kind not in ("cube", "plane"))


def prism(parent, pts, depth, color, loc=(0, 0, 0), scale=(1, 1, 1), flat=None):
    """Extruded 2D polygon (points in XZ, y is thickness) -> mesh child."""
    n = len(pts)
    d = depth / 2
    verts = [(x, -d, z) for x, z in pts] + [(x, d, z) for x, z in pts]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    o = _mesh_obj("prism", verts, faces)
    o.parent, o.location, o.scale = parent, loc, scale
    return _paint(o, color, flat, smooth=False)


_FONT = None


def _font():
    global _FONT
    if _FONT is None:
        project_fonts = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
        for p in (os.environ.get("BLENDER_AGENT_FONT", ""),
                  os.path.join(project_fonts, "DejaVuSans-Bold.ttf"),
                  "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
            if p and os.path.exists(p):
                try:
                    _FONT = bpy.data.fonts.load(p)
                    break
                except Exception:
                    pass
        else:
            _FONT = False
    return _FONT or None


def clean_text(s):
    s = str(s).replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2026", "...")
    return s.encode("ascii", "ignore").decode()


def text_part(parent, text, color, height=1.0, max_width=None, wrap=None, extrude=None, loc=(0, 0, 0)):
    """Centered text child. `height` = height of one line in world units; auto-shrunk to fit max_width."""
    text = clean_text(text)
    lines = textwrap.wrap(text, wrap) if wrap else [text]
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = "\n".join(lines) if lines else " "
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.size = 1.0
    cu.extrude = (0.04 if not STATE["flat"] else 0.0) if extrude is None else extrude
    f = _font()
    if f:
        cu.font = cu.font_bold = f
    o = _link(bpy.data.objects.new("text", cu))
    o.parent = parent
    o.rotation_euler = (math.pi / 2, 0, 0)
    o.location = loc
    o.scale = (height, height, height)
    if max_width:  # measure AFTER scaling + a depsgraph update (dimensions are stale before that); twice for safety
        for _ in range(2):
            bpy.context.view_layer.update()
            w = o.dimensions.x
            if w > max_width:
                k = max_width / w
                o.scale = (o.scale[0] * k, o.scale[1] * k, o.scale[2] * k)
    return _paint(o, color, smooth=False)


# ----------------------------------------------------------------------------- animation helpers
def key(obj, f, loc=None, rot=None, scale=None, interp=None):
    if loc is not None:
        obj.location = loc
        obj.keyframe_insert("location", frame=f)
    if rot is not None:
        obj.rotation_euler = rot
        obj.keyframe_insert("rotation_euler", frame=f)
    if scale is not None:
        obj.scale = scale
        obj.keyframe_insert("scale", frame=f)
    if interp:
        ad = obj.animation_data
        if ad and ad.action:
            for fc in _fcurves(ad.action):
                for kp in fc.keyframe_points:
                    if int(kp.co[0]) == f:
                        kp.interpolation = interp


def _fcurves(action):
    try:
        return list(action.fcurves)
    except AttributeError:  # Blender 5.x layered actions
        out = []
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
        return out


def ease_all(obj, interp="BEZIER"):
    ad = obj.animation_data
    if ad and ad.action:
        for fc in _fcurves(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = interp


def sample(t0, t1, fn, step=2):
    """Yield (frame, t) every `step` frames between t0 and t1 seconds (inclusive)."""
    f0, f1 = frame(t0), frame(t1)
    f = f0
    while f < f1:
        yield f, (f - 1) / STATE["fps"]
        f += step
    yield f1, (f1 - 1) / STATE["fps"]


def end_t():
    return (STATE["frames"] - 1) / STATE["fps"]


def apply_entry(root, entry, delay, base_scale, pos):
    """Entry animation on the root empty. Before `delay` the object is invisible (scale ~0)."""
    fps = STATE["fps"]
    f0, dur = frame(delay), int(0.55 * fps)
    tiny = (0.0001,) * 3
    full = (base_scale,) * 3
    key(root, 1, loc=pos, scale=tiny, interp="CONSTANT")
    if entry in ("pop_in", "grow", "fade_in", "type", ""):
        key(root, max(1, f0 - 1), loc=pos, scale=tiny, interp="CONSTANT")
        key(root, f0 + int(dur * 0.6), loc=pos, scale=tuple(base_scale * 1.15 for _ in range(3)), interp="BEZIER")
        key(root, f0 + dur, loc=pos, scale=full, interp="BEZIER")
        return
    off = {
        "slide_in_left": (-W() * 0.7, 0),
        "slide_in_right": (W() * 0.7, 0),
        "slide_in_top": (0, H * 0.7),
        "slide_in_bottom": (0, -H * 0.7),
    }.get(entry)
    if off is None:  # "none" -> just appear
        key(root, max(1, f0 - 1), loc=pos, scale=tiny, interp="CONSTANT")
        key(root, f0, loc=pos, scale=full, interp="CONSTANT")
        return
    start = (pos[0] + off[0], pos[1], pos[2] + off[1])
    key(root, max(1, f0 - 1), loc=start, scale=tiny, interp="CONSTANT")
    key(root, f0, loc=start, scale=full, interp="CONSTANT")
    key(root, f0 + dur, loc=pos, scale=full, interp="BEZIER")


def apply_move(root, move_to, delay, move_time, base_scale, pos):
    if not move_to:
        return
    dest = (move_to[0] * W() / 2, pos[1], move_to[1] * H / 2)
    f0 = frame(delay + 0.6)
    f1 = max(f0 + 2, frame(delay + 0.6 + move_time))
    key(root, f0, loc=pos, scale=(base_scale,) * 3, interp="LINEAR")
    key(root, f1, loc=dest, scale=(base_scale,) * 3, interp="LINEAR")
    key(root, STATE["frames"], loc=dest, scale=(base_scale,) * 3, interp="LINEAR")


def apply_loop(node, loop, delay, unit):
    """Continuous motion on the inner node (relative to the root)."""
    if not loop or loop == "none":
        return
    t0, t1 = delay + 0.4, end_t()
    for f, t in sample(t0, t1, None):
        ph = (t - t0)
        if loop == "float":
            key(node, f, loc=(0, 0, math.sin(ph * 2.4) * 0.05 * unit))
        elif loop == "bounce":
            key(node, f, loc=(0, 0, abs(math.sin(ph * 4.0)) * 0.12 * unit))
        elif loop == "spin":
            key(node, f, rot=(0, 0, ph * 1.6))
        elif loop == "roll":
            key(node, f, rot=(0, -ph * 2.0, 0))
        elif loop == "sway":
            key(node, f, rot=(0, math.sin(ph * 2.5) * 0.14, 0))
        elif loop == "pulse":
            s = 1 + 0.08 * math.sin(ph * 5.0)
            key(node, f, scale=(s, s, s))
        elif loop == "shake":
            key(node, f, loc=(math.sin(ph * 40) * 0.02 * unit, 0, math.cos(ph * 33) * 0.02 * unit))


# ----------------------------------------------------------------------------- stickman rig
LIMB = 0.022


def _limb(parent, length, color, radius=LIMB):
    part("cylinder", parent, color, loc=(0, 0, -length / 2), scale=(radius * 2, radius * 2, length), smooth=True)
    part("sphere", parent, color, loc=(0, 0, 0), scale=(radius * 2.2,) * 3)


def build_stickman(parent, color="#111111", face=True):
    """Returns dict of joint empties. Unit height 1, origin at the body centre."""
    j = {}
    j["pelvis"] = empty("pelvis", parent, (0, 0, -0.02))
    j["torso"] = empty("torso", j["pelvis"])
    part("cylinder", j["torso"], color, loc=(0, 0, 0.15), scale=(LIMB * 2, LIMB * 2, 0.3))
    j["neck"] = empty("neck", j["torso"], (0, 0, 0.3))
    j["head"] = empty("head", j["neck"], (0, 0, 0.1))
    part("sphere", j["head"], color, scale=(0.19, 0.19, 0.19))
    if face:
        for sx in (-1, 1):
            part("sphere", j["head"], "#ffffff", loc=(sx * 0.035, -0.085, 0.02), scale=(0.035,) * 3, flat=True)
        part("cube", j["head"], "#ffffff", loc=(0, -0.088, -0.035), scale=(0.06, 0.01, 0.012), flat=True)
    for side, sx in (("l", -1), ("r", 1)):
        j[side + "_sh"] = empty(side + "_sh", j["torso"], (sx * 0.02, 0, 0.28))
        _limb(j[side + "_sh"], 0.16, color)
        j[side + "_el"] = empty(side + "_el", j[side + "_sh"], (0, 0, -0.16))
        _limb(j[side + "_el"], 0.15, color)
        j[side + "_hip"] = empty(side + "_hip", j["pelvis"], (sx * 0.02, 0, 0))
        _limb(j[side + "_hip"], 0.25, color)
        j[side + "_kn"] = empty(side + "_kn", j[side + "_hip"], (0, 0, -0.25))
        _limb(j[side + "_kn"], 0.25, color)
    return j


def _pose(action, t):
    """Joint angles (radians, about the view axis) + bob for a stickman action at time t."""
    s = math.sin
    d = math.radians
    p = dict(torso=0, head=0, l_sh=d(6), l_el=d(-8), r_sh=d(-6), r_el=d(8), l_hip=0, l_kn=0, r_hip=0, r_kn=0, bob=0)
    if action == "idle":
        p["l_hip"], p["r_hip"] = d(4), d(-4)
        p["bob"] = 0.004 * s(t * 2.2)
        p["l_sh"] += d(3) * s(t * 2.2)
        p["r_sh"] -= d(3) * s(t * 2.2)
    elif action in ("walk", "run"):
        w = 6.0 if action == "walk" else 9.5
        a = d(30 if action == "walk" else 50)
        p["l_hip"], p["r_hip"] = a * s(t * w), -a * s(t * w)
        p["l_kn"] = d(35 if action == "walk" else 70) * max(0, -s(t * w + 0.6))
        p["r_kn"] = d(35 if action == "walk" else 70) * max(0, s(t * w + 0.6))
        p["l_sh"], p["r_sh"] = -a * 0.9 * s(t * w), a * 0.9 * s(t * w)
        p["l_el"], p["r_el"] = d(-25), d(25)
        p["torso"] = d(-4 if action == "walk" else -14)
        p["bob"] = 0.012 * abs(s(t * w))
    elif action == "wave":
        p["r_sh"] = d(-150)
        p["r_el"] = d(-25) * s(t * 9) - d(20)
        p["head"] = d(4) * s(t * 3)
        p["bob"] = 0.004 * s(t * 2.2)
    elif action in ("jump", "celebrate"):
        ph = (t * 3.2) % (2 * math.pi)
        p["bob"] = 0.09 * max(0, s(ph)) if action == "jump" else 0.05 * abs(s(t * 6))
        up = 1 if s(ph) > 0 or action == "celebrate" else 0
        p["l_sh"], p["r_sh"] = d(150) * up + d(10), d(-150) * up - d(10)
        p["l_el"], p["r_el"] = d(20) * s(t * 10), d(-20) * s(t * 10)
        p["l_kn"] = p["r_kn"] = d(30) * max(0, -s(ph))
    elif action == "think":
        p["r_sh"] = d(-105)
        p["r_el"] = d(-118)
        p["head"] = d(6) * s(t * 1.5)
        p["bob"] = 0.003 * s(t * 2)
    elif action == "point":
        p["r_sh"] = d(-88)
        p["r_el"] = d(-4)
        p["l_sh"] += d(4) * s(t * 2)
    elif action == "talk":
        p["r_sh"] = d(-40) + d(28) * s(t * 5.3)
        p["r_el"] = d(-40) * (1 + s(t * 5.3))
        p["l_sh"] = d(40) + d(18) * s(t * 4.1 + 1)
        p["l_el"] = d(30)
        p["head"] = d(5) * s(t * 3.3)
        p["bob"] = 0.005 * s(t * 4)
    elif action == "sad":
        p["head"] = d(-16)
        p["torso"] = d(8)
        p["bob"] = 0.002 * s(t * 1.5)
    return p


def animate_stickman(joints, action, delay):
    t0 = delay
    sign = {"torso": 1, "head": 1, "l_sh": 1, "l_el": 1, "r_sh": 1, "r_el": 1, "l_hip": 1, "l_kn": 1, "r_hip": 1, "r_kn": 1}
    step = 2
    for f, t in sample(0.0, end_t(), None, step):
        p = _pose(action, max(0.0, t - t0))
        for name in sign:
            joints[name if name in ("torso", "head") else name].rotation_euler = (0, p[name], 0)
            joints[name].keyframe_insert("rotation_euler", frame=f)
        joints["pelvis"].location = (0, 0, -0.02 + p["bob"])
        joints["pelvis"].keyframe_insert("location", frame=f)


# ----------------------------------------------------------------------------- icons
def _star_pts(n=5, r_out=0.5, r_in=0.22):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi / 2 + i * math.pi / n
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def build_icon(parent, name, color):
    """Composite icons in a unit box. `color` is the accent colour."""
    P = lambda *a, **k: part(*a, **k)
    dark, light = "#222222", "#f2f2f2"
    if name == "star":
        prism(parent, _star_pts(), 0.12, color)
    elif name == "heart":
        pts = []
        for i in range(48):
            a = 2 * math.pi * i / 48
            x = 16 * math.sin(a) ** 3
            z = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
            pts.append((x / 34, z / 34 + 0.02))
        prism(parent, pts, 0.14, color)
    elif name in ("arrow", "arrow_right"):
        prism(parent, [(-0.5, 0.14), (0.1, 0.14), (0.1, 0.36), (0.5, 0), (0.1, -0.36), (0.1, -0.14), (-0.5, -0.14)], 0.12, color)
    elif name == "check":
        prism(parent, [(-0.48, 0.0), (-0.32, -0.16), (-0.12, -0.0), (0.32, 0.42), (0.48, 0.26), (-0.12, -0.34)], 0.12, color)
    elif name == "cross":
        pts = [(-0.5, 0.36), (-0.36, 0.5), (0, 0.14), (0.36, 0.5), (0.5, 0.36), (0.14, 0), (0.5, -0.36), (0.36, -0.5), (0, -0.14), (-0.36, -0.5), (-0.5, -0.36), (-0.14, 0)]
        prism(parent, pts, 0.12, color)
    elif name == "bolt":
        prism(parent, [(0.1, 0.5), (-0.3, -0.04), (-0.02, -0.04), (-0.12, -0.5), (0.32, 0.1), (0.04, 0.1), (0.3, 0.5)], 0.12, color)
    elif name == "lightbulb":
        P("sphere", parent, color, loc=(0, 0, 0.12), scale=(0.62, 0.62, 0.62))
        P("cylinder", parent, "#888888", loc=(0, 0, -0.32), scale=(0.28, 0.28, 0.22))
        P("cylinder", parent, "#555555", loc=(0, 0, -0.46), scale=(0.18, 0.18, 0.08))
    elif name == "coin":
        P("cylinder", parent, color, rot=(math.pi / 2, 0, 0), scale=(0.9, 0.9, 0.12))
        text_part(parent, "$", "#7a5a00", height=0.62, extrude=0.0, loc=(0, -0.07, 0))
    elif name == "laptop":
        P("cube", parent, "#9aa0a6", loc=(0, 0, -0.32), scale=(0.95, 0.62, 0.06))
        P("cube", parent, dark, loc=(0, 0.28, 0.02), scale=(0.8, 0.05, 0.6), rot=(math.radians(-12), 0, 0))
        P("cube", parent, color, loc=(0, 0.25, 0.02), scale=(0.7, 0.03, 0.5), rot=(math.radians(-12), 0, 0), flat=True)
    elif name == "phone":
        P("cube", parent, dark, scale=(0.36, 0.06, 0.8))
        P("cube", parent, color, loc=(0, -0.035, 0.02), scale=(0.3, 0.02, 0.66), flat=True)
    elif name in ("chart_up", "chart_bar"):
        for i, hgt in enumerate((0.25, 0.45, 0.65, 0.9)):
            P("cube", parent, color, loc=(-0.36 + i * 0.24, 0, -0.5 + hgt / 2), scale=(0.18, 0.1, hgt))
        if name == "chart_up":
            prism(parent, [(-0.5, 0.0), (0.0, 0.18), (0.5, 0.5), (0.5, 0.32), (0.0, 0.0), (-0.5, -0.18)], 0.05, "#222222", loc=(0, -0.08, 0.05), scale=(1, 1, 0.7))
    elif name == "clock":
        P("cylinder", parent, light, rot=(math.pi / 2, 0, 0), scale=(0.95, 0.95, 0.1))
        P("torus", parent, dark, rot=(math.pi / 2, 0, 0), scale=(2.3, 2.3, 2.3))
        P("cube", parent, dark, loc=(0, -0.08, 0.15), scale=(0.05, 0.03, 0.32))
        P("cube", parent, dark, loc=(0.12, -0.08, 0), scale=(0.28, 0.03, 0.05))
    elif name == "globe":
        P("sphere", parent, "#2f7fd8", scale=(0.9, 0.9, 0.9))
        P("sphere", parent, "#3cae5c", loc=(-0.15, -0.3, 0.2), scale=(0.35, 0.2, 0.3))
        P("sphere", parent, "#3cae5c", loc=(0.22, -0.32, -0.15), scale=(0.3, 0.2, 0.25))
    elif name == "question":
        text_part(parent, "?", color, height=1.3, extrude=0.08)
    elif name == "exclaim":
        text_part(parent, "!", color, height=1.3, extrude=0.08)
    elif name == "lock":
        P("cube", parent, color, loc=(0, 0, -0.15), scale=(0.7, 0.2, 0.55))
        P("torus", parent, "#888888", loc=(0, 0, 0.18), rot=(math.pi / 2, 0, 0), scale=(0.95, 0.95, 0.95))
    elif name == "gear":
        P("cylinder", parent, color, rot=(math.pi / 2, 0, 0), scale=(0.7, 0.7, 0.18))
        for i in range(8):
            a = i * math.pi / 4
            P("cube", parent, color, loc=(0.4 * math.cos(a), 0, 0.4 * math.sin(a)), rot=(0, -a, 0), scale=(0.2, 0.18, 0.16))
        P("cylinder", parent, "#ffffff", loc=(0, -0.1, 0), rot=(math.pi / 2, 0, 0), scale=(0.24, 0.24, 0.05), flat=True)
    elif name == "tree":
        P("cylinder", parent, "#7a4f2a", loc=(0, 0, -0.3), scale=(0.16, 0.16, 0.4))
        P("cone", parent, color, loc=(0, 0, 0.05), scale=(0.8, 0.8, 0.7))
        P("cone", parent, color, loc=(0, 0, 0.32), scale=(0.6, 0.6, 0.55))
    elif name == "house":
        P("cube", parent, light, loc=(0, 0, -0.16), scale=(0.8, 0.5, 0.5))
        prism(parent, [(-0.5, 0.09), (0, 0.5), (0.5, 0.09)], 0.6, color)
        P("cube", parent, dark, loc=(0, -0.26, -0.28), scale=(0.16, 0.02, 0.28))
    elif name == "sun":
        P("sphere", parent, color, scale=(0.55, 0.55, 0.55))
        for i in range(12):
            a = i * math.pi / 6
            P("cube", parent, color, loc=(0.42 * math.cos(a), 0, 0.42 * math.sin(a)), rot=(0, -a, 0), scale=(0.16, 0.05, 0.05))
    elif name == "cloud":
        for x, z, s in ((-0.25, -0.05, 0.4), (0.05, 0.08, 0.55), (0.3, -0.06, 0.38)):
            P("sphere", parent, "#f4f7fb", loc=(x, 0, z), scale=(s, s * 0.7, s))
    else:  # unknown -> coloured badge with the icon's first letter
        P("sphere", parent, color, scale=(0.85, 0.5, 0.85))
        text_part(parent, (name or "?")[:1].upper(), "#ffffff", height=0.6, extrude=0.0, loc=(0, -0.28, 0))




# ----------------------------------------------------------------------------- objects
def add_object(spec):
    """Build one object from its spec dict. Returns the root empty."""
    typ = str(spec.get("type", "cube")).lower()
    color = spec.get("color") or ("#111111" if typ == "stickman" else "#ffffff")
    pos_n = spec.get("pos", [0, 0])
    x = float(pos_n[0]) * W() / 2
    z = float(pos_n[1]) * H / 2
    depth = float(pos_n[2]) * 3 if len(pos_n) > 2 else 0.0
    raw_size = spec.get("size", 0.3)
    size = max(0.02, min(2.0, float(raw_size))) if not isinstance(raw_size, (list, tuple)) else 1.0
    unit = size * H
    delay = max(0.0, float(spec.get("delay", 0.0)))
    root = empty(spec.get("id") or typ, None, (x, depth, z))
    node = empty("loop", root)
    threed = STATE["style"] == "3d"

    if typ == "text":
        max_w = W() * 0.9
        wrap = 26 if STATE["aspect"] > 1 else 13
        # root is scaled by `unit` later, so build the text at unit height and shrink the width budget accordingly
        text_part(node, spec.get("text", ""), color, height=1.0, max_width=max_w / unit, wrap=wrap)
    elif typ == "stickman":
        joints = build_stickman(node, color, spec.get("face", True))
        animate_stickman(joints, spec.get("action", "idle") if spec.get("action") in ACTIONS else "idle", delay)
    elif typ == "icon":
        build_icon(node, str(spec.get("icon", "star")).lower(), color)
    elif typ == "rect":
        sz = spec.get("size", [0.5, 0.1])
        w, h = (sz if isinstance(sz, (list, tuple)) and len(sz) == 2 else (0.5, 0.1))
        part("cube", node, color, scale=(float(w) * W(), 0.12 if threed else 0.02, float(h) * H))
        unit = 1.0
        size = 1.0
    elif typ in SHAPES or typ == "ground":
        if typ == "ground":
            part("cube", node, color, scale=(W() * 3, 40, 0.2), loc=(0, 0, -0.1))
            unit = 1.0
            size = 1.0
        else:
            part(typ, node, color, scale=(1, 1, 1))
    else:
        build_icon(node, typ, color)

    if typ not in ("rect", "ground"):
        node.scale = (1, 1, 1)
    base = unit if typ not in ("rect", "ground") else 1.0
    if typ not in ("rect", "ground"):
        apply_entry(root, spec.get("enter", "pop_in"), delay, base, (x, depth, z))
    else:
        apply_entry(root, spec.get("enter", "pop_in"), delay, 1.0, (x, depth, z))
    apply_move(root, spec.get("move_to"), delay, float(spec.get("move_time", 2.0)), base, (x, depth, z))
    apply_loop(node, spec.get("loop", "none"), delay, unit)
    return root


# ----------------------------------------------------------------------------- scene
def add_camera(style, move):
    d = 14.0
    rig = empty("cam_rig", None, (0, 0, 0))
    cd = bpy.data.cameras.new("cam")
    cam = _link(bpy.data.objects.new("cam", cd))
    cam.parent = rig
    cam.location = (0, -d, 0)
    cam.rotation_euler = (math.pi / 2, 0, 0)
    bpy.context.scene.camera = cam
    if style == "3d":
        cd.type = "PERSP"
        cd.sensor_fit = "VERTICAL"
        cd.angle = math.radians(38)
        dist = (H / 2) / math.tan(cd.angle / 2) * 1.05
        cam.location = (0, -dist, 0)
        rig.rotation_euler = (-math.radians(9), 0, math.radians(-10))
    else:
        cd.type = "ORTHO"
        cd.ortho_scale = H if STATE["aspect"] <= 1 else H * STATE["aspect"]
        if STATE["aspect"] <= 1:
            cd.ortho_scale = H
    f1, f2 = 1, STATE["frames"]
    if move == "orbit" and style == "3d":
        key(rig, f1, rot=(-math.radians(9), 0, math.radians(-16)), interp="LINEAR")
        key(rig, f2, rot=(-math.radians(9), 0, math.radians(16)), interp="LINEAR")
    elif style == "3d":
        key(rig, f1, rot=(-math.radians(9), 0, math.radians(-10)), interp="LINEAR")
        key(rig, f2, rot=(-math.radians(9), 0, math.radians(10)), interp="LINEAR")
    if move in ("push_in", "pull_out"):
        a, b = (1.0, 0.93) if move == "push_in" else (0.93, 1.0)
        if style == "3d":
            base = cam.location.y
            key(cam, f1, loc=(0, base * a, 0), interp="LINEAR")
            key(cam, f2, loc=(0, base * b, 0), interp="LINEAR")
        else:
            cd.ortho_scale = cd.ortho_scale
            base = cd.ortho_scale
            cd.ortho_scale = base * a
            cd.keyframe_insert("ortho_scale", frame=f1)
            cd.ortho_scale = base * b
            cd.keyframe_insert("ortho_scale", frame=f2)
    elif move in ("pan_left", "pan_right"):
        sgn = -1 if move == "pan_left" else 1
        if style != "3d":
            key(rig, f1, loc=(-sgn * W() * 0.035, 0, 0), interp="LINEAR")
            key(rig, f2, loc=(sgn * W() * 0.035, 0, 0), interp="LINEAR")
    return cam


def setup_scene(width, height, fps, duration, style, bg, engine="auto"):
    """Fresh empty scene with resolution, timing, background and render engine configured."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    STATE.update(fps=fps, frames=max(2, int(math.ceil(duration * fps)) + 1), aspect=width / height, style=style,
                 flat=(style != "3d"))
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = width, height, 100
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = 1, STATE["frames"]
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    bgn = world.node_tree.nodes.get("Background")
    if bgn:
        bgn.inputs["Color"].default_value = rgba(bg)
        bgn.inputs["Strength"].default_value = 1.0
    world.color = rgba(bg)[:3]
    sc.world = world
    chosen = pick_engine(sc, engine)
    if style == "3d":
        sun = _link(bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")))
        sun.data.energy = 3.0
        sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(30))
    return chosen


def pick_engine(sc, engine):
    order = {
        # flat-colour 2D styles look identical in Workbench and render ~10x faster on this class of laptop
        "auto": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"] if STATE["style"] == "3d" else ["BLENDER_WORKBENCH"],
        "eevee": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"],
        "workbench": ["BLENDER_WORKBENCH"],
        "cycles": ["CYCLES"],
    }.get(engine, ["BLENDER_WORKBENCH"])
    for name in order:
        try:
            sc.render.engine = name
            break
        except TypeError:
            continue
    if sc.render.engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        for attr in ("taa_render_samples",):
            try:
                setattr(sc.eevee, attr, 16)
            except Exception:
                pass
    if sc.render.engine == "BLENDER_WORKBENCH":
        sh = sc.display.shading
        sh.light = "FLAT" if STATE["flat"] else "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_object_outline = False
        sc.display.render_aa = "8"
    elif sc.render.engine == "CYCLES":
        sc.cycles.samples = 24
        sc.cycles.device = "CPU"
    return sc.render.engine


def build_shot(shot, width, height, fps, duration, engine="auto"):
    style = shot.get("style", "kinetic")
    style = style if style in ("3d", "stickman", "kinetic") else "kinetic"
    bg = shot.get("bg") or ("#f4f1ea" if style == "stickman" else "#101826" if style == "kinetic" else "#dfe9f5")
    chosen = setup_scene(width, height, fps, duration, style, bg, engine)
    add_camera(style, shot.get("camera", "static"))
    roots = []
    for spec in (shot.get("objects") or [])[:24]:
        try:
            roots.append(add_object(spec))
        except Exception as exc:  # one bad object must not kill the shot
            print("[scene_lib] skipped object", spec.get("type"), "->", repr(exc))
    return chosen, roots
