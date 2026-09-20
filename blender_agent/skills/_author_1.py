"""Authors batch 1 of the skill library: physics, effects, lighting, materials (all verified by the ada_chain_reaction render
and/or a headless test in skills/tests). Re-running overwrites these files, so edit here or in the .md files, not both."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import skills as S

SRC = "own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)"
SKILLS = []


def add(id, name, category, kind, when, triggers, body, applies=("cinematic", "3d"), recipe=None, test=None, exemplar=None,
        avoid=None, tags=None, source=None):
    meta = {"id": id, "name": name, "category": category, "kind": kind, "status": "verified", "applies_to": list(applies),
            "when_to_use": when, "triggers": triggers}
    if avoid:
        meta["avoid_when"] = avoid
    if recipe:
        meta["uses_recipe"] = recipe
    if test:
        meta["test"] = f"tests/{test}.py"
    if exemplar:
        meta["exemplar"] = f"exemplars/{exemplar}.mp4"
    if tags:
        meta["tags"] = tags
    meta["source"] = source or [SRC]
    meta["version"] = 1
    SKILLS.append((meta, body))


# ============================================================================= PHYSICS
add("rigid-body-render-prestep", "Make rigid-body physics actually play in a headless render", "physics", "pitfall",
    "Any shot with rigid bodies (falling, colliding, toppling, piling objects) rendered with `bpy.ops.render.render(animation=True)` in background mode.",
    ["rigid body", "physics", "falling", "collide", "topple", "domino", "crash", "pile", "bounce", "drop", "collapse", "gravity"],
    """## What it achieves
Rigid-body objects really move in the rendered video instead of hanging frozen (the ball rolls but nothing it hits ever reacts).

## Procedure
1. Build the scene, add the rigid body world (`C.rigid_world()`), objects (`C.rigid(...)`), keyframes.
2. BEFORE rendering, step every frame once in order, then rewind:
   `for f in range(sc.frame_start, sc.frame_end + 1): sc.frame_set(f)` then `sc.frame_set(sc.frame_start)`.
3. Render the animation as usual: the render reads the physics cache that step 2 filled.
4. For a single still at time t you must also step frames 1..t in order (`frame_set` straight to t shows the initial pose).

## Pitfalls
- Rigid-body simulation only runs in the *active* (viewport) depsgraph; the render depsgraph replays a cache. Without step 2 nothing simulates. Cloth and particle systems were observed to render correctly without it; rigid bodies and soft bodies stayed frozen (jellies hovered in the first jelly render).
- Reading `matrix_world` inside a `render_pre` handler did not show the simulated pose in my tests: judge by the rendered frames.
- This cost me one full re-render of 4 shots (~40 min) - the pre-step costs about 2 s.

## Code
```python
sc = bpy.context.scene
for f in range(sc.frame_start, sc.frame_end + 1):
    sc.frame_set(f)          # fills the rigid-body point cache
sc.frame_set(sc.frame_start)
bpy.ops.render.render(animation=True)
```
""", test="rigid_prestep", tags=["headless", "cache"])

add("rigid-body-launch-release", "Launch a rigid ball with a keyframed approach, then release it to physics", "physics", "technique",
    "A ball, wrecking ball, bowling ball or projectile must hit dynamic objects at a controlled time and speed.",
    ["ball", "hits", "launch", "roll", "throw", "wrecking", "projectile", "knocks", "smash", "push"],
    """## What it achieves
A hand-authored, art-directed hit: the ball arrives exactly when the script says and carries real momentum into the collision.

## Procedure
1. Make the ball an ACTIVE rigid body (`C.rigid(ball, "ACTIVE", mass=..., shape="SPHERE")`).
2. Keyframe its location with **LINEAR** interpolation at constant speed: start hold, then a straight run that continues *past* the contact point.
3. Animate the `rigid_body.kinematic` flag: True until just before contact, then False (`C.release_at(ball, t_contact - 0.12)`).
4. Physics inherits the velocity from the last keyframed motion, so the ball keeps going into the target.

