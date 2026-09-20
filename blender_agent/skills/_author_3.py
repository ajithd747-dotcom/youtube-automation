"""Authors batch 3: character, motion, camera, composition, pacing, workflow and performance skills from my own work on the
ada_chain_reaction video (verified by that render and/or a headless test in skills/tests)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import skills as S

SRC = "own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)"
SKILLS = []


def add(id, name, category, kind, when, triggers, body, applies=("cinematic", "3d"), recipe=None, test=None, exemplar=None, tags=None):
    meta = {"id": id, "name": name, "category": category, "kind": kind, "status": "verified", "applies_to": list(applies),
            "when_to_use": when, "triggers": triggers}
    if recipe:
        meta["uses_recipe"] = recipe
    if test:
        meta["test"] = f"tests/{test}.py"
    if exemplar:
        meta["exemplar"] = f"exemplars/{exemplar}.mp4"
    if tags:
        meta["tags"] = tags
    meta["source"] = [SRC]
    meta["version"] = 1
    SKILLS.append((meta, body))


# ============================================================================= CHARACTER / MOTION
add("robot-character-rig", "3D robot character rigged from empties, greeting / celebrating on a glossy floor", "character", "recipe",
    "The narration introduces a character, greets the viewer, or celebrates; a friendly 3D mascot is needed.",
    ["meet", "introduce", "hello", "welcome", "robot", "mascot", "character", "hero", "greeting", "wave", "cheer"],
    """## What it achieves
A 1.8 m stylised robot (white coated body, dark joints, glowing eyes/chest/antenna) that can wave, walk, celebrate and think - no armature needed.

## Procedure
1. `root, j = C.build_robot(loc, color="#e8edf5", accent="#22d3ff", scale=1.0)` builds a hierarchy of empties (pelvis, torso, neck, head, l/r shoulder, elbow, hip, knee); meshes are parented to the joints.
2. `C.animate_robot(j, action)` keys the joint rotations every 2 frames from the shared pose functions (`idle walk run wave jump celebrate think point talk sad`) plus pelvis bob.
3. Frontal view (facing the camera at -Y): plane="front" (swing about local Y). Profile view (walking sideways): rotate `root` +90 deg about Z (faces +X) and use plane="side" (swing about local X).
4. Camera for a standing shot: 30-32 mm, distance 9-10.5 m, target z 1.7-2.0 so the head, raised arm and a title above all fit.
5. Recipe `robot_intro` adds a gold ring and a glass sphere either side and a floating title.

## Pitfalls
- Title at z 3.3 collided with the head/antenna; use z >= 3.9 (4.5 when arms are raised).
- Change of accent colour (`accent="#ff4fd8"`) recolours the glow parts only - keep the body colour constant across shots for consistency.
""", applies=("cinematic", "3d"), recipe="robot_intro", exemplar="robot_intro", test="camera_framing", tags=["rig", "recipe"])

add("walk-cycle-profile", "Walk cycle in profile with a tracking camera (workshop walk)", "motion", "recipe",
    "A character travels from A to B: walking to work, journey, morning routine.",
    ["walk", "walks", "walking", "journey", "travel", "morning", "workshop", "route", "goes", "heads to", "commute"],
    """## What it achieves
A readable walk in profile: legs scissor forward/back with knee bend on the trailing leg, arms counter-swing, torso leans slightly, pelvis bobs.

## Procedure
1. Recipe `workshop_walk` (mood `studio`, fog 0.7): dark wall, shelves with glowing orbs, crates, a warm SPOT lamp (9000 W, 50 deg) casting a visible cone.
2. Pose numbers (from `_pose`): hip swing +-30 deg (run 50), knee bend 35 deg (run 70) only on the trailing leg (`max(0, sin(w t + 0.6))`), arm swing 0.9 x hip swing, elbows -25/+25 deg, torso -4 deg (run -14), bob 0.012 x |sin|, w = 6 rad/s (walk) / 9.5 (run).
3. Face +X: `root.rotation_euler = (0, 0, +pi/2)`; use `animate_robot(..., plane="side")`; travel with root keyframes LINEAR from `walk_from` to `walk_to` over the shot duration.
4. Camera 34 mm at distance ~9.5 m (x from -2.5 to +1.5), height 1.5-1.6, target follows the robot (z ~1.05), f/2.6.

