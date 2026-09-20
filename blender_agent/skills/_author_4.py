"""Batch 4: skills learned while recreating the anime reference clip (benchmark loop), plus promotion of reference skills that are now
implemented and measured. Re-runnable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import skills as S

SRC = "own-experience: anime-clip recreation benchmark (2026-09-19)"
NEW = []


def add(id, name, category, kind, when, triggers, body, applies=("any",), test=None, exemplar=None, tags=None):
    meta = {"id": id, "name": name, "category": category, "kind": kind, "status": "verified", "applies_to": list(applies), "when_to_use": when,
            "triggers": triggers}
    if test:
        meta["test"] = f"tests/{test}.py"
    if exemplar:
        meta["exemplar"] = exemplar
    if tags:
        meta["tags"] = tags
    meta["source"] = [SRC]
    meta["version"] = 1
    NEW.append((meta, body))


add("benchmark-recreation-loop", "Recreate a reference video and close the gap with measured comparisons", "workflow", "rule",
    "The goal is to reproduce (or reach the quality of) an existing video, or to check how good the agent's output really is.",
    ["recreate", "reference", "benchmark", "compare", "same as", "match the video", "quality gap", "clone the style", "reproduce"],
    """## Procedure
1. Evidence: `skill_extract.py video <file>` (cuts, motion, loudness, transcript, contact sheets); look at a dense contact sheet (every 0.5 s) to write a shot list with times.
2. Spec: one entry per shot (preset, seconds, params) whose durations sum to the reference length; keep the audio plan (tempo, key, energy curve, hits) from `analyze.py`.
3. Build with the project's tools (Blender presets + FX overlays + music agent + voice agent) and cache each shot.
4. Compare with `benchmark/compare.py ref rec outdir`: duration ratio, cut-alignment F1, motion correlation, SSIM, colour-histogram intersection, mean-colour, brightness correlation, audio score; it also writes a side-by-side video and a contact sheet.
5. Read `per_time` in report.json to find WHERE it fails, fix the largest gap first, re-render only changed shots, repeat. Keep each round's report to prove improvement.
## Pitfalls
- Do not read the aggregate score alone: black frames dominate SSIM/hist averages.
- Always look at the contact sheet: numbers said 'colour worse' when the real cause was a grading filter tinting pure black.
- Match STRUCTURE, TIMING, PALETTE LOGIC and AUDIO CHARACTERISTICS; do not copy the reference's art, character or soundtrack (originals only).
""", tags=["benchmark"])

add("exact-frame-count-per-shot", "Render exactly round(duration x fps) frames per shot or the timeline drifts", "workflow", "pitfall",
    "Concatenating many separately rendered shots that must land on exact times (music hits, cuts, reference matching).",
    ["timing drift", "frame count", "off by one", "sync", "shot length", "concatenate", "concat", "timeline", "cut times"],
    """## Procedure
- The scene builders keep one extra end key frame (`frames = ceil(T fps) + 1`) so animation curves close; set `scene.frame_end = frame_start + round(T * fps) - 1` before rendering (render_shot does this for `anime`).
- Verify: `ffprobe -count_frames` per shot = round(T x fps).
## Pitfalls
- 14 shots x 1 extra frame = 0.58 s of drift: the final black shot began at 10.1 s instead of 9.55 s and every later frame comparison was wrong.
- Physics cinematic shots (`cinematic` style) still carry the extra frame; fix the same way if exact sync matters.
""", tags=["timing"])

add("keep-blacks-black-in-grading", "Colour grading must not lift pure black", "effects", "pitfall",
    "Applying an ffmpeg/Blender colour grade to footage that contains black frames, fades or letterboxing.",
    ["grade", "colorbalance", "tint", "black frame", "fade", "lifted blacks", "eq filter", "color correction", "histogram"],
    """## Procedure
