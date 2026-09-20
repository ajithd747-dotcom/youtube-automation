"""Authors batch 2: skills DISTILLED FROM THE REFERENCE VIDEOS in "reference vedios/". Status `reference` = advisory until the
agent implements + tests the technique (then promote to `verified`). Evidence packs: skills/sources/<slug>/evidence.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import skills as S

SKILLS = []
GP = "video:blender-2d-animation-basics-for-beginners-grease-pencil-effe"
SK = "video:how-to-create-viral-stickman-animations-with-ai-100-free"
MEME = "video:can-you-relate-4k-memes-animation-shorts"
V7 = "video:videoplayback-7"
V8 = "video:videoplayback-8"
ANIME = "video:blender-grease-pencil-practice-fantasy-anime-scene"


def add(id, name, category, kind, when, triggers, body, source, applies=("any",), status="reference", test=None, recipe=None, tags=None):
    meta = {"id": id, "name": name, "category": category, "kind": kind, "status": status, "applies_to": list(applies),
            "when_to_use": when, "triggers": triggers}
    if test:
        meta["test"] = f"tests/{test}.py"
    if recipe:
        meta["uses_recipe"] = recipe
    if tags:
        meta["tags"] = tags
    meta["source"] = source
    meta["version"] = 1
    SKILLS.append((meta, body))


# ----------------------------------------------------------------------------- Blender 2D tutorial (compositing / effects)
add("gp-shader-effects-glow-rim-blur-colorize", "Grease Pencil effects stack: glow, rim light, soft blur, colorize", "style-2d", "technique",
    "A hand-drawn / 2D Grease Pencil look needs quick polish: warm glow, back-light outline, softened digital edges, colour matched to the background.",
    ["grease pencil", "2d animation", "glow", "rim light", "outline glow", "cartoon", "hand drawn", "anime", "cel", "colorize", "effects"],
    """## What it achieves
Non-destructive polish on a Grease Pencil object in a few clicks, live in EEVEE.

## Procedure (tutorial 0:30-3:00)
1. Select the Grease Pencil object -> Properties -> Effects tab (magic-wand icon). Effects stack like filters and can be reordered/toggled.
2. **Glow**: mode Luminance, blend Add, tune Threshold to catch only the bright highlights, Opacity for strength, Size for spread.
3. **Rim light**: blend Add, pick the rim colour, use Offset to place the back-light, Blur to smooth, Samples for quality.
4. **Blur**: very small size; softens vector-sharp edges for a vintage feel. Too high = mushy.
5. **Colorize**: custom mode, subtle hue matching the scene (the tutorial uses green), Factor slider to dilute; unifies character and background.
6. Extras: Shadow, Pixelate, Wave distortion; Blur in Depth-of-Field mode uses the camera's DOF settings.
7. Order matters: glow -> rim -> blur -> colorize worked best.

## Pitfalls
- In Blender 4.3+ Grease Pencil is the new GPv3 data type and the effects API/UI moved; verify property names on the installed version before scripting.
- Keep glow Threshold high or the whole picture blooms.
""", [f"{GP}@0:30-3:00"], applies=("stickman", "kinetic", "2d"), tags=["grease pencil"])

add("compositor-bloom-lens-grain-chain", "Compositor chain: bloom, colour bleed, lens dispersion, film grain, sharpen, defocus", "effects", "technique",
    "A finished shot should look cinematic or vintage: glow, chromatic edges, grain, animated depth of field.",
    ["cinematic", "vintage", "film grain", "chromatic aberration", "lens distortion", "bloom", "depth of field", "defocus", "color bleed", "polish", "compositing"],
    """## What it achieves
A layered post chain that upgrades any render without re-rendering the 3D.