## Parameters that worked
- Steel ball: radius 0.75, mass 60 kg, friction 0.3, ~6.7 m/s (7.6 m in 1.1 s), released 0.12 s before contact.
- Domino trigger ball: radius 0.42, mass 3, released 0.05 s before contact.

## Pitfalls
- BEZIER (ease-out) on the last approach key leaves ~0 velocity at release: the ball stops short and the wall never collapses (this happened in the first crate render).
- Release after the keyframed motion has ended, not on the last key.
- The keyframed end position must lie beyond the target so the velocity estimate is not zero.

## Code
```python
key(ball, 1, loc=start, interp="LINEAR")
key(ball, frame(t0), loc=start, interp="LINEAR")
v = (x_contact - start[0]) / (t_contact - t0)
key(ball, frame(t_contact + 0.3), loc=(start[0] + v * (t_contact + 0.3 - t0), y, z), interp="LINEAR")
C.release_at(ball, t_contact - 0.12)
```
""", test="rigid_launch_release", tags=["kinematic", "velocity"])

add("domino-chain-reaction", "Colourful domino chain reaction with a trailing camera", "physics", "recipe",
    "The script talks about a chain reaction, one small push causing a cascade, momentum, cause and effect, or a row of things falling one after another.",
    ["domino", "chain reaction", "one small push", "cascade", "topples", "one after another", "momentum", "ripple effect", "domino effect"],
    """## What it achieves
A winding row of pastel dominoes toppling in a wave (rigid body), lit by a low sun, with the camera following the fall front.

## Procedure
1. Use recipe `domino_run` (mood `sunset` or `day`, dark floor `#3b414f`, fog <= 0.15).
2. Dominoes: cube scale (0.12, 0.5, 1.0), spacing 0.58 m along an S-curve `y = 1.6 sin(0.42 x)`, hue ramp 0-0.85 across the row, each rotated to the path tangent.
3. Physics: mass 0.25, friction 0.55, bounce 0.05, collision margin 0.0005, world substeps 20, solver iterations 30, time_scale 1.0.
4. Trigger with a red glossy ball (see rigid-body-launch-release) hitting domino 0 at t = 0.9 s.
5. Camera trails the wave: target empty copies a keyed lead empty that reaches the last domino at `1.2 + 0.17 * n` seconds.
6. Pre-step frames before rendering (see rigid-body-render-prestep).

## Parameters that worked (measured)
- The wave travels one domino per ~0.17 s; first domino falls at ~1.7 s. 26 dominoes finish at ~5.7 s, so 26 fits a 7-8 s narration; 34 needs ~9 s.
- Lens 42 mm, f/2.2, camera 5 m from the row at z 1.2-1.7.

## Pitfalls
- White/cream floor + day sun + fog = washed-out, unreadable dominoes; use a dark floor and backlight.
- If the camera schedule is shorter than the fall time the camera ends before the wave does: schedule = measured wave time.
""", applies=("cinematic",), recipe="domino_run", exemplar="domino_run", tags=["rigid body", "recipe"])

add("wall-smash-destruction", "Steel ball smashes a wall of crates in slow motion", "physics", "recipe",
    "A climax, impact, crash, collapse, demolition, or 'everything comes crashing down' moment.",
    ["smash", "crash", "crashing down", "destroy", "collapse", "wall", "demolish", "impact", "knock down", "tower", "break"],
    """## What it achieves
A 5x7 wall of wooden crates is hit by a heavy steel ball; crates tumble and scatter, camera shakes on impact.

## Procedure
1. Recipe `crate_smash`, mood `sunset` (warm backlight reads best; `night` is too dark).
2. Crates 0.6 m cubes with bevel 0.03, wood PBR (`#a9743f`, roughness 0.65), mass 0.8, friction 0.6, bounce 0.05, margin 0.001; world substeps 15, iterations 25, time_scale 0.75 (slow motion).
3. Ball: 1.5 m diameter chrome (metallic 1, roughness 0.12), 60 kg, launched with constant speed (see rigid-body-launch-release), contact at ~1.5 s.
4. Camera: slow dolly right (-2 -> +3.5 m), lens 36 mm, f/2.4, plus decaying shake `a = 0.18 * exp(-k/6)` over 0.7 s from the impact frame.
5. Pre-step the physics before rendering.

