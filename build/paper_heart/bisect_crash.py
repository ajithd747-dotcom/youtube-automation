"""Which downloaded asset crashes EEVEE here?

    blender -b --factory-startup --python build/paper_heart/bisect_crash.py -- <which>

`which` is one of: none | lamps | poles | covers | tree | all

A 1024 png on a plane renders fine (test_texture_crash.py), but the dressed street died with
EXCEPTION_ACCESS_VIOLATION - the same signature as the note in the project memory. So the
crash is real and something narrower than "image textures" triggers it. Renders tiny and fast
so each arm of the bisect costs seconds.

Run one arm per process: a crash takes the process with it, so they cannot share one.
"""
import sys
from pathlib import Path

import bpy

MODELS = Path("build/paper_heart/models").resolve()


def append_model(stem):
    src = MODELS / f"{stem}.blend"
    if not src.exists():
        print(f"MISSING {stem}", flush=True)
        return []
    with bpy.data.libraries.load(str(src), link=False) as (sd, dd):
        dd.objects = list(sd.objects)
    out = [o for o in dd.objects if o is not None and o.type == "MESH"]
    for o in out:
        bpy.context.collection.objects.link(o)
    print(f"appended {stem}: {len(out)} meshes", flush=True)
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    which = argv[0] if argv else "all"
    bpy.ops.wm.read_factory_settings(use_empty=True)

    cam_d = bpy.data.cameras.new("C")
    cam = bpy.data.objects.new("C", cam_d)
    bpy.context.collection.objects.link(cam)
    cam.location = (0, -14, 4)
    cam.rotation_euler = (1.35, 0, 0)
    bpy.context.scene.camera = cam
    ld = bpy.data.lights.new("L", "SUN")
    ld.energy = 3.0
    bpy.context.collection.objects.link(bpy.data.objects.new("L", ld))

    sets = {"lamps": ["street_lamp_01"], "poles": ["modular_electricity_poles"],
            "covers": ["water_manhole_cover"], "tree": ["jacaranda_tree"],
            "all": ["street_lamp_01", "modular_electricity_poles",
                    "water_manhole_cover", "jacaranda_tree"], "none": []}
    for stem in sets.get(which, []):
        append_model(stem)

    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x, sc.render.resolution_y = 480, 270
    sc.eevee.taa_render_samples = 16
    sc.render.filepath = str((Path("renders/paper_heart/_bisect") / which).resolve())
    print(f"rendering arm={which} ...", flush=True)
    bpy.ops.render.render(write_still=True)
    print(f"ARM OK {which}", flush=True)


if __name__ == "__main__":
    main()