## Procedure (tutorial 3:30-7:30)
1. Compositing workspace, tick **Use Nodes**. Render Layers -> ... -> Composite. Add a Viewer to preview any socket.
2. **Colour bleed**: Blur (slight) mixed with the original in a Mix node, blend `Color`, small factor.
3. **Bloom**: Filter > Glare, type Bloom; tune threshold, strength, size.
4. **Lens**: Transform > Lens Distortion, Projector mode, a tiny Dispersion -> chromatic aberration.
5. **Grain**: load a grain video/image, Mix with `Overlay`, factor 0.1-0.2.
6. **Sharpen**: Filter > Box Sharpen, small factor (recovers sharpness lost to distortion).
7. **Animated depth of field**: Blur > Defocus; connect the Z/Depth output of Render Layers (enable View Layer > Z pass); keyframe the F-stop.

## Cost on this laptop (measured) - do the cheap ones in ffmpeg
- Glare bloom is cheap (~0.3 s/frame at 720p); Blur/Defocus nodes are not (a 260 px blur cost ~3 s/frame).
- ffmpeg equivalents: chromatic `rgbashift=rh=2:bh=-2`, grain `noise=alls=6:allf=t`, sharpen `unsharp=5:5:0.4`, colour bleed `gblur` + `blend=all_mode=screen:all_opacity=0.25`.

## Pitfalls
- Previewing the compositor in the viewport is CPU heavy (tutorial 5:00).
""", [f"{GP}@3:30-7:30"], applies=("cinematic", "3d", "any"), tags=["compositor"])

add("render-output-settings-test-half-res", "Final output settings and testing at half resolution first", "workflow", "rule",
    "Before committing to a long render: choose codec/container and test cheaply.",
    ["render", "output", "export", "codec", "h.264", "png sequence", "transparent", "test render", "resolution", "quality"],
    """## Procedure (tutorial 7:30-9:00)
1. Output Properties: resolution = target (1920x1080 or 1280x720); output folder; File Format **FFmpeg**, container MPEG-4 (or QuickTime), codec **H.264**, quality preset High.
2. Need transparency for compositing elsewhere -> render a **PNG sequence** instead.
3. Set Start/End frame to cover the animation.
4. Test a single frame (F12), then test the animation at **50% resolution or lower** before the full-quality render (Ctrl+F12 = render animation).
5. EEVEE is fast; Cycles/fancier is slower - pick per shot.

## In this agent
`--preview` (360p, 12 fps, draft quality) is the 50%-test; `--plan-only` reviews the shot list first; per-shot caching means only changed shots re-render.
""", [f"{GP}@7:30-9:00"], tags=["render"])

add("hook-promise-agenda-opening", "Open with a question, a promise, then the agenda (first 30 s)", "pacing", "rule",
    "Writing or structuring the first seconds of an explainer / tutorial video.",
    ["intro", "hook", "opening", "explainer", "tutorial", "what if", "welcome", "today we", "agenda", "curious"],
    """## Procedure (tutorial 0:00-0:30, ~134 wpm)
1. 0-7 s: a curiosity question that promises a transformation ("What if a few clever tweaks could transform your animation into a cinematic masterpiece? Curious how? Stick around.").
2. Next ~10 s: "Welcome back ... today we are wrapping up X by doing Y".
3. Next ~10 s: agenda in one sentence: "We'll cover A for quick polish, B for advanced tweaks like C, D, then E".
4. Visual during the hook: the *finished result* (character in the final scene) with bold outlined 2-3 word captions; only then switch to the working screen.
5. A single soft call to action mid-way (sponsor/membership at ~3:00) and a subscribe ask at the end (9:30).

## Numbers
Speech rate 134 wpm (tutorial 1) vs 197 wpm (tutorial 2, rushed); calm explainers sit near 130-160 wpm.
""", [f"{GP}@0:00-0:30", f"{GP}@9:00-9:40"], tags=["script"])

add("screencast-annotation-arrows", "Screen-recording tutorials: red arrow/circle on the exact UI control", "composition", "technique",
    "Making a tutorial or 'how to use the software' video from screen footage.",
    ["tutorial", "screen recording", "click", "button", "menu", "how to use", "interface", "annotation", "highlight"],
    """## Procedure (tutorial 1:01, 2:41)
