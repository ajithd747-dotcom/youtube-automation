# PAPER HEART — handoff to a fresh machine

Everything needed to continue this film on a new laptop (30 GB RAM, 12 cores) that has no
memory of the project. Written 2026-09-20 on the old box (5.9 GB RAM, 4 cores, integrated
Radeon), which is why so much of what follows is about constraints that **no longer apply**.

---

## 0. PASTE THIS FIRST

Copy the whole project folder to the new machine, open a Claude Code session in it, and paste
the block below as your first message.

> I'm continuing an animated short called **Paper Heart** — a 3:34 wordless romance, 55 shots,
> 5136 frames at 24 fps, 1920×1080, built in Blender 4.5 and finished in ffmpeg.
>
> Read these four files first, in this order, before doing anything:
> - `scripts/paper_heart/HANDOFF.md` — state, build order, pitfalls (start here)
> - `scripts/paper_heart/script.md` — the full shot-by-shot script
> - `scripts/paper_heart/shots.json` — machine-readable shot list
> - `scripts/paper_heart/style_shinkai.md` — the target look and the method
>
> This machine has **30 GB RAM and 12 cores** — roughly 5× the memory and 3× the cores of the
> machine the project was built on. Section 3 of HANDOFF lists decisions that were made only
> because of the old hardware and should be re-evaluated. Do that re-evaluation before you
> build anything, and tell me what you'd change.
>
> First concrete task: run the benchmark in HANDOFF section 4 and report the numbers, so we
> know what this machine can actually afford.

---

## 1. What the film is

A man drowning in work and a woman drowning in exam pressure cross a street. Their eyes meet,
the world stops, and they both let go of the thing that was crushing them — his career call,
her exam papers. The papers catch the wind and draw a heart in the air.

No dialogue. No subtitles. The score carries it.

**The two sacrifices carry equal weight and the structure enforces that.** Acts 1 and 2 are the
same length and shot count. S46 (he ends the call) and S48 (she lets go) are both 120 frames.
Both release paper — he has gripped one worn folded page since S09, and it takes the notch at
the apex of the heart. And it has a consequence: at S54 the phone rings a **second** time on
the ground and he doesn't look. The first hang-up was reflex; ignoring the second ring is a
decision.

Runtime is set by one rule: *the audience must want him to take that call, and want her to keep
those papers, before either lets go.* That is why each world gets 48 seconds.

---

## 2. What is done, and what is not

| Piece | State | Where |
| --- | --- | --- |
| Full script, 55 shots, validated frame maths | **Done** | `scripts/paper_heart/script.md` |
| Machine-readable shot list | **Done** | `scripts/paper_heart/shots.json` |
| Score specification (keys, motif, modulations, heartbeat frames) | **Done** | `script.md` §2 |
| Character design sheet with palettes | **Done** | `scripts/paper_heart/characters.md` |
| Target-look analysis + method | **Done** | `scripts/paper_heart/style_shinkai.md` |
| **Act 6 render (the paper heart)** | **449 / 456 frames** | `renders/paper_heart/act6/` |
| Act 6 comp/finish script | Written, not yet run | `build/paper_heart/finish_act6.sh` |
| Crossing plate (S27) + comp method | **Proven** | `renders/paper_heart/plates/` |
| Dressed street version | **CRASHES** — see §5 | `build/paper_heart/plate_crossing.blend` |
| Character import + toon shader | Written, **never run** | `build/paper_heart/import_character.py` |
| Acts 1–5 | **Not built** — blocked on characters | — |
| The two character models | **Not sourced** — needs a human with a browser | see §7 |

**Immediate wins on arriving:**

```bash
# 1. finish Act 6 - 7 frames left, resumable, skips what's on disk
blender -b build/paper_heart/act6.blend -a

# 2. comp it to mp4
bash build/paper_heart/finish_act6.sh
```

---

## 3. Decisions to re-evaluate on the better hardware

These were forced by 5.9 GB RAM / 4 cores / integrated Radeon. **Most should now be reversed.**

