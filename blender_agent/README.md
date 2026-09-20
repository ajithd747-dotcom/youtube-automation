# Blender video agent

Paste a script -> get an animated MP4. Blender runs headless, no GUI needed.

```bash
python blender_agent/agent.py scripts/procrastination-joke_script.json      # existing pipeline script (.json/.md)
python blender_agent/agent.py --paste                                       # paste text in the terminal, finish with a line: END
python blender_agent/agent.py --clipboard                                   # use the script text on your clipboard
python blender_agent/agent.py --text "Sentence one. Sentence two. ..."
python blender_agent/agent.py script.txt --style cinematic --qa --plan-only  # 3D + physics, with visual QA, review the plan first
```
Options: `--style auto|stickman|kinetic|3d|cinematic` `--format normal|shorts` `--preview` (360p/12fps draft) `--quality draft|standard|final`
`--qa` `--plan-only` `--engine auto|eevee|workbench|cycles` `--voice <edge-tts voice>` `--replan` `--no-custom` `--no-tts` `--max-segments N` `--name X` `--out file.mp4`

Output: `video/<name>_blender.mp4` (working files in `blender_agent/work/<name>/`, plan in `plan.json` - edit it and re-run: only changed shots re-render).

## Styles
| style | what Blender does | speed on this laptop |
|---|---|---|
| `stickman`, `kinetic`, `3d` | procedural 2D/3D scenes from a small JSON DSL, Workbench/EEVEE | seconds per shot |
| `cinematic` | 12 tested scene recipes with PBR, ray-traced reflections/refraction, soft shadows, volumetric haze, DOF, motion blur, bloom, real physics | 3-6 s/frame at 720p |
| `anime` (presets, used by `recreate/`) | toon shading + hull outlines, posable original hero with lagging hair, energy FX, roll cameras | 1.4 s/frame at 1080p |

### Cinematic recipes (`blender_side/cine_recipes*.py`)
`robot_intro`, `workshop_walk`, `glass_showcase`, `domino_run` (rigid bodies), `crate_smash` (rigid bodies), `cloth_banner` (cloth + wind),
`fireworks` (particles), `jelly_pit` (soft body + rigid bodies), `finale_confetti` (particles + turbulence), `campfire_smoke` (**Mantaflow fire + smoke**),
`water_splash` (**Mantaflow liquid**), `fuzzy_creature` (**particle hair/fur**). The director picks recipe + mood + title per segment from the meaning
of the narration (skills decide); `visual-qa` (`--qa`) still-checks every shot and fixes exposure/haze before the long render.

## Skills (the agent's learned know-how) - `blender_agent/skills/`
Markdown + YAML files: what it achieves, **when to use it (triggers)**, procedure, measured parameters, pitfalls, code, exemplar clip, headless test.
- `python blender_agent/skills.py list | show <id> | match "<script text>" | validate | verify | stats | learn <run> | promote <id>`
- Statuses: `verified` (tested / used in a finished video), `reference` (distilled from a reference video/book, advisory), `candidate` (auto-proposed, never used until verified).
- Used automatically: the director gets the best-matching skills for each segment, the coder gets technique/pitfall skills next to the Blender docs, every run records usage
  and turns human edits of `plan.json` into candidate skills.
- Grow it: `python blender_agent/skill_extract.py video|text <file>` builds an evidence pack (transcript, cuts, motion, loudness, contact sheets) in `skills/sources/`;
  drop books/PDFs in `reference vedios/` and run `skill_extract.py all`; `skill_extract.py distill <slug>` drafts candidates with the LLM.
- Author batches live in `skills/_author_*.py` (re-runnable).

## Recreate + benchmark a reference video (`recreate/`, `benchmark/`)
`python blender_agent/benchmark/compare.py <reference> <recreation> <out_dir> [--speech <transcript.json>]` -> SSIM, colour histogram, cuts, motion, WER, pitch,
loudness, side-by-side video, contact sheet. `recreate/anime_clip.py` (12 s anime action clip: Blender toon presets + music agent) and
`recreate/tutorial_voice.py` + `record_gui.py` + `assemble_tutorial.py` (10 min Blender tutorial: matched narration + a REAL Blender GUI screen recording made by a scripted tour).

## Agents (`../agents/`)
`python agents/cli.py list | count | verify | create-agent | create-tool | create-skill`. Music agent (FluidSynth + numpy synth, reference matching), voice agent
(Kokoro local TTS + edge-tts, word timings, karaoke captions), visual-qa agent, plus the Blender/skill/benchmark agents. Each has its own skill library.

## Knowledge base (docs the coder retrieves)
`knowledge/kb.py` BM25 index of Blender's own API (dumped from the installed binary), the cookbook, learned fixes, **verified skills**, and anything in `knowledge/docs_inbox/`
or crawled (`kb.py build --crawl <url>`). `kb.py search "<query>"`.

## Setup notes
- Blender 4.5 LTS (`blender` on PATH); `BLENDER_PATH` overrides detection. ffmpeg/ffprobe on PATH. `.env` LLM keys for the director/coder (falls back to heuristics).
- Audio tools downloaded into `agents/tools_bin/`: FluidSynth 2.6.1 + GeneralUser GS soundfont. pip: faster-whisper, kokoro, soundfile, mido, piper-tts.
- GUI recording takes over the screen (fullscreen) for ~9 minutes; do not touch the machine meanwhile.
- Hardware reality (2 cores, integrated GPU, 6 GB): cinematic ~3-6 s/frame at 720p; a 1-minute video = 1-2 hours; use `--quality draft --preview` while iterating.

## Known limits
- Shots come from a fixed, tested recipe library (12 cinematic + 13 anime presets + the 2D DSL); new scene types are added as recipe + skill, or via the coder for small effects.
- Characters are stylised (robot, toon hero, fuzzy creature), not realistic humans; text is ASCII-only.
- Recreations match structure, timing, palette logic and audio characteristics of a reference, not its hand-drawn art or its narrator's real voice (never cloned).