- Show the whole UI, then draw a thick red circle + arrow around the control being clicked at the moment it is named in the narration.
- Long static holds are normal (1.9 cuts/min, one shot lasted 217 s) - the narration carries the pace; cut only when the workflow changes screen.
- Zoom/crop into the property panel when the numbers matter; keep cursor movement slow.
""", [f"{GP}@1:01", f"{GP}@2:41"], tags=["tutorial"])

# ----------------------------------------------------------------------------- stickman AI tutorial
add("stickman-explainer-scene-card", "Stickman explainer: one structured scene card per shot", "style-2d", "technique",
    "Psychology, self-improvement, motivational or simple explainer videos told with a minimalist stickman on white.",
    ["stickman", "self improvement", "psychology", "motivation", "explainer", "minimalist", "white background", "doubt", "mirror", "confidence"],
    """## What it achieves
Every scene is fully specified, so a different tool/agent can draw or animate it consistently.

## Procedure (tutorial 2:00-3:30, sample video 9:00-9:40)
Per scene write a card with these fields:
`Pose` (standing slightly slouched) - `Action` (looking at a small mirror) - `Facial Expression` (doubtful, slightly sad) - `Prop` (hand mirror) - `Background` (minimal white) - `Aspect ratio` 16:9.
Visual style seen in the sample: white background, black round-head stickman with medium line thickness, big expressive face (brows + mouth carry the emotion), props big and simple (magnifying glass, mirror, punching bag), grey scribbled speech bubbles for "voices in your head", pale grey silhouettes for other people, minimal panels/kinetic numbers for the hook (2026 "Want to become").
Captions: white bold, 2-4 words at a time, bottom-centre, soft shadow.

## In this agent
Maps to a stickman shot: `stickman.action`, an `expression` (planned), a prop icon, `bg #ffffff`. Use `stickman` style, palette paper/white.
""", [f"{SK}@2:00-3:30", f"{SK}@9:00-9:40"], applies=("stickman",), tags=["stickman", "scene card"])

add("consistent-character-base-prompt", "Define the character once, repeat it verbatim in every scene", "workflow", "rule",
    "A video with a recurring character across many shots/scenes must not change look between shots.",
    ["character", "consistent", "same character", "recurring", "mascot", "protagonist", "series"],
    """## Procedure (tutorial 2:30-3:30)
1. Generate a **base prompt/description** first (e.g. "Simple black stickman with a round head, clean smooth lines, minimalist, expressive face, consistent proportions, medium line thickness, flat illustration, white background, soft emotional tone").
2. Paste that base text unchanged into every scene's prompt; only Pose/Action/Expression/Prop/Background vary.
3. Work in parts (about 1 minute of script per part) but reuse the same base block so parts match.
4. Check consistency by putting two scenes side by side before animating.

## In this agent
Keep character parameters in the plan (rig, colour, proportions, accent colour) and pass the same values to every shot: the robot uses `build_robot(color, accent, scale)` with fixed defaults per video; do not randomise per shot.
""", [f"{SK}@2:30-3:30"], tags=["consistency"])

add("scene-by-scene-production-loop", "Production loop: per scene = visual + motion + voiceover, then assemble", "workflow", "rule",
    "Planning the pipeline for any narrated animated video.",
    ["workflow", "pipeline", "storyboard", "shot list", "script to video", "production", "assemble", "parts"],
    """## Procedure (tutorial 1:00-8:30)
1. Pick topic + length; write the script in parts.
2. Per scene produce three things: a still/visual spec, a motion (animation) spec, and the voiceover text.
3. Generate visuals for all scenes first, check them side by side, then animate each (start-frame -> motion prompt).
4. Voiceover: feed the whole part as ONE paragraph to the TTS (natural prosody); deep, calm, premium voice for psychology content.
5. Import visuals in scene order, lay the voiceover, auto-generate captions ("normal" style), export.

## In this agent
This is `agent.py`: segments -> voiceover -> director shot spec (visual+motion) -> Blender render -> mux + captions. Improvement noted: TTS per whole paragraph then split by word timings keeps prosody continuous.
""", [f"{SK}@1:00-8:30"], tags=["pipeline"])

add("calm-deep-narration-voice", "Choose the narration voice to match the content", "audio", "rule",
    "Selecting or configuring text-to-speech for a video.",
    ["voice", "narration", "voiceover", "tts", "calm", "deep", "premium", "energetic", "serious", "comedy voice"],
    """## Procedure