## Pitfalls
- Everything stayed frozen in the first render (no pre-step); see rigid-body-render-prestep.
- Spot light from above (14000 W, 55 deg) gives crisp shadows on the debris; without it the pile is muddy.
- Keep the impact >= 1 s after the start so viewers see the setup, and >= 2.5 s before the end so the scatter can settle.
""", applies=("cinematic",), recipe="crate_smash", exemplar="crate_smash", tags=["rigid body", "recipe", "slow motion"])

add("cloth-flag-wind", "Flag / banner rippling in the wind (cloth simulation)", "physics", "recipe",
    "Flags, banners, curtains, capes, sails, or anything cloth-like moved by wind: victory, pride, unfurling.",
    ["flag", "banner", "wind", "cloth", "fabric", "unfurl", "ripple", "flutter", "victory", "pride", "curtain", "sail"],
    """## What it achieves
A striped banner pinned to a pole flaps naturally: waves travel along it, the free edge droops and lifts.

## Procedure
1. Recipe `cloth_banner` (mood `day`, fog 0.2).
2. Grid plane 46x26 subdivisions, size 5x3 m; rotate to stand in the XZ plane, then **apply the transform**.
3. Vertex group `pin` with weight 1 on the left edge only (`x < x_min + 0.02`); `cloth.settings.vertex_group_mass = "pin"`.
4. Settings: quality 8, mass 0.15, air_damping 2.5, gravity (0, 0, -3) (lighter than real cloth so it flies), tension = compression stiffness 25, bending 1.2, self-collision off.
5. Wind: `bpy.ops.object.effector_add(type="WIND", rotation=(-pi/2, 0, radians(-70)))` -> blows mostly along +X (along the banner) with a 34% push into it; strength keys 0 -> 260 (0.6 s) -> 420 (mid) -> 300, noise 1.2.
6. Add a Subsurf (level 1) after the Cloth modifier. Wave texture (BANDS, direction **Z**, scale 2.2) -> constant ColorRamp gives the stripes.

## Pitfalls
- An empty has no force field: use `bpy.ops.object.effector_add`; `empty.field` is None otherwise.
- The wind vector is the effector's local **Z** axis. Wind perpendicular to the cloth only inflates it into a sail (y range 4 m, x shrinks to the pole); wind purely along the cloth stretches it flat. 70 deg between them ripples.
- Strength 650+ with mass 0.25 crumples the cloth to the pole; 90-170 with real gravity leaves it hanging like a curtain.
- Stripes direction depends on the plane orientation; on an XZ banner use bands along Z (Y bands give a solid colour).
""", applies=("cinematic",), recipe="cloth_banner", test="cloth_wind", exemplar="cloth_banner", tags=["cloth", "wind", "recipe"])

add("soft-body-jelly", "Wobbling translucent jelly (soft body)", "physics", "technique",
    "Jelly, gel, rubber, squishy or bouncy blobs that deform on impact.",
    ["jelly", "wobble", "squishy", "rubber", "gel", "bouncy", "soft", "blob", "jiggle"],
    """## What it achieves
An ico-sphere squashes on landing and wobbles back, with a glassy jelly material.

## Procedure
1. `primitive_ico_sphere_add(subdivisions=3, radius=0.75)` (642 verts: enough to deform smoothly; more is slow).
2. Add a SOFT_BODY modifier: mass 1, friction 0.6, `use_goal=False`, `use_edges=True`, pull 0.35, push 0.35, bend 0.6, damping 0.35, self-collision off.
3. The floor needs a **Collision** modifier (in addition to any rigid-body passive setting) or the jelly falls through.
4. Set the soft-body point cache range to the shot length.
5. Material: Principled, transmission 0.85, IOR 1.35, roughness 0.12, small emission 0.6 in the same hue.

