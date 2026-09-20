"""Batch 5: skills learned while recreating the Blender 2D tutorial (GUI screen recording, GP effects API, compositor API, timeline-locked
narration) and promotion of the reference skills that were implemented. Re-runnable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import skills as S

ROOT = Path(__file__).resolve().parents[2]
SRC = "own-experience: tutorial recreation benchmark (2026-09-19)"
NEW = []


def add(id, name, category, kind, when, triggers, body, applies=("any",), tags=None):
    meta = {"id": id, "name": name, "category": category, "kind": kind, "status": "verified", "applies_to": list(applies), "when_to_use": when,
            "triggers": triggers, "source": [SRC], "version": 1}
    if tags:
        meta["tags"] = tags
    NEW.append((meta, body))


add("blender-gui-screen-recording", "Record real Blender UI: scripted tour + ffmpeg gdigrab", "workflow", "technique",
    "A tutorial / how-to / 'show the software' video needs authentic Blender GUI footage (properties, node editors, effects) instead of mock-ups.",
    ["tutorial", "screen recording", "how to", "blender interface", "gui", "walkthrough", "screencast", "demonstrate", "ui footage"],
    """## Procedure (recreate/tutorial_gui.py + record_gui.py)
1. `record_gui.py` starts `ffmpeg -f gdigrab -framerate 24 -draw_mouse 0 -i desktop -vf scale=1280:720 -c:v libx264 -preset ultrafast -crf 18`, then launches `blender --python tutorial_gui.py -- <speed> <log>` (quote paths with spaces!).
2. Dismiss the first-run splash: Windows `SetCursorPos` away then a click where Continue sits (ctypes `user32.mouse_event`); park the pointer in a corner.
3. Inside Blender: `bpy.ops.wm.window_fullscreen_toggle()` (16:9 capture), `preferences.view.ui_scale = 1.25`, viewport `shading.type='RENDERED'` + camera view so effects show live.
4. Timeline engine: a `bpy.app.timers` tick every 0.05 s runs (t, function) steps and tweens (lerp of a property between two times) so sliders visibly move while the narration explains them; every step is try/except + logged.
5. Editors: `area.spaces.active.context = 'OBJECT'|'OUTPUT'|...` picks the Properties tab; `bpy.context.window.workspace = bpy.data.workspaces['Compositing']` switches workspace; `with bpy.context.temp_override(window, area, region): bpy.ops.node.view_all()` keeps new nodes in view.
6. Log `TOUR START` (wall clock) and the recorder start time: trim with `-ss offset`.
7. ALWAYS dry-run with `--speed 20` (27 s) and look at a contact sheet before the real 9-minute run.
## Pitfalls
- The machine is unusable while recording (fullscreen); nobody may click. The capture is 1920x1080 physical even if the display is scaled.
- Properties tab enum lists only tabs valid for the ACTIVE object: the Effects tab needs the Grease Pencil object active (adding a camera afterwards stole the active object).
- Setting `default_value` on a socket that does not exist prints thousands of `RNA_float_set` lines: guard tweens.
""", applies=("any",), tags=["gui", "ffmpeg", "tutorial"])

add("grease-pencil-effects-python-45", "Grease Pencil objects and shader effects from Python (Blender 4.5)", "style-2d", "technique",
    "Scripting Grease Pencil (2D) objects and their Effects: glow, rim light, blur, colorize, shadow, pixelate, wave.",
    ["grease pencil", "shader effect", "fx_glow", "fx_rim", "fx_blur", "fx_colorize", "2d animation python", "gpencil", "monkey"],
    """## Procedure
- Object: `bpy.ops.object.grease_pencil_add(type='MONKEY'|'STROKE'|'EMPTY'|'LINEART_SCENE'...)`; recolour via `mat.grease_pencil.color`, `.fill_color`, `.show_fill`.
- Effects: `obj.shader_effects.new(name, 'FX_GLOW')`; types FX_BLUR, FX_COLORIZE, FX_FLIP, FX_GLOW, FX_PIXEL, FX_RIM, FX_SHADOW, FX_SWIRL, FX_WAVE.
  - Glow: `mode='LUMINANCE'`, `threshold` (lower = more glows), `opacity`, `size=(x,y)`, `samples`, `glow_color`.
  - Rim: `mode='ADD'`, `rim_color`, `offset=(x,y)` px, `blur=(x,y)` px.
  - Blur: `size=(x,y)`, `samples`, `use_dof_mode`.
  - Colorize: `mode='CUSTOM'`, `low_color`, `factor`.
  - Toggle with `fx.show_viewport` / `show_render`.
- Brightness matters: glow on LUMINANCE finds nothing on dark strokes - use bright strokes on a dark background.
- Stack order used in the tutorial: glow -> rim -> blur -> colorize.
""", applies=("2d", "stickman", "any"), tags=["grease pencil"])

add("compositor-node-api-45", "Building compositor chains from Python (nodes, sockets, gotchas)", "effects", "technique",
    "Creating or animating compositor nodes by script: Glare, Blur, Mix, Lens Distortion, Filter, Defocus, Viewer.",
    ["compositor", "node tree", "glare", "lens distortion", "defocus", "mix node", "viewer node", "z pass", "post processing script"],
    """## Procedure
