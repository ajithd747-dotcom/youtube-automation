"""Cinematic 3D mode (runs INSIDE Blender). Real lighting + physics instead of flat 2D layouts:

  * PBR materials (metal, glass, emissive), sky/sunset/night/studio/neon moods, sun + area lights with soft shadows
  * EEVEE Next: ray-traced reflections/refraction, fast GI + AO, motion blur, depth of field, volumetric fog
  * compositor: bloom glare + vignette
  * physics: rigid bodies (dominoes, crates, ball pits), cloth (flag/banner + wind), soft body (jelly), particles (fireworks, dust)
  * a 3D robot character with walk/wave/jump/celebrate cycles, glowing text titles, camera rigs with focus pulls

World is metric: Z up, floor at z=0, camera looks toward +Y. `recipes` build a whole scene for one shot.
"""
import math
import random

import bpy

import scene_lib as L
from scene_lib import STATE, end_t, frame, key

QUALITY = {  # samples, raytracing, motion blur, volumetrics tile, shadow rays
    "draft": dict(samples=6, rt=False, mblur=False, vol_tile="8", rays=1, shadow_res=0.5),
    "standard": dict(samples=14, rt=True, mblur=True, vol_tile="4", rays=1, shadow_res=1.0),
    "final": dict(samples=24, rt=True, mblur=True, vol_tile="2", rays=2, shadow_res=1.0),
}
CFG = {"quality": "standard", "mood": "day"}


# ----------------------------------------------------------------------------- materials / meshes
def pbr(color, metallic=0.0, rough=0.5, emit=0.0, emit_color=None, transmission=0.0, ior=1.45, coat=0.0, name="pbr"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    col = L.rgba(color)
    m.diffuse_color = col
    b.inputs["Base Color"].default_value = col
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = ior
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = L.rgba(emit_color or color)
        b.inputs["Emission Strength"].default_value = emit
    return m


def mesh(kind, mat, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), parent=None, bevel=0.0, smooth=True, name=None, shadow=True):
    o = L.part(kind, parent, "#ffffff", loc=loc, scale=scale, rot=rot, flat=False, smooth=smooth and kind not in ("cube", "plane"))
    o.data.materials.clear()
    o.data.materials.append(mat)
    if name:
        o.name = name
    if bevel:
        bm = o.modifiers.new("Bevel", "BEVEL")
        bm.width, bm.segments, bm.limit_method = bevel, 3, "ANGLE"
        if smooth:
            o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    if not shadow:
        o.visible_shadow = False
    return o


def floor(color="#2b2f3a", rough=0.18, metallic=0.0, size=120, z=0.0):
    return mesh("plane", pbr(color, metallic, rough, name="floor"), loc=(0, 0, z), scale=(size, size, 1), name="floor")


def light(kind, loc, energy, color="#ffffff", size=2.0, target=None, angle=None, spot=None):
    ld = bpy.data.lights.new("light", kind)
    ld.energy = energy
    ld.color = L.rgba(color)[:3]
    if kind == "AREA":
        ld.size = size
    elif kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = size
    elif kind == "SUN" and angle is not None:
        ld.angle = angle
    if kind == "SPOT" and spot:
        ld.spot_size = spot
    o = L._link(bpy.data.objects.new("light", ld))
    o.location = loc
    if target is not None and kind != "POINT":
        c = o.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    return o


def look_at_empty(loc):
    return L.empty("focus", None, loc)