- Psychology / self-improvement / emotional explainers: deep, calm, slow (edge-tts `en-US-ChristopherNeural` or `EricNeural`, rate -5..-10%). The reference asks for "Deep and calm and premium".
- Comedy / stickman jokes: energetic (`en-US-GuyNeural`, rate +0..+8%).
- News / crime: serious (`ChristopherNeural`).
- Aim for 130-160 wpm; leave 0.3-0.4 s of air after each segment (the agent pads 0.35 s).
""", [f"{SK}@8:00-8:30", f"{GP}@0:00-9:30"], tags=["tts"])

add("loudness-target-minus-14-lufs", "Master to about -14 LUFS", "audio", "rule",
    "Every final mix; tutorials/shorts that sound too quiet or too loud.",
    ["loudness", "volume", "quiet", "loud", "lufs", "normalize", "audio level", "mix"],
    """## Evidence (measured with ffmpeg ebur128)
Meme short -14.3 LUFS, Blender tutorial -14.7, anime clip -14.4 (social-ready), stickman tutorial -22.0 (noticeably quiet).

## Procedure
Final mix: `loudnorm=I=-14:TP=-1.5:LRA=11` (single pass is fine for narration) after concatenation, so every segment has one consistent level. With music, duck it ~12-15 dB under the voice.
""", [f"{MEME}", f"{GP}", f"{ANIME}", f"{SK}"], tags=["ffmpeg"])

# ----------------------------------------------------------------------------- vertical shorts (videoplayback 7 / 8, meme)
add("word-highlight-captions", "Word-by-word highlighted captions (karaoke) and bold outlined hook captions", "composition", "technique",
    "Shorts / vertical comedy or any video where captions should carry energy and retention.",
    ["captions", "subtitles", "karaoke", "word by word", "highlight", "shorts", "tiktok", "reels", "bold text", "yellow"],
    """## Evidence
- videoplayback (7): 1-3 words at a time near 60-70% of frame height; white bold outlined text with the **current word in yellow** ("I'm *finally*", "a *job*,", "you made *it!*").
- Blender tutorial intro (0:01, 0:41): 2-3 huge yellow (`#FFE000`) words with a thick black outline in the lower third ("a few clever tweaks", "Get the Source files").
- Stickman tutorial sample: white bold, 2-4 words, bottom-centre with soft shadow.

## Procedure
1. Get word timings: edge-tts `WordBoundary` events (offset/duration) or faster-whisper word timestamps.
2. Group into 1-3 word chunks (<= ~14 characters), each shown from its first word start to its last word end.
3. ASS karaoke: `\\k<centiseconds>` per word with `PrimaryColour` white and `SecondaryColour` yellow, outline 4-6 px black, Arial Black/Impact-like bold, size ~5-6% of height.
4. Keep captions out of faces and keep the title banner separate (see shorts-top-title-banner).
""", [f"{V7}@0:01-0:27", f"{GP}@0:01,0:41", f"{SK}@9:00"], applies=("any",), tags=["captions", "shorts"])

add("shorts-top-title-banner", "Persistent top title banner for shorts", "composition", "technique",
    "Vertical (9:16) videos that need a hook/label visible the whole time.",
    ["shorts", "vertical", "title", "pov", "banner", "hook title", "tiktok", "reels", "headline"],
    """## Evidence
videoplayback (7): all 30 s show "POV: YOU'RE LIVING THE AMERICAN DREAM" in a black rounded box, white italic caps, 2 lines, top 4-12% of the frame. videoplayback (8): "WHERE IS MY PHONE" in a bold display font + emoji across the top for all 15 s.

