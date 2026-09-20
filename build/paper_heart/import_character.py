"""Import a VRM character and convert it to the PAPER HEART anime look.

    blender -b --python build/paper_heart/import_character.py -- <model.vrm> <girl|man> [out.blend]

A downloaded VRM arrives with flat MToon or Principled materials. This rebuilds every material
as the three-step toon shader from scripts/paper_heart/script.md section 8, applies the palette
from characters.md, and adds the inverted-hull outline.

The shader is the thing that decides quality, not the model - a mid-tier model with this setup
beats a premium one with default materials. So this is the part worth getting right.

NOT YET RUN AGAINST A REAL MODEL. The VRM addon and the .vrm files both need a browser and a
login, so this is written from the spec and needs a first pass with a real file. Expect the
material-name matching in CHARACTERS[...]['match'] to need widening for whatever model you
actually download - print the names first with --list.
"""
import sys
from pathlib import Path

import bpy

VRM_EXT_ZIP = Path("build/paper_heart/vendor/vrm_ext.zip")


def srgb(hexstr):
    h = hexstr.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return (f(r), f(g), f(b), 1.0)


# Palettes from scripts/paper_heart/characters.md. Shadows are hue-shifted, never just darker -
# multiplying by grey is the single most common thing that makes 3D toon look wrong.
CHARACTERS = {
    "girl": {
        "height": 1.62,
        "rim": "#F2A98A",                      # warm sunset rim, her standing treatment
        "parts": {
            "hair":  {"match": ("hair", "kami", "髪"),       "base": "#1A1620", "shadow": "#221E2E", "light": "#3E3646"},
            "skin":  {"match": ("skin", "face", "body", "肌"), "base": "#F5D9C4", "shadow": "#D9A899", "light": "#FFF0E2"},
            "eyes":  {"match": ("eye", "iris", "目"),         "base": "#7FA8C9", "shadow": "#5C7F9E", "light": "#BBD9EE"},
            "cloth": {"match": ("cloth", "jacket", "shirt", "tops"), "base": "#E8A08A", "shadow": "#C07A66", "light": "#F7C0AC"},
            "inner": {"match": ("inner", "camisole", "under"), "base": "#F5F0E8", "shadow": "#D8CFC4", "light": "#FFFFFF"},
        },
    },
    "man": {
        "height": 1.80,
        "rim": "#DCE8F2",                      # cold window rim through Acts 1-3; warm it at the contact
        "parts": {
            "hair":  {"match": ("hair", "kami", "髪"),       "base": "#EDEDF2", "shadow": "#C3C4D0", "light": "#FFFFFF"},
            "skin":  {"match": ("skin", "face", "body", "肌"), "base": "#F2DCC9", "shadow": "#D4A899", "light": "#FFF2E6"},
            "eyes":  {"match": ("eye", "iris", "目"),         "base": "#35C5D4", "shadow": "#1E93A6", "light": "#9BEAF2"},
            "cloth": {"match": ("cloth", "shirt", "tops", "sweater"), "base": "#1C1C22", "shadow": "#121216", "light": "#33333D"},
            "glove": {"match": ("glove", "hand"),             "base": "#1A1A1F", "shadow": "#101014", "light": "#3A3A45"},
        },
    },
}


def ensure_vrm_addon():
    """Enable the VRM importer, installing the vendored zip if it is not present yet."""
    for mod in ("io_scene_vrm", "bl_ext.user_default.vrm", "bl_ext.vscode_development.vrm"):
        try:
            bpy.ops.preferences.addon_enable(module=mod)
            print(f"VRM addon enabled: {mod}")
            return True
        except Exception:
            continue
    if VRM_EXT_ZIP.exists():
        try:
            bpy.ops.extensions.package_install_files(
                filepath=str(VRM_EXT_ZIP.resolve()), repo="user_default",
                enable_on_install=True)
            bpy.ops.wm.save_userpref()
            print("VRM addon installed from", VRM_EXT_ZIP)
            return True
        except Exception as e:                       # noqa: BLE001
            print("VRM extension install failed:", e)
    print("VRM addon unavailable - install it once from", VRM_EXT_ZIP)
    return False


