"""Batch 6: simulation skills (Mantaflow fire/smoke, liquid, particle hair) + recipe skills for the three new scenes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import skills as S

SRC = "own-experience: fx recipes (Blender 4.5 Mantaflow / hair particles, 2026-09-19)"
NEW = []


def add(id, name, category, kind, when, triggers, body, applies=("cinematic", "3d"), recipe=None, tags=None):
    meta = {"id": id, "name": name, "category": category, "kind": kind, "status": "verified", "applies_to": list(applies), "when_to_use": when,
            "triggers": triggers, "source": [SRC], "version": 1}
    if recipe:
        meta["uses_recipe"] = recipe
    if tags:
        meta["tags"] = tags
    NEW.append((meta, body))


add("mantaflow-fire-smoke", "Real simulated fire + smoke with Mantaflow (campfire recipe)", "physics", "recipe",
    "The script has fire, a campfire, flames, smoke, embers, warmth at night, burning.",
    ["fire", "campfire", "flames", "smoke", "embers", "burning", "bonfire", "warm", "torch", "cozy"],
    """## Procedure (recipe `campfire_smoke`, cine_recipes_fx.py)
1. Domain: cube scaled (5, 5, 6.8) at (0, 4, 3.4) with a Fluid modifier `DOMAIN`, `domain_type='GAS'`, `resolution_max` 40 (draft) / 64 (standard) / 96 (final), `use_noise=False`, `beta=1.6` (buoyancy), `cache_directory` in `bpy.app.tempdir`, cache frames 1..N.
2. **The flow object must lie INSIDE the domain** (a source below the domain floor emits nothing: the first test rendered no smoke). Flow: small ellipsoid, Fluid `FLOW`, `flow_type='BOTH'`, `flow_behavior='INFLOW'`, `flow_source='MESH'`, temperature 2.4, density 1, fuel 1; `hide_render=True`.
3. Domain material: ONLY a volume material (clear the mesh's material slots first): Principled Volume, Density 6, Color `#3a3532`, Blackbody Intensity 1.4.
4. Flicker: point light `#ff8a3c` keyed every 2 frames, energy 900 x (0.75..1.25). Embers: 90 particles from an ico-sphere, instanced emissive sphere (emission 12), gravity weight -0.15.
5. `bpy.ops.fluid.bake_all()` at the end of the recipe (active object = domain). Camera 32 mm f/2.8, slow push in.
## Measured (this laptop)
Bake: res 64 x 96 frames = 44 s; res 40 draft ~20 s; render at 480x270 draft 5.7 s/frame, so a 5 s shot at 720p is ~15 min. Cache 2.8 MB.
## Pitfalls
- A domain that keeps a surface material renders as a solid slab.
- `bpy.ops.object.quick_smoke` does nothing in background mode: set the domain/flow up by hand.
""", applies=("cinematic",), recipe="campfire_smoke", tags=["mantaflow", "fire"])

add("mantaflow-liquid-splash", "Liquid splash into a pool with refraction (water recipe)", "physics", "recipe",
    "Water, drops, splashes, a pool, drinks, rain, ocean-like calm liquid.",
    ["water", "splash", "liquid", "drop", "pool", "rain", "drink", "wave", "pour", "ocean", "puddle"],
    """## Procedure (recipe `water_splash`)
1. Domain cube (4.4, 4.4, 3.0) at (0, 4, 1.5), `domain_type='LIQUID'`, `resolution_max` 40/56/80, `use_mesh=True` (the surface mesh is what renders), `time_scale=0.8` for slow motion.
2. Initial fluid = flow objects with `flow_type='LIQUID'`, `flow_behavior='GEOMETRY'`: a slab (pool, 4.2 x 4.2 x 0.9) and three spheres (drops) above it; all `hide_render=True`.
3. Material on the domain (the liquid mesh): Principled transmission 1, IOR 1.33, roughness 0.03, tint `#cfe8ff` - clear the other slots first.
4. Studio-stripe world + 2 area lights so the refraction has something to bend; camera low and to the side (lens 38, f/3.2) moving 3 m.
5. `bpy.ops.fluid.bake_all()`. Measured: draft bake + still ~51 s.
## Pitfalls
- Needs ray tracing for refraction; drops at 0.5 m in a 4.4 m domain at res 56 give ~8 cm voxels - splashes are soft; use res 80 for hero shots.
- Fewer than 2 s of simulation looks like a static pool: give the drops 1.7-2.4 m of fall.
""", applies=("cinematic",), recipe="water_splash", tags=["mantaflow", "liquid"])

add("particle-hair-fur", "Fur and hair with particle hair (fuzzy creature recipe)", "physics", "recipe",
    "Fur, fluffy animals, pets, hair, grass-like strands, soft cute characters.",
    ["fur", "fluffy", "hair", "pet", "cute", "animal", "furry", "soft", "creature", "strands", "fuzzy"],
    """## Procedure (recipe `fuzzy_creature`)
1. Emitter mesh (sphere body) + particle system `type='HAIR'`: count 1800 (draft) / 4500, `hair_length` 0.34, `child_type='INTERPOLATED'`, `child_percent` 4, `rendered_child_count` 8, `child_radius` 0.12, `clump_factor` 0.45, `roughness_1` 0.06, `root_radius` 0.012, `tip_radius` 0, `use_close_tip`, `render_type='PATH'`.
2. Names differ from older tutorials: it is `child_percent` (not `child_nbr`).
3. Fur colour = the body's Principled material (`#ffb45a`, roughness 0.55); eyes are glossy spheres; ears/feet ovals.
4. Life: squash & stretch bounce keyed every 0.25 s (scale z 0.88..1.05) + a WIND effector (strength 4, noise 1.5).
5. Camera 45 mm f/2.4 at 4.2 m.
## Pitfalls
- Hair looks like a fuzzy sphere unless the light rakes across it: use a backlight/rim; the day mood washed it out in the first test (QA agent: exposure -0.6).
""", applies=("cinematic",), recipe="fuzzy_creature", tags=["hair", "particles"])

add("simulation-cost-and-bake-rules", "Budget simulation shots: bake once, fewer voxels in draft, keep sims short", "performance", "rule",
    "Adding fluid, smoke, hair or cloth simulations to a plan.",
    ["bake", "simulation cost", "mantaflow", "fluid", "resolution", "cache", "simulation time", "fire", "liquid"],
    """## Rules
- Bake inside the recipe (build time) - each Blender process re-bakes: keep resolution at 40 for draft/QA, 64 standard, 96 final.
- Domain frames = shot frames (`cache_frame_end = STATE['frames']`); the render then plays the cache.
- Shots longer than ~6 s multiply bake time: cut sims into 4-5 s beats.
- Budget (720p standard): smoke ~3 s/frame + bake 45 s; liquid ~4 s/frame + bake 1-2 min; hair ~1.5x a plain shot.
- QA stills of sim shots take 20-50 s each because of the bake.
""", applies=("any",), tags=["simulation"])

for meta, body in NEW:
    S.write_skill(S.SKILLS_DIR / meta["category"] / f"{meta['id']}.md", meta, body)
print("authored", len(NEW), "skills")
