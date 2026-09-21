"""Runs INSIDE Blender: rung 3 of the recreation ladder -- a parametric scene built from the shot script alone.

    blender -b --python training/blender_level3.py -- job.json

No reference pixels enter this file. job.json carries a scene spec derived from the shot script (build_scene_spec in training/recreate_level3.py)
and a list of parameter candidates; every candidate is rendered for every requested frame:

    {"spec": {...}, "candidates": [{...params...}, ...], "frames": [0, 7, ...], "width": 320, "height": 180,
     "samples": 16, "out_dir": "..."}

Output: <out_dir>/c{k:02d}_f{frame:05d}.png, frame = shot-relative frame index.

Scene: a backdrop plane coloured with the measured top/middle/bottom band colours (colour ramp over height), a subject proxy
(ellipsoid) at the measured face/subject box, a key point light from the measured screen-space light direction, a world fill, a camera
following the measured path keyframes, film exposure keyed to the measured exposure curve, and compositor bloom + vignette.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

CAM_DIST = 10.0
LENS_MM, SENSOR_MM = 50.0, 36.0
SUBJECT_DEPTH = 3.0            # subject proxy sits this far in front of the backdrop


def srgb_to_linear(c):
    return [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]


def rgb_lin(rgb_uint8, gain=1.0):
    return [min(max(v * gain, 0.0), 1.0) for v in srgb_to_linear([x / 255.0 for x in rgb_uint8])]


def view_size_at(distance, aspect):
    w = SENSOR_MM / LENS_MM * distance
    return w, w / aspect


def setup_render(width, height, samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 2
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = width, height, 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.display_settings.display_device = "sRGB"
    return sc


SHADING = {"mode": "lit"}      # "cel": flat emission at the measured colour, the anime look; set from spec["shading"]


def diffuse_material(name, colour_lin=None, ramp=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    if SHADING["mode"] == "cel":
        emit = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(emit.outputs["Emission"], nt.nodes["Material Output"].inputs["Surface"])
        bsdf = emit                                            # colour sockets below go to the emission node
        bsdf.inputs["Strength"].default_value = 1.0
        if ramp is None:
            bsdf.inputs["Color"].default_value = (*colour_lin, 1.0)
            return mat, bsdf, None
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        cr = nt.nodes.new("ShaderNodeValToRGB")
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        nt.links.new(sep.outputs["Y"], cr.inputs["Fac"])
        nt.links.new(cr.outputs["Color"], bsdf.inputs["Color"])
        els = cr.color_ramp.elements
        while len(els) < len(ramp):
            els.new(0.5)
        for el, (pos, col) in zip(els, ramp):
            el.position, el.color = pos, (*col, 1.0)
        return mat, bsdf, cr
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    if ramp is None:
        bsdf.inputs["Base Color"].default_value = (*colour_lin, 1.0)
        return mat, bsdf, None
    # vertical colour ramp over the plane's generated Z (0 = bottom, 1 = top)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    cr = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Y"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])
    els = cr.color_ramp.elements
    while len(els) < len(ramp):
        els.new(0.5)
    for el, (pos, col) in zip(els, ramp):
        el.position, el.color = pos, (*col, 1.0)
    return mat, bsdf, cr


DEFAULT_SHAPE = {   # character proxy, in units of the face box (x, y, w, h); tuned per shot by training/tune_character_shape.py
    "hair_w": 1.15, "hair_h": 1.05, "hair_cy": 0.35,
    "head_w": 0.75, "head_h": 0.8, "head_cy": 0.6,
    "body_w": 2.0, "body_top": 0.95,
    # silhouette style only (spec["character_style"] == "silhouette")
    "spike": 0.12, "side_len": 0.6, "bang_len": 0.35, "neck_w": 0.35, "shoulder_drop": 0.35,
}
BANG_TEETH = 5


def make_flat(name, rgb):
    mesh = bpy.data.meshes.new(name)
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    mat, _, _ = diffuse_material(name, colour_lin=rgb_lin(rgb))
    mesh.materials.append(mat)
    return o


def set_flat_outline(o, pts, dist, aspect):
    """Replace o's mesh with one flat n-gon through screen points pts [(x, y) frame fractions], `dist` from the camera."""
    vw, vh = view_size_at(dist, aspect)
    verts = [((x - 0.5) * vw, dist - CAM_DIST, (0.5 - y) * vh) for x, y in pts]
    m = o.data
    m.clear_geometry()
    m.from_pydata(verts, [], [list(range(len(verts)))])
    m.update()


