"""Runs INSIDE Blender's GUI: performs the tutorial's steps live (Grease Pencil effects, compositor chain, output settings) on a timeline
that mirrors the reference narration, so a screen recording of it is a real 'how to' video made by the agent.

Launched by record_gui.py:  blender --python tutorial_gui.py -- <speed> <log>
Every step is wrapped in try/except: a failing step is logged and the tour continues.
"""
import json
import math
import sys
import time
import traceback

import bpy

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SPEED = float(ARGS[0]) if ARGS else 1.0
LOG = ARGS[1] if len(ARGS) > 1 else "tutorial_gui.log"
T_START = None
STEPS = []       # (t_seconds, name, fn)
TWEENS = []      # (t0, t1, setter, v0, v1)


def log(msg):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(f"{time.time():.3f} {msg}\n")


def at(t):
    def deco(fn):
        STEPS.append((t, fn.__name__, fn))
        return fn
    return deco


def tween(t0, t1, setter, v0, v1):
    TWEENS.append((t0, t1, setter, v0, v1))


def lerp(a, b, u):
    if isinstance(a, (tuple, list)):
        return tuple(a[i] + (b[i] - a[i]) * u for i in range(len(a)))
    return a + (b - a) * u


def area(kind):
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == kind:
                return w, a
    return None, None


def props_tab(tab):
    w, a = area("PROPERTIES")
    if a:
        a.spaces.active.context = tab
        a.tag_redraw()


def ctx_override(kind):
    w, a = area(kind)
    if not a:
        return None
    r = next((r for r in a.regions if r.type == "WINDOW"), None)
    return dict(window=w, area=a, region=r)


def redraw():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            a.tag_redraw()


# ----------------------------------------------------------------------------- scene
def setup_scene():
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.object.grease_pencil_add(type="MONKEY", location=(0, 0, 0))
    gp = bpy.context.active_object
    gp.name = "Drawing"
    for m in gp.data.materials:            # bright, saturated strokes on a dark plate so glow / rim light are clearly visible
        try:
            gm = m.grease_pencil
            gm.color = (1.0, 0.86, 0.45, 1.0)
            gm.show_fill = True
            gm.fill_color = (0.95, 0.42, 0.18, 1.0)
        except Exception:
            pass
    bpy.ops.object.camera_add(location=(0, -8, 0), rotation=(math.pi / 2, 0, 0))
    sc.camera = bpy.context.active_object
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = gp
    gp.select_set(True)
    try:
        bpy.context.preferences.view.ui_scale = 1.25
    except Exception:
        pass
    sc.camera.data.type = "ORTHO"
    sc.camera.data.ortho_scale = 4.2
    w = bpy.data.worlds.new("bg")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.02, 0.05, 0.08, 1)
    sc.world = w
    for name, attr in (("render.engine", "BLENDER_EEVEE_NEXT"),):
        try:
            sc.render.engine = attr
        except Exception:
            pass
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.frame_start, sc.frame_end = 1, 48
    # viewport: camera view + rendered preview so effects are visible live
    w_, a = area("VIEW_3D")
    if a:
        sp = a.spaces.active
        sp.shading.type = "RENDERED"
        sp.region_3d.view_perspective = "CAMERA"
        sp.overlay.show_overlays = False
        sp.show_gizmo = False
    gp["is_gp"] = True
    return gp


# ----------------------------------------------------------------------------- the tour (times in seconds since the tour started ~ 0:41 of the video)
GP = None


@at(0.5)
def intro():
    global GP
    GP = setup_scene()
    props_tab("OBJECT")


@at(18.0)         # 0:59  "click on the effects tab (magic wand)"
def open_effects_tab():
    props_tab("SHADERFX")


@at(27.0)         # 1:08  add glow
def add_glow():
    fx = GP.shader_effects.new("Glow", "FX_GLOW")
    fx.mode = "LUMINANCE"
    fx.threshold, fx.opacity, fx.size = 1.0, 0.0, (0, 0)
    fx.samples = 8
    tween(28, 52, lambda v: setattr(GP.shader_effects["Glow"], "threshold", v), 1.0, 0.32)
    tween(30, 58, lambda v: setattr(GP.shader_effects["Glow"], "opacity", v), 0.0, 0.55)
    tween(34, 62, lambda v: setattr(GP.shader_effects["Glow"], "size", (v, v)), 0.0, 28.0)


@at(74.0)         # 1:55  rim light
def add_rim():
    fx = GP.shader_effects.new("Rim", "FX_RIM")
    fx.mode = "ADD"
    fx.rim_color = (1.0, 0.78, 0.35)
    tween(75, 90, lambda v: setattr(GP.shader_effects["Rim"], "offset", (int(v), int(-v * 0.6))), 0, 14)
    tween(80, 96, lambda v: setattr(GP.shader_effects["Rim"], "blur", (int(v), int(v))), 0, 10)


