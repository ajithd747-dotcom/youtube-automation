"""Build a Blender Grease Pencil scene from exported cel data and render it.

Runs inside Blender:
    blender -b --factory-startup --python recreate/gp_build.py -- job.json

The scene is a real 2D-animation setup, not a video overlay: an orthographic camera,
a Grease Pencil object whose layers are the cel layers an animator would use
(BG / FILL / INK / GLOW), one material per palette colour, and keyframes only on the
frames where the reference has a new drawing - so the holds stay holds.
"""
import json
import pickle
import sys
from pathlib import Path

import bpy
import numpy as np

W, H = 1920, 1080
ORTHO_W = 16.0
ORTHO_H = ORTHO_W * H / W


# ---------------------------------------------------------------- helpers

def px_to_world(pts):
    """Image pixels -> GP local XY (camera plane), Y flipped."""
    p = np.asarray(pts, np.float32)
    x = (p[:, 0] / W - 0.5) * ORTHO_W
    y = (0.5 - p[:, 1] / H) * ORTHO_H
    return x, y


def srgb_to_linear(c):
    c = np.asarray(c, np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_gp_material(name, rgb, fill=True, stroke=False, alpha=1.0):
    mat = bpy.data.materials.new(name)
    bpy.data.materials.create_gpencil_data(mat)
    g = mat.grease_pencil
    lin = srgb_to_linear(rgb)
    g.show_fill = fill
    g.show_stroke = stroke
    if fill:
        g.fill_color = (*lin, alpha)
    if stroke:
        g.color = (*lin, alpha)
        g.mode = "LINE"
    return mat


# ---------------------------------------------------------------- build

def add_polys(drawing, polys, mat_of, closed=True, radius=0.004, colors=None):
    """Filled polygons -> cyclic GP strokes, painted in list order.

    `colors` optionally tints each polygon (sRGB 0-255); without it the polygon takes
    its material's fill colour, which is how the palette materials are meant to work.
    """
    if not polys:
        return
    sizes = [len(p["pts"]) for p in polys]
    drawing.add_strokes(sizes)
    n, nc = sum(sizes), len(sizes)

    pos = np.zeros((n, 3), np.float32)
    o = 0
    for p in polys:
        x, y = px_to_world(p["pts"])
        k = len(x)
        pos[o:o + k, 0] = x
        pos[o:o + k, 1] = y
        o += k

    ensure_attrs(drawing)
    a = drawing.attributes
    a["position"].data.foreach_set("vector", pos.ravel())
    a["radius"].data.foreach_set("value", np.full(n, radius, np.float32))
    a["opacity"].data.foreach_set("value", np.ones(n, np.float32))
    a["material_index"].data.foreach_set(
        "value", np.array([mat_of(p) for p in polys], np.int32))
    a["cyclic"].data.foreach_set("value", np.full(nc, 1 if closed else 0, np.int32))
    # these two exist as soon as we create them, and default to 0 - an unset
    # fill_opacity makes every fill invisible, which is what "renders black" looks like
    a["fill_opacity"].data.foreach_set("value", np.ones(nc, np.float32))
    fc = np.zeros((nc, 4), np.float32)          # alpha 0 => use the material colour
    if colors is not None:
        fc[:, :3] = srgb_to_linear(np.asarray(colors))
        fc[:, 3] = 1.0
    a["fill_color"].data.foreach_set("color", fc.ravel())
    drawing.tag_positions_changed()


def add_lines(drawing, strokes, mat_index, width_scale=1.0):
    """Ink polylines -> open GP strokes with per-point radius and colour."""
    if not strokes:
        return
    sizes = [len(s["pts"]) for s in strokes]
    drawing.add_strokes(sizes)
    n, nc = sum(sizes), len(sizes)

    pos = np.zeros((n, 3), np.float32)
    rad = np.zeros(n, np.float32)
    col = np.zeros((n, 4), np.float32)
    o = 0
    for s in strokes:
        x, y = px_to_world(s["pts"])
        k = len(x)
        pos[o:o + k, 0] = x
        pos[o:o + k, 1] = y
        # stroke width is in pixels; GP radius is half-width in world units
        rad[o:o + k] = max(0.0015, s["width"] * width_scale * ORTHO_W / W * 0.5)
        # BGR, like `palette_bgr` and unlike the glow polygons, which export_cels
        # already flips. Harmless while ink is near-black, which is every cel shot in
        # this reference - it only showed up on the tutorial half, whose construction
        # lines are salmon red and were coming out blue.
        col[o:o + k, :3] = srgb_to_linear(s["color"][::-1])
        col[o:o + k, 3] = 1.0
        o += k

    ensure_attrs(drawing)
    a = drawing.attributes
    a["position"].data.foreach_set("vector", pos.ravel())
    a["radius"].data.foreach_set("value", rad)
    a["opacity"].data.foreach_set("value", np.ones(n, np.float32))
    a["vertex_color"].data.foreach_set("color", col.ravel())
    a["material_index"].data.foreach_set("value", np.full(nc, mat_index, np.int32))
    a["cyclic"].data.foreach_set("value", np.zeros(nc, np.int32))
    a["fill_opacity"].data.foreach_set("value", np.ones(nc, np.float32))
    drawing.tag_positions_changed()


ATTR_SPEC = [("radius", "FLOAT", "POINT"), ("opacity", "FLOAT", "POINT"),
             ("vertex_color", "FLOAT_COLOR", "POINT"),
             ("material_index", "INT", "CURVE"), ("cyclic", "BOOLEAN", "CURVE"),
             ("fill_color", "FLOAT_COLOR", "CURVE"), ("fill_opacity", "FLOAT", "CURVE")]


def ensure_attrs(drawing):
    for nm, dt, dom in ATTR_SPEC:
        if drawing.attributes.get(nm) is None:
            drawing.attributes.new(nm, dt, dom)


def add_background(sc, bg_path, shot, analysis_w):
    """The painted background plate, on its own plane behind the cels.

    This is how the shot was actually made: a painted background with drawn cels over
    it.  The plate is built aligned to the shot's first frame, so it has to be pushed
    back through the tracked camera drift to move with the shot; it is oversized so the
    pan never reveals an edge.
    """
    img = bpy.data.images.load(bg_path)
    mat = bpy.data.materials.new("BG")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "EXTEND"
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])

    drift = shot.get("drift") or [[0, 0]]
    pad = 1.0 + 2.0 * max(1e-3, max(abs(d[0]) for d in drift) / analysis_w)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -1))
    pl = bpy.context.object
    pl.scale = (ORTHO_W * pad, ORTHO_H * pad, 1)
    pl.data.materials.append(mat)

    # replay the drift the plate was aligned out of
    sx = ORTHO_W / analysis_w
    sy = ORTHO_H / (analysis_w * H / W)
    for i, (dx, dy) in enumerate(drift):
        pl.location = (dx * sx, -dy * sy, -1)
        pl.keyframe_insert("location", frame=i + 1)
    for fc in pl.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    return pl