## Pitfalls
- Robot facing -X walks backwards: +90 deg about Z faces +X, -90 deg faces -X.
- Camera at 6.2 m with 40 mm cropped the head; 9.5 m / 34 mm framed the full body (see camera-framing-safe-area).
- Frontal-plane swing on a robot in profile makes the legs scissor toward the camera - always use the side plane.
""", recipe="workshop_walk", test="robot_walk_profile", exemplar="workshop_walk", tags=["walk", "recipe"])

add("character-action-vocabulary", "Pick the character action from the meaning of the line", "character", "rule",
    "Choosing which animation cycle a character performs for a script segment.",
    ["action", "gesture", "animation choice", "wave", "think", "point", "celebrate", "sad", "jump", "talk", "run"],
    """## Rules
| narration says | action | why |
|---|---|---|
| hello, meet, welcome, greeting | `wave` | raised right arm, elbow oscillates 9 rad/s |
| wonder, idea, decide, hmm, question | `think` | hand to chin, small head tilt |
| look, notice, see, this one | `point` | arm horizontal |
| explains, describes, states a fact | `talk` | alternating arm gestures + head nod (default for narration) |
| win, success, thanks, cheers | `celebrate` / `jump` | both arms up, hops |
| fail, tired, bored, stuck | `sad` | head down, torso 8 deg forward |
| rushes, chases, hurries | `run` | larger swing, forward lean |
| goes, travels, arrives | `walk` | with root motion |
Default to `talk` or `idle` when unsure; never repeat the same action for more than two consecutive shots.
""", applies=("any",), tags=["actions"])

add("easing-and-overshoot-pop-in", "Springy entrances: overshoot 12-15% then settle", "motion", "technique",
    "Anything appearing on screen: titles, props, characters, icons.",
    ["appear", "pop in", "entrance", "overshoot", "spring", "bounce in", "reveal", "easing", "ease"],
    """## Procedure
- Scale from ~0 (hold at 0.001 until the delay) -> 1.12-1.15 over ~60% of the entrance -> 1.0 by frame +14 (0.55 s at 24 fps), BEZIER.
- Slide-ins: start off-screen 0.7 x frame width/height away, ease to the target in 0.55 s.
- Use LINEAR for anything that must carry constant speed into a physics release (see rigid-body-launch-release) and for camera dollies.
- Stagger multiple objects by 0.3-0.4 s so each gets its own beat.

## Code
```python
key(root, 1, scale=(0.001,) * 3, interp="CONSTANT")
key(root, f0 + 8, scale=(1.12,) * 3, interp="BEZIER")
key(root, f0 + 14, scale=(1, 1, 1), interp="BEZIER")
```
""", applies=("any",), test="pop_in_overshoot", tags=["easing"])

# ============================================================================= CAMERA
add("camera-follow-target-copy-location", "Camera that tracks a moving action front", "camera", "technique",
    "The action travels across the frame (a chain reaction, a walker, a rolling ball) and the camera must stay with it.",
    ["follow", "track", "tracking shot", "trailing", "chase camera", "dolly", "moves along", "pan with"],
    """## Procedure
1. Camera object with a TRACK_TO constraint (`TRACK_NEGATIVE_Z`, up `UP_Y`) on a target empty; DOF focus object = the same empty.
2. Key a *lead* empty along the action path with LINEAR interpolation timed to the measured event speed; give the target a COPY_LOCATION constraint to the lead.
3. Key the camera position separately (LINEAR): keep it 5-9 m to the side, lens 34-42 mm, height 1.2-1.7 m.
4. Call `cam.animation_data_clear()` before re-keying if the helper already keyed the camera.