# ----------------------------------------------------------------------------- scene setup / look
def setup(width, height, fps, duration, mood="day", quality="standard", fog=0.0, bloom=True, vignette=False):
    # vignette=False: ffmpeg adds it in the final mux; the compositor blur costs ~3 s/frame here
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    STATE.update(fps=fps, frames=max(2, int(math.ceil(duration * fps)) + 1), aspect=width / height, style="cinematic", flat=False)
    CFG.update(quality=quality, mood=mood)
    q = QUALITY.get(quality, QUALITY["standard"])
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = width, height, 100
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = 1, STATE["frames"]
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = name
            break
        except TypeError:
            continue
    ev = sc.eevee
    ev.taa_render_samples = q["samples"]
    ev.use_shadows = True
    ev.use_raytracing = q["rt"]
    if q["rt"]:
        try:
            ev.ray_tracing_options.resolution_scale = "2"
            ev.ray_tracing_options.trace_max_roughness = 0.5
        except Exception:
            pass
    for attr, val in (("use_fast_gi", True), ("use_gtao", True), ("gtao_distance", 1.5), ("volumetric_tile_size", q["vol_tile"]),
                      ("volumetric_samples", 48), ("shadow_ray_count", q["rays"]), ("shadow_step_count", 8),
                      ("shadow_resolution_scale", q["shadow_res"]), ("motion_blur_steps", 4)):
        try:
            setattr(ev, attr, val)
        except Exception:
            pass
    for attr, val in (("clamp_surface_direct", 30.0), ("clamp_surface_indirect", 8.0)):
        try:
            setattr(ev, attr, val)
        except Exception:
            pass
    sc.render.use_motion_blur = q["mblur"]
    try:
        sc.render.motion_blur_shutter = 0.45
    except Exception:
        pass
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.view_settings.exposure = {"sunset": -1.5, "day": -0.5, "night": 0.4, "studio": 0.0, "neon": 0.3}.get(mood, 0.0)
    _world(sc, mood, fog)
    _lights(mood)
    _compositor(sc, bloom, vignette)
    if fog > 0:
        add_fog(0.01 * fog)
    return sc


def _world(sc, mood, fog):
    w = bpy.data.worlds.new("world")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    if mood in ("day", "sunset"):
        sky = nt.nodes.new("ShaderNodeTexSky")
        try:
            sky.sky_type = "MULTIPLE_SCATTERING"
        except Exception:
            pass
        sky.sun_elevation = math.radians(38 if mood == "day" else 7)
        sky.sun_rotation = math.radians(150 if mood == 'day' else 28)  # sunset: sun behind the subjects (rim light, long shadows)
        sky.altitude = 0
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 1.0
        CFG["sun_el"], CFG["sun_rot"] = sky.sun_elevation, sky.sun_rotation
    elif mood in ("studio", "neon"):
        _stripe_world(nt, bg, mood)
    else:
        col = {"night": "#060b1c"}.get(mood, "#0a0c12")
        bg.inputs["Color"].default_value = L.rgba(col)
        bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    CFG['fog'] = fog
    sc.world = w


