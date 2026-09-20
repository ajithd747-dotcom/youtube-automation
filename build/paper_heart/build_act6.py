"""Act 6 of PAPER HEART — the paper storm and the heart, built and rendered at full quality.

    blender -b --factory-startup --python build/paper_heart/build_act6.py -- <out_dir> [start] [end]

This is the climax and it is entirely procedural, so it needs no sourced character art:
60 A4 sheets, a low sun behind them, and the choreography that takes them from a turbulent
updraught into a clean heart and out again.

The heart is NOT simulated. A rigid-body solver will never land 60 cards on a clean curve, so
the sheets are driven by layered noise for the chaos and by per-sheet target transforms on a
heart curve for the formation, cross-faded between the two. The cross-fade is the whole trick:
it reads as the wind *choosing* to do it.

Deliberately no image textures anywhere - this machine's Radeon driver dies on textured planes
in EEVEE (atio6axx.dll), and every surface here is a plane. Sky and paper are procedural.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

FPS = 24
RES = (1920, 1080)
N_SHEETS = 60
A4 = (0.210, 0.297)                      # metres, real A4 - scale reads in the flutter

# Act 6 shot boundaries, absolute film frames (see scripts/paper_heart/shots.json)
S50 = (4465, 4560)      # the wind takes them
S51 = (4561, 4680)      # the spiral
S52 = (4681, 4824)      # the heart: gather 4705-4740, form 4741-4752, hold, loosen 4801-4824
GATHER0, GATHER1 = 4705, 4740
FORM0, FORM1 = 4741, 4752
HOLD1 = 4800
LOOSEN1 = 4824


# ----------------------------------------------------------------- utilities

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def hexcol(h, alpha=1.0):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    # sRGB -> linear, because Blender node colours are linear
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return (f(r), f(g), f(b), alpha)


# ----------------------------------------------------------------- look

def build_world():
    """Nishita sky: real atmospheric scattering and a real sun disc, generated not sampled.

    A hand-built gradient got the orientation wrong and had no sun in it. This is still
    procedural - no environment image - so it stays clear of the textured-plane crash, and it
    gives the low sun the whole act is backlit by.
    """
    w = bpy.data.worlds.new("Dusk")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(5.4)        # low sunset; see note on the notch below
    sky.sun_rotation = math.radians(180)         # due -Y, i.e. straight behind the heart
    sky.sun_intensity = 0.22
    sky.sun_size = math.radians(2.6)
    sky.altitude = 120
    sky.air_density = 2.1                        # thicker air = warmer, hazier dusk
    sky.dust_density = 1.4
    sky.ozone_density = 2.3

    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bg.inputs["Strength"].default_value = 0.30


def paper_material():
    """Toon paper that glows when the sun is behind it.

    Three things make it read as animation cel rather than a 3D card: a hard three-step ramp
    (two steps reads cheap), a shadow that shifts hue warm instead of just going darker, and a
    backlight term so a sheet between camera and sun lights up from within.
    """
    m = bpy.data.materials.new("PaperToon")
    m.use_nodes = True
    m.use_backface_culling = False
    nt = m.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    emit = nt.nodes.new("ShaderNodeEmission")
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    # backlight: how much this sheet faces away from camera while the sun is behind it
    layw = nt.nodes.new("ShaderNodeLayerWeight")
    bmul = nt.nodes.new("ShaderNodeMath")

    diff.inputs["Color"].default_value = hexcol("FFFFFF")
    nt.links.new(diff.outputs["BSDF"], s2rgb.inputs["Shader"])
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])

    # three hard steps: warm shadow -> cream mid -> hot white
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = hexcol("C9A38F")     # hue-shifted, not grey
    ramp.color_ramp.elements[1].position = 0.34
    ramp.color_ramp.elements[1].color = hexcol("FFF8EE")
    e = ramp.color_ramp.elements.new(0.72)
    e.color = hexcol("FFFFFF")

    layw.inputs["Blend"].default_value = 0.35
    bmul.operation = "MULTIPLY"
    bmul.inputs[1].default_value = 0.42
    nt.links.new(layw.outputs["Facing"], bmul.inputs[0])

    emit.inputs["Color"].default_value = hexcol("FFF2DC")
    emit.inputs["Strength"].default_value = 1.70

    nt.links.new(ramp.outputs["Color"], mix.inputs[1])
    nt.links.new(emit.outputs["Emission"], mix.inputs[2])
    nt.links.new(bmul.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def build_ground():
    """A dark silhouetted plain under the heart.

    Without it the lower half of frame is the unlit part of the sky and reads as a void; the
    shot needs a horizon line for the heart to float above and for the two figures to stand on.
    Kept almost black on purpose - at this sun angle real ground would be silhouette anyway.
    """
    bpy.ops.mesh.primitive_plane_add(size=400.0, location=(0.0, 0.0, 0.0))
    g = bpy.context.active_object
    g.name = "Ground"
    m = bpy.data.materials.new("GroundToon")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfDiffuse")
    bsdf.inputs["Color"].default_value = hexcol("2A1A12")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    g.data.materials.append(m)
    return g


def his_page_material():
    """His page, not hers. Warmer, softer, obviously handled.

    It has to be findable in a frame with sixty other sheets without being loud about it, so it
    is separated by hue and by having no hot white band, not by being brighter.
    """
    m = bpy.data.materials.new("HisPage")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    emit = nt.nodes.new("ShaderNodeEmission")
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    layw = nt.nodes.new("ShaderNodeLayerWeight")
    bmul = nt.nodes.new("ShaderNodeMath")

    diff.inputs["Color"].default_value = hexcol("FFFFFF")
    nt.links.new(diff.outputs["BSDF"], s2rgb.inputs["Shader"])
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = hexcol("B08A6A")
    ramp.color_ramp.elements[1].position = 0.34
    ramp.color_ramp.elements[1].color = hexcol("E8CFA8")
    e = ramp.color_ramp.elements.new(0.74)
    e.color = hexcol("F7E4C2")

    layw.inputs["Blend"].default_value = 0.35
    bmul.operation = "MULTIPLY"
    bmul.inputs[1].default_value = 0.46
    nt.links.new(layw.outputs["Facing"], bmul.inputs[0])
    emit.inputs["Color"].default_value = hexcol("FFE2B4")
    emit.inputs["Strength"].default_value = 1.55

    nt.links.new(ramp.outputs["Color"], mix.inputs[1])
    nt.links.new(emit.outputs["Emission"], mix.inputs[2])
    nt.links.new(bmul.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def make_his_page(mat):
    """One A4 sheet with a fold across it - months of being carried in a fist."""
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    ob = bpy.context.active_object
    ob.name = "his_page"
    ob.scale = (A4[0], A4[1], 1.0)
    bpy.ops.object.transform_apply(scale=True)
    sub = ob.modifiers.new("sub", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 3
    # a real crease, so it reads as handled rather than fresh
    for v in ob.data.vertices:
        v.co.z += 0.016 * math.cos(v.co.y / A4[1] * math.pi * 2.0)
    ob.data.materials.append(mat)
    for poly in ob.data.polygons:
        poly.use_smooth = False
    return ob


def animate_his_page(ob):
    """From his hand to the notch, then down last of all.

    Hers is a flood; his is one page. It arrives at the apex of the heart on the same frame her
    ribbon completes it, so the shape is finished by both of them at once, and it is the last
    thing still in the air when the rest has gone.
    """
    notch = heart_point(0.5)                    # t=0, top centre dip - where the eye goes
    rise0, rise1 = 4500, PEAK                   # leaves his hand as the call dies
    for f in range(S50[0], 4921):
        if f <= rise0:
            pos = MAN + Vector((-0.10, -0.16, 0.02))
            rot = Euler((math.radians(74.0), 0.0, math.radians(28.0)))
        elif f <= rise1:
            k = smooth((f - rise0) / float(rise1 - rise0))
            arc = Vector((0.0, 0.0, math.sin(k * math.pi) * 1.15))   # lifts over, not straight up
            pos = (MAN + Vector((-0.10, -0.16, 0.02))).lerp(notch, k) + arc
            spin = (1.0 - k) * 900.0
            rot = Euler((math.radians(74.0 + 16.0 * k + spin * 0.10),
                         math.radians(spin * 0.16),
                         math.radians(28.0 + spin * 0.21)))
        else:
            k = smooth((f - LETGO) / float(LETGO_FADE)) if f > LETGO else 0.0
            flut = math.sin(f * 0.11) * 0.035
            pos = notch + Vector((flut, math.cos(f * 0.09) * 0.05, flut * 0.6))
            pos += Vector((-0.55, 0.12, -0.28)) * max(0.0, f - LETGO) * 0.16 * k
            rot = Euler((math.radians(90.0 + flut * 60.0 + f * 1.4 * k),
                         math.radians(f * 0.9 * k), math.radians(f * 1.7 * k)))
        ob.location = pos
        ob.rotation_euler = rot
        ob.keyframe_insert("location", frame=f)
        ob.keyframe_insert("rotation_euler", frame=f)
    for fc in ob.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def build_lighting():
    """Low sun directly behind the vortex, plus a cool fill so the shadow side keeps its hue."""
    sd = bpy.data.lights.new("Sun", "SUN")
    sd.energy = 2.6
    sd.color = hexcol("FFD9A0")[:3]
    sd.angle = math.radians(1.2)
    sun = bpy.data.objects.new("Sun", sd)
    bpy.context.collection.objects.link(sun)
    sun.location = (0.0, -26.0, 5.5)
    sun.rotation_euler = Euler((math.radians(83.4), 0, math.radians(180)))

    fd = bpy.data.lights.new("Fill", "AREA")
    fd.energy = 60.0
    fd.size = 18.0
    fd.color = hexcol("8FB3D9")[:3]
    fill = bpy.data.objects.new("Fill", fd)
    bpy.context.collection.objects.link(fill)
    fill.location = (7.0, 9.0, 7.0)
    fill.rotation_euler = Euler((math.radians(55), 0, math.radians(150)))
    return sun


# ----------------------------------------------------------------- the path

GIRL = Vector((2.45, 0.30, 1.15))        # screen right, her hands
MAN = Vector((-2.45, -0.20, 1.25))       # screen left
HEART_C = Vector((0.0, 0.0, 3.60))
HEART_S = 0.13                           # ~3.9 m tall, ~2.1 m half-width

# The papers do not park on a static outline. They fly, and the heart is what their flight
# draws in the air: a spiralling ribbon that leaves her hands, traces the whole heart between
# them, and runs out past him, after which the wind is just wind again. That is what "create a
# love symbol in a motion" has to mean - the symbol is the motion, not a formation.
TRAVERSE = 287                           # frames for one sheet to fly the whole path
PEAK = 4752                              # heart fully drawn, sun through the notch
T0 = PEAK - TRAVERSE                     # first sheet leaves her hands
LETGO = 4800                             # after this the path releases them to the wind
LETGO_FADE = 46


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def rnd(seed, a=0.0, b=1.0):
    """Deterministic pseudo-random - same build every run, so renders stay resumable."""
    x = math.sin(seed * 127.1 + 311.7) * 43758.5453
    return a + (x - math.floor(x)) * (b - a)


def heart_point(sp):
    """Heart curve at parameter sp in [0,1]: bottom -> right -> notch -> left -> bottom.

    Direction matters. She is screen right, so the ribbon has to climb her side first and come
    down his, or the whole gesture reads backwards.
    """
    t = math.pi - 2.0 * math.pi * sp
    x = 16 * math.sin(t) ** 3
    z = (13 * math.cos(t) - 5 * math.cos(2 * t)
         - 2 * math.cos(3 * t) - math.cos(4 * t))
    return Vector((x, 0.0, z)) * HEART_S + HEART_C


def build_path(n=900):
    """girl -> heart loop -> man, resampled to constant arc length.

    Constant arc length is what keeps the sheets evenly spaced; sampling the raw parameter
    bunches them at the lobes and starves the point, which is where the eye checks the shape.
    """
    raw = []
    lead = 90
    for i in range(lead):                          # out of her hands, up to the heart's point
        u = i / lead
        raw.append(GIRL.lerp(heart_point(0.0), smooth(u))
                   + Vector((0, 0, math.sin(u * math.pi) * 0.35)))
    for i in range(n):                             # the heart itself
        raw.append(heart_point(i / (n - 1.0)))
    for i in range(lead):                          # down out of the heart and away to him
        u = i / lead
        raw.append(heart_point(1.0).lerp(MAN, smooth(u))
                   + Vector((0, 0, math.sin(u * math.pi) * 0.35)))

    cum = [0.0]
    for a, b in zip(raw, raw[1:]):
        cum.append(cum[-1] + (b - a).length)
    total = cum[-1]
    out, j = [], 0
    for i in range(n):
        want = total * i / (n - 1.0)
        while j < len(cum) - 2 and cum[j + 1] < want:
            j += 1
        out.append(raw[j])
    return out


def path_at(path, u):
    """Position and unit tangent at u in [0,1]."""
    u = max(0.0, min(0.9999, u))
    f = u * (len(path) - 1)
    i = int(f)
    a, b = path[i], path[min(i + 1, len(path) - 1)]
    pos = a.lerp(b, f - i)
    tan = path[min(i + 2, len(path) - 1)] - path[max(i - 2, 0)]
    tan = tan.normalized() if tan.length > 1e-6 else Vector((1.0, 0.0, 0.0))
    return pos, tan


def spiral_offset(tan, ang, r):
    """Corkscrew the sheet around the path. The ribbon needs volume or it reads as a drawn
    line rather than paper caught in a rising wind."""
    up = Vector((0.0, 1.0, 0.0))                   # heart lies in XZ, so Y is a clean binormal
    n = tan.cross(up)
    n = n.normalized() if n.length > 1e-6 else Vector((0.0, 1.0, 0.0))
    b = tan.cross(n).normalized()
    return (n * math.cos(ang) + b * math.sin(ang)) * r


# ----------------------------------------------------------------- sheets

def make_sheet(i, mat):
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    ob = bpy.context.active_object
    ob.name = "sheet_%03d" % i
    ob.scale = (A4[0], A4[1], 1.0)
    bpy.ops.object.transform_apply(scale=True)

    sub = ob.modifiers.new("sub", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 2

    ob.data.materials.append(mat)
    for poly in ob.data.polygons:
        poly.use_smooth = False
    return ob


def animate(sheets, path):
    """Stagger the sheets so the heart is progressively drawn and complete exactly at PEAK.

    Sheet 0 leaves first and is at the far end by PEAK; the last leaves at PEAK and is still
    in her hands. Between them the ribbon covers the whole curve, so the symbol finishes on
    the frame the score peaks on. After LETGO the path stops holding any of them and it is
    just wind again.
    """
    stagger = TRAVERSE / max(1, len(sheets) - 1)
    f_start, f_end = S50[0], 4920                  # through S53, where they blow away
    for i, ob in enumerate(sheets):
        release = T0 + i * stagger
        turns = rnd(i * 3.7, 2.4, 4.1)
        phase = rnd(i * 5.3, 0.0, math.tau)
        rad = rnd(i * 8.9, 0.10, 0.30)
        spin = 1.0 if i % 2 else -1.0
        drift = Vector((rnd(i * 2.2, -0.9, -0.3), rnd(i * 6.1, -0.5, 0.5),
                        rnd(i * 4.5, 0.25, 0.7)))

        for f in range(f_start, f_end + 1):
            u = (f - release) / TRAVERSE

            if u <= 0.0:                           # still held, trembling in her hands
                pos = GIRL + Vector((rnd(i * 1.1, -0.06, 0.06), rnd(i * 2.7, -0.05, 0.05),
                                     rnd(i * 3.3, -0.05, 0.05)))
                rot = Euler((math.radians(88 + rnd(i * 9.1, -12, 12)), 0.0,
                             math.radians(rnd(i * 7.3, -18, 18))))
            else:
                pos, tan = path_at(path, u)
                ang = phase + u * turns * math.tau * spin
                taper = math.sin(min(1.0, u) * math.pi) ** 0.5    # tighter at both ends
                pos = pos + spiral_offset(tan, ang, rad * taper)
                rot = Euler((
                    math.radians(90.0 + math.degrees(math.asin(max(-1.0, min(1.0, tan.z)))) * 0.6),
                    math.radians(math.degrees(math.atan2(tan.y, tan.x)) * 0.25 + ang * 12.0),
                    math.radians(-math.degrees(math.atan2(tan.z, tan.x)) + ang * 6.0)))

                if u > 1.0 or f > LETGO:           # off the end, or the path has let go
                    k = smooth(max((f - LETGO) / float(LETGO_FADE), (u - 1.0) * 3.0))
                    t_free = f - max(LETGO, release + TRAVERSE)
                    free = pos + drift * max(0.0, t_free) * 0.45
                    free += Vector((math.sin(f * 0.07 + i) * 0.20,
                                    math.cos(f * 0.06 + i) * 0.16,
                                    math.sin(f * 0.05 + i * 2.0) * 0.12)) * k
                    pos = pos.lerp(free, k)
                    rot = Euler((rot.x + math.radians(f * 1.9 * spin * k),
                                 rot.y + math.radians(f * 1.1 * spin * k),
                                 rot.z + math.radians(f * 2.4 * spin * k)))

            ob.location = pos
            ob.rotation_euler = rot
            ob.keyframe_insert("location", frame=f)
            ob.keyframe_insert("rotation_euler", frame=f)

        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def build_figures():
    """Backlit silhouette stand-ins, so the ribbon visibly starts at her and ends at him.

    These get replaced by the real characters. At this sun angle they are pure silhouette
    anyway, which is exactly why this shot can be built before the models exist.
    """
    mat = bpy.data.materials.new("Silhouette")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfDiffuse")
    bsdf.inputs["Color"].default_value = hexcol("1A1008")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    for name, base, h, shoulder in (("Girl", GIRL, 1.64, 0.20), ("Man", MAN, 1.80, 0.25)):
        parts = []
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.135, depth=h * 0.56,
                                            location=(base.x, base.y, h * 0.28))
        legs = bpy.context.active_object
        legs.name = "fig_%s_legs" % name
        legs.scale = (1.0, 0.62, 1.0)
        parts.append(legs)

        bpy.ops.mesh.primitive_cone_add(vertices=20, radius1=shoulder, radius2=0.14,
                                        depth=h * 0.36,
                                        location=(base.x, base.y, h * 0.74))
        torso = bpy.context.active_object
        torso.name = "fig_%s_torso" % name
        torso.scale = (1.0, 0.58, 1.0)
        torso.rotation_euler = Euler((math.pi, 0.0, 0.0))     # wider at the shoulders
        parts.append(torso)

        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.105,
                                             location=(base.x, base.y, h * 0.97))
        head = bpy.context.active_object
        head.name = "fig_%s_head" % name
        head.scale = (1.0, 0.92, 1.12)
        parts.append(head)

        for o in parts:
            o.data.materials.append(mat)


def build_camera():
    cam_d = bpy.data.cameras.new("Cam")
    cam_d.lens = 38.0
    cam_d.dof.use_dof = True
    cam_d.dof.aperture_fstop = 2.2
    cam = bpy.data.objects.new("Cam", cam_d)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    focus = bpy.data.objects.new("Focus", None)
    bpy.context.collection.objects.link(focus)
    cam_d.dof.focus_object = focus

    track = cam.constraints.new("TRACK_TO")
    track.target = focus
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    # S50 low and close on the lifting sheets -> S51 crane up with the spiral ->
    # S52 orbit round and rise so the heart lands centre frame against the sun
    # The gesture now runs right-to-left across 5.2 m (her hands to him) and 4.6 m of height,
    # so the camera has to sit back far enough to hold both ends of it. At 38 mm that is ~9 m.
    # It starts tight on her hands, pulls back as the ribbon climbs, sits still while the heart
    # completes, then drifts left to follow the papers out past him.
    # Low and looking up, all the way through. The heart has to sit against the sky: at eye
    # height it projects below the horizon onto dark ground and stops reading as a shape at
    # all. Camera stays around 1.2 m - roughly the height of her hands - so the two of them
    # stay as foreground silhouettes along the bottom edge.
    keys = [
        (S50[0],  (2.10, -3.60, 1.35), (2.45, 0.30, 1.30)),
        (S50[1],  (1.75, -5.40, 1.30), (1.80, 0.00, 2.30)),
        (S51[0],  (1.60, -5.85, 1.30), (1.60, 0.00, 2.55)),
        (S51[1],  (0.70, -8.00, 1.25), (0.50, 0.00, 3.40)),
        (PEAK,    (0.00, -9.05, 1.20), (0.00, 0.00, 3.60)),
        (LETGO,   (-0.40, -9.15, 1.25), (-0.20, 0.00, 3.60)),
        (4920,    (-1.60, -8.80, 1.35), (-1.70, 0.00, 3.15)),
    ]
    for f, loc, foc in keys:
        cam.location = loc
        cam.keyframe_insert("location", frame=f)
        focus.location = foc
        focus.keyframe_insert("location", frame=f)
    for ob in (cam, focus):
        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    return cam


# ----------------------------------------------------------------- scene

def setup_scene(out_dir, f0, f1):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = f0, f1

    ee = sc.eevee
    ee.taa_render_samples = 64
    for attr, val in (("use_gtao", True), ("gtao_distance", 0.3),
                      ("use_bloom", False), ("use_motion_blur", False)):
        if hasattr(ee, attr):
            setattr(ee, attr, val)
    if hasattr(ee, "use_raytracing"):
        ee.use_raytracing = True

    # Standard, never Filmic: Filmic is built for photographic latitude and it turns the flat
    # toon bands into gradients, which is precisely the look we are trying not to have.
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    # The sky was clipping to pure white and white paper vanished into it. A deep
    # twilight is also simply the right look: the sheets have to be the brightest
    # thing in frame for the heart to read at all.
    sc.view_settings.exposure = -0.55

    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.compression = 15
    sc.render.filepath = str((Path(out_dir).resolve() / "f_"))
    sc.render.use_overwrite = False        # resumable: skip frames already on disk
    sc.render.use_placeholder = True


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_dir = argv[0] if argv else "renders/paper_heart/act6"
    f0 = int(argv[1]) if len(argv) > 1 else S50[0]
    f1 = int(argv[2]) if len(argv) > 2 else 4920
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    clear()
    build_world()
    build_lighting()
    build_ground()
    mat = paper_material()
    build_figures()
    sheets = [make_sheet(i, mat) for i in range(N_SHEETS)]
    path = build_path()
    animate(sheets, path)
    # His one page. Her hundreds draw the heart; his single creased sheet takes the notch, so
    # the finished shape is made of what both of them gave up rather than only what she did.
    page = make_his_page(his_page_material())
    animate_his_page(page)
    build_camera()
    setup_scene(out_dir, f0, f1)

    bpy.ops.wm.save_as_mainfile(filepath=str(Path("build/paper_heart/act6.blend").resolve()))
    print(f"RESULT built sheets={len(sheets)}+1(his page) frames={f0}-{f1} out={out_dir}",
          flush=True)


if __name__ == "__main__":
    main()