## Pitfalls
- Schedule the lead empty from a **measured** event speed (dominoes: 0.17 s each) - a guessed schedule ends before the action does.
- Perspective foreshortening makes long rows look shorter: trail from behind-left, not straight on.
""", exemplar="domino_run", tags=["camera"])

add("camera-framing-safe-area", "Keep the subject fully in frame: distance, lens and a numeric check", "camera", "rule",
    "Every shot with a character or key object; any time a head/feet/prop is cropped.",
    ["framing", "cropped", "head cut off", "safe area", "composition", "in frame", "distance", "lens", "subject"],
    """## Rules (measured)
- Full-body 1.8 m character: camera distance >= 9 m with a 30-34 mm lens, or >= 5.3 m at 18 mm. 6.2 m at 40 mm cropped the head.
- Leave 10% headroom: target z = 55% of character height.
- Titles above the subject need at least 0.5 m clearance from raised hands.
- QA before a long render: project key points to the camera with `bpy_extras.object_utils.world_to_camera_view` at first/middle/last frame; require 0.02 < x < 0.98 and 0.03 < y < 0.97 (skills/tests/camera_framing.py does this).
- A shot that fails the check should be re-framed, not re-rendered.
""", applies=("any",), test="camera_framing", tags=["qa"])

add("camera-impact-shake", "Decaying camera shake on impact", "camera", "technique",
    "Collisions, explosions, landings, heavy hits.",
    ["impact", "shake", "explosion", "hit", "boom", "crash", "landing", "punch", "earthquake"],
    """## Procedure
For `k` frames after the impact frame `f0`: offset the camera position by a random vector in [-a, a]^3 with `a = 0.18 * exp(-k / 6)`, key every frame (LINEAR) for ~0.7 s, then continue the normal move. Total shake amplitude <= 0.2 m at 8 m distance.

## Pitfalls
- Re-key the *whole* camera path in that range (base path + noise), otherwise the shake fights the dolly.
- Do not shake earlier than 1 s into the shot or the setup is lost.
""", exemplar="crate_smash", tags=["camera"])

add("depth-of-field-focus", "Depth of field: focus object, aperture and when to open it up", "camera", "rule",
    "Choosing DOF for a shot: intimate/cinematic vs busy background.",
    ["depth of field", "dof", "bokeh", "blur", "focus", "f-stop", "aperture", "background blur", "cinematic"],
    """## Rules
- Enable `cam.data.dof.use_dof`, set `focus_object` to the target empty (follows moving subjects), `aperture_fstop`.
- f/2.0-2.6 for hero shots with plain backgrounds (intro, glass, walk); f/3.5-5 when the background has structure or the subject is far (cloth, fireworks f/5).
- The neon stripe world at f/2.4 turned into a blur soup: use f/4+ when the environment is bright and patterned.
- Depth of field in EEVEE Next costs little; the Defocus compositor node is far more expensive.
""", tags=["camera", "dof"])

# ============================================================================= COMPOSITION / PACING
add("title-3d-glow-text", "Glowing extruded 3D titles that fit and stay readable", "composition", "technique",
    "A hook, chapter or ending needs on-screen text inside the 3D scene.",
    ["title", "headline", "text", "caption", "on screen text", "label", "3d text", "logo", "heading"],
    """## Procedure
1. `C.title_3d(text, loc, size, delay, width)`: font Arial Bold, extrude 0.08, bevel 0.015, pop-in with overshoot at `delay`.
2. Colours by mood: bright sky (day/sunset) -> dark navy letters `#1a2140`, faint warm emission; dark scenes -> white letters with strong emission (1.6) in an accent glow colour (pink, orange).
3. Fit: measure `dimensions.x` AFTER scaling and a `view_layer.update()`; shrink to fit `width` (default 9 m). Never scale the same text with both its font size and a parent empty.
4. Position: 4-4.5 m high for a standing character, 4.6 m for wide scenes; keep it clear of raised arms; 1-4 words.
5. Non-hero shots only show a small title (0.7 size at y 4): if it must be read, place it in the shot's own layout instead.