def hair_back_outline(cx, top, cw, ch, spike, side_bottom, n=24):
    """Crown: upper half-ellipse with spikes on every other point, then straight side locks down to side_bottom."""
    pts = []
    for i in range(n + 1):
        a = math.pi * i / n                                   # 0 = right, pi = left, over the top
        r = 1.0 + (spike if i % 2 else 0.0)
        pts.append((cx + 0.5 * cw * r * math.cos(a), top + 0.5 * ch - 0.5 * ch * r * math.sin(a)))
    pts += [(cx - 0.5 * cw, side_bottom), (cx - 0.3 * cw, side_bottom), (cx + 0.3 * cw, side_bottom), (cx + 0.5 * cw, side_bottom)]
    return pts


def bangs_outline(cx, y0, w, length):
    """Fringe over the forehead: straight top edge at y0, zigzag bottom edge `length` lower."""
    pts = [(cx - 0.5 * w, y0), (cx + 0.5 * w, y0)]
    for i in range(BANG_TEETH * 2 + 1):
        x = cx + 0.5 * w - w * i / (BANG_TEETH * 2)
        pts.append((x, y0 + (length if i % 2 else length * 0.35)))
    return pts


def body_outline(cx, neck_y, neck_w, shoulder_w, shoulder_drop):
    return [(cx - 0.5 * neck_w, neck_y), (cx + 0.5 * neck_w, neck_y), (cx + 0.5 * shoulder_w * 0.8, neck_y + shoulder_drop * 0.6),
            (cx + 0.5 * shoulder_w, neck_y + shoulder_drop), (cx + 0.5 * shoulder_w, 1.3), (cx - 0.5 * shoulder_w, 1.3),
            (cx - 0.5 * shoulder_w, neck_y + shoulder_drop), (cx - 0.5 * shoulder_w * 0.8, neck_y + shoulder_drop * 0.6)]


def make_ellipsoid(name, rgb):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.5)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    mat, _, _ = diffuse_material(name, colour_lin=rgb_lin(rgb))
    o.data.materials.append(mat)
    return o


def place_on_screen(o, cx, cy, sw, sh, dist, aspect, depth_ratio=0.6):
    """Put ellipsoid o so its silhouette covers the screen box centred (cx, cy), size (sw, sh) in frame fractions, `dist` from the camera."""
    vw, vh = view_size_at(dist, aspect)
    o.location = ((cx - 0.5) * vw, dist - CAM_DIST, (0.5 - cy) * vh)          # camera sits at y = -CAM_DIST looking +Y
    o.scale = (max(sw, 1e-3) * vw, max(min(sw * vw, sh * vh), 1e-3) * depth_ratio, max(sh, 1e-3) * vh)


def screen_ellipsoid(name, cx, cy, sw, sh, dist, aspect, rgb, depth_ratio=0.6):
    o = make_ellipsoid(name, rgb)
    place_on_screen(o, cx, cy, sw, sh, dist, aspect, depth_ratio)
    return o


