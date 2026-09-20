"""Shared Blender-side building blocks for the recreation ladder (imported by blender_level1.py, blender_level2.py).

Everything renders in Workbench with flat lighting and vertex colours under the Standard view transform, so the output
colours are exactly the colours put in and nothing is lit that the measurements did not say was lit.
"""
import bpy
import numpy as np


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def setup_scene(width, height):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = width, height, 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.display_settings.display_device = "sRGB"
    shading = scene.display.shading
    shading.light, shading.color_type, shading.show_specular_highlight = "FLAT", "VERTEX", False
    scene.display.render_aa = "OFF"
    aspect = width / height
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type, cam_data.ortho_scale = "ORTHO", aspect
    cam = bpy.data.objects.new("cam", cam_data)
    cam.location = (0, 0, 2)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene, aspect


def build_colour_plane(scene, gw, gh, aspect):
    """Plane with one vertex per grid cell centre + a border ring carrying the edge colours. Returns (mesh, colour attribute)."""
    xs = np.concatenate([[0.0], (np.arange(gw) + 0.5) / gw, [1.0]])
    ys = np.concatenate([[0.0], (np.arange(gh) + 0.5) / gh, [1.0]])
    verts = [((x - 0.5) * aspect, (0.5 - y), 0.0) for y in ys for x in xs]     # row 0 = top of the picture
    nx, ny = gw + 2, gh + 2
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]
    mesh = bpy.data.meshes.new("layout")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    attr = mesh.color_attributes.new("col", "FLOAT_COLOR", "POINT")
    scene.collection.objects.link(bpy.data.objects.new("layout", mesh))
    return mesh, attr


def set_plane_colours(mesh, attr, cells_rgb_uint8):
    cells = cells_rgb_uint8.astype(np.float32) / 255.0
    padded = np.pad(cells, ((1, 1), (1, 1), (0, 0)), mode="edge")
    lin = srgb_to_linear(padded).reshape(-1, 3)
    attr.data.foreach_set("color", np.concatenate([lin, np.ones((len(lin), 1), np.float32)], axis=1).ravel())
    mesh.update()


def make_line_object(scene):
    mesh = bpy.data.meshes.new("lines")
    obj = bpy.data.objects.new("lines", mesh)
    scene.collection.objects.link(obj)
    return mesh


def set_line_ribbons(mesh, seg_a, seg_b, seg_rgb_uint8, width_px, height_px, aspect, half_width_px):
    """Rebuild the line mesh: one flat quad per segment. seg_a/seg_b: [S,2] pixel coords (x right, y down); colours per segment."""
    mesh.clear_geometry()
    if len(seg_a) == 0:
        return
    a = np.asarray(seg_a, np.float64)
    b = np.asarray(seg_b, np.float64)
    d = b - a
    ln = np.hypot(d[:, 0], d[:, 1])
    ok = ln > 1e-6
    a, b, d, ln = a[ok], b[ok], d[ok], ln[ok]
    col = np.asarray(seg_rgb_uint8)[ok]
    s = len(a)
    if s == 0:
        return
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1) / ln[:, None] * half_width_px
    corners = np.stack([a + nrm, a - nrm, b - nrm, b + nrm], axis=1)               # [S,4,2] in pixels
    x = (corners[:, :, 0] / width_px - 0.5) * aspect
    y = 0.5 - corners[:, :, 1] / height_px
    co = np.stack([x, y, np.full_like(x, 0.01)], axis=2).reshape(-1, 3)
    mesh.vertices.add(4 * s)
    mesh.vertices.foreach_set("co", co.ravel())
    mesh.loops.add(4 * s)
    mesh.loops.foreach_set("vertex_index", np.arange(4 * s))
    mesh.polygons.add(s)
    mesh.polygons.foreach_set("loop_start", np.arange(s) * 4)
    mesh.polygons.foreach_set("loop_total", np.full(s, 4))
    mesh.update()
    attr = mesh.color_attributes.new("col", "FLOAT_COLOR", "POINT")
    lin = srgb_to_linear(col.astype(np.float32) / 255.0)
    rgba = np.concatenate([np.repeat(lin, 4, axis=0), np.ones((4 * s, 1), np.float32)], axis=1)
    attr.data.foreach_set("color", rgba.ravel())
    mesh.update()