def toon_material(name, base, shadow, light, rim, is_eye=False):
    """Three hard steps, hue-shifted shadow, fresnel rim.

    Three steps rather than two: two reads as cheap, three reads as cel. The terminator is kept
    under 2% of the ramp width so the transition stays a line, not a gradient.
    """
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    add = nt.nodes.new("ShaderNodeMixRGB")
    fres = nt.nodes.new("ShaderNodeFresnel")
    rimramp = nt.nodes.new("ShaderNodeValToRGB")
    emit = nt.nodes.new("ShaderNodeEmission")

    diff.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(diff.outputs["BSDF"], s2rgb.inputs["Shader"])
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])

    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = srgb(shadow)
    ramp.color_ramp.elements[1].position = 0.33
    ramp.color_ramp.elements[1].color = srgb(base)
    hi = ramp.color_ramp.elements.new(0.72)
    hi.color = srgb(light)

    # rim: tight fresnel band, added not mixed, so it never darkens the base
    fres.inputs["IOR"].default_value = 1.45
    rimramp.color_ramp.interpolation = "CONSTANT"
    rimramp.color_ramp.elements[0].position = 0.0
    rimramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    rimramp.color_ramp.elements[1].position = 0.62
    rimramp.color_ramp.elements[1].color = srgb(rim)
    nt.links.new(fres.outputs["Fac"], rimramp.inputs["Fac"])

    add.blend_type = "ADD"
    add.inputs["Fac"].default_value = 0.85 if not is_eye else 0.35
    nt.links.new(ramp.outputs["Color"], add.inputs[1])
    nt.links.new(rimramp.outputs["Color"], add.inputs[2])

    # Anime eyes lie about physics on purpose: a physically correct specular looks dead, so the
    # eye carries a little constant emission to keep the highlight alive in shadow.
    emit.inputs["Strength"].default_value = 1.0 if not is_eye else 1.25
    nt.links.new(add.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return m


def add_outline(ob, thickness=0.003):
    """Inverted hull. This is what anime games actually ship (Arc System Works); Freestyle is
    CPU-bound and this box has four cores, so it is reserved for the hero shots only."""
    mat = bpy.data.materials.get("OUTLINE")
    if mat is None:
        mat = bpy.data.materials.new("OUTLINE")
        mat.use_nodes = True
        mat.use_backface_culling = True
        nt = mat.node_tree
        nt.nodes.clear()
        o = nt.nodes.new("ShaderNodeOutputMaterial")
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = srgb("#140F14")
        nt.links.new(e.outputs["Emission"], o.inputs["Surface"])
    if mat.name not in [m.name for m in ob.data.materials]:
        ob.data.materials.append(mat)
    idx = len(ob.data.materials) - 1

    sol = ob.modifiers.new("outline", "SOLIDIFY")
    sol.thickness = thickness
    sol.offset = 1.0
    sol.use_flip_normals = True
    sol.use_rim = False
    sol.material_offset = idx
    sol.material_offset_rim = idx


def classify(mat_name, parts):
    low = mat_name.lower()
    for key, spec in parts.items():
        if any(tok in low for tok in spec["match"]):
            return key
    return None


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        print("usage: ... -- <model.vrm> <girl|man> [out.blend]")
        return
    src = Path(argv[0])
    who = argv[1] if len(argv) > 1 else "girl"
    dst = argv[2] if len(argv) > 2 else f"build/paper_heart/{who}.blend"
    spec = CHARACTERS[who]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not ensure_vrm_addon():
        return
    bpy.ops.import_scene.vrm(filepath=str(src.resolve()))

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    print(f"imported {len(meshes)} meshes")
    seen = {}
    for ob in meshes:
        for slot in ob.material_slots:
            if slot.material is None:
                continue
            key = classify(slot.material.name, spec["parts"])
            print(f"  material {slot.material.name!r} -> {key}")
            if key is None:
                continue
            if key not in seen:
                p = spec["parts"][key]
                seen[key] = toon_material(f"{who}_{key}", p["base"], p["shadow"],
                                          p["light"], spec["rim"], is_eye=(key == "eyes"))
            slot.material = seen[key]
        add_outline(ob)

    # normalise scale so both characters share one world unit system
    arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if arms:
        arm = arms[0]
        h = max(v.z for o in meshes for v in
                [o.matrix_world @ c for c in [vv.co for vv in o.data.vertices[:400]]]) or 1.0
        if h > 0.1:
            k = spec["height"] / h
            arm.scale = (k, k, k)
            print(f"scaled to {spec['height']} m (factor {k:.3f})")

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(dst).resolve()))
    print(f"RESULT {who} -> {dst}  materials converted: {sorted(seen)}")


if __name__ == "__main__":
    main()