## Pitfalls
- Soft bodies do not collide with each other unless self-collision/collision modifiers are set up; keep them apart.
- Extreme deformation from a drop above ~6 m: drop from 2-4 m.
""", applies=("cinematic",), test="soft_body_jelly", tags=["soft body"])

add("jelly-ball-pit-party", "Jelly blobs and a rain of colourful balls under neon light", "physics", "recipe",
    "Fun, play, party, bounce, energy, colourful chaos, celebration of motion.",
    ["party", "bounce", "jelly", "balls", "colourful", "colorful", "playful", "energy", "fun", "wobbling", "bouncing"],
    """## What it achieves
5 soft-body jellies and 34 rigid balls (radius 0.28-0.5) fall into a pile on a mirror floor lit by magenta/cyan light.

## Procedure
1. Recipe `jelly_pit`, mood `neon` (uses the stripe world, see studio-softbox-stripe-world).
2. Balls: rigid sphere, mass = 2r, friction 0.5, restitution 0.5, spawned at z = 5 + 0.55 i so they rain in sequence; rigid world substeps 10, iterations 20; floor passive with restitution 0.35.
3. Camera 34 mm, f/2.4 from (-6.5, -9, 3) to (6, -9.5, 2.2) looking at (0, 1.5, 1).
4. Pre-step frames (rigid-body-render-prestep) - otherwise the balls never appear.

## Pitfalls
- The neon stripe world is very bright behind the pile: expect a blurry busy backdrop at f/2.4; use f/4+ if the background competes with the action.
""", applies=("cinematic",), recipe="jelly_pit", exemplar="jelly_pit", tags=["recipe", "soft body", "rigid body"])

add("force-fields-wind-turbulence", "Wind / turbulence force fields need the effector operator", "physics", "pitfall",
    "Any simulation (cloth, particles, smoke) that should be pushed by wind, gusts or turbulence.",
    ["wind", "gust", "turbulence", "breeze", "blow", "force field", "swirl", "air"],
    """## Procedure
1. Create with `bpy.ops.object.effector_add(type="WIND"|"TURBULENCE"|"VORTEX", location=..., rotation=...)`, then use `bpy.context.active_object.field`.
2. Animate `field.strength` with `field.keyframe_insert("strength", frame=...)` for gusts (ramp in over ~0.6 s).
3. Direction of a WIND field is its local +Z axis: choose the rotation so Z points where the air should go.

## Pitfalls
- `L.empty(...)` objects have `field = None`; setting `.field.type` raises AttributeError.
- Wind acts on cloth/particles/soft bodies, not on rigid bodies unless their effector weights allow it.
""", tags=["effector"])

# ============================================================================= EFFECTS
add("particle-burst-fireworks", "Fireworks: instanced spark bursts with light flashes and bloom", "effects", "recipe",
    "Fireworks, sparks, explosions of light, celebration at night, a magical finale.",
    ["fireworks", "sparks", "burst", "night sky", "celebrate", "explosion", "sparkle", "finale", "magic"],
    """## What it achieves
Several coloured spherical bursts over a dark reflective lake; each burst also flashes a light that illuminates water and fog.

## Procedure
1. Recipe `fireworks`, mood `night`, fog 0.5, mirror floor (`#050810`, roughness 0.03, metallic 0.9).
2. Per burst: hidden spark source (small emissive sphere, emission 14, `hide_render=True`) + emitter icosphere (subdivisions 3, 642 verts) at (x -8..8, y 16-24, z 9-13).
3. Particle settings: count 520, `frame_start = burst frame`, `frame_end = +1` (single-frame emission), lifetime 55 (+-40%), `emit_from="VERT"`, `normal_factor` 9, `factor_random` 1.4, gravity weight 0.25, `render_type="OBJECT"`, `instance_object = spark`, size 1 (+-50%).
4. Hide the emitter with `emitter.show_instancer_for_render = False`.
5. Flash: POINT light energy keyed 0 -> 60000 W at the burst frame -> 0 after 0.35 s.
6. Camera far back: lens 24, f/5, from (0, -10, 1.5) rising to z 2.6, looking at (0, 20, 8).
7. Compositor Glare (bloom) threshold ~1.6 makes the sparks glow.