| Decision | Why it was made | On 30 GB / 12 cores |
| --- | --- | --- |
| Environments as **still plates**, not per-frame | Per-frame was 3–15 min/frame → 428 h | Re-time it. Per-frame may now be affordable, which unlocks moving foliage, real camera moves, and rain that actually falls in 3D |
| **No Freestyle** line art | CPU-bound, 4 cores | 12 cores makes it plausible. Re-time; it gives better lines than inverted hull |
| **Inverted hull** outlines everywhere | cheap | Keep as default, but test Freestyle on the 12 hero shots |
| Only **12 hero shots** at high quality | render budget | Possibly render everything at hero quality |
| **1k textures** on models | memory | Go 2k–4k |
| Foliage kept sparse | 2 GB/plate ceiling | Real scatter systems become possible — this was the single biggest visual gap |
| Bloom/grade in **ffmpeg not the compositor** | compositor cost ~3 s/frame | **Keep this regardless.** It is faster everywhere and makes the grade iterable without re-rendering |
| Characters on **2s**, camera on **1s** | — | **Keep.** This is art direction, not a performance compromise. It is the main thing that reads as anime |

Do not undo the last two. Everything above them is fair game.

---

## 4. Benchmark first

Before committing to a plan, measure. Run these and record the numbers.

```bash
# A. does a textured plane render? (old box: yes at 1k, but see §5)
blender -b --factory-startup --python build/paper_heart/test_texture_crash.py

# B. the known-good plate, full quality  (old box: 6m59s, ~2.0 GB peak)
blender -b build/paper_heart/plate_crossing.blend -f 1

# C. a heavy animated frame              (old box: ~28 s/frame)
blender -b build/paper_heart/act6.blend -f 4752
```

If B lands under ~60 s, per-frame environment rendering is affordable and §3 row 1 flips.

---

## 5. The crash — a real, unresolved bug

`build/paper_heart/plate_crossing.blend` currently **crashes with `EXCEPTION_ACCESS_VIOLATION`**
and it is a reliable reproducer. Worth solving early, because it gates the environment work.

What is known:

- The old project notes blamed "image-textured planes in EEVEE". **That is not the whole story.**
- A 1024² file-backed texture on a plane renders **fine** (`test_texture_crash.py`, exit 0).
- Each downloaded model renders **fine alone** — lamps, poles, manhole covers, jacaranda tree
  all pass individually (`bisect_crash.py`).
- All of them **together** crash.
- It crashes at *every* setting tried: 960×540/64 samples with volumetrics and raytracing
  **off**, 1280×720/96, and 1920×1080/256. So it is not resolution, samples or effects load.
- 2.65 GB of system RAM was free at the time, so it is not plain system OOM.

Leading theory: **GPU memory exhaustion on the integrated Radeon**, which surfaces as an access
violation rather than a clean out-of-memory. If the new machine has a discrete GPU this may
simply evaporate — test it first. If it still crashes, bisect combinations rather than single
assets (`bisect_crash.py` takes `none|lamps|poles|covers|tree|all`).

The **previous** plate — real asphalt, textured facades, olive trees — renders fine at full
quality and is intact:
`renders/paper_heart/plates/S27_crossing.png` and `S27_final.png`.

---

## 6. Setup on the new machine

```bash
# Blender 4.5 LTS — match the version, the scripts use 4.5 API names
#   https://www.blender.org/download/lts/
# Verify:
blender --version

# Python side (for comp, scoring, contact sheets)
pip install opencv-python numpy scikit-image

# ffmpeg must be on PATH
ffmpeg -version
```

**Copy from the old machine** (whole folder is simplest):

| Path | Size | Needed? |
| --- | --- | --- |
| `scripts/paper_heart/` | ~85 KB | **Yes** — all the specs |
| `build/paper_heart/*.py`, `*.sh` | ~70 KB | **Yes** — all the build code |
| `build/paper_heart/tex/` | 31 MB | Yes (or re-download, §7) |
| `build/paper_heart/models/` | 288 MB | Yes (or re-download) |
| `renders/paper_heart/act6/` | 738 MB | Yes if you want the 449 rendered frames |
| `build/paper_heart/act6.blend` | 13 MB | Yes |
| `build/paper_heart/plate_crossing.blend` | 790 MB | Only as a crash reproducer — it rebuilds from script in seconds |

---

## 7. What a human still has to do

**Source the two characters.** This cannot be automated — every source needs a browser and a
login. See `characters.md` for full palettes, costume detail and search terms.

- **BOOTH.pm** (best quality) — search `VRM`, `VRChat`, `3Dキャラクター`. Most ¥1,500–5,000, many free
- **Sketchfab** — `VRM` / `anime-style` tags
- **VRoid Studio** (free) — build them yourself in ~20 min each; both designs are within its presets
- **Mixamo** (free, Adobe login) — walk cycles, idle, sitting, typing, look-up

