"""Does an image-textured plane still crash EEVEE on this GPU?

    blender -b --factory-startup --python build/paper_heart/test_texture_crash.py

This single question decides whether the photoreal-painterly style is reachable at all. That
look is built on textured surfaces - painted asphalt, brick, leaf cards, signage. The project
notes record `atio6axx.dll` access violations from image-textured planes in EEVEE, which is why
every plate so far has been procedural, and procedural is exactly what caps the detail.

The note came out of a Grease Pencil cel render, so it may not generalise. Testing it costs two
minutes and either unblocks the whole style or settles it for good.

Exit 0 and "TEXTURE TEST PASSED" means textures are safe here.
A hard crash with no output means the note stands.
"""
import sys
from pathlib import Path

import bpy

OUT = Path("renders/paper_heart/_texture_test")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # generate a texture in memory and save it, so the test needs no downloaded asset
    img = bpy.data.images.new("TestTex", width=1024, height=1024)
    px = []
    for y in range(1024):
        for x in range(1024):
            v = ((x // 64) + (y // 64)) % 2
            px += [0.85 if v else 0.15, 0.45, 0.25 if v else 0.75, 1.0]
    img.pixels = px
    tex_path = (OUT / "checker.png").resolve()
    img.filepath_raw = str(tex_path)
    img.file_format = "PNG"
    img.save()
    print("wrote test texture:", tex_path, flush=True)

    # reload it from disk as a real file-backed image - that is the case that crashed
    bpy.data.images.remove(img)
    loaded = bpy.data.images.load(str(tex_path))

    bpy.ops.mesh.primitive_plane_add(size=6.0)
    plane = bpy.context.active_object
    m = bpy.data.materials.new("TexPlane")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = loaded
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    plane.data.materials.append(m)

    cam_d = bpy.data.cameras.new("C")
    cam = bpy.data.objects.new("C", cam_d)
    bpy.context.collection.objects.link(cam)
    cam.location = (0, -5, 3)
    cam.rotation_euler = (1.0, 0, 0)
    bpy.context.scene.camera = cam

    ld = bpy.data.lights.new("L", "SUN")
    ld.energy = 3.0
    light = bpy.data.objects.new("L", ld)
    bpy.context.collection.objects.link(light)

    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.eevee.taa_render_samples = 32
    sc.render.filepath = str((OUT / "result.png").resolve())
    print("rendering an image-textured plane in EEVEE ...", flush=True)
    bpy.ops.render.render(write_still=True)
    print("TEXTURE TEST PASSED - image textures render fine on this GPU", flush=True)


if __name__ == "__main__":
    main()
    sys.exit(0)