## Pitfalls
- `ParticleSettings.use_render_emitter` no longer exists in Blender 4.5: use the object property `show_instancer_for_render`.
- 250000 W flashes wash the whole frame purple; 60000 W is enough.
- Stagger bursts across the shot: `t = 0.3 + i * (T - 1.5) / n`, hue steps of 0.19.
""", applies=("cinematic",), recipe="fireworks", test="particle_burst", exemplar="fireworks", tags=["particles", "recipe"])

add("confetti-rain-particles", "Confetti rain with turbulence and a glowing title finale", "effects", "recipe",
    "An ending, thanks, celebration, call to action (like/subscribe), success moment.",
    ["thanks", "subscribe", "like", "celebration", "confetti", "ending", "outro", "congratulations", "cheers", "hooray"],
    """## What it achieves
Robot cheers under a glowing 3D title while coloured chips rain down.

## Procedure
1. Recipe `finale_confetti`, mood `night`.
2. Five hidden chip meshes (cube 0.3 x 0.02 x 0.19, emissive 0.6, one hue each). One plane emitter (10 x 6 m) at z 9.5 with 5 particle systems, each: count 150, `frame_start 1`, `frame_end T-1 s`, lifetime 140, `normal_factor -0.8`, random 0.8, gravity weight 0.06 (floaty), rotations on with random angular velocity 6.
3. `bpy.ops.object.effector_add(type="TURBULENCE")` strength 3, size 1.5 above the scene so the chips flutter.
4. Colored rim lights (magenta and cyan area lights) + a top spot make the robot readable in the dark.
5. Title `title_3d(..., loc=(0, 2, 4.5))`; camera pulls back (10.5 -> 8.6 m) with the robot centred at z ~2.

## Pitfalls
- Chips smaller than ~0.15 m vanish at 720p; 0.3 m reads as confetti.
- Title placed at z 3.6 collided with the raised arms; 4.5 clears them.
""", applies=("cinematic",), recipe="finale_confetti", exemplar="finale_confetti", tags=["particles", "recipe"])

add("compositor-glare-bloom", "Bloom / glow via the compositor Glare node (and its NaN trap)", "effects", "technique",
    "Anything that should glow: neon, lamps, sparks, magic, emissive text, sun highlights.",
    ["glow", "bloom", "neon", "glowing", "light", "shine", "halo", "radiant", "lamp"],
    """## Procedure
1. `scene.use_nodes = True`; Render Layers -> Glare -> Composite. Glare type `BLOOM` (fallback `FOG_GLOW`), quality MEDIUM.
2. Threshold ~1.6 (only genuinely bright pixels), size 7, strength 0.7 (set via the node input `Strength`).
3. Make the glowing objects emissive with strength 2-14 in the shader; sparks 14, title text 0.5-1.6, eyes/chest glow 6.
4. Set EEVEE `clamp_surface_direct = 30`, `clamp_surface_indirect = 8`.

## Cost
Bloom is cheap (~0.3 s/frame at 720p on this laptop).

## Pitfalls
- A sun disc reflected in a glossy floor is astronomically bright: bloom turned it into a checkerboard of artefact squares (probably inf/NaN pixels). Clamping direct/indirect light (step 4) and keeping the sun energy at 2-3.5 removed them.
- Threshold 0.9 blooms the whole bright sky and hazes the picture.
""", tags=["compositor"])

add("film-finish-ffmpeg", "Film look in the final mux: vignette, grade, dip to black (not in the compositor)", "effects", "technique",
    "Every finished shot in cinematic mode; whenever a vignette, colour grade or fade is wanted.",
    ["vignette", "cinematic look", "grade", "fade", "film look", "dip to black", "polish"],
    """## Procedure
Apply in the per-segment ffmpeg mux, together with captions:
`vignette=PI/5,eq=contrast=1.06:saturation=1.12,fade=t=in:st=0:d=0.18,fade=t=out:st=<dur-0.18>:d=0.18,subtitles=...`