## Procedure
Title = a situation or question in <= 6 words, often prefixed "POV:"; box or outlined text at the top safe area (5-12% from the top), constant for the whole video; captions live lower down so they never collide.
""", [f"{V7}@0:01-0:27", f"{V8}@0:01-0:13"], applies=("any",), tags=["shorts"])

add("vertical-blurred-background-fill", "Fit 16:9 footage into 9:16 with a blurred, zoomed copy behind it", "composition", "technique",
    "Repurposing landscape animation for Shorts/Reels, or any letterboxed content in a vertical frame.",
    ["shorts", "vertical", "9:16", "blurred background", "letterbox", "repurpose", "reels", "fill"],
    """## Evidence
videoplayback (8): the animation plays in a 16:9-ish band in the middle; the same picture, enlarged and heavily blurred, fills the top and bottom areas; the title sits over the top band.

## Procedure (ffmpeg)
`[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2`
Then add the top title banner and captions below the picture band. Natively vertical renders (`--format shorts`) do not need this.
""", [f"{V8}@0:01-0:13"], applies=("any",), tags=["ffmpeg", "shorts"])

add("shorts-cut-rate", "Cut rate and shot length for shorts vs tutorials", "pacing", "rule",
    "Deciding how many shots a video needs and how long each should last.",
    ["pacing", "cut rate", "shot length", "shorts", "retention", "editing rhythm", "fast cuts", "how many shots"],
    """## Measured (scene-cut detection + frame-difference motion)
| video | length | shots | mean shot | cuts/min | motion |
|---|---|---|---|---|---|
| videoplayback (7) vertical comedy | 30 s | 12 | 2.5 s (median 1.8) | 22 | 19 |
| videoplayback (8) vertical comedy | 15 s | 8 | 1.8 s (median 1.5) | 29 | 27 |
| anime action clip | 12 s | 5 | 2.3 s | 20 | 33 |
| meme short (one continuous drawn take) | 11 s | 1 | - | 0 | 14 |
| Blender tutorial (screencast) | 588 s | 20 | 29 s (median 10 s) | 1.9 | 4 |

## Rules
- Shorts/comedy: 1.5-2.5 s per shot, alternate wide / close-up; a new visual event every ~2 s.
- Explainers with narration: 4-8 s per shot (the agent uses narration length + 0.35 s).
- Tutorials: hold long, cut on workflow changes.
""", [f"{V7}", f"{V8}", f"{ANIME}", f"{MEME}", f"{GP}"], tags=["metrics"])

add("wide-to-closeup-reaction-cut", "Alternate wide two-shots with close-ups on emotion, insert a prop cutaway for the punchline", "camera", "technique",
    "Dialogue or reaction comedy: setup, emotional beat, punchline.",
    ["reaction", "close-up", "dialogue", "punchline", "comedy", "two shot", "cutaway", "emotion", "talking"],
    """## Evidence (videoplayback 7, 0:01-0:27)
Wide two-shot on the sofa for setup lines; close-up on the speaker when the emotion peaks ("insurance, and" at 0:11 fills the frame); insert cut to the prop for the punchline (fridge, ketchup bottle at 0:24-0:27); expression changes with each line (sad -> hopeful grin -> worried).

## Procedure
1. Setup lines: wide/medium, both characters visible.
2. Emotional peak or reveal: cut to close-up (head fills 60-80% of the frame) for 1-2 s.
3. Punchline: cutaway to the object that explains the joke, then back to a reaction.
4. Change the cut on the *word* that carries the emotion, not between sentences.
""", [f"{V7}@0:01-0:27"], applies=("stickman", "3d", "cinematic"), tags=["camera", "comedy"])

add("shock-reaction-burst-closeup", "Shock beat: extreme close-up, radial burst lines, sweat drops", "effects", "technique",
    "A character is shocked, panics, screams or discovers something (loss, jump-scare, sudden realisation).",
    ["shock", "panic", "scream", "surprised", "scared", "realise", "gasp", "freak out", "where is", "jump scare"],
    """## Evidence (videoplayback 8, 0:02, 0:07, 0:12; meme 0:04-0:08)
Extreme close-up on wide-open eyes (large white eyes, tiny pupils) + open mouth; background switches to a radial sunburst / speed-line pattern (orange-yellow or pastel rays); blue sweat drops fly off the head; short zoom punch-in; a burst of comic 'shake' marks beside the face.

