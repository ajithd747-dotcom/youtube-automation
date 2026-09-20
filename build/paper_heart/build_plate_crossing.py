"""S27 test plate: the wet crossing at dusk. One still, maximum quality.

    blender -b --factory-startup --python build/paper_heart/build_plate_crossing.py -- <out.png>

This is the proof-of-method frame for the photoreal-painterly pivot (scripts/paper_heart/
style_shinkai.md). If this one still looks right, the method is proven and every other plate is
repetition: render the environment ONCE per shot at a quality per-frame rendering could never
afford, then animate cel characters over it and do rain, bloom and haze in ffmpeg.

Budget here is minutes, not seconds, because there are 55 of these and not 5136.

Everything is procedural. This machine's Radeon driver crashes EEVEE on image-textured planes,
and a street is nothing but planes - so the asphalt, the windows, the foliage and the sky are
all built from noise and gradients rather than sampled from files.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

RES = (1920, 1080)
SAMPLES = 256          # one frame; spend it
TEX = Path(__file__).resolve().parent / "tex"     # CC0 surfaces from Poly Haven
MODELS = Path(__file__).resolve().parent / "models"


def hexcol(h, a=1.0):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return (f(r), f(g), f(b), a)


def rnd(seed, a=0.0, b=1.0):
    x = math.sin(seed * 127.1 + 311.7) * 43758.5453
    return a + (x - math.floor(x)) * (b - a)


# ----------------------------------------------------------------- materials

def _img(name):
    """Load a texture off disk, or None if it was never downloaded.

    Image textures were avoided across this whole pipeline because of a recorded Radeon crash;
    retesting showed that note was specific to the old Grease Pencil cel path, not to textures
    in general (build/paper_heart/test_texture_crash.py). Real surfaces are what lift an
    environment out of "procedural noise on primitives", so they are worth the risk - but the
    code still degrades to procedural if a file is missing.
    """
    for ext in ("jpg", "png"):
        f = TEX / f"{name}.{ext}"
        if f.exists():
            img = bpy.data.images.load(str(f), check_existing=True)
            return img
    return None


def _tex_surface(nt, bsdf, base, scale, nonlinear_maps=("nor_gl", "Rough")):
    """Wire Diffuse / normal / roughness for a Poly Haven set, at a given tiling scale."""
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(coord.outputs["UV"], mapping.inputs["Vector"])

    made = {}
    for slot, suffix in (("Base Color", "Diffuse"), ("Roughness", "Rough")):
        img = _img(f"{base}_{suffix}")
        if img is None:
            continue
        if suffix in nonlinear_maps:
            img.colorspace_settings.name = "Non-Color"
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        t.extension = "REPEAT"
        nt.links.new(mapping.outputs["Vector"], t.inputs["Vector"])
        nt.links.new(t.outputs["Color"], bsdf.inputs[slot])
        made[suffix] = t

    nimg = _img(f"{base}_nor_gl")
    if nimg is not None:
        nimg.colorspace_settings.name = "Non-Color"
        nt_img = nt.nodes.new("ShaderNodeTexImage")
        nt_img.image = nimg
        nt_img.extension = "REPEAT"
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = 0.8
        nt.links.new(mapping.outputs["Vector"], nt_img.inputs["Vector"])
        nt.links.new(nt_img.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return made, mapping


def m_wet_asphalt():
    """Real asphalt, selectively wetted.

    Wetness is a *modifier* on a real surface, not a surface of its own: the texture supplies
    the aggregate and the cracks, and a large-scale noise decides which parts of it are holding
    water. Driving roughness from noise alone gave a mirror with nothing in it.
    """
    m = bpy.data.materials.new("WetAsphalt")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    made, _ = _tex_surface(nt, bsdf, "asphalt_02", scale=26.0)

    # puddle mask: big soft patches, sparse
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.4
    noise.inputs["Detail"].default_value = 6.0
    pud = nt.nodes.new("ShaderNodeValToRGB")
    pud.color_ramp.elements[0].position = 0.42
    pud.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)      # dry-ish
    pud.color_ramp.elements[1].position = 0.52
    pud.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)      # standing water
    nt.links.new(noise.outputs["Fac"], pud.inputs["Fac"])

    # where there is water: roughness -> near 0 and base colour darkens
    if "Rough" in made:
        rmix = nt.nodes.new("ShaderNodeMixRGB")
        rmix.blend_type = "MIX"
        rmix.inputs[2].default_value = (0.04, 0.04, 0.04, 1.0)
        nt.links.new(pud.outputs["Color"], rmix.inputs["Fac"])
        nt.links.new(made["Rough"].outputs["Color"], rmix.inputs[1])
        nt.links.new(rmix.outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.35
    if "Diffuse" in made:
        dmix = nt.nodes.new("ShaderNodeMixRGB")
        dmix.blend_type = "MULTIPLY"
        dmix.inputs[2].default_value = (0.35, 0.36, 0.40, 1.0)
        nt.links.new(pud.outputs["Color"], dmix.inputs["Fac"])
        nt.links.new(made["Diffuse"].outputs["Color"], dmix.inputs[1])
        nt.links.new(dmix.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = hexcol("14161A")

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def m_pavement():
    m = bpy.data.materials.new("Pavement")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    made, _ = _tex_surface(nt, bsdf, "concrete_floor_worn_001", scale=14.0)
    if "Diffuse" not in made:
        bsdf.inputs["Base Color"].default_value = hexcol("3A3A3E")
    bsdf.inputs["Roughness"].default_value = 0.55 if "Rough" not in made else 1.0
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def m_flat(name, col, rough=0.75, emit=None, emit_str=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if emit is not None:
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = hexcol(emit)
        e.inputs["Strength"].default_value = emit_str
        nt.links.new(e.outputs["Emission"], out.inputs["Surface"])
        return m
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = hexcol(col)
    b.inputs["Roughness"].default_value = rough
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return m


def m_foliage():
    """Leaf mass. Not a leaf - a mass. At this focal length and depth of field the eye reads
    clustered value variation, so the material carries the variation and the geometry stays
    cheap enough to fit in 6 GB."""
    m = bpy.data.materials.new("Foliage")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    noise.inputs["Scale"].default_value = 26.0
    noise.inputs["Detail"].default_value = 10.0
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = hexcol("14301A")
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = hexcol("7FB23A")
    mid = ramp.color_ramp.elements.new(0.52)
    mid.color = hexcol("3E7A2A")
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.62
    # a little transmission so the low sun glows through the canopy edges
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.18
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


# ----------------------------------------------------------------- scene pieces

def build_road():
    bpy.ops.mesh.primitive_plane_add(size=400.0, location=(0, 0, 0))
    road = bpy.context.active_object
    road.name = "Road"
    road.data.materials.append(m_wet_asphalt())

    # Pavements either side, raised. Without a kerb there is no street - just tarmac to the
    # horizon, which is what made the first pass read as a canyon floor.
    kerb = m_pavement()
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(side * 9.5, 40.0, 0.07))
        pav = bpy.context.active_object
        pav.name = f"pavement_{side}"
        pav.scale = (7.0, 160.0, 0.14)
        pav.data.materials.append(kerb)

    # Zebra crossing spanning the carriageway, close enough to camera to read
    stripe_mat = m_flat("Stripe", "E4E0D4", rough=0.5)
    for i in range(7):
        y = 1.6 + i * 1.25
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.0, y, 0.008))
        st = bpy.context.active_object
        st.name = f"stripe_{i}"
        st.scale = (11.0, 0.55, 1.0)
        st.data.materials.append(stripe_mat)

    # centre line further down the road
    for i in range(14):
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.0, 14.0 + i * 6.0, 0.007))
        cl = bpy.context.active_object
        cl.scale = (0.14, 1.8, 1.0)
        cl.data.materials.append(stripe_mat)


def m_facade(base, scale, tint="FFFFFF"):
    """A real wall surface. Untextured blocks read as cardboard slabs no matter how they are
    lit - the facades were the single biggest thing separating this plate from the reference."""
    m = bpy.data.materials.new(f"Facade_{base}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    made, _ = _tex_surface(nt, bsdf, base, scale=scale)
    if "Diffuse" in made and tint != "FFFFFF":
        mixn = nt.nodes.new("ShaderNodeMixRGB")
        mixn.blend_type = "MULTIPLY"
        mixn.inputs["Fac"].default_value = 1.0
        mixn.inputs[2].default_value = hexcol(tint)
        nt.links.new(made["Diffuse"].outputs["Color"], mixn.inputs[1])
        nt.links.new(mixn.outputs["Color"], bsdf.inputs["Base Color"])
    if "Diffuse" not in made:
        bsdf.inputs["Base Color"].default_value = hexcol("1B1E24")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def build_city():
    """Blocks either side, receding, on real wall textures. Windows stay emissive planes -
    at this distance a lit rectangle is all the eye wants, and it keeps the geometry cheap."""
    facades = [m_facade("concrete_wall_008", 3.0, "7C8794"),
               m_facade("damaged_plaster", 2.4, "6E7480"),
               m_facade("brick_4", 4.0, "5E6470")]
    lit = m_flat("Win", "000000", emit="FFD9A0", emit_str=7.0)
    cool = m_flat("WinCool", "000000", emit="AECBE8", emit_str=4.0)

    for side in (-1, 1):
        for i in range(9):
            d = 22.0 + i * 15.0
            w = rnd(i * 3.1 + side, 5.0, 9.0)
            h = rnd(i * 7.7 + side, 7.0, 22.0)
            x = side * (15.0 + rnd(i * 2.3, 0.0, 5.0))
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, d, h / 2))
            b = bpy.context.active_object
            b.name = f"blk_{side}_{i}"
            b.scale = (w, rnd(i * 5.5, 6.0, 11.0), h)
            b.data.materials.append(facades[i % len(facades)])

            # a sparse scatter of lit windows on the face that sees camera
            for k in range(int(rnd(i * 9.1, 5, 14))):
                wy = d - rnd(k * 1.7 + i, 3.0, 5.4)
                wz = rnd(k * 4.3 + i, 2.0, h - 1.5)
                wx = x - side * (w / 2 + 0.02)
                bpy.ops.mesh.primitive_plane_add(size=1.0, location=(wx, wy, wz))
                win = bpy.context.active_object
                win.rotation_euler = Euler((0.0, math.radians(90), 0.0))
                win.scale = (rnd(k * 2.2, 0.5, 1.0), rnd(k * 6.1, 0.6, 1.3), 1.0)
                win.data.materials.append(lit if rnd(k * 8.8) > 0.35 else cool)


def append_model(stem):
    """Pull the meshes out of a downloaded CC0 .blend and park the masters out of shot.

    Returns the prototype objects; callers instance them with `inst.data = proto.data` so the
    mesh is shared. Instancing matters more than usual here: a jacaranda is heavy, and 2 GB a
    plate against 5.9 GB of RAM leaves no room to duplicate geometry.
    """
    src = MODELS / f"{stem}.blend"
    if not src.exists():
        print(f"  (missing model {stem})")
        return []
    with bpy.data.libraries.load(str(src), link=False) as (src_data, dst_data):
        dst_data.objects = list(src_data.objects)
    proto = [o for o in dst_data.objects if o is not None and o.type == "MESH"]
    for o in proto:
        o.location = (0.0, 0.0, -500.0)
        bpy.context.collection.objects.link(o)
    return proto


def place(proto, x, y, z=0.0, scale=1.0, rot_z=0.0):
    for o in proto:
        inst = o.copy()
        inst.data = o.data                      # shared mesh, not a copy
        inst.location = (o.location.x + x, o.location.y + y, z)
        inst.scale = tuple(v * scale for v in o.scale)
        inst.rotation_euler = Euler((o.rotation_euler.x, o.rotation_euler.y, rot_z))
        bpy.context.collection.objects.link(inst)


def build_trees():
    """Jacaranda along both pavements.

    The first pass used an arid olive-type tree because it was the first CC0 model to hand,
    and it read wrong immediately - the reference street is wet and temperate. Species is not
    a detail here; it is most of what the eye uses to place a location.
    """
    proto = append_model("jacaranda_tree")
    if not proto:
        return
    for i, (x, y) in enumerate([(-8.8, 16.0), (8.9, 24.0), (-9.1, 36.0),
                                (9.3, 50.0), (-9.5, 66.0)]):
        place(proto, x, y, z=0.14, scale=rnd(i * 3.3, 0.9, 1.3),
              rot_z=rnd(i * 7.1, 0.0, math.tau))


def build_streetlamps():
    """Modelled lamps, plus the emissive bulb they do not ship with."""
    proto = append_model("street_lamp_01")
    glow = m_flat("LampGlow", "000000", emit="FFC98A", emit_str=120.0)
    for i, (x, y) in enumerate([(-9.7, 12.0), (9.8, 28.0), (-9.9, 44.0), (10.0, 62.0)]):
        if proto:
            place(proto, x, y, z=0.14, scale=1.0,
                  rot_z=math.pi if x > 0 else 0.0)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.13,
                                             location=(x + (0.9 if x < 0 else -0.9), y, 4.9))
        b = bpy.context.active_object
        b.scale = (1.0, 1.0, 0.55)
        b.data.materials.append(glow)


def build_street_furniture():
    """Poles with overhead wires, and manhole covers in the road.

    Wires cut across a sky and give the frame something to read depth against - they are a
    signature of this style, and the cheapest detail here by far.
    """
    poles = append_model("modular_electricity_poles")
    if poles:
        for i, (x, y) in enumerate([(-10.4, 20.0), (-10.4, 48.0), (-10.4, 76.0),
                                    (10.5, 34.0), (10.5, 62.0)]):
            place(poles, x, y, z=0.14, scale=1.0, rot_z=math.pi if x > 0 else 0.0)

    covers = append_model("water_manhole_cover")
    if covers:
        for i, (x, y) in enumerate([(-2.4, 9.0), (3.1, 21.0), (-1.2, 40.0)]):
            place(covers, x, y, z=0.005, scale=1.0, rot_z=rnd(i * 4.4, 0.0, math.tau))


def build_sky_and_sun():
    w = bpy.data.worlds.new("Dusk")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(2.6)
    sky.sun_rotation = math.radians(0.0)        # straight down the street, into camera
    sky.sun_intensity = 0.35
    sky.altitude = 80
    sky.air_density = 2.4
    sky.dust_density = 3.0                      # haze is most of the aerial perspective
    sky.ozone_density = 1.4
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bg.inputs["Strength"].default_value = 0.9

    sd = bpy.data.lights.new("Sun", "SUN")
    sd.energy = 4.2
    sd.color = hexcol("FFD2A0")[:3]
    sd.angle = math.radians(2.0)
    sun = bpy.data.objects.new("Sun", sd)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = Euler((math.radians(87.4), 0.0, 0.0))


def build_haze_volume():
    """God rays and depth, in a box.

    A world volume renders black on this GPU - a known failure from the earlier project - so
    the atmosphere is a bounded cube around the street instead.
    """
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 55, 16))
    v = bpy.context.active_object
    v.name = "Haze"
    v.scale = (80.0, 140.0, 34.0)
    m = bpy.data.materials.new("HazeVol")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumeScatter")
    vol.inputs["Color"].default_value = hexcol("FFE0C0")
    vol.inputs["Density"].default_value = 0.0024
    vol.inputs["Anisotropy"].default_value = 0.55      # forward scatter = shafts
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    v.data.materials.append(m)


def build_camera():
    cd = bpy.data.cameras.new("Cam")
    cd.lens = 34.0
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = 2.8                        # soft, but the street must stay legible
    cam = bpy.data.objects.new("Cam", cd)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.location = (0.0, -11.5, 1.68)          # standing eye height
    cam.rotation_euler = Euler((math.radians(84.5), 0.0, 0.0))

    focus = bpy.data.objects.new("Focus", None)
    bpy.context.collection.objects.link(focus)
    focus.location = (0.0, 7.0, 0.8)                   # the crossing itself
    cd.dof.focus_object = focus


def setup(out_png):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = SAMPLES
    for attr, val in (("use_gtao", True), ("gtao_distance", 0.6),
                      ("use_bloom", False), ("use_motion_blur", False)):
        if hasattr(sc.eevee, attr):
            setattr(sc.eevee, attr, val)
    # reflections are the point of a wet street; this is the expensive switch and it earns it
    if hasattr(sc.eevee, "use_raytracing"):
        sc.eevee.use_raytracing = True
    if hasattr(sc.eevee, "use_volumetric_shadows"):
        sc.eevee.use_volumetric_shadows = True

    # Standard, not Filmic: the reference lets its highlights clip, and Filmic exists to stop
    # exactly that. The blown windows and blown sky are the look, not a mistake.
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = -0.2

    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = str(Path(out_png).resolve())


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_png = argv[0] if argv else "renders/paper_heart/plates/S27_crossing.png"
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    build_sky_and_sun()
    build_road()
    build_city()
    build_trees()
    build_streetlamps()
    build_street_furniture()
    build_haze_volume()
    build_camera()
    setup(out_png)
    bpy.ops.wm.save_as_mainfile(
        filepath=str(Path("build/paper_heart/plate_crossing.blend").resolve()))
    print(f"RESULT plate scene built -> {out_png}", flush=True)


if __name__ == "__main__":
    main()