## Pitfalls
- White glow text on a bright sky is invisible (the first intro).
- 'Crash!' at size 0.7 was barely legible; give key words size >= 0.9 and a 0.3 s delay.
""", applies=("cinematic",), test="text_fit", tags=["text"])

add("narration-driven-shot-length", "Shot length = narration length + padding; make the physics fit", "pacing", "rule",
    "Deciding how long each shot lasts and whether an event fits inside it.",
    ["duration", "timing", "shot length", "narration", "sync", "length", "seconds", "fit", "pace"],
    """## Rules
- Shot duration = audio duration + 0.35 s (agent default). Speech rate ~2.6 words/s.
- Sim events must finish inside the shot: domino wave 0.17 s per domino (+1.7 s lead-in), crate impact at ~1.5 s with >= 2.5 s of aftermath, fireworks bursts spread over `T - 1.5 s`, cloth needs ~0.6 s wind ramp.
- Size scenes to the duration: `count = (T - 2) / 0.17` dominoes (26 for 7.5 s).
- Typical ada video: 10 segments, 4.2-7.5 s each = 55 s.
""", applies=("any",), tags=["timing"])

add("vary-scene-recipes", "Do not repeat a scene type in consecutive shots", "pacing", "rule",
    "Assigning scene recipes/moods to consecutive script segments.",
    ["variety", "repeat", "monotony", "recipe", "next shot", "different look", "sequence"],
    """## Rules
- Pass the list of already used recipes to the director; reject an answer equal to the previous one.
- Alternate mood between neighbours (studio -> day -> sunset -> night -> neon) and alternate calm shots with physics shots.
- Repeat a recipe only after >= 3 other shots and change its mood/title (the ada video reuses `robot_intro` in neon at segment 9).
""", applies=("cinematic",), tags=["director"])

add("caption-safe-band", "Reserve the caption band so nothing collides with subtitles", "composition", "rule",
    "Laying out any shot that will get burned-in captions.",
    ["captions", "subtitles", "safe area", "bottom band", "text overlap", "layout", "portrait"],
    """## Rules
- Landscape: captions occupy the bottom ~15%; nothing may extend below z = -0.72 (normalised frame). Portrait: bottom ~25%; floor -0.5. ASS font size 5.2% of height (landscape) / 3% (portrait), 2 lines max in landscape.
- Multi-line 3D/2D text: estimate height as `lines * 0.9 * size`; wrap at 26 chars (landscape) / 13 (portrait).
- Portrait 9:16: stack objects vertically, max 5 objects per shot.
""", applies=("any",), tags=["layout"])

# ============================================================================= WORKFLOW / PERFORMANCE
add("preview-first-render-workflow", "Plan, preview, then render: review before the long render", "workflow", "rule",
    "Starting any new video, especially cinematic ones that take an hour or more.",
    ["preview", "draft", "plan", "review", "long render", "workflow", "iterate", "test render"],
    """## Procedure
1. `agent.py script.txt --style cinematic --plan-only` -> voiceover + `work/<name>/plan.json` (recipe / mood / title per shot).
2. Edit plan.json by hand if a choice is wrong (the edit is remembered as a preference).
3. `--quality draft --preview` for a fast look (640x360, 12 fps).
4. Full render in the background; look at each finished `work/<name>/segNN_*.mp4` as it appears and fix problems in that shot only.
5. To force one shot to re-render after a code change, change its plan entry (e.g. `"params": {"v": 2}`): the cache key hashes the shot dict, quality, size and duration - not code.

## Pitfalls
- Wait for physics shots before trusting the plan: verify motion in the finished shot (frozen physics looked fine in stills).
""", applies=("any",), tags=["workflow"])

add("render-cost-model", "What a render costs on this laptop and how to spend it", "performance", "rule",
    "Estimating render time, choosing quality, or trying to speed things up.",
    ["render time", "slow", "speed", "performance", "cost", "eta", "quality", "fast", "how long"],
    """## Measured (2 CPU cores, integrated Radeon, EEVEE Next, 1280x720, 24 fps, 'standard' 14 samples + ray tracing)