## Procedure
1. Cut to a close-up for 0.5-1 s; scale eyes up 1.3-1.6x, pupils 0.4x.
2. Replace/overlay the background with radial lines centred on the face (thin -> thick from centre outward), colours warm.
3. 6-10 sweat-drop shapes flung outward with gravity; 2-4 short 'shake' strokes at the head sides.
4. Zoom punch: scale 1.0 -> 1.12 in 4 frames then settle; optional 2-frame camera shake.
""", [f"{V8}@0:02,0:07,0:12", f"{MEME}@0:04-0:08"], applies=("stickman", "2d", "cinematic"), tags=["effects", "comedy"])

add("expression-progression-arc", "Give each beat a distinct facial state: calm, worry, panic, relief", "character", "technique",
    "A character reacts over several beats (comedy, drama, self-improvement).",
    ["expression", "emotion", "face", "worried", "relief", "reaction", "arc", "mood", "eyes", "mouth"],
    """## Evidence
- Meme short (11 s, one drawn take): calm singing in the shower -> hands clamped on head (panic) -> huge eyes/tiny pupils/quivering mouth (fear) -> monster cutaway -> eyes red and relaxed with a wide grin (relief). Each state is held ~1-1.5 s.
- videoplayback 7: brow + mouth changes on every subtitle chunk (annoyed -> hopeful smile -> blank).

## Procedure
1. List the emotional beats of the segment (3-4 max in 10 s).
2. Per beat define: eye size/pupil size, brow angle, mouth shape (flat, open, grin, wobble), plus one body cue (slump, hands on head, shrug).
3. Hold each state 1-1.5 s, change on a word or sound, and use anticipation: a 3-4 frame squash/stretch before the change.
4. Add cheap secondary details: sweat drops, tears, foam, blush.
""", [f"{MEME}@0:01-0:09", f"{V7}@0:01-0:27"], applies=("stickman", "3d", "cinematic"), tags=["character", "face"])

add("jump-scare-cutaway-timing", "Insert a one-second scary/comic cutaway at ~30% of a short", "pacing", "technique",
    "A short comedy/horror sketch needs a spike of surprise, then a payoff reaction.",
    ["jump scare", "cutaway", "monster", "surprise", "twist", "horror comedy", "reveal"],
    """## Evidence (meme short, 11 s)
At 0:03 (27% of the runtime) a single hard cut shows the monster in the doorway (different palette: dark red eyes on grey), ~1 s; the next 6 s are the character's reactions; the last second is the relief punchline.

## Procedure
Setup 25-30% -> hard cut to the threat for ~1 s (no transition, no caption) -> reaction takes 50-60% -> payoff/relief ~10%.
""", [f"{MEME}@0:03"], applies=("stickman", "cinematic", "any"), tags=["comedy", "structure"])

add("paper-texture-hand-drawn-look", "Hand-drawn paper look: muted tint, uneven outlines, watermark-safe corner", "style-2d", "technique",
    "Doodle / whiteboard / storybook comedy where a hand-drawn feel is wanted.",
    ["hand drawn", "doodle", "paper", "pencil", "sketch", "storybook", "line boil", "cartoon"],
    """## Evidence (meme short)
Sage-grey-green paper background with faint sketch lines for the room, thick black outline character with uneven line weight, soap-foam and sweat as white/black doodles, channel handle as a semi-transparent watermark mid-frame.

## Procedure
Background `#a9b59a`-like paper tone with slight vignette; outline colour near-black `#111`, line width 4-6 px at 1080 wide; redraw/jitter the outline at 8-12 fps ("line boil") while the body moves at 24; one accent colour only for the payoff (red eye).
""", [f"{MEME}@0:01-0:09"], applies=("stickman", "2d"), tags=["style"])

# ----------------------------------------------------------------------------- anime Grease Pencil action clip
add("anime-action-speed-lines-and-accent", "Action shot: speed lines, dutch angle, one saturated accent colour", "effects", "technique",
    "Fast motion, flying, chase, dive, power-up, impact; anime / high-energy 2D look.",
    ["action", "fast", "speed", "dive", "flying", "chase", "anime", "power up", "energy", "rush", "dash"],
    """## Evidence (12 s Grease Pencil clip, 5 shots, 20 cuts/min, motion 33)