## Why
A compositor vignette (Ellipse mask + Blur size 260) cost ~2.5-3 s **per frame** on this 2-core CPU - it doubled the render time. ffmpeg does the same in milliseconds.

## Pitfalls
- Put the fades before `subtitles` in the filter chain so the captions stay solid while the picture dips to black.
- Bloom is fine in the compositor (cheap); blur-based nodes are not.
""", applies=("any",), tags=["performance", "ffmpeg"])

# ============================================================================= LIGHTING / MATERIALS
add("backlit-sunset-mood", "Warm backlit sunset with rim light and long shadows", "lighting", "technique",
    "Golden hour, sunrise/sunset, dramatic warm light, a hopeful or epic tone.",
    ["sunset", "golden hour", "sunrise", "warm light", "dusk", "backlit", "dramatic", "epic", "silhouette"],
    """## Procedure
1. Sky texture (MULTIPLE_SCATTERING), `sun_elevation = 7 deg`, `sun_rotation = 28 deg` so the sun is **behind** the subjects (camera looks toward +Y, sun at +Y).
2. Sun light: energy 2.2, colour `#ff9a55`, angle 1.2 deg; aligned to the sky sun direction.
3. Fill: AREA light 500 W, size 6, `#ffd2a8` from the camera side at (-4, -9, 4) so backlit faces keep detail.
4. **Exposure -1.5** (`view_settings.exposure`), AgX "Medium High Contrast" look.
5. Dark floor, low fog (<= 0.15) - a bright floor and haze turn the shot to milk.

## Pitfalls
- With the sun in front of the camera (rotation 150-210 deg) shadows fall behind objects and the image looks flat.
- Exposure 0 with a sunset sky clips the horizon to white; -0.9 was still washed out with fog 0.5; -1.5 with fog <= 0.2 worked.
- Reflected sun in glossy floors needs clamping (see compositor-glare-bloom).
""", tags=["mood"])

add("studio-softbox-stripe-world", "Studio / neon environment with procedural softbox stripes", "lighting", "technique",
    "Glass, gold, chrome, mirror floors or product shots in an empty dark world; neon club looks.",
    ["glass", "chrome", "gold", "metal", "reflection", "mirror", "product", "showcase", "studio", "shiny", "neon", "refraction"],
    """## What it achieves
Reflective and refractive objects finally look like glass/metal because they reflect a structured bright environment.

## Procedure
1. World shader: base dark colour + 2 Wave textures (BANDS, X and Y directions, scale 5 and 3) from Generated coordinates -> ColorRamp (0 at 0.86, colour x gain 3-5 at 0.95) -> ADD-mixed onto the base. Studio stripes white/cool-white; neon stripes magenta `#ff2fb3` / cyan `#22d3ff`.
2. Floor: roughness 0.05, metallic 0.4 (mirror-like) so objects double in the floor.
3. Materials: glass transmission 1.0, IOR 1.5, roughness 0.02; gold metallic 1, roughness 0.15, `#d4af37`; chrome `#e8e8ee` metallic 1 roughness 0.02.
4. Lights: 3 area lights (900 W white key, 350 W cool fill, 600 W warm back).

## Pitfalls
- A black world makes chrome black. Emissive panels placed off-screen do **not** appear in EEVEE Next reflections (screen-space tracing + world probe only), the stripes must live in the *world*.
- Hard black/white stripes read as "test pattern" on glass; keep gains moderate and add a glowing crystal for colour.
""", test="studio_world_stripes", exemplar="glass_showcase", tags=["reflections", "world"])

add("volumetric-fog-box", "Haze and light shafts using a bounded volume box", "lighting", "technique",
    "Atmosphere: fog, haze, dusty air, god rays, spotlight beams in a workshop or night scene.",
    ["fog", "haze", "light shaft", "god rays", "beam", "dusty", "atmosphere", "mist", "spotlight", "smoke-filled"],
    """## Procedure
