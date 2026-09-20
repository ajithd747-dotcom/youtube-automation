# youtube-automation -- standing rules for any Claude session in this repo

These rules live **in the repo, not in ~/.claude**, so they survive a change of VPS. Set by the owner on 2026-09-20.
`training/SPEC.md` is the canonical definition of the training work; this file is the short version that loads every session.

## The project

Research -> script -> video -> upload pipeline, a Blender animation agent (`blender_agent/`) and a password-protected
review dashboard (`dashboard/`). **Current goal:** train the Blender agent by recreating every reference video from
scratch -- picture, character voice-over and background music -- frame by frame, scoring each frame against the reference
and adjusting the script until it stops improving, and saving the skills learned. Reference videos are uploaded through
the dashboard into `reference vedios/`.

## Rules

1. **All files live inside this folder.** Tools go in `tools/` (see `tools/README.md`), services are described in
   `operate/README.md`, scratch and outputs go under the repo (gitignored). Nothing new in `~/.local`, `~/.cache` or
   `/tmp` except thin symlinks and package-manager caches you cannot redirect. Downloading tools needs no permission.

2. **The per-frame script standard is the default for ANY script, storyboard or shot plan about a video.** A script
   written for the recreation work must capture, for every frame or shot: **lighting, camera and subject motion,
   physics, composition, colour, transitions, audio and characters** -- plus depth/focus and on-screen text. Every value
   is backed by a measurement (`training/describe_frames.py`); anything that cannot be measured is written
   `NOT MEASURED`, never guessed and never defaulted. Do not write a script from imagination or from the title of a
   video. Full field list: `training/SPEC.md` section 4. Procedure: the `frame-script-standard` skill
   (`.claude/skills/`) and the `frame-script-writer` agent (`.claude/agents/`). The Blender agent's own copy is
   `blender_agent/skills/workflow/per-frame-script-standard.md`, marked `always: true` so its director never plans without it.

3. **Reference videos are other people's copyrighted work.** They and everything derived from them (frames, tables,
   recreations, evidence packs) stay local and gitignored. Recreations exist to measure and train the agent; never
   upload one, never put one in the dashboard's "Created" group.

4. **Environment:** Linux VPS, 12 CPU cores, 30 GB RAM, no GPU. Run Python with `.venv/bin/python`. Blender is
   `tools/blender-wrapper.sh` (CPU/software GL). `ffmpeg` has libass but **no `drawtext`**. Ollama runs from `tools/ollama`
   and is the keyless fallback in `llm_router.py`; cloud provider keys live in `.env` (gitignored, never read or print them).
   Use the cores: parallelism is worker processes, not more agents (max 5 subagents at once).

5. **Verify, then claim.** Before multi-step work say how it will be verified; after, run it and report the real result.
   A recreation iteration counts only if Blender rendered the frames and they were scored in the same run.

6. **Everything is in git, and git is the backup.** Commit the piece of work that produced a change. Pushing goes to a
   private GitHub repo only after checking it is private and scanning for credential shapes.