@at(108.0)        # 2:29  gentle blur
def add_blur():
    fx = GP.shader_effects.new("Blur", "FX_BLUR")
    tween(109, 124, lambda v: setattr(GP.shader_effects["Blur"], "size", (v, v)), 0.0, 3.0)


@at(124.0)        # 2:45  colorize
def add_colorize():
    fx = GP.shader_effects.new("Colorize", "FX_COLORIZE")
    fx.mode = "CUSTOM"
    fx.low_color = (0.1, 0.3, 0.16, 1)
    tween(125, 140, lambda v: setattr(GP.shader_effects["Colorize"], "factor", v), 0.0, 0.3)


@at(146.0)        # 3:07  toggle effects on/off to show the difference
def toggles():
    for name in ("Colorize", "Blur", "Rim", "Glow"):
        pass


def toggle_all(on):
    for fx in GP.shader_effects:
        fx.show_viewport = on


@at(150.0)
def fx_off():
    toggle_all(False)


@at(155.0)
def fx_on():
    toggle_all(True)


@at(168.0)        # 3:29  compositor tab
def go_compositing():
    bpy.context.window.workspace = bpy.data.workspaces["Compositing"]
    sc = bpy.context.scene
    sc.use_nodes = True
    w, a = area("NODE_EDITOR")
    if a:
        a.spaces.active.show_backdrop = True


def N(kind, name, loc):
    nt = bpy.context.scene.node_tree
    n = nt.nodes.new(kind)
    n.name = n.label = name
    n.location = loc
    return n


def nt():
    return bpy.context.scene.node_tree


def fit_nodes():
    ov = ctx_override("NODE_EDITOR")
    if ov and ov["region"]:
        try:
            with bpy.context.temp_override(**ov):
                bpy.ops.node.view_all()
        except Exception:
            pass


@at(192.0)        # 3:53  render layers + composite already there; add Glare
def add_glare():
    tree = nt()
    rl = next(n for n in tree.nodes if n.type == "R_LAYERS")
    comp = next(n for n in tree.nodes if n.type == "COMPOSITE")
    rl.location, comp.location = (-800, 100), (700, 100)
    g = N("CompositorNodeGlare", "Glare", (300, 100))
    g.glare_type = "BLOOM"
    tree.links.new(rl.outputs["Image"], g.inputs["Image"])
    tree.links.new(g.outputs["Image"], comp.inputs["Image"])
    tween(200, 215, lambda v: setattr(nt().nodes["Glare"], "threshold", v), 1.0, 0.7)
    tween(205, 220, lambda v: setattr(nt().nodes["Glare"], "size", int(v)), 3, 8)


@at(228.0)        # 4:47  viewer + backdrop
def add_viewer():
    tree = nt()
    v = N("CompositorNodeViewer", "Viewer", (700, -150))
    tree.links.new(tree.nodes["Glare"].outputs["Image"], v.inputs["Image"])


@at(270.0)        # 5:30  blur + mix (colour bleed)
def add_blur_mix():
    tree = nt()
    rl = next(n for n in tree.nodes if n.type == "R_LAYERS")
    b = N("CompositorNodeBlur", "Blur", (-500, -80))
    b.size_x = b.size_y = 6
    m = N("CompositorNodeMixRGB", "ColorBleed", (-150, 100))
    m.blend_type = "COLOR"
    m.inputs[0].default_value = 0.25
    tree.links.new(rl.outputs["Image"], b.inputs["Image"])
    tree.links.new(rl.outputs["Image"], m.inputs[1])
    tree.links.new(b.outputs["Image"], m.inputs[2])
    g = tree.nodes["Glare"]
    tree.links.new(m.outputs["Image"], g.inputs["Image"])
    tween(272, 300, lambda v: setattr(nt().nodes["ColorBleed"].inputs[0], "default_value", v), 0.0, 0.3)


@at(320.0)        # 5:20-6:00 lens distortion
def add_lens():
    tree = nt()
    g = tree.nodes["Glare"]
    comp = next(n for n in tree.nodes if n.type == "COMPOSITE")
    ld = N("CompositorNodeLensdist", "LensDistortion", (500, 100))
    ld.use_projector = True
    tree.links.new(g.outputs["Image"], ld.inputs["Image"])
    tween(322, 345, lambda v: nt().nodes["LensDistortion"].inputs[2].__setattr__("default_value", v), 0.0, 0.03)
    tree.links.new(ld.outputs["Image"], comp.inputs["Image"])