- Tint only mids/highlights: `colorbalance=rm=0.02:bm=0.03:rh=0.02:bh=0.04`; never use the shadow terms (`rs/gs/bs`) on footage with black.
- `eq=saturation=0.82:contrast=1.04:gamma=1.02` keeps 0 -> 0.
- Check: `mean` of a known black frame must stay 0.0 after the grade.
## Evidence
Adding `bs=0.05` turned black frames into dark blue and collapsed the histogram-intersection metric from 1.0 to 0.0 on every black frame.
""", applies=("any",), tags=["ffmpeg", "colour"])

add("toon-shading-hull-outline", "Cel shading + inverted-hull outlines in EEVEE Next", "style-2d", "technique",
    "An anime / cartoon / cel-shaded 3D look: flat colour bands with black outlines.",
    ["toon", "cel shading", "cel-shaded", "anime", "outline", "cartoon 3d", "flat shading", "ink lines", "comic"],
    """## Procedure
1. Material: Diffuse (white) -> Shader to RGB -> ColorRamp (interpolation CONSTANT: 0.0 shadow, 0.34 base, 0.78 highlight) -> Emission. Shadow colour = base x 0.55 with a cool tint (0.85, 0.75, 1.0); highlight = base x 1.18 + 0.02.
2. Outline: a second material slot (black emission, `use_backface_culling=True`) + Solidify modifier: thickness -0.006..-0.05 (scale with object size), offset 1, `use_flip_normals=True`, `material_offset=1`.
3. Render: Standard view transform, sun light 3.0, ray tracing/shadows off, 8 samples: ~1.4 s/frame at 1920x1080 on this laptop (vs 3-6 s for the physically based look).
4. Background/FX use flat Emission materials so they stay unshaded; glowing FX emission 6-8 + compositor Glare threshold 1.4.
## Pitfalls
- Shader-to-RGB only works with EEVEE, and only sees lights that reach the Diffuse node: add a sun.
- Outline thickness in metres: 0.008 for small armour, 0.012 limbs, 0.03-0.05 for buildings.
""", applies=("cinematic", "3d", "2d", "anime"), tags=["toon"])

add("camera-rig-with-roll-and-relative-framing", "Camera rig: track target, true roll, offsets relative to the subject", "camera", "technique",
    "Dutch angles / rolling camera, or any shot where the subject moves and the framing must stay guaranteed.",
    ["dutch angle", "roll", "tilt", "camera roll", "framing", "follow", "close-up", "relative camera", "rolled camera", "whip"],
    """## Procedure
1. `rig` empty with a TRACK_TO constraint (`TRACK_NEGATIVE_Z`, up `UP_Y`) to a `target` empty; the camera is the rig's CHILD at local (0,0,0). Roll = the camera's local Z rotation (`cam.rotation_euler = (0, 0, radians(deg))`), keyed over time.
2. Key rig and target positions per shot (BEZIER); add handheld shake by keying small random offsets every 2 frames (LINEAR).
3. Frame relative to the subject: `cam_pos(t) = subject_pos(t) + offset`, `look(t) = subject_pos(t) + look_offset`. Typical offsets for a 1.75 m hero: full body (0,-4,0.9) lens 40; low angle (0,-3,-1.7) looking up; close-up face (0.05,-1.2,1.72) lens 50; top-down (0,0.3,6) roll 25-40 deg.
## Pitfalls
- A Track-To camera cannot roll by itself; rolling the rig instead breaks the track. Use the child camera.
- Absolute camera positions rot when the subject path changes; relative offsets do not.
""", applies=("cinematic", "3d", "anime"), tags=["camera"])

add("radial-speed-lines-overlay", "Manga speed lines as a numpy/PIL RGBA sequence overlaid with ffmpeg", "effects", "technique",
    "Fast movement, impact or dramatic close-ups in an anime/comic look.",
    ["speed lines", "manga", "action lines", "focus lines", "radial lines", "impact frame", "dash", "burst lines", "anime action"],
    """## Procedure
- Per frame (re-randomised every 2nd frame = 'drawn on twos'): 46 tapered triangles from radius r0 = 0.38-0.62 H to r1 = r0 + 0.3-0.8 H at random angles around the focus point; width 0.15-0.5% of H; colour (70,68,82) alpha 150; transparent outside the effect windows.
- Write `sl_%04d.png` (RGBA) for the whole duration and composite: `ffmpeg -i video -framerate 24 -i sl_%04d.png -filter_complex "[0:v][1:v]overlay=shortest=1"`.
- Use 0.35-0.6 s windows at the dive, the smear and the speed close-up; keep the centre clear so the subject stays readable.
## Pitfalls
- 90 thick dark lines (alpha 215) covered the subject and looked like a sticker; 46 thin semi-transparent lines matched the reference.
""", applies=("any",), tags=["fx", "ffmpeg"])

add("muted-world-palette-and-haze", "Desaturate the environment and add haze so the subject and FX pop", "lighting", "rule",
    "A landscape or backdrop looks garish next to the character or effects; matching a muted anime/painterly reference.",
    ["muted", "desaturated", "haze", "atmosphere", "painterly", "background too saturated", "garish", "environment colour", "terrain"],
    """## Procedure