def build(job):
    data = pickle.loads(Path(job["cels"]).read_bytes())
    shot = data["shot"]
    pal = data["palette_bgr"]                      # BGR float
    keys = data["keys"]
    draws = data["drawings"]
    start, end = shot["start"], shot["end"]

    clear_scene()
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.render.fps = job.get("fps", 30)
    sc.frame_start, sc.frame_end = 1, end - start
    sc.render.film_transparent = not job.get("bg_plane")
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.filepath = job["out"]
    sc.render.engine = job.get("engine", "BLENDER_EEVEE_NEXT")
    # Blender defaults to the AgX view transform, which is built for photographic
    # footage: it desaturates saturated colour and rolls off highlights, so the flat
    # teal FX came out dim pastel (peak value 194 against the reference's 255) and every
    # flat lost saturation.  Cel art wants its colours passed through untouched.
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0

    cam_d = bpy.data.cameras.new("Cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = ORTHO_W
    cam = bpy.data.objects.new("Cam", cam_d)
    cam.location = (0, 0, 10)
    sc.collection.objects.link(cam)
    sc.camera = cam

    # The background plate is composited in post, not put on a plane here: an
    # image-textured plane in EEVEE crashes this machine's Radeon driver, and
    # compositing outside Blender is faster besides.
    if job.get("bg_plane"):
        add_background(sc, job["bg_plane"], shot, job.get("analysis_width", 192))

    gp = bpy.data.grease_pencils_v3.new("Cels")
    ob = bpy.data.objects.new("Cels", gp)
    sc.collection.objects.link(ob)

    # one material per palette colour, plus ink
    for i, bgr in enumerate(pal):
        ob.data.materials.append(make_gp_material(f"pal{i:02d}",
                                                  (bgr[2], bgr[1], bgr[0])))
    ink_mat = make_gp_material("INK", (20, 20, 20), fill=False, stroke=True)
    ob.data.materials.append(ink_mat)
    ink_idx = len(pal)
    glow_mat = make_gp_material("GLOW", (255, 255, 255))
    ob.data.materials.append(glow_mat)
    glow_idx = len(pal) + 1

    L_fill = gp.layers.new("FILL")
    L_glow = gp.layers.new("GLOW")
    L_ink = gp.layers.new("INK")
    # cel art is lit by the drawing, not by scene lamps; without this GP renders black
    for L in (L_fill, L_glow, L_ink):
        L.use_lights = False

    wscale = job.get("ink_width_scale", 1.0)
    for i, (k, d) in enumerate(zip(keys, draws)):
        f = k - start + 1                            # scene frame for this drawing
        add_polys(L_fill.frames.new(f).drawing, d["fills"], lambda p: int(p["mat"]))
        # Every drawing gets a GLOW key, including the empty ones. A Grease Pencil frame
        # holds until the next key, so skipping the empty ones left the energy blast
        # stuck on screen for every later drawing that had no FX of its own.
        gd = L_glow.frames.new(f).drawing
        if d["glow"]:
            add_polys(gd, d["glow"], lambda p: glow_idx,
                      colors=[p["color"] for p in d["glow"]])
        add_lines(L_ink.frames.new(f).drawing, d["ink"], ink_idx, wscale)

    if job.get("save_blend"):
        bpy.ops.wm.save_as_mainfile(filepath=job["save_blend"])

    bpy.ops.render.render(animation=True)
    return {"ok": True, "frames": end - start, "drawings": len(draws)}


if __name__ == "__main__":
    jp = sys.argv[sys.argv.index("--") + 1]
    job = json.loads(Path(jp).read_text(encoding="utf-8"))
    res = build(job)
    print("RESULT " + json.dumps(res))
