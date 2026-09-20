# PAPER HEART — the photoreal-painterly pivot

Target look taken from `reference vedios/.../Anime Scenes made in Blender (Garden of Words…) 720P.mp4`
(47 s, 1280×720, 24 fps). Measured off the footage, not remembered.

This replaces the flat-toon direction in `script.md` §1. It is a real pivot and it changes the
production method more than it changes the art direction, so read the method section before
building anything.

---

## 1. What the reference is actually doing

The signature is **one specific combination**: flat cel-shaded *characters* composited over
**painterly, near-photorealistic environments**. Not toon everything. Not realistic everything.
The contrast between the two is the whole look.

Measured across sampled frames:

| | value | note |
| --- | --- | --- |
| Saturation | **54 – 147** (greens peak at 147) | Very high. Flat toon sits around 30–60 |
| Contrast (σ) | **38 – 93** | High, and it varies hugely shot to shot |
| Value | 90 – 184 | Deliberately blown highlights in the bright shots |

The stack, in order of how much it matters:

1. **Painterly environment detail.** Dense foliage, wet stone, distant city haze. Every surface
   has texture and variation. This is 80% of the look and it is the expensive 80%.
2. **Blown highlights.** Bright areas are allowed to clip to white — leaves against sky, a lamp,
   a window. Nothing is protected. This is the opposite of a careful exposure.
3. **Extreme shallow focus.** Foreground and background dissolve into large, soft bokeh.
4. **Rain, and what rain does.** Streaks in air, ripples in puddles, wet reflective ground,
   droplets on surfaces. The wetness is doing as much work as the rain itself.
5. **Volumetric light** through foliage and rain.
6. **Aerial perspective** — distance goes hazy and desaturates toward a tint.
7. **Lens character** — flare, chromatic aberration, slight vignette.
8. **Cel characters**, flat and simple, sitting inside all of it.

---

## 2. The hard part: this machine

Rendering that per frame is not possible here, and it is worth being exact about why rather
than discovering it eight hours in.

| Scene content | Measured / estimated per frame |
| --- | --- |
| Act 6 as it stands (60 flat planes, procedural sky) | **~28 s** (measured) |
| + dense vegetation, volumetrics, rain, wet reflections, heavy DOF | **3–15 min** (estimate, EEVEE, 4 cores / integrated Radeon / 6 GB) |

At 5 minutes a frame, 5136 frames is **428 hours — eighteen days**. And 6 GB RAM is the harder
wall than time: a single dense foliage scene can exceed it on its own.

**So do not render the environments per frame.**

---

## 3. The method that makes it possible — and it is the authentic one

**Anime backgrounds are painted once and characters are animated over them.** That is literally
how the medium works, including in the film this reference is imitating. A background is a
*plate*, not a per-frame render.

So:

| Layer | How | Cost |
| --- | --- | --- |
| **Environment** | Render **one still per shot** at maximum quality — minutes per frame is fine when there are 55 of them, not 5136. Add life with a 2.5D camera move over the still (parallax on 3–5 depth-separated layers) rather than re-rendering | 55 stills × 10 min ≈ **9 h**, once |
| **Characters** | Flat cel, rendered per frame over transparent film, composited on top | cheap — this is the only per-frame 3D |
| **Rain** | 2D streak layer, composited. Already prototyped in `build/paper_heart/style_test.py` | **milliseconds/frame** |
| **Bloom, haze, aberration, vignette, flare** | ffmpeg, per act | **milliseconds/frame** |
| **Puddle ripples, droplets** | short rendered loops, or 2D, composited | cheap |

This is not a compromise forced by weak hardware — it is how the craft is done, and it is why
hand-drawn anime can afford backgrounds far more detailed than anything animated per frame.

Already proven: `build/paper_heart/style_test.py` applies grade → haze → bloom → rain → lens to
a finished frame and lands at **sat 82.8, contrast 40.7**, inside the reference's measured band,
at no meaningful render cost. Run it to see the stack build up step by step.

---

## 4. What changes in the existing plan

| Element | Was | Now |
| --- | --- | --- |
| Environments | flat toon geometry | **painterly plates**, rendered once per shot, 2.5D parallax |
| Characters | flat toon | **unchanged** — cel is correct, it is what the reference does |
| Colour | muted two-palette | **saturation up hard**; keep the two-world split, push both further |
| Highlights | protected | **allowed to clip** |
| DOF | selective | **everywhere**, and stronger |
| Weather | none | **rain through the city acts**; the paper heart stays clear-sky at dusk |
| Outlines | inverted hull everywhere | **softer / thinner** — the reference's characters have delicate lines, not heavy toon outlines |
| Render budget | ~13 h | ~9 h of plates + a few h of characters + minutes of comp |

**The two-world colour script still works and gets better.** His cold office and her warm
cramped room both intensify: sat up, highlights blowing out through the window behind him, her
sodium bulb going properly amber. The convergence at the crossing is then a bigger event.

**Rain earns its place in the story, not just the look.** Put it through Acts 1–3: rain on his
office window, rain on her desk window, wet street at the crossing. Then **it stops at the
contact** (f3073) — the same frame the sound cuts. Act 6's sky is clear because the weather
broke when they met. That is the kind of thing this style is *for*.

---

## 5. What I can and cannot fetch

| | |
| --- | --- |
| **Can** | Poly Haven (CC0, public API, no login) — HDRIs, and vegetation/rock/ground assets. Procedural skies, rain, water, all the comp work |
| **Cannot** | The two characters (BOOTH/Mixamo/VRoid need a browser + login). Any asset behind an account |

Vegetation density is the one place to be careful with 6 GB: use instanced low-poly cards for
mid-ground foliage rather than full geometry, and lean on the DOF — most of the frame is out of
focus in this style anyway, which is a gift.

---

## 6. Order to do it in

1. **One test plate, all the way through.** Pick the crossing (S27) — wet street, city haze,
   low sun. Build it, render one still at max quality, comp the full stack over it. If that one
   frame looks right, the method is proven and everything else is repetition.
2. Re-grade Act 6 with the stack (it is already rendering; the comp is a post pass, so nothing
   is wasted).
3. Build the remaining plates shot by shot.
4. Characters last, once the models exist.

Act 6 as rendered is **not wasted by this pivot** — it is a clear-sky dusk sequence, which is
exactly what the story wants after the rain breaks, and the grade stack applies to it in post.