Design them as **original characters** to the specs in `characters.md`. If you pick a
ready-made model that resembles an existing franchise character, check its licence terms —
that is a different question from the palettes and costume notes in the sheet, which are
original design direction.

Then install the VRM addon (already downloaded to `build/paper_heart/vendor/vrm_ext.zip`) and:

```bash
blender -b --python build/paper_heart/import_character.py -- path/to/girl.vrm girl
blender -b --python build/paper_heart/import_character.py -- path/to/man.vrm  man
```

That script has **never been run against a real model.** Expect the material-name matching to
need widening — it prints every material and what it matched, so one run makes it obvious.

**Assets re-download** (CC0, no login, public API — a working example is in the git history of
`build_plate_crossing.py`): Poly Haven at `https://api.polyhaven.com/`, needs a `User-Agent`
header or it 403s. Textures used: `asphalt_02`, `concrete_floor_worn_001`, `concrete_wall_008`,
`damaged_plaster`, `brick_4`. Models: `jacaranda_tree`, `street_lamp_01`,
`modular_electricity_poles`, `water_manhole_cover`.

---

## 8. Build order

1. **Benchmark** (§4) and re-evaluate §3. Report before building.
2. **Finish Act 6** — 7 frames, then `finish_act6.sh`.
3. **Solve or sidestep the crash** (§5).
4. **Lock the music.** Everything cuts to it; the spec is in `script.md` §2. Free route:
   Spitfire LABS in any DAW. Fast route: the Suno/Udio prompt is in that section verbatim.
5. **Grey-box animatic** at 480p for all 55 shots with real camera moves. Fix pacing here —
   a 3:34 wordless film lives or dies on pacing and this is the only cheap place to find a sag.
6. **Characters** (§7).
7. **Environments** — plates or per-frame depending on the benchmark. Start with S27; it is the
   only one already built.
8. **Render, comp per act in ffmpeg, assemble.**

---

## 9. Pitfalls already paid for

Each of these cost real time on the old machine. They are not hardware-specific.

- **Colour management must be `Standard`, not Filmic.** Filmic is built for photographic
  latitude and turns flat colour bands into gradients — it destroys the cel look. One setting,
  large effect.
- **Bloom, glare, grade and vignette belong in ffmpeg**, never the Blender compositor. ~3 s/frame
  there against milliseconds here, and it makes the grade iterable without re-rendering.
- **A white subject on a bright sky is invisible.** The first Act 6 exposure clipped the sky to
  white and the heart vanished into it. The sheets have to be the brightest thing in frame.
- **The camera must be low for anything meant to read against the sky.** At eye height the
  paper heart projected below the horizon onto dark ground and stopped reading as a shape.
- **Do not simulate the heart.** A rigid-body solver never lands 60 cards on a clean curve. The
  papers fly a hand-authored path and the heart is what their flight draws. Constant-arc-length
  resampling is what keeps them evenly spaced — sampling the raw curve bunches them at the
  lobes and starves the point, which is exactly where the eye checks the shape.
- **Direction matters in that path**: she is screen right, so the ribbon climbs her side first
  and comes down his. Reversed, the gesture reads backwards.
- **Species is not a detail.** An arid olive tree on a wet temperate street reads wrong
  instantly. Most of how an audience places a location is vegetation.
- **Untextured blocks read as cardboard** no matter how well lit. Real surfaces were the single
  biggest step up in the plate.
- **`use_overwrite=False`** on renders makes them resumable — but it also silently skips frames
  already on disk, so delete before re-rendering a changed shot or you will review stale frames.
- **Python output is block-buffered when redirected.** Use `python -u` for anything whose
  progress you intend to watch, or it looks hung for minutes.
- **A process check that greps for process names matches itself** and loops forever. Match on
  process name, not command-line substring.
- **Stopping a background task does not stop its children.** One kept rendering for 20 minutes
  after being "stopped" and raced a foreground job over the same files. Kill the tree.

---

## 10. Reference material

- Target look: `reference vedios/vedios/blender reference vedios/vidssave.com Anime Scenes made in Blender (Garden of Words by Makoto Shinkai) - Recreation 720P.mp4`
  — the style analysis with measured values is in `style_shinkai.md`. Measured band: saturation
  54–147, contrast 38–93.
- Character references: drop the two supplied images into `scripts/paper_heart/reference/` as
  `girl.jpg` and `man.jpg`. They arrived through chat and were never on disk; `characters.md`
  captures everything that drives the build.