def clip_above(pts, y_cut):
    """Sutherland-Hodgman clip of polygon pts to the half-plane y <= y_cut (screen y grows downward)."""
    out = []
    for i, (x1, y1) in enumerate(pts):
        x0, y0 = pts[i - 1]
        in0, in1 = y0 <= y_cut, y1 <= y_cut
        if in0 != in1:
            t = (y_cut - y0) / (y1 - y0)
            out.append((x0 + t * (x1 - x0), y_cut))
        if in1:
            out.append((x1, y1))
    return out


def build_character(ch, style="ellipsoid"):
    """Character proxy from the semantic pass + measured colours: body (behind), hair (behind the head), head (front);
    the silhouette style adds bangs in front of the head and uses flat outlines for hair and body."""
    col = {"body": ch.get("body_rgb"), "hair": ch.get("hair_rgb"), "head": ch.get("skin_rgb")}
    parts = {}
    for k, rgb in col.items():
        if not isinstance(rgb, list):
            continue
        parts[k] = make_flat(k, rgb) if (style == "silhouette" and k != "head") else make_ellipsoid(k, rgb)
    if style == "outline":
        # measured silhouette: whole outline in the body colour, the part above the chin in the hair colour, head in front
        for k in ("body", "hair"):
            if k in parts:
                bpy.data.objects.remove(parts.pop(k))
        parts["outline_body"] = make_flat("outline_body", col["body"] if isinstance(col["body"], list) else col["hair"])
        if isinstance(col["hair"], list):
            parts["outline_hair"] = make_flat("outline_hair", col["hair"])
    if style == "silhouette" and isinstance(col["hair"], list):
        parts["bangs"] = make_flat("bangs", col["hair"])
    parts["_style"] = style
    return parts


def place_character(parts, face_xywh, shape, aspect, outline=None):
    """Anime face boxes span brows to chin: hair extends above, the body starts below the chin."""
    x, y, w, h = face_xywh
    s = {**DEFAULT_SHAPE, **(shape or {})}
    cx, d_head = x + w / 2, CAM_DIST - SUBJECT_DEPTH
    if parts.get("_style") == "outline":
        pts = [tuple(p) for p in outline]
        set_flat_outline(parts["outline_body"], pts, d_head + 0.8, aspect)
        if "outline_hair" in parts:
            hair = clip_above(pts, y + s["body_top"] * h)
            set_flat_outline(parts["outline_hair"], hair if len(hair) >= 3 else pts[:3], d_head + 0.4, aspect)
        if "head" in parts:
            place_on_screen(parts["head"], cx, y + s["head_cy"] * h, s["head_w"] * w, s["head_h"] * h, d_head, aspect, 0.7)
        return
    if parts.get("_style") == "silhouette":
        if "body" in parts:
            set_flat_outline(parts["body"], body_outline(cx, y + s["body_top"] * h, s["neck_w"] * w, s["body_w"] * w, s["shoulder_drop"] * h), d_head + 0.8, aspect)
        if "hair" in parts:
            top = y + s["hair_cy"] * h - 0.5 * s["hair_h"] * h
            set_flat_outline(parts["hair"], hair_back_outline(cx, top, s["hair_w"] * w, s["hair_h"] * h, s["spike"], y + (s["hair_cy"] + s["side_len"]) * h + 0.5 * s["hair_h"] * h),
                             d_head + 0.4, aspect)
        if "head" in parts:
            place_on_screen(parts["head"], cx, y + s["head_cy"] * h, s["head_w"] * w, s["head_h"] * h, d_head, aspect, 0.7)
        if "bangs" in parts:
            head_top = y + (s["head_cy"] - 0.5 * s["head_h"]) * h
            set_flat_outline(parts["bangs"], bangs_outline(cx, head_top, s["head_w"] * w * 1.05, s["bang_len"] * h), d_head - 0.6, aspect)
        return
    if "body" in parts:
        top = y + s["body_top"] * h
        place_on_screen(parts["body"], cx, (top + 1.3) / 2, s["body_w"] * w, 1.3 - top, d_head + 0.8, aspect, 0.5)
    if "hair" in parts:
        place_on_screen(parts["hair"], cx, y + s["hair_cy"] * h, s["hair_w"] * w, s["hair_h"] * h, d_head + 0.4, aspect, 0.7)
    if "head" in parts:
        place_on_screen(parts["head"], cx, y + s["head_cy"] * h, s["head_w"] * w, s["head_h"] * h, d_head, aspect, 0.7)