- `scene.use_nodes = True` creates Render Layers + Composite in `scene.node_tree`.
- Nodes: `CompositorNodeGlare` (glare_type BLOOM; threshold/size/quality), `CompositorNodeBlur` (size_x/size_y), `CompositorNodeMixRGB` (blend_type COLOR/OVERLAY; inputs[0] = factor), `CompositorNodeLensdist` (use_projector, dispersion input), `CompositorNodeFilter` (filter_type SHARPEN...; inputs[0] = factor), `CompositorNodeDefocus` (use_zbuffer, f_stop keyframeable), `CompositorNodeViewer`, `CompositorNodeRGB`.
- Depth for Defocus: `view_layer.use_pass_z = True`; connect Render Layers `Depth` -> Defocus `Z`.
- Layout: set `node.location`; keep all in view with `bpy.ops.node.view_all()` in a node-editor `temp_override`.
- Animate f-stop: `d.f_stop = 128; d.keyframe_insert('f_stop', frame=1)` then 3.0 at the end.
## Cost
Glare is cheap; Blur/Defocus are CPU-expensive - prefer ffmpeg for blur-like post on long renders (see film-finish-ffmpeg).
""", applies=("any",), tags=["compositor"])

add("timeline-locked-narration", "Narration that keeps the reference timeline: sentence-level TTS + tempo fit", "audio", "technique",
    "Voice-over must land on fixed timestamps (recreating a video, syncing to a storyboard, matching a screen tour).",
    ["timeline", "timestamps", "sync narration", "same script", "recreate voiceover", "lock to timeline", "narration timing", "align tts"],
    """## Procedure (recreate/tutorial_voice.py)
1. Transcribe the reference (faster-whisper) and split each segment into sentences; distribute each segment's time over its sentences by character count.
2. Fix systematic mis-hearings in the transcript (dictionary of regex fixes: Grease Pencil, EEVEE, grain, chromatic aberration...).
3. Voice agent picks the voice by median pitch (calibrated on a fixed sentence) and sets speed from measured wpm; pitch shift <= +-4 semitones.
4. Synthesize per sentence, place each clip at its original start; if a clip exceeds its slot by > 2 %, `atempo` up to 1.3x; keep word times scaled accordingly.
5. Master: mono files measure 3 dB lower than stereo for the same audio - compare like with like (reference mono -18.0 LUFS = stereo -14.7).
## Result (tutorial, 588 s)
pitch 121.2 Hz vs 119.4 Hz, pace 135 wpm vs 134 wpm, 130 sentences, duration 585.8 s vs 587.7 s. Kokoro on this CPU synthesised 10 minutes of speech in ~17 minutes.
""", applies=("any",), tags=["voice", "sync"])

for meta, body in NEW:
    S.write_skill(S.SKILLS_DIR / meta["category"] / f"{meta['id']}.md", meta, body)


def upgrade(sid, extra):
    sk = next(x for x in S.load_all(True) if x.id == sid)
    meta = dict(sk.meta)
    meta["status"], meta["version"] = "verified", int(meta.get("version", 1)) + 1
    if SRC not in meta["source"]:
        meta["source"] = list(meta["source"]) + [SRC]
    S.write_skill(sk.path, meta, sk.body.rstrip() + "\n\n" + extra.strip() + "\n")


upgrade("gp-shader-effects-glow-rim-blur-colorize", """## Implemented (verified in Blender 4.5)
Scripted and screen-recorded end to end (glow -> rim -> blur -> colorize, values tweened live): see grease-pencil-effects-python-45 and blender-gui-screen-recording.""")
upgrade("compositor-bloom-lens-grain-chain", """## Implemented (verified in Blender 4.5)
The chain Blur+Mix(Color) -> Glare(Bloom) -> Lens Distortion(projector, dispersion 0.03) -> grain Mix(Overlay 0.15) -> Filter(Sharpen 0.12) -> Defocus(Z pass, f-stop 128 -> 3) was built live by script and recorded; details in compositor-node-api-45.""")
upgrade("render-output-settings-test-half-res", """## Implemented (verified in Blender 4.5)
Recorded live: resolution 1920x1080 at 100 % -> 50 %, File Format FFMPEG, MPEG-4, H.264, constant rate factor HIGH, frame range 1-96, single-frame test render at 25 %.""")
upgrade("hook-promise-agenda-opening", """## Implemented (verified)
Recreation intro: 38 s reel of the agent's own anime clip with 2-3 word huge yellow outlined captions timed to the narration words (voice agent `captions.write_ass(style='hook')`), then a 3 s 'Get the source files' card.""")
upgrade("word-highlight-captions", """## Implemented (verified)
`agents/voice/tools/captions.py` (karaoke / hook / plain ASS from word timings). Used for the tutorial intro hook captions.""")
with S.library(ROOT / "agents" / "voice" / "skills", ["voice-choice", "prosody", "sync", "captions", "quality", "tools"]):
    upgrade("voice-reference-matching", """## Implemented (verified) - tutorial narrator
Reference: median f0 119.4 Hz, 134 wpm overall. Chosen: Kokoro `am_adam` speed 1.035, +0.26 semitones -> measured 121.2 Hz, 135 wpm.""")
print("authored", len(NEW), "skills; upgraded 6")