@at(345.0)        # 6:00-6:30 film grain overlay
def add_grain():
    tree = nt()
    comp = next(n for n in tree.nodes if n.type == "COMPOSITE")
    ld = tree.nodes["LensDistortion"]
    noise = N("CompositorNodeRGB", "GrainSource", (300, -320))
    noise.outputs[0].default_value = (0.5, 0.5, 0.5, 1)
    m = N("CompositorNodeMixRGB", "GrainOverlay", (900, 100))
    m.blend_type = "OVERLAY"
    m.inputs[0].default_value = 0.0
    tree.links.new(ld.outputs["Image"], m.inputs[1])
    tree.links.new(noise.outputs[0], m.inputs[2])
    tree.links.new(m.outputs["Image"], comp.inputs["Image"])
    tween(347, 365, lambda v: setattr(nt().nodes["GrainOverlay"].inputs[0], "default_value", v), 0.0, 0.15)


@at(375.0)        # 6:30-7:00 sharpen
def add_sharpen():
    tree = nt()
    comp = next(n for n in tree.nodes if n.type == "COMPOSITE")
    m = tree.nodes["GrainOverlay"]
    f = N("CompositorNodeFilter", "Sharpen", (1100, 100))
    f.filter_type = "SHARPEN_DIAMOND" if hasattr(f, "filter_type") else "SHARPEN"
    f.inputs[0].default_value = 0.0
    tree.links.new(m.outputs["Image"], f.inputs["Image"])
    tree.links.new(f.outputs["Image"], comp.inputs["Image"])
    tween(377, 392, lambda v: setattr(nt().nodes["Sharpen"].inputs[0], "default_value", v), 0.0, 0.12)


@at(405.0)        # 7:00 defocus with Z pass
def add_defocus():
    bpy.context.view_layer.use_pass_z = True
    tree = nt()
    rl = next(n for n in tree.nodes if n.type == "R_LAYERS")
    f = tree.nodes["Sharpen"]
    comp = next(n for n in tree.nodes if n.type == "COMPOSITE")
    d = N("CompositorNodeDefocus", "Defocus", (1300, 100))
    d.use_zbuffer = True
    tree.links.new(f.outputs["Image"], d.inputs["Image"])
    tree.links.new(rl.outputs["Depth"] if "Depth" in rl.outputs else rl.outputs[-1], d.inputs["Z"])
    tree.links.new(d.outputs["Image"], comp.inputs["Image"])
    d.f_stop = 128.0
    d.keyframe_insert("f_stop", frame=1)
    d.f_stop = 3.0
    d.keyframe_insert("f_stop", frame=48)


@at(440.0)        # 7:21 back to the layout, output properties
def go_layout():
    bpy.context.window.workspace = bpy.data.workspaces["Layout"]
    props_tab("OUTPUT")


@at(452.0)
def out_resolution():
    sc = bpy.context.scene
    tween(452, 462, lambda v: setattr(sc.render, "resolution_percentage", int(v)), 100, 50)
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080


@at(468.0)
def out_format():
    r = bpy.context.scene.render
    r.image_settings.file_format = "FFMPEG"
    r.ffmpeg.format = "MPEG4"
    r.ffmpeg.codec = "H264"
    r.ffmpeg.constant_rate_factor = "HIGH"


@at(490.0)
def out_frames():
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, 96
    tween(490, 498, lambda v: setattr(bpy.context.scene, "frame_current", int(v)), 1, 40)


@at(505.0)        # 8:30  small test render at 50%
def test_render():
    bpy.context.scene.render.resolution_percentage = 25
    bpy.context.scene.frame_set(24)
    try:
        bpy.ops.render.render("INVOKE_DEFAULT")
    except Exception:
        log("render invoke failed: " + traceback.format_exc()[-200:])


@at(520.0)
def finish():
    log("TOUR DONE")
    open(LOG + ".done", "w").write("done")


def tick():
    global T_START
    if T_START is None:
        T_START = time.time()
        log("TOUR START")
    t = (time.time() - T_START) * SPEED
    for st in list(STEPS):
        if st[0] <= t:
            STEPS.remove(st)
            try:
                st[2]()
                if st[1].startswith("add_") and bpy.context.window.workspace.name == "Compositing":
                    fit_nodes()
                log(f"step {st[1]} @ {t:.1f}s")
            except Exception:
                log(f"step {st[1]} FAILED: {traceback.format_exc()[-400:]}")
    for tw in TWEENS:
        t0, t1, setter, v0, v1 = tw
        if t0 <= t <= t1 + 0.5:
            try:
                setter(lerp(v0, v1, min(1.0, (t - t0) / max(0.01, t1 - t0))))
            except Exception:
                pass
    redraw()
    if not STEPS and t > 540 / max(SPEED, 1e-6) * SPEED:
        return None
    return 0.05


def start():
    try:
        w, _ = area("VIEW_3D")
        bpy.ops.wm.window_fullscreen_toggle()
    except Exception:
        pass
    bpy.app.timers.register(tick, first_interval=2.0)
    return None


bpy.app.timers.register(start, first_interval=1.5)