def build_scene(sc, spec, width, height):
    aspect = width / height
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens, cam_data.sensor_width, cam_data.sensor_fit = LENS_MM, SENSOR_MM, "HORIZONTAL"
    cam = bpy.data.objects.new("cam", cam_data)
    cam.location = (0.0, -CAM_DIST, 0.0)
    cam.rotation_euler = (math.pi / 2, 0.0, 0.0)          # looks along +Y, up = +Z
    sc.collection.objects.link(cam)
    sc.camera = cam

    # backdrop: 1.6x the view so camera shift/zoom/roll never shows its edge
    vw, vh = view_size_at(CAM_DIST, aspect)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0), rotation=(math.pi / 2, 0, 0))
    back = bpy.context.active_object
    back.scale = (vw * 1.6, vh * 1.6, 1)
    reg = spec["regions"]
    # the view covers the middle 1/1.6 of the plane's height: map view thirds onto plane coordinates
    lo, hi = 0.5 - 0.5 / 1.6, 0.5 + 0.5 / 1.6
    at = lambda f: lo + (hi - lo) * f                        # f = 0 bottom of view, 1 top of view
    ramp = [(at(1 / 6), rgb_lin(reg["bottom_third_rgb"])), (at(0.5), rgb_lin(reg["middle_third_rgb"])), (at(5 / 6), rgb_lin(reg["top_third_rgb"]))]
    mat, back_bsdf, back_ramp = diffuse_material("backdrop", ramp=ramp)
    back.data.materials.append(mat)

    subject = None
    ch = spec.get("character")
    if ch and spec.get("subject_bbox_xywh"):
        subject = build_character(ch, spec.get("character_style", "ellipsoid"))
    elif spec.get("subject_bbox_xywh") and spec.get("subject_rgb"):
        x, y, w, h = spec["subject_bbox_xywh"]
        subject = screen_ellipsoid("subject", x + w / 2, y + h / 2, w, h, CAM_DIST - SUBJECT_DEPTH, aspect, spec["subject_rgb"], depth_ratio=0.6)

    # key = point light off to the brighter side: its falloff paints the measured screen-space gradient even on a flat backdrop
    # (a sun lights a flat plane evenly and cannot)
    sun_data = bpy.data.lights.new("key", "POINT")
    sun_data.shadow_soft_size = 1.0
    sun = bpy.data.objects.new("key", sun_data)
    sc.collection.objects.link(sun)

    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    sc.world = world
    bg = world.node_tree.nodes["Background"]

    sc.use_nodes = True
    nt = sc.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers")
    glare = nt.nodes.new("CompositorNodeGlare")
    glare.glare_type = "BLOOM"
    ell = nt.nodes.new("CompositorNodeEllipseMask")
    ell.inputs["Size"].default_value = (0.95, 0.95)
    blur = nt.nodes.new("CompositorNodeBlur")
    blur.inputs["Size"].default_value = (0.2 * width, 0.2 * height)     # Blender 4.5: pixel size is a socket, not factor_x/y
    mix = nt.nodes.new("CompositorNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    comp = nt.nodes.new("CompositorNodeComposite")
    nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
    nt.links.new(ell.outputs["Mask"], blur.inputs["Image"])
    nt.links.new(glare.outputs["Image"], mix.inputs[1])
    nt.links.new(blur.outputs["Image"], mix.inputs[2])
    nt.links.new(mix.outputs["Image"], comp.inputs["Image"])
    return {"aspect": aspect, "character": subject if isinstance(subject, dict) else None, "cam": cam, "sun": sun, "bg": bg, "glare": glare, "vignette": mix, "subject": subject, "back_bsdf": back_bsdf}


KEY_RADIUS = 9.0                # key light distance from the backdrop centre
KEY_ENERGY_W = 1000.0           # key_energy 1.0 = this many watts


def aim_key(key, screen_angle_deg, elevation_deg):
    """Place the key on the brighter side of the screen: screen angle 0 = right, 90 = down (camera looks +Y, up +Z).
    elevation = angle out of the backdrop plane toward the camera; low elevation = grazing light = strong gradient."""
    a, e = math.radians(screen_angle_deg), math.radians(elevation_deg)
    toward_light = Vector((math.cos(a) * math.cos(e), -math.sin(e), -math.sin(a) * math.cos(e)))   # -Y = toward the camera
    key.location = toward_light * KEY_RADIUS


def apply_candidate(sc, obj, spec, p):
    aim_key(obj["sun"], p["key_screen_angle_deg"], p["key_elevation_deg"])
    obj["sun"].data.energy = p["key_energy"] * KEY_ENERGY_W
    obj["bg"].inputs["Color"].default_value = (*rgb_lin(spec["world_rgb"]), 1.0)
    obj["bg"].inputs["Strength"].default_value = p["fill_strength"]
    obj["glare"].inputs["Strength"].default_value = p["bloom_strength"]
    obj["glare"].inputs["Threshold"].default_value = 0.8
    obj["vignette"].inputs["Fac"].default_value = p["vignette"]
    if obj["character"]:
        place_character(obj["character"], spec["subject_bbox_xywh"], p.get("shape"), obj["aspect"], spec.get("outline"))


def key_animation(sc, obj, spec, p):
    """Camera path and exposure curve as real keyframes (shot-relative frames)."""
    cam = obj["cam"]
    base_lens = LENS_MM
    for k in spec["camera_keys"]:
        f = k["frame"]
        cam.data.shift_x = -k["dx"]                    # image moves opposite to the camera window
        cam.data.shift_y = k["dy"]                     # dy > 0 = image moves down = window moves up
        cam.data.lens = base_lens * (1.0 + k["zoom"])
        cam.rotation_euler = (math.pi / 2, -math.radians(k["roll_deg"]), 0.0)
        cam.data.keyframe_insert("shift_x", frame=f)
        cam.data.keyframe_insert("shift_y", frame=f)
        cam.data.keyframe_insert("lens", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    offsets = p.get("exposure_offsets") or {}
    cel = SHADING["mode"] == "cel"                             # cel colours are the measured colours: no exposure on top
    for k in spec["exposure_keys"]:
        sc.view_settings.exposure = 0.0 if cel else p["exposure"] + float(offsets.get(str(k["frame"]), 0.0))
        sc.view_settings.keyframe_insert("exposure", frame=k["frame"])


def main():
    job = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
    spec = job["spec"]
    out = Path(job["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    SHADING["mode"] = spec.get("shading", "lit")
    sc = setup_render(int(job["width"]), int(job["height"]), int(job.get("samples", 16)))
    obj = build_scene(sc, spec, int(job["width"]), int(job["height"]))
    n = 0
    for c, p in enumerate(job["candidates"]):
        apply_candidate(sc, obj, spec, p)
        if sc.animation_data:
            sc.animation_data_clear()
        if obj["cam"].animation_data:
            obj["cam"].animation_data_clear()
        if obj["cam"].data.animation_data:
            obj["cam"].data.animation_data_clear()
        key_animation(sc, obj, spec, p)
        for f in job["frames"]:
            sc.frame_set(int(f))
            sc.render.filepath = str(out / f"c{c:02d}_f{int(f):05d}.png")
            bpy.ops.render.render(write_still=True)
            n += 1
    print(f"LEVEL3_DONE {n} renders -> {out}")


main()