- Terrain bands (toon, noise scale ~16 on the plane's object coordinates): `#6f5a52, #8a6d5f, #a98a76, #bd9f8b, #a3a2a6`; sky `#a9b9c8` -> horizon `#dfe4e7`; clouds flat `#c9d2d9`.
- Grade: `eq=saturation=0.82:contrast=1.04` + a slight pink-cool tint in mids/highlights only.
- The only saturated colour in frame is the FX (magenta emission 6-8 + bloom).
## Measured
The first, saturated brown/orange desert scored histogram-intersection 0.44; the reference terrain is a desaturated pink-brown.
""", applies=("any",), tags=["colour"])

for meta, body in NEW:
    S.write_skill(S.SKILLS_DIR / meta["category"] / f"{meta['id']}.md", meta, body)

# ---- promote / extend existing skills with implementation notes + measurements
def upgrade(sid, extra, status="verified"):
    sk = next(x for x in S.load_all(True) if x.id == sid)
    meta = dict(sk.meta)
    meta["status"] = status
    meta["version"] = int(meta.get("version", 1)) + 1
    if SRC not in meta["source"]:
        meta["source"] = list(meta["source"]) + [SRC]
    S.write_skill(sk.path, meta, sk.body.rstrip() + "\n\n" + extra.strip() + "\n")


upgrade("anime-action-speed-lines-and-accent", """## Implemented (verified)
`blender_side/anime_recipes.py` presets: plunge, aerial_dive, side_lunge, up_shot, crouch_explosion, top_down, smear, speed_close, grin_close, back_leap, ledge_small, hair_close, black. Speed lines: see radial-speed-lines-overlay. FX helpers in `anime_lib.py`: `shard` (magenta triangle prism, emission 7), `laser` (thin emissive streak, hard cut on/off), `petals` (30 keyframed glowing ellipsoids), `debris` (26 grey shards + 9 puffs). Render: 1.4 s/frame at 1080p.
Result vs reference (round 3 benchmark): see work/recreate_anime/compare*/report.json.""")
upgrade("follow-through-secondary-motion", """## Implemented (verified)
`anime_lib.hair_follow(j, path, fps, lag, gain)`: five spiky hair chains (3-5 pointed cone segments each); every segment rotates against the ROOT velocity (`rx = -vy*6*gain`, `ry = vx*6*gain`, clamped +-70 deg) sampled `i*lag` frames in the past (lag 2), plus a small sine flutter and a constant 12 deg droop. Hair swings back on a dive and settles when the body stops.""")
upgrade("establishing-dark-to-light-reveal", """## Implemented (verified)
`plunge` preset: exposure keyed -10 (black hold 0.9 s, matching the reference) -> -2.6 at 1.0 s -> -0.7 at 1.5 s while the camera drops from 120 m to 60 m with a -10..-18 deg roll.""")
with S.library(Path(__file__).resolve().parents[2] / "agents" / "music" / "skills", ["mood", "arrangement", "sync", "mixing", "reference-matching", "tools"]):
    upgrade("music-reference-matching", """## Implemented (verified) - result on the anime clip
`MusicAgent.plan_from_reference` + `refine_to_reference(rounds=3)` (FluidSynth strings/choir/bass/arp/kit + numpy risers/impacts, `eq_match`, `match_dynamics`, loudnorm to the reference LUFS): comparison score 0.233 (0 = identical): LUFS -14.4 vs -14.4, LRA 1.8 vs 2.2, energy-curve correlation 0.99, key F major = F major, tempo 90.5 vs 89 (half of the detected 178), centroid 1461 vs 1364 Hz, band-share L1 0.12. Audio score 0.875 in `benchmark/compare.py`.""")
print("authored", len(NEW), "new skills; upgraded 4")