- Simple shots 3.2 s/frame; glass/mirror 4.6; workshop with spot + fog 5.9; fireworks 2.3-3; cloth 2.5.
- A 55 s video = 1320 frames = 83 min first pass; +42 min for the shots that needed fixes.
- Per-shot fixed cost ~15-60 s (Blender start + shader compile).
- Removing the compositor vignette (blur 260) saved ~3 s/frame; the biggest lever is *resolution* (540p ~ 0.6x). Samples 8 vs 14 saved ~10%. Ray tracing, fog, DOF, motion blur each cost < 10%.
- Two Blender processes do not help (GPU-bound).

## Rules
- Budget = frames x seconds-per-frame; estimate 4 s/frame for cinematic. Use `--quality draft --preview` while iterating.
- Move blur-like post effects (vignette, grain, sharpen) to ffmpeg; keep bloom (cheap) in the compositor.
- Render only what changed (per-shot cache) and review shots as they finish.
""", applies=("any",), tags=["performance"])

add("blender-45-headless-api-gotchas", "Blender 4.5 headless API facts that broke scripts", "workflow", "pitfall",
    "Writing or debugging bpy code that runs with `blender -b`.",
    ["bpy", "api", "error", "attributeerror", "keyerror", "headless", "blender 4.5", "script", "exception", "traceback"],
    """## Facts (each cost a failed run)
- Engine ids: `BLENDER_EEVEE_NEXT` (4.2-4.5), `BLENDER_EEVEE` (5.x), `BLENDER_WORKBENCH`.
- Principled inputs: `Transmission Weight`, `Coat Weight`, `Emission Color`, `Emission Strength`.
- `ParticleSettings.use_render_emitter` is gone: `obj.show_instancer_for_render = False`.
- Empties have no `.field`: `bpy.ops.object.effector_add(type=...)`.
- `FCurves`: `action.fcurves` in 4.x, layered actions in 5.x (`scene_lib._fcurves` handles both).
- `text.dimensions` is stale until `view_layer.update()` and excludes the parent's scale at creation time.
- `bpy.ops.mesh.primitive_*_add` links to the active collection: unlink then link to `scene.collection` when parenting manually.
- A world **volume** rendered black (EEVEE Next, this GPU): use a volume box.
- `bpy.ops.wm.read_factory_settings(use_empty=True)` gives a clean scene and keeps the addon-free environment.
- `image.pixels` + numpy reads a rendered PNG for QA (luminance checks).
- Use the API dump (`python blender_agent/knowledge/kb.py search "<name>"`) before guessing names.
""", applies=("any",), tags=["api"])

add("physics-timing-calibration", "Measure the simulation before scheduling cameras and shot lengths", "physics", "rule",
    "Any physics event whose duration is not obvious (chain reactions, piles, cloth settling).",
    ["timing", "calibrate", "measure", "how long", "simulation time", "schedule", "physics timing"],
    """## Procedure
1. Build the recipe in a probe script with the real parameters; step frames with `frame_set` and record when each object crosses a threshold (e.g. domino height < 0.42 m).
2. Derive: first event time, per-item speed, last event time.
3. Set the camera/lead-empty schedule and the number of items from these numbers (domino: 1.7 s lead, 0.17 s each).
4. Re-measure if substeps, mass, spacing or time_scale change.
""", tags=["physics", "qa"])

add("light-flash-on-events", "Flash a light at bursts and impacts", "lighting", "technique",
    "Explosions, fireworks, camera flashes, lightning, magic zaps.",
    ["flash", "burst", "explosion", "lightning", "zap", "firework", "illuminate", "spark"],
    """## Procedure
POINT light at the event; key `light.data.energy`: 0 at t-0.02 s, peak at t, 0 at t+0.35 s (frames via `frame(t)`). Peak 60000 W for a burst 20 m away over a mirror lake; scale with distance squared. The flash lights fog and water, which sells the size of the burst.

## Pitfalls
- 250000 W washed the whole frame purple.
""", exemplar="fireworks", tags=["lighting"])

for meta, body in SKILLS:
    S.write_skill(S.SKILLS_DIR / meta["category"] / f"{meta['id']}.md", meta, body)
print("authored", len(SKILLS), "skills")