1. Add a large cube (e.g. centre (0, 8, 6), size 46 x 46 x 12), display WIRE, `visible_shadow = False`.
2. Material: Volume output <- Principled Volume, density 0.004-0.012 (`0.01 * fog`), anisotropy 0.3.
3. `scene.eevee.volumetric_end = 70`; quality presets: tile size 8 (draft) / 4 (standard) / 2 (final), 48 samples.
4. A SPOT light (9000-16000 W, 40-55 deg) aimed through the box makes visible cones.

## Pitfalls
- A **world** volume rendered pure black on this iGPU under EEVEE Next. Use the box.
- Density > 0.012 over 46 m washes the frame out; the intro shot looked like milk at 0.8*0.01 with a bright sky.
- Fog adds only a small per-frame cost, but its look differs between draft and final quality: judge it in a still at the target quality.
""", test="fog_box", tags=["volumetrics"])

add("neon-club-lighting", "Neon magenta/cyan club look", "lighting", "technique",
    "Party, nightlife, cyberpunk, futuristic or energetic scenes.",
    ["neon", "club", "cyberpunk", "party", "futuristic", "disco", "night", "electric"],
    """## Procedure
Mood `neon`: near-black world `#04030a`, stripe world (magenta/cyan), area lights magenta 500 W at (-6,-6,5), cyan 500 W at (7,-4,4), violet 300 W behind; exposure +0.3; mirror floor; bloom on. Title text white with pink emission.

## Pitfalls
- Everything saturates to pink/blue: keep the subject's base colour light grey/white so it takes both hues.
""", tags=["mood"])

add("exposure-and-haze-control", "Avoid washed-out shots: exposure per mood, haze budget, contrast check", "lighting", "rule",
    "Any shot that looks hazy, milky, low-contrast or overexposed; choosing exposure/fog for a mood.",
    ["hazy", "washed out", "milky", "low contrast", "overexposed", "too bright", "flat", "foggy"],
    """## Rules (measured on the ada_chain_reaction render)
- Exposure by mood: sunset -1.5, day -0.5, studio 0, night +0.4, neon +0.3.
- Fog budget: night/workshop up to 0.7, sunset <= 0.2, day <= 0.2. Fog + bright sky + bright floor = milk.
- Floors: dark (`#3b414f`) under bright skies; pale floors only in dark moods.
- QA: render a still; mean luminance should sit around 0.15-0.55 with a max above 0.85 (highlights) and min below 0.05 (blacks). A flat histogram means too much haze.

## Pitfalls
- The intro (sunset + fog 0.5) and the banner (day + fog 0.2, white sky) shots were hazy in the first video: lower fog and darken the ground.
""", applies=("any",), tags=["qa"])

add("pbr-glass-gold-chrome", "PBR material recipes: glass, gold, chrome, coated paint, emissive", "materials", "technique",
    "Any 3D object that should look real: glass, gold, chrome, painted plastic, glowing parts.",
    ["glass", "gold", "chrome", "metal", "paint", "plastic", "glossy", "material", "emissive", "crystal"],
    """## Parameters (Principled BSDF)
- Glass: base white, transmission weight 1.0, IOR 1.5, roughness 0.02 (needs ray tracing + a bright environment).
- Gold: `#d4af37`, metallic 1, roughness 0.15-0.18.
- Chrome: `#e8e8ee`, metallic 1, roughness 0.02-0.12.
- Glossy paint: base colour, coat weight 0.5-1.0 (red ball, dominoes).
- Wood crate: `#a9743f`, roughness 0.65.
- Jelly: transmission 0.85, IOR 1.35, roughness 0.12.
- Emission: set `Emission Color` and `Emission Strength` (2-14).

## Pitfalls
- Input names in 4.x: "Transmission Weight", "Coat Weight", "Emission Strength" (older names raise KeyError).
- Enable EEVEE ray tracing for refraction (`use_raytracing`, resolution scale 2, max roughness 0.5).
""", tags=["materials"])

for meta, body in SKILLS:
    S.write_skill(S.SKILLS_DIR / meta["category"] / f"{meta['id']}.md", meta, body)
print("authored", len(SKILLS), "skills")