- Environment is desaturated blue-grey/brown; the *only* saturated colour is the magenta energy (glowing petals, a giant light shard) -> the eye follows the FX.
- Close-up at 0:06: thin dark **radial speed lines** converge on the character; camera is rolled (dutch angle); background terrain streaks.
- Character hair trails behind the motion with overlapping delay (follow-through).
- Cut pattern: dark establishing plunge (0:01) -> tracking medium (0:02) -> pose wide (0:03-0:04) -> speed-line close-up (0:06) -> particles beat (0:07) -> back-view exit (0:08).

## Procedure
1. Pick a muted palette for world/sky, choose ONE accent hue for energy, glow it (additive) and give it particles.
2. Speed lines: 40-80 thin lines radiating from a point behind the subject, random lengths, 2-4 frame life, re-randomised every frame (hold shots 2 frames).
3. Roll the camera 5-12 degrees on close-ups; blur/streak the background along the motion direction.
4. 2-3 s per shot; end on a back view or hold-out pose.
""", [f"{ANIME}@0:01-0:10"], applies=("cinematic", "3d", "2d"), tags=["anime", "fx"])

add("follow-through-secondary-motion", "Overlapping action: hair, cloth, antennas lag behind the body", "motion", "technique",
    "Any character or object that moves fast and stops: hair, capes, tails, antennae, straps should keep moving.",
    ["hair", "cape", "tail", "antenna", "follow through", "secondary motion", "overlap", "flowing", "trail", "flutter"],
    """## Evidence
Anime clip: long pink hair trails opposite to the flight direction and only settles after the body stops (0:02, 0:04, 0:08).

## Procedure
1. Body moves first; appendages start 2-4 frames later (offset the keyframes) and overshoot by 10-20% before settling.
2. For rigged parts use a damped spring: `angle(t) = A e^(-d t) cos(w t)` with d 3-5, w 12-18 rad/s.
3. For cloth/hair use physics (cloth pinned at the root with light gravity, or soft body) rather than hand keys.
""", [f"{ANIME}@0:02-0:08"], applies=("cinematic", "3d", "stickman"), tags=["motion"])

add("establishing-dark-to-light-reveal", "Open dark, reveal light: a fast establishing plunge", "pacing", "technique",
    "The first shot of an action or epic sequence needs impact and a sense of scale.",
    ["establishing", "opening shot", "reveal", "epic", "scale", "aerial", "fade in", "intro shot", "landscape"],
    """## Evidence
Anime clip 0:00-0:01: near-black aerial view of terrain that brightens as the camera plunges, followed by a bright wide of the hero.

## Procedure
Start the first shot at exposure -2..-3 and animate to normal over 0.8-1.2 s while the camera moves forward/down; hold the hero shot 1.5-2 s.
""", [f"{ANIME}@0:00-0:03"], applies=("cinematic", "3d"), tags=["camera"])

add("colour-script-muted-world-accent-fx", "Colour script: muted environment, single saturated accent for the action", "lighting", "rule",
    "Choosing colours for a scene so the important thing reads instantly.",
    ["colour", "color", "palette", "accent", "saturated", "muted", "contrast", "focus the eye", "color script"],
    """## Evidence
Anime clip: greys/browns for the world, hero in dark greys, hair soft pink, and the only fully saturated hue (magenta) for energy/FX. Stickman tutorial sample: pure black on white with grey secondary shapes.

## Procedure
Limit to a neutral base + 1 accent + 1 supporting colour; make the FX/prop that matters the highest-saturation, highest-luminance item; keep backgrounds 30-50% less saturated than the subject.
""", [f"{ANIME}@0:02-0:08", f"{SK}@9:01-9:41"], applies=("any",), tags=["colour"])

for meta, body in SKILLS:
    S.write_skill(S.SKILLS_DIR / meta["category"] / f"{meta['id']}.md", meta, body)
print("authored", len(SKILLS), "reference skills")