def _stripe_world(nt, bg, mood):
    """World shader with bright softbox stripes: gives chrome/glass/gold something to reflect (a black world = black metal)."""
    coord = nt.nodes.new("ShaderNodeTexCoord")
    maps = []
    cols = [("#ffffff", 5.0, 3.0), ("#cfe0ff", 3.0, 5.0)] if mood == "studio" else [("#ff2fb3", 4.0, 3.0), ("#22d3ff", 3.0, 5.5)]
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs[0].default_value = L.rgba("#0c0e14" if mood == "studio" else "#07040f")
    prev = base.outputs[0]
    for color, scale, gain in cols:
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type, w.bands_direction = "BANDS", "X" if color in ("#ffffff", "#ff2fb3") else "Y"
        w.inputs["Scale"].default_value = scale
        w.inputs["Distortion"].default_value = 0.0
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "LINEAR"
        ramp.color_ramp.elements[0].position = 0.86
        ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
        ramp.color_ramp.elements[1].position = 0.95
        c = L.rgba(color)
        ramp.color_ramp.elements[1].color = (c[0] * gain, c[1] * gain, c[2] * gain, 1)
        nt.links.new(coord.outputs["Generated"], w.inputs["Vector"])
        nt.links.new(w.outputs["Fac"], ramp.inputs["Fac"])
        add = nt.nodes.new("ShaderNodeMixRGB")
        add.blend_type, add.inputs[0].default_value = "ADD", 1.0
        nt.links.new(prev, add.inputs[1])
        nt.links.new(ramp.outputs["Color"], add.inputs[2])
        prev = add.outputs["Color"]
    nt.links.new(prev, bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0


def add_fog(density=0.012, center=(0, 8, 6), size=(46, 46, 12)):
    """Atmospheric haze as a bounded volume box (a world volume renders black in EEVEE Next on this GPU).
    Lights + shadows through it give visible light shafts."""
    m = bpy.data.materials.new("fog")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = density
    v.inputs["Anisotropy"].default_value = 0.3
    nt.links.new(v.outputs["Volume"], out.inputs["Volume"])
    box = mesh("cube", m, loc=center, scale=size, name="fogbox", shadow=False)
    box.display_type = "WIRE"
    try:
        bpy.context.scene.eevee.volumetric_end = 70
    except Exception:
        pass
    return box


def panel(loc, size, color, strength, target=(0, 0, 1)):
    """Emissive softbox that only shows up in reflections/refractions (hidden from the camera itself)."""
    m = pbr(color, 0, 1.0, emit=strength, emit_color=color, name="panel")
    o = mesh("plane", m, loc=loc, scale=(size[0], size[1], 1), shadow=False, name="panel")
    o.visible_camera = False
    c = o.constraints.new("TRACK_TO")
    tgt = L.empty("panel_t", None, target)
    c.target, c.track_axis, c.up_axis = tgt, "TRACK_Z", "UP_Y"
    return o


def _lights(mood):
    tgt = look_at_empty((0, 0, 0.5))
    CFG["light_target"] = tgt
    if mood in ("day", "sunset"):
        el, rot = CFG["sun_el"], CFG["sun_rot"]
        d = (math.cos(el) * math.sin(rot), math.cos(el) * math.cos(rot), math.sin(el))
        s = light("SUN", (d[0] * 20, d[1] * 20, d[2] * 20), 3.5 if mood == "day" else 2.2, "#fff2dd" if mood == "day" else "#ff9a55", target=tgt, angle=math.radians(1.2))
        if mood == "sunset":  # soft warm fill from the camera side so backlit subjects keep detail
            light("AREA", (-4, -9, 4), 500, "#ffd2a8", 6, tgt)
    elif mood == "night":
        light("SUN", (8, -6, 12), 0.6, "#6f8cff", target=tgt, angle=math.radians(2))
    elif mood == "studio":
        light("AREA", (-6, -8, 7), 900, "#ffffff", 5, tgt)
        light("AREA", (7, -5, 4), 350, "#bcd4ff", 4, tgt)
        light("AREA", (0, 8, 6), 600, "#ffd9b0", 4, tgt)
        panel((-8, -4, 4), (2.5, 7), "#ffffff", 6)
        panel((8, -4, 4), (2.5, 7), "#cfe0ff", 5)
        panel((0, -2, 10), (10, 3), "#ffffff", 4)
    elif mood == "neon":
        light("AREA", (-6, -6, 5), 500, "#ff2fb3", 4, tgt)
        light("AREA", (7, -4, 4), 500, "#22d3ff", 4, tgt)
        light("AREA", (0, 8, 5), 300, "#7b5cff", 5, tgt)
        panel((-8, -4, 3), (2.0, 7), "#ff2fb3", 7)
        panel((8, -4, 3), (2.0, 7), "#22d3ff", 7)
        panel((0, 8, 5), (10, 2), "#7b5cff", 4)


def _compositor(sc, bloom, vignette):
    sc.use_nodes = True
    nt = sc.node_tree
    nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers")
    comp = nt.nodes.new("CompositorNodeComposite")
    last = rl.outputs["Image"]
    if bloom:
        gl = nt.nodes.new("CompositorNodeGlare")
        try:
            gl.glare_type = "BLOOM"
        except Exception:
            gl.glare_type = "FOG_GLOW"
        for attr, val in (("threshold", 1.6), ("size", 7), ("quality", "MEDIUM")):
            try:
                setattr(gl, attr, val)
            except Exception:
                pass
        try:
            gl.inputs["Strength"].default_value = 0.7
        except Exception:
            pass
        nt.links.new(last, gl.inputs["Image"])
        last = gl.outputs["Image"]
    if vignette:
        em = nt.nodes.new("CompositorNodeEllipseMask")
        em.width, em.height = 0.92, 0.88
        bl = nt.nodes.new("CompositorNodeBlur")
        bl.size_x = bl.size_y = 260
        try:
            bl.filter_type = "GAUSS"
        except Exception:
            pass
        mix = nt.nodes.new("CompositorNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 0.55
        nt.links.new(em.outputs["Mask"], bl.inputs["Image"])
        # multiply image by a mask that is 1 in the middle, ~0.45 at the corners
        base = nt.nodes.new("CompositorNodeMixRGB")
        base.blend_type = "MIX"
        base.inputs[1].default_value = (0.45, 0.45, 0.45, 1)
        base.inputs[2].default_value = (1, 1, 1, 1)
        nt.links.new(bl.outputs["Image"], base.inputs[0])
        nt.links.new(last, mix.inputs[1])
        nt.links.new(base.outputs["Image"], mix.inputs[2])
        mix.inputs[0].default_value = 1.0
        last = mix.outputs["Image"]
    nt.links.new(last, comp.inputs["Image"])


# ----------------------------------------------------------------------------- camera
def camera(start, end, target_start=(0, 0, 1), target_end=None, lens=35, fstop=2.8, focus_target=True, shake=0.0):
    """Keyframed camera: position start->end, aimed at a (moving) target; focus locked on the target (depth of field)."""
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.sensor_fit = "HORIZONTAL"
    cam = L._link(bpy.data.objects.new("cam", cd))
    bpy.context.scene.camera = cam
    tgt = L.empty("cam_target", None, target_start)
    c = cam.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    f1, f2 = 1, STATE["frames"]
    key(cam, f1, loc=start, interp="BEZIER")
    key(cam, f2, loc=end, interp="BEZIER")
    key(tgt, f1, loc=target_start, interp="BEZIER")
    key(tgt, f2, loc=target_end or target_start, interp="BEZIER")
    if fstop:
        cd.dof.use_dof = True
        cd.dof.focus_object = tgt if focus_target else None
        cd.dof.aperture_fstop = fstop
    if shake:
        rnd = random.Random(3)
        for f in range(f1, f2, 3):
            t = (f - 1) / STATE["fps"]
            p = [start[i] + (end[i] - start[i]) * (f - 1) / max(1, f2 - 1) for i in range(3)]
            key(cam, f, loc=(p[0] + rnd.uniform(-1, 1) * shake, p[1] + rnd.uniform(-1, 1) * shake, p[2] + rnd.uniform(-1, 1) * shake * 0.6), interp="BEZIER")
    return cam, tgt


# ----------------------------------------------------------------------------- text
def title_3d(text, loc=(0, 0, 2.2), color="#ffffff", glow="#ffb347", size=0.9, delay=0.0, width=9.0):
    """Extruded, beveled 3D text that pops in and glows."""
    root = L.empty("title", None, loc)
    cu = bpy.data.curves.new("t3d", "FONT")
    cu.body = L.clean_text(text)
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.extrude, cu.bevel_depth, cu.bevel_resolution = 0.08, 0.015, 3
    f = L._font()
    if f:
        cu.font = cu.font_bold = f
    o = L._link(bpy.data.objects.new("t3d", cu))
    o.parent = root
    o.rotation_euler = (math.pi / 2, 0, 0)
    if CFG.get("mood") in ("day", "sunset"):  # bright sky: dark solid letters with a hint of warm glow read best
        o.data.materials.append(pbr("#1a2140", 0.2, 0.3, emit=0.5, emit_color=glow))
    else:
        o.data.materials.append(pbr(color, 0.1, 0.25, emit=1.6, emit_color=glow))
    o.scale = (size, size, size)
    bpy.context.view_layer.update()
    if o.dimensions.x > width:
        k = width / o.dimensions.x
        o.scale = (size * k, size * k, size * k)
    f0 = frame(delay)
    key(root, 1, scale=(0.001,) * 3, interp="CONSTANT")
    key(root, max(1, f0 - 1), scale=(0.001,) * 3, interp="CONSTANT")
    key(root, f0 + 8, scale=(1.12,) * 3, interp="BEZIER")
    key(root, f0 + 14, scale=(1, 1, 1), interp="BEZIER")
    return root


# ----------------------------------------------------------------------------- physics helpers
def rigid(o, kind="ACTIVE", mass=1.0, shape="BOX", friction=0.6, bounce=0.1, margin=None):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.rigidbody.object_add(type=kind)
    rb = o.rigid_body
    rb.mass, rb.friction, rb.restitution, rb.collision_shape = mass, friction, bounce, shape
    if margin is not None:
        rb.use_margin, rb.collision_margin = True, margin
    return rb


def rigid_world(substeps=12, iterations=24, end_frame=None):
    sc = bpy.context.scene
    if sc.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    w = sc.rigidbody_world
    w.substeps_per_frame, w.solver_iterations = substeps, iterations
    w.point_cache.frame_start, w.point_cache.frame_end = 1, end_frame or STATE["frames"]
    return w


def release_at(o, t):
    """Kinematic (keyframe-driven) until time t, then free physics: hand-authored launches keep their velocity."""
    f = frame(t)
    o.rigid_body.kinematic = True
    o.keyframe_insert("rigid_body.kinematic", frame=1)
    o.keyframe_insert("rigid_body.kinematic", frame=max(1, f - 1))
    o.rigid_body.kinematic = False
    o.keyframe_insert("rigid_body.kinematic", frame=f)


# ----------------------------------------------------------------------------- robot character
def build_robot(loc=(0, 0, 0), color="#e8edf5", accent="#22d3ff", scale=1.0):
    """Stylised 3D robot; joints are empties (same rig layout as the stickman) so scene_lib poses drive it."""
    root = L.empty("robot", None, loc)
    body = pbr(color, 0.35, 0.28, coat=0.4, name="robot_body")
    dark = pbr("#1b2130", 0.6, 0.35, name="robot_dark")
    glow = pbr(accent, 0, 0.3, emit=6.0, name="robot_glow")
    s = 1.8 * scale  # robot is ~1.8 m tall
    j = {}
    j["pelvis"] = L.empty("pelvis", root, (0, 0, 0.95 * s))
    j["torso"] = L.empty("torso", j["pelvis"])
    mesh("cube", body, loc=(0, 0, 0.26 * s), scale=(0.36 * s, 0.22 * s, 0.5 * s), parent=j["torso"], bevel=0.05 * s)
    mesh("cube", glow, loc=(0, -0.115 * s, 0.30 * s), scale=(0.14 * s, 0.01 * s, 0.14 * s), parent=j["torso"])
    j["neck"] = L.empty("neck", j["torso"], (0, 0, 0.56 * s))
    j["head"] = L.empty("head", j["neck"], (0, 0, 0.11 * s))
    mesh("sphere", body, scale=(0.3 * s, 0.28 * s, 0.26 * s), parent=j["head"])
    mesh("cube", dark, loc=(0, -0.11 * s, 0.01 * s), scale=(0.24 * s, 0.06 * s, 0.11 * s), parent=j["head"], bevel=0.02 * s)
    for sx in (-1, 1):
        mesh("sphere", glow, loc=(sx * 0.05 * s, -0.145 * s, 0.015 * s), scale=(0.045 * s, 0.02 * s, 0.045 * s), parent=j["head"])
    mesh("cylinder", dark, loc=(0, 0, 0.17 * s), scale=(0.02 * s, 0.02 * s, 0.09 * s), parent=j["head"])
    mesh("sphere", glow, loc=(0, 0, 0.23 * s), scale=(0.05 * s, 0.05 * s, 0.05 * s), parent=j["head"])
    for side, sx in (("l", -1), ("r", 1)):
        j[side + "_sh"] = L.empty(side + "_sh", j["torso"], (sx * 0.24 * s, 0, 0.47 * s))
        mesh("sphere", dark, scale=(0.13 * s,) * 3, parent=j[side + "_sh"])
        mesh("cylinder", body, loc=(0, 0, -0.14 * s), scale=(0.075 * s, 0.075 * s, 0.28 * s), parent=j[side + "_sh"])
        j[side + "_el"] = L.empty(side + "_el", j[side + "_sh"], (0, 0, -0.28 * s))
        mesh("sphere", dark, scale=(0.095 * s,) * 3, parent=j[side + "_el"])
        mesh("cylinder", body, loc=(0, 0, -0.13 * s), scale=(0.068 * s, 0.068 * s, 0.26 * s), parent=j[side + "_el"])
        mesh("sphere", dark, loc=(0, 0, -0.29 * s), scale=(0.11 * s,) * 3, parent=j[side + "_el"])
        j[side + "_hip"] = L.empty(side + "_hip", j["pelvis"], (sx * 0.11 * s, 0, 0))
        mesh("sphere", dark, scale=(0.12 * s,) * 3, parent=j[side + "_hip"])
        mesh("cylinder", body, loc=(0, 0, -0.2 * s), scale=(0.09 * s, 0.09 * s, 0.4 * s), parent=j[side + "_hip"])
        j[side + "_kn"] = L.empty(side + "_kn", j[side + "_hip"], (0, 0, -0.4 * s))
        mesh("sphere", dark, scale=(0.1 * s,) * 3, parent=j[side + "_kn"])
        mesh("cylinder", body, loc=(0, 0, -0.19 * s), scale=(0.08 * s, 0.08 * s, 0.38 * s), parent=j[side + "_kn"])
        mesh("cube", dark, loc=(0, -0.05 * s, -0.4 * s), scale=(0.13 * s, 0.24 * s, 0.07 * s), parent=j[side + "_kn"], bevel=0.02 * s)
    mesh("cylinder", body, loc=(0, 0, -0.03 * s), scale=(0.28 * s, 0.2 * s, 0.14 * s), parent=j["pelvis"])
    return root, j


def animate_robot(j, action, t_start=0.0, walk_from=None, walk_to=None, walk_time=3.0, plane="front"):
    """Drive the robot joints with the shared stickman pose functions; optional walk along the floor."""
    base_z = j["pelvis"].location[2]
    root = j["pelvis"].parent
    for f, t in L.sample(0.0, end_t(), None, 2):
        p = L._pose(action, max(0.0, t - t_start))
        for name in ("torso", "head", "l_sh", "l_el", "r_sh", "r_el", "l_hip", "l_kn", "r_hip", "r_kn"):
            # front: swing in the picture plane (facing the camera); side: swing forward/back (robot in profile)
            j[name].rotation_euler = (p[name], 0, 0) if plane == "side" else (0, p[name], 0)
            j[name].keyframe_insert("rotation_euler", frame=f)
        j["pelvis"].location = (0, 0, base_z + p["bob"] * 1.8)
        j["pelvis"].keyframe_insert("location", frame=f)
    if walk_from and walk_to:
        key(root, 1, loc=walk_from, interp="LINEAR")
        key(root, frame(walk_time), loc=walk_to, interp="LINEAR")
    return j
