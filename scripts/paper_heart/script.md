# PAPER HEART — wordless romance

**Runtime 3:34 · 5136 frames @ 24 fps** · 1920×1080 · no dialogue, no subtitles · score-driven

A man drowning in work and a woman drowning in exam pressure cross a street. Their eyes meet,
the world stops, and they both let go of the thing that was crushing them — his career call,
her exam papers. The papers catch the wind and draw a heart in the air.

**The two things they release carry equal weight, and the film has to earn both.** His call is
months of waiting; her papers are a year of it. Neither is a small gesture and neither is the
other's support act. The structure enforces it: Act 1 and Act 2 are the same length and the
same shot count, S46 and S48 are both 120 frames, and — the part that matters most — **they
both let go of paper.** He has been gripping one worn folded page since S09, the pitch he
rehearsed for months. When the call dies he opens that hand too. His single creased page flies
up with her hundreds, and it is the page that takes the notch at the top of the heart.

Without that, her sacrifice becomes something beautiful and his merely stops — equal screen
time, unequal weight. One page fixes it: the heart is made of both of them.

**And the sacrifice has to lead somewhere or it costs nothing.** So at the end the phone rings
a second time (S54), lying on the ground among her scattered sheets, and he does not look at
it. The opportunity is still live — that is what makes the price real and ongoing rather than
a single impulse he might not have meant. The first hang-up was a reflex; **ignoring the second
ring is a decision.** He chooses again, this time knowing.

It deliberately never says whether he loses the job. Show him ruined and it becomes a morality
tale about career versus happiness; show it working out and it becomes a fantasy. Leaving it
open keeps it a love story. The image that carries it is both of their abandoned things lying
together — his dead phone and his creased page among her white paper — and neither of them
looking down.

---

## Why 3:30

The first pass ran 60 seconds and it was the wrong length. Each world got 11 seconds — enough to
*state* "he is busy, she is stressed", nowhere near enough to make an audience *feel* it. And
the ending only lands if the two things they give up genuinely hurt to give up.

So the runtime is set by one rule: **the audience must want him to take that call, and want her
to keep those papers, before either of them lets go.** That costs time.

| | 0:60 version | this version | what the time buys |
| --- | --- | --- | --- |
| His world | 11s | **48s** | repetition, missed meals, 7 missed calls, the pitch he's been rehearsing — so the call has a price |
| Her world | 11s | **48s** | the argument through the door, the bill, the photo turned face down, months of red X's |
| Crossing | 12s | **32s** | near-misses, the crowd, the slow inevitability |
| Contact & stop | 12s | **36s** | room to actually hold on their faces |
| Letting go | 12s | **22s** | the hesitation has weight |
| Paper heart | 14s | **24s** | the heart forms, *holds*, and breaks |

Longer than this and a wordless piece sags. 3:30 also matches the natural arc of an emotional
instrumental — verse, verse, build, peak, resolve — which matters because this film is cut to
music, not to action.

**54 shots. Render budget:** 5040 frames × ~1.4 s/frame toon at 1080p ≈ **2 hours** for a full
pass, plus the paper sim bake. Preview at 50% ≈ 30 min.

---

## 1. Style decision: 3D toon, not hand-drawn 2D

You asked for the art to come from online rather than be drawn from scratch. That decides it.

**Go 3D, shaded to look 2D.**

| | hand-drawn 2D | 3D toon (chosen) |
| --- | --- | --- |
| What's actually available online | static illustrations, inconsistent styles | **rigged, posable anime characters + motion capture** |
| 5040 frames of a consistent character | you'd be drawing every one | pose the same model across 54 shots |
| Style drift | severe — every source artist differs | none, one model |
| Render cost here | ~1.4 s/frame | ~1.4 s/frame |

You cannot download 5040 frames of consistent 2D character animation. You *can* download a
rigged anime character and a walk cycle in ten minutes. The 2D look then comes from **shading
and timing**, not drawing: a hard two-step toon ramp, an inverted-hull outline, character acting
held **on 2s** while camera and FX run on 1s, and the sparkle / bloom / speed-line layer
composited in ffmpeg.

That "characters on 2s, camera on 1s" split is the single biggest thing that reads as anime
rather than as a game cutscene.

### Where the art comes from — highest quality tier

VRoid is the *fast* answer. It is not the *best* answer: its default output reads as generic
"VRoid face" and anyone who watches anime will clock it instantly. For the highest quality:

| Need | Best source | Why it's the top tier |
| --- | --- | --- |
| **Both characters** | **BOOTH.pm** — search `VRM`, `VRChat`, `3Dキャラクター` | Japanese creator marketplace. Professionally made VRChat/VRM avatars: proper edge flow, hand-painted textures, real hair cards, full blendshape sets, anime-correct eye geometry. Most are ¥1,500–5,000 (~$10–35); a lot are free. **This is where the good anime models actually live.** |
| Alternatives | **Sketchfab** (`VRM`, `anime-style` tags), **VRoid Hub** | Sketchfab has downloadable rigged anime characters; VRoid Hub is free but more variable. |
| Fallback | **VRoid Studio** + custom textures painted in Krita | Free. Only use if you're willing to repaint the face/hair textures by hand — that's what lifts it out of "default VRoid". |
| Body animation | **Mixamo** (free) | Walk cycles, idle, sitting, typing, look-up. Auto-retarget. Hand-key the acting beats on top. |
| Environments & props | **Poly Haven** (CC0), **BlenderKit**, **Quaternius / Kenney** | Office, desk, monitors, book towers, street. |
| HDRI lighting | **Poly Haven** (CC0), 4K+ | `studio_small_08` office; low-sun HDRI for the street. |
| Shading | **Free NPR node kits** (Blendkit, itch.io NPR starter packs) or roll your own | See §8 — the shader matters more than the model. |

Since you're not publishing, licences don't gate anything here.

**The thing that actually determines quality is not the model — it's the shading.** A mid-tier
BOOTH model with a properly built anime shader beats a premium model with default materials,
every time. Budget your effort accordingly: §8 is where the quality lives.

### ⚠ The honest constraint: this machine

"Highest quality" and "2 CPU cores, integrated Radeon, 6 GB RAM" are in direct tension. Real
numbers for 5040 frames:

| Tier | Setup | s/frame | Total render |
| --- | --- | --- | --- |
| Draft | 480p, flat toon, no DOF | ~0.4 | **35 min** |
| Standard | 1080p, basic toon, inverted hull | ~1.4 | **2 h** |
| **High** ← recommended | 1080p, full NPR shader, hair specular, anime eyes, rim light, DOF, 64 samples | ~5 | **7 h** |
| Very high | 1440p, same + volumetrics everywhere | ~12 | **17 h** |
| Freestyle lines | any of the above **+ Freestyle** | +15–40 | **+21 to +56 h** |

**Recommendation: High tier, and do not use Freestyle globally.** Freestyle is CPU-bound and
you have two cores — it would take longer than everything else combined. Inverted hull is what
actual anime games ship (Guilty Gear Xrd, Arc System Works) and at this resolution the
difference is invisible in motion.

**Where to spend the extra quality — selectively.** Studios don't render every shot at max.
Nominate ~12 hero shots (the close-ups where faces carry the film) and render *those* with
Freestyle line art and higher samples; leave the 42 wides and inserts on inverted hull:

> Hero shots: **S03, S16, S33, S34, S36, S38, S39, S40, S44, S46, S48, S52**

That's ~1,100 frames at ~25 s/frame ≈ 7.5 h, plus ~3,900 frames at ~5 s ≈ 5.5 h → **~13 h total**
for a film that looks maxed-out everywhere it matters. Run it overnight.

**6 GB RAM is the real ceiling, not the GPU.** High-poly BOOTH models plus a full environment
will thrash. Mitigations: render one shot per Blender process (your pipeline already does this),
decimate background props, use proxies for anything beyond mid-ground, and keep only the
characters in the shot at full resolution.

### ⚠ Test this before building anything

This machine's Radeon driver **crashes EEVEE on image-textured planes** (`atio6axx.dll`) — it's
in the project notes from the 2D pipeline. A VRM character *is* an image-textured mesh.

Render one frame of one imported VRM before you model, rig or animate anything. If it crashes,
bake each character down to flat toon colours — a VRoid model is flat anime art anyway and loses
almost nothing. Budget an hour either way.

Other constraints from this project that apply directly:
- **Bloom, glare, vignette in ffmpeg — not the compositor** (~3 s/frame there vs ms here).
- **World volumes render black on this GPU** — god-rays in Act 6 need a volume *box*.
- **Rigid bodies need frame pre-stepping** before an animation render — critical for the paper.
- **Every shot must render exactly `round(dur × fps)` frames.**

---

## 2. The score — full specification

No dialogue means the music *is* the edit. Lock the track first, cut to it second. Reference
territory: **Joe Hisaishi** (melody), **Ludovico Einaudi** (piano intimacy), **Rachmaninoff**
(the peak). Neo-classical, orchestral, no electronics, no drums.

### The one idea the whole score is built on

**A four-note descending motif that never resolves — until the last eight bars of the film.**

```
THE MOTIF (his, A minor, 68 bpm):     A – G – F – E      falling, resigned, loops
HER VERSION (D minor, up a fourth):   D – C – B♭ – A     same shape, more urgent
```

Up a perfect fourth is deliberate: it is literally the same melody one step higher in tension,
so the two worlds *sound like the same person in different rooms*. And D minor against A minor
is a IV–i relationship — it **wants** to resolve to the other. When both motifs finally play
together in Act 3 they slot into each other like they were always one melody.

At the peak the motif **inverts and ascends** (E – F – G – A) for the first time. At the very
end it resolves to the tonic — the first resolved cadence in three and a half minutes. That
withheld resolution is why the ending will feel earned rather than sweet.

### Key and tempo map

| Frames | Time | Key / tempo | Instrumentation | Musical event |
| --- | --- | --- | --- | --- |
| 1–1152 | 0:00–0:48 | **A minor**, 68 bpm | Solo piano, close-mic, heavy pedal. Clock tick. | His motif, looping, never cadencing. Each time the day repeats (S05) **add one more inner voice** — by the fourth loop it's cluttered and suffocating |
| 1153–2304 | 0:48–1:36 | **D minor**, 72 bpm | Solo cello carries the melody; piano underneath | Her motif. Cello because it sits in the human chest register — it feels like held breath |
| 2305–3072 | 1:36–2:08 | **D minor → F major**, 72→84 bpm | Piano + cello + violin, strings enter pp | The two motifs interleave in counterpoint. First warmth in the film |
| **3073** | **2:08.0** | **silence** | — | **EVERYTHING STOPS.** See below |
| 3073–3216 | 2:08–2:14 | sustained **A** | One violin harmonic + sub-bass + heartbeat | The single note both themes share |
| 3217–3936 | 2:14–2:44 | **F major**, 84 bpm | Violin melody, strings swelling underneath | Motif **inverts and ascends** for the first time. Heartbeat 60→130 bpm |
| 3937–4464 | 2:44–3:06 | **F major**, 76 bpm | Full strings, piano returns, cello countermelody | Main theme opens properly. His and her voices now playing the *same* line an octave apart |
| 4465–4751 | 3:06–3:17 | **F → A♭ major**, 72 bpm | Full strings + harp glissandi | The lift. Modulating up a minor third — the classic transcendence move |
| **4752** | **3:17.0** | **A♭ major** | + **wordless female choir**, 8 voices | **PEAK.** Sun bursts through the heart. Everything at once |
| 4753–4920 | 3:17–3:25 | A♭ → F | Choir thins out, strings sustain | Release |
| 4921–5040 | 3:25–3:30 | **F major**, 60 bpm | Solo piano, alone | The motif once, slowly, **ascending — and it finally resolves** |

### The silence at f3073 is the most important sound in the film

Everything before it is noise: phones, traffic, crowd, pages, that clock. At the eye contact:

- cut **all** diegetic sound to zero over 3 frames (f3073–3075)
- cut the music dead on the same frame — no tail, no reverb wash
- leave **one violin harmonic on A** and a **sub-bass drop** (40 Hz, 1.5 s decay)
- the heartbeat enters at f3081

A full second of near-silence at 2:08 in a 3:30 film is a big swing. It will feel wrong when you
first cut it and right when you watch it with someone else in the room.

### The heartbeat is a musical instrument, not a sound effect

Soft kick + 45 Hz sub, no click. Place hits exactly on the frames in §5 — they accelerate
72→120 bpm through S38/S39, then to 288 bpm in S41 where the two pulses merge into one. Duck
the strings 2 dB on every hit so the audience feels it in their chest rather than hears it.

### Getting the actual audio at this quality

| Route | Quality | Notes |
| --- | --- | --- |
| **Spitfire Audio LABS** (free) | ★★★★★ | *The* answer for free film-grade instruments. `Soft Piano`, `Strings`, `Cello`, `Voices` are genuinely used in released scores. Needs any DAW (Reaper is ~free). You play the motif above and it sounds like a real score. |
| **Suno / Udio** (paid, cheap) | ★★★★☆ | Fastest route to a full orchestral 3:30. Prompt below. Since you're not publishing, no licence concern. |
| **Pixabay Music / Uppbeat / Chosic** | ★★★☆☆ | Free, instant, but you're fitting your edit to someone else's structure rather than the reverse. |
| Your **FluidSynth + GeneralUser GS** agent | ★★☆☆☆ | Honest assessment: a General MIDI soundfont will not deliver "intense romantic orchestral" — GM strings sound like MIDI. **Use it to mock up the motifs and lock the timing**, then replace with LABS or Suno for the final. That's still genuinely useful: it's how you test the 3:30 structure for free. |

Ready-to-use generation prompt:

> *Emotional neo-classical orchestral score, 3 minutes 30. Begins solo close-mic piano in A minor,
> 68 bpm, a falling four-note motif that loops without resolving, lonely and mechanical. At 0:48
> a solo cello takes the same motif in D minor, warmer but more anxious. At 1:36 piano and cello
> interleave and strings enter quietly, modulating toward F major. At 2:08 everything cuts to
> near-silence — one sustained high violin harmonic and a slow heartbeat. Strings swell back from
> 2:14, the motif now ascending instead of falling. Full warm strings from 2:44. At 3:06 it
> modulates up a minor third to A♭ major and a wordless female choir enters for a huge romantic
> peak at 3:17 with harp. Falls back to solo piano at 3:25 and resolves gently. No drums, no
> percussion, no electronics, no vocals with words. Hisaishi and Rachmaninoff influence.*

---

## 3. Colour script

Two cold, separate palettes → converge → warm gold.

| Act | Palette | Hex |
| --- | --- | --- |
| His world | Cold corporate. Blue-grey, cyan monitor spill, dead fluorescent | `#2B3440` `#4A5A6A` `#7FD4E8` `#C9D6DE` |
| Her world | Warm but oppressive. Sodium bulb, dusty amber, paper too bright | `#3A2C22` `#8A6A45` `#D9A441` `#F2EDE4` |
| Crossing | The palettes meet — his cool from screen left, her warm from screen right | `#4A5A6A` → `#D9A441` |
| The stop | Everything greys out **except them** | crowd `#9A9A9A` @ 15% sat |
| The heart | Full saturation, rose gold, flare | `#FFD9A0` `#FF9E7A` `#FF6B8A` `#FFF6EC` |
| Resolve | Soft pastel, low contrast | `#F7E3D3` `#E8B9A8` |

Grade per act in ffmpeg at the end, not per shot.

---

## 4. Shot list — 54 shots

### ACT 1 · THE GRIND (his world) — f0001–1152 · 0:00–0:48

The job: make the audience feel the weight, and make them *want him to get that call*.

| Shot | Frames | Dur | Content |
| --- | --- | --- | --- |
| **S01** | 0001–0072 | 3.0s | Extreme macro, wall clock second hand. Cold fluorescent. Mechanical steps, no ease. Cut on the tick. |
| **S02** | 0073–0168 | 4.0s | Whip-pan across open-plan office. Nobody looks up. Heavy horizontal smear f0100–0120. Background figures on 3s, deliberately stiff. |
| **S03** | 0169–0264 | 4.0s | **HIM at his desk.** Phone on shoulder, three monitors, sticky notes fringing the screens. Tie loose, dark circles. **On 3s — almost nothing moves.** Fingers, one blink f0230, a cursor on 1s. The stillness is the character. |
| **S04** | 0265–0336 | 3.0s | Insert: unread count climbing — 47, 48, 51. A task list that scrolls and never ends. |
| **S05** | 0337–0432 | 4.0s | **The days repeat.** Same desk, same pose, light changing: morning white → afternoon gold → evening blue → night black. Four dissolves, 24 frames each. He barely moves between them. |
| **S06** | 0433–0504 | 3.0s | Insert: a lunch gone cold and untouched. Three coffee rings on a report. |
| **S07** | 0505–0600 | 4.0s | He rubs his eyes. In the dark monitor he catches his own reflection and holds it a beat too long. |
| **S08** | 0601–0696 | 4.0s | Phone buzzes face-down. He flips it: **7 missed calls — SUPERIOR.** He's been unreachable, drowning. |
| **S09** | 0697–0792 | 4.0s | He mouths something silently to himself — rehearsing. A folded page of notes in his fist, worn soft from handling. **This is the pitch he's been waiting months to give.** |
| **S10** | 0793–0888 | 4.0s | **The call comes.** Screen lights: SUPERIOR — INCOMING. He sits bolt upright, straightens his tie for a phone call, breathes once. |
| **S11** | 0889–0984 | 4.0s | He answers. Nods. Listens hard. First time in Act 1 his face has hope in it. |
| **S12** | 0985–1080 | 4.0s | Still on the call, he walks — corridor, lift, lobby. Speed-ramped: the world blurs, the call is all that exists. |
| **S13** | 1081–1152 | 3.0s | He pushes out of the revolving door into low golden street light, phone still at his ear. |

**Why S09 matters:** without it, hanging up in Act 5 is just a nice gesture. With it, it costs
him something the audience watched him earn.

### ACT 2 · THE WEIGHT (her world) — f1153–2304 · 0:48–1:36

Structurally identical to Act 1 — same shot count, same rhythm, mirrored. That symmetry is what
says *these two are the same person in different rooms* before they ever meet.

| Shot | Frames | Dur | Content |
| --- | --- | --- | --- |
| **S14** | 1153–1224 | 3.0s | Macro on a wall calendar. Red X's, dozens of them, marching toward a circled exam date. Mirror of S01's clock. |
| **S15** | 1225–1320 | 4.0s | Slow pan of her room: towers of prep books, paper everywhere, a fan losing its fight. Cramped where his office was vast. |
| **S16** | 1321–1416 | 4.0s | **HER at her desk.** Highlighter in her teeth, hair tied up badly, same dark circles. **On 3s. Same 3% push-in as S03.** Blink f1382. Anxious arrhythmic pen tap on 2s. |
| **S17** | 1417–1488 | 3.0s | Insert: mock-test score circled in red. Below target. Under it, three older sheets — also circled, also below. |
| **S18** | 1489–1584 | 4.0s | **Her days repeat.** Same desk, light cycling morning → night, four 24-frame dissolves. Mirror of S05. The book tower grows a little each time. |
| **S19** | 1585–1656 | 3.0s | Insert: a cup of tea someone left hours ago, skin formed on top, untouched. Beside it, a plate of food also untouched. |
| **S20** | 1657–1752 | 4.0s | Door ajar. Two silhouettes in the next room, arguing — shapes only, never faces. She puts on headphones. **Nothing is playing.** |
| **S21** | 1753–1848 | 4.0s | She picks up a framed family photo, everyone smiling, looks at it a long moment, and turns it face down. |
| **S22** | 1849–1944 | 4.0s | Insert: an envelope on the table she wasn't meant to see — FINAL NOTICE. She reads it, puts it back exactly where it was. |
| **S23** | 1945–2040 | 4.0s | She squares the A4 stack — hundreds of printed sheets, a year of work. Her thumb runs down the edge of it the way you touch something you have bled for. This stack is her way out, and it is also the thing crushing her; that double meaning is what makes dropping it cost something. **Establish it clearly — it becomes the heart.** |
| **S24** | 2041–2136 | 4.0s | She tries to work. Can't. The walls feel closer — a slow 8% lens compression over the shot sells it without moving anything. |
| **S25** | 2137–2232 | 4.0s | She stands, grabs the stack to her chest, and goes — down a dim stairwell, past the closed door of the argument. |
| **S26** | 2233–2304 | 3.0s | She pushes out into the same golden street light. Mirror of S13. |

### ACT 3 · THE CROSSING — f2305–3072 · 1:36–2:08

| Shot | Frames | Dur | Content |
| --- | --- | --- | --- |
| **S27** | 2305–2400 | 4.0s | Wide, symmetrical, locked. The crossing. He enters bottom-left (cool side), she bottom-right (warm side). Neither looks up. |
| **S28** | 2401–2496 | 4.0s | His side. Walking fast, talking into the phone, weaving through people. |
| **S29** | 2497–2592 | 4.0s | Her side. Walking slowly, hugging the papers, head down. |
| **S30** | 2593–2688 | 4.0s | The crowd flows between them. Two near-misses where a body passes through the sightline exactly when one of them might have looked up. |
| **S31** | 2689–2784 | 4.0s | Signal changes. The crowd surges from both sides. They step into the crossing. |
| **S32** | 2785–2880 | 4.0s | The gap narrows. Still not looking. Camera low, between their feet, crowd legs on both sides. |
| **S33** | 2881–2952 | 3.0s | **He lifts his eyes.** Mid-sentence into the phone. 4-frame lift: f2917 down → 2919 mid → 2921 up → 2923 settle. Hold. Pupils dilate 15%. |
| **S34** | 2953–3012 | 2.5s | **She lifts hers.** Mirrored, half a beat faster. |
| **S35** | 3013–3072 | 2.5s | The last three steps. Speed ramps to 40%. Everything else stays at normal speed — only they slow down. |

### ACT 4 · THE CONTACT AND THE STOP — f3073–3936 · 2:08–2:44

| Shot | Frames | Dur | Content |
| --- | --- | --- | --- |
| **S36** | 3073–3096 | 1.0s | ⭐ **THE CONTACT.** 24 frames, every one specified in §5. |
| **S37** | 3097–3216 | 5.0s | **THE WORLD STOPS.** Everything but the two of them freezes on f3097 and desaturates over 24 frames. A pigeon mid-flap. A dropped coin in the air. Slow 180° arc around them — the only motion besides their breathing. |
| **S38** | 3217–3312 | 4.0s | His POV. Hard push-in on her face. Heartbeat begins. Iris-ring flare, everything else to creamy DOF. |
| **S39** | 3313–3408 | 4.0s | Her POV of him. Mirrored exactly. *Matching these two is what makes it mutual instead of one-sided.* |
| **S40** | 3409–3504 | 4.0s | ⭐ **The smile reaches the brain.** Intercut both. A small bloom blooms at the eye-line and travels *up* the frame over 6 frames — soft light trail, barely there. Then the smile arrives: eyes first, mouth second, 8 frames apart. |
| **S41** | 3505–3600 | 4.0s | **Hearts racing.** Accelerating radial pulses on both, intercut faster and faster. Frame edges breathe. |
| **S42** | 3601–3696 | 4.0s | ⭐ **Their problems dissolve.** Behind him, the office tower peels away into drifting ash. Behind her, the book towers and the arguing silhouettes crumble to paper flakes. Literal, brief, and gone in 4 seconds. |
| **S43** | 3697–3816 | 5.0s | **Only two people in the world.** The crowd finishes dissolving to white. The street goes. The buildings go. They stand in a warm white void, still ten feet apart. |
| **S44** | 3817–3936 | 5.0s | Two-shot. Blush blooms over 8 frames, `#FF9E7A` at 25%, two small highlight dashes each. 12–16 sparse sparkles drift up. Both breathe out. |

### ACT 5 · LETTING GO — f3937–4464 · 2:44–3:06

| Shot | Frames | Dur | Content |
| --- | --- | --- | --- |
| **S45** | 3937–4032 | 4.0s | The world snaps quietly back. His phone is still at his ear. The call timer is still running — **the stake returns.** Cut between the timer and her face. |
| **S46** | 4033–4152 | 5.0s | ⭐ **He ends the call.** The hesitation, the pull-back, the press. Frame-by-frame in §5. |
| **S47** | 4153–4248 | 4.0s | Screen goes black, her reflection in the dead glass. **Then his other hand opens** and the worn folded page from S09 — the pitch, months of rehearsal — drops out of it. **His key light shifts cyan → gold over 10 frames.** Shoulders drop 4px. He lets go of paper too; that is what makes the two of them equal. |
| **S48** | 4249–4368 | 5.0s | ⭐ **She lets go.** Fingers open one at a time. Frame-by-frame in §5. |
| **S49** | 4369–4464 | 4.0s | The stack tips out of her arms and falls. First gust hits on f4448. |

### ACT 6 · THE PAPER HEART — f4465–5040 · 3:06–3:30

| Shot | Frames | Dur | Content |
| --- | --- | --- | --- |
| **S50** | 4465–4560 | 4.0s | The wind takes them. The sheets **lift instead of falling** and the first start away from her hands. **His single creased page lifts from his side of frame at the same moment** — one warm, folded, obviously different sheet among her clean white ones. Sun behind, each sheet translucent with a warm rim. Camera low and tight on her. |
| **S51** | 4561–4680 | 5.0s | The ribbon climbs **her** side of frame in a corkscrew, drawing the right lobe of the heart as it goes. Camera pulls back and cranes, still looking up. |
| **S52** | 4681–4824 | 6.0s | ⭐ **THE HEART, DRAWN.** The ribbon runs over the notch, down his side and out toward him. **His page arrives at the notch — the apex, dead centre, where the eye goes** — on the same frame her ribbon completes. At **f4752 the whole heart is in the air at once**, made of both of them, and the score peaks. Then the path lets go. Choreography in §5. |
| **S53** | 4825–4920 | 4.0s | Past him the heart has no hold on them any more and the sheets blow away as ordinary wind, tumbling out of frame. They step toward each other through the last of it — walk on 2s against paper on 1s. |
| **S54** | 4921–5016 | 4.0s | ⭐ **THE SECOND RING.** Ground level, among the settling sheets: her white paper, his creased page, and his phone lying face up. The screen lights — `SUPERIOR CALLING`. **Cyan: the only cool light left in a frame that has gone entirely gold.** It buzzes twice, shivering against the paper. Nobody reaches for it. The screen dies. |
| **S55** | 5017–5136 | 5.0s | Two hands, not touching, a 2cm gap **held for a full second**. Pull back to a wide two-shot: the two of them, the settled paper, the dark phone. Neither has looked down. Fade to `#FFF6EC` over the final 24 frames. |

---

## 5. Frame-by-frame — the six beats that carry the film

### ⭐ S36 · THE CONTACT · f3073–3096 (24 frames)

Every frame. This is one second that the preceding two minutes exist to set up.

| Frame | Image | Effect | Audio |
| --- | --- | --- | --- |
| 3073 | Two-shot, eyes lock, both mid-stride | **2-frame white flash, 40%** | **ALL SOUND CUTS** |
| 3074 | Held | flash → 15% | silence |
| 3075 | Held | flash gone; radial blur 3% from centre | violin note begins, quiet |
| 3076 | First fully clean frame | pupils start to dilate | violin sustains |
| 3077–3080 | Held | crowd desaturates 5%/frame | |
| 3081 | Held | crowd 25% | **heartbeat 1 — his** |
| 3082–3084 | Held | crowd 40% | |
| 3085 | His lips part 2px | crowd 50%; warm gold creeps in from her side of frame | **heartbeat 2 — hers** (4 frames later; they are not yet in sync) |
| 3086–3088 | Held | crowd 60% | |
| 3089 | Her eyes widen 3px | crowd 70% | |
| 3090–3092 | Held | crowd 80%; palettes now converged | violin swells |
| 3093 | His breath catches — chest rises 2px | crowd 90% | |
| 3094–3095 | Held | crowd 95% | |
| 3096 | Last frame before the arc begins | full gold wash, 10% | **heartbeats land together for the first time** |

**The detail that sells it:** their heartbeats start out of sync (f3081 / f3085) and converge on
f3096 — and stay locked for the rest of the film. Nobody notices consciously. Everyone feels it.

### ⭐ S38–S41 · THE HEARTBEAT

Radial scale of the frame edges, +1.5%, snapping back over 3 frames with a hard ease-out. Done
in ffmpeg, not in-camera.

| | beat frames | intervals | bpm |
| --- | --- | --- | --- |
| His (S38) | 3220, 3240, 3258, 3274, 3288, 3300 | 20, 18, 16, 14, 12 | 72 → 120 |
| Hers (S39) | 3316, 3336, 3354, 3370, 3384, 3396 | 20, 18, 16, 14, 12 | 72 → 120 |
| Both (S41) | 3508, 3524, 3538, 3550, 3560, 3568, 3574, 3580, 3585, 3590 | 16→5 | 90 → 288 |

By S41 the two pulses are a single shared rhythm.

### ⭐ S40 · THE SMILE REACHING THE BRAIN · f3409–3504

Your phrase, made literal but restrained — if it looks like a lightning bolt it becomes comedy.

| Frames | Beat |
| --- | --- |
| 3409–3420 | Her face, neutral, eyes already soft |
| 3421–3426 | A small warm bloom appears at her eye-line — 8px, `#FFD9A0`, 30% opacity |
| 3427–3432 | It travels *up* the frame over 6 frames and fades at her hairline. Soft trail, no hard edges |
| 3433–3444 | **Her eyes smile first** — lower lids lift 3px. The mouth hasn't moved yet |
| 3445–3452 | 8 frames later, the mouth follows. This delay is the entire trick: eyes before mouth reads as genuine, together reads as posed |
| 3453–3504 | Cut to him, identical treatment, 4 frames quicker — he's further gone than she is |

### ⭐ S46 · HE ENDS THE CALL · f4033–4152 (120 frames)

| Frames | Action | Note |
| --- | --- | --- |
| 4033–4052 | Close on the phone. Screen lit, call timer climbing | The timer is the stake, still counting |
| 4053–4072 | His thumb enters frame, moves toward the red button | Slow. On 2s |
| 4073–4096 | Thumb hovers 5mm above END CALL. **Stops.** | 24 frames of nothing. This is where the audience holds their breath |
| 4097–4108 | Thumb pulls **back** 2mm | The doubt. He remembers what this call is |
| 4109–4120 | Cut to his face. He looks up at her again | The reason |
| 4121–4132 | Back to the hand. The thumb comes down, decisive | Faster going down than it went up |
| **4133** | **THE PRESS** | 1-frame white dot at the fingertip |
| 4134–4144 | Screen goes black. The timer freezes, visible 2 frames, then dies | Let the audience read the number |
| 4145–4152 | His hand lowers out of frame. Phone forgotten | On 3s — released |

### ⭐ S48 · SHE LETS GO · f4249–4368 (120 frames)

The deliberate mirror. His release is a decision; hers is a surrender.

| Frames | Action | Note |
| --- | --- | --- |
| 4249–4268 | Close on her arms crushing the stack to her chest | Knuckles pale |
| 4269–4284 | The grip loosens. The whole stack drops 3px in her arms | Almost imperceptible |
| 4285–4296 | **Little finger** opens | One finger at a time. This is the whole shot |
| 4297–4308 | **Ring finger** | Stack tips 5° |
| 4309–4320 | **Middle finger** | Stack tips 12°, top sheets begin to slide |
| 4321–4330 | Cut to her face — **she isn't looking at the papers, she's looking at him** | 10 frames. This is *why* she can let go |
| 4331–4342 | **Index finger** | Stack tips 30°, sliding fast |
| 4343–4356 | **Thumb** — the last contact — opens | Falling freely now |
| 4357–4368 | Wide: the stack leaves her hands entirely | |

### ⭐ S54 · THE SECOND RING · f4921–5016 (96 frames)

| Frames | Beat | Note |
| --- | --- | --- |
| 4921–4944 | Ground level. The last sheets settle. His creased page lands among her white ones | Shallow focus, paper filling frame |
| 4945–4952 | The phone screen **lights** | Cyan `#7FD4E8` — the first cool light since Act 3, and it now looks *wrong* against the gold |
| 4953–4968 | `SUPERIOR CALLING`. It buzzes — the phone shivers 2px against the paper | The only movement in frame |
| 4969–4984 | It buzzes a second time. Hold. **Nobody reaches for it** | The length of this hold is the whole point. Let it get uncomfortable |
| 4985–5000 | The screen dims and dies | 16-frame fade, slow |
| 5001–5016 | Gold reclaims the frame. Only paper and a dark phone | No cool light left in the film |

**Do not cut to his face during this shot.** The temptation is to show him deciding. Staying on
the ground — on the abandoned things — is what says he isn't even thinking about it.

### ⭐ S50–S53 · THE HEART IS DRAWN, NOT ASSEMBLED · f4465–4920

**The symbol is the motion.** The sheets never park on a static outline — they fly, and the
heart is the shape their flight leaves in the air. A ribbon of paper leaves her hands, spirals
up her side of frame, over the notch, down his side, and runs out past him; at the peak the
whole curve is occupied at once, and after that the wind is just wind again.

*(Built and rendering — `build/paper_heart/build_act6.py`.)*

**The path.** girl → full heart loop → man, concatenated and then **resampled to constant arc
length**. The resampling is not cosmetic: sampling the raw heart parameter bunches sheets at
the lobes and starves the point, which is exactly where the eye checks the shape. Traverse
direction matters too — she is screen right, so the ribbon must climb *her* side first and come
down his, or the gesture reads backwards.

**The stagger.** One sheet takes 287 frames to fly the whole path. Sheet 0 leaves at f4465 and
reaches his end at f4752; the last sheet leaves *at* f4752 and is still in her hands. Between
them the ribbon covers the entire curve, so the heart completes on exactly the frame the score
peaks on.

| Frames | Phase |
| --- | --- |
| 4465–4560 | First sheets leave her hands and lift. Only the lead-in and the start of the right lobe exist yet |
| 4561–4680 | The ribbon climbs her side, corkscrewing. Right lobe complete, reaching for the notch |
| 4681–4751 | Over the notch and down his side. The shape becomes legible as a heart |
| **4752** | **The whole heart is in the air at once.** Peak of the score |
| 4753–4800 | Held — sheets keep flying, so the shape breathes rather than freezing |
| 4801–4920 | The path releases them (46-frame fade) and they blow away past him as ordinary wind |

**Each sheet corkscrews around the path** — 2.4 to 4.1 turns, radius tapering at both ends.
Without it the ribbon reads as a drawn line rather than paper caught in a rising wind.

### Two production notes from building it

**The camera has to be low and looking up.** At eye height the heart projects *below* the
horizon onto dark ground and stops reading as a shape entirely. At 1.2 m looking up it sits
against the sky and the two of them stay as foreground silhouettes along the bottom edge.

**White paper on a bright sky is invisible.** The first exposure clipped the sky to pure white
and the heart simply disappeared into it. The sheets must be the brightest thing in frame, so
the sky is a deep twilight (exposure −0.55) — which is also the more romantic frame.

**Changed from the original plan:** the sun no longer bursts through the notch in-camera. With
the camera low enough for the heart to read against the sky, the sun would have to sit 18.6°
up to line up with the notch, which is not a sunset any more. The low sun is the better image;
add the notch flare in the ffmpeg pass instead.

---

## 6. Animation timing cheat-sheet

| Element | Timing | Why |
| --- | --- | --- |
| Character acting | **on 2s** | Standard anime. Instantly reads hand-drawn |
| Exhaustion beats (S03, S16) | **on 3s** | Time dragging |
| Camera | **on 1s** | Smooth camera + stepped characters = the anime signature |
| Paper, particles, FX | **on 1s** | Physical things should flow |
| Eye-lifts (S33/S34) | **on 1s, 4 frames** | Fast enough to feel involuntary |
| Heartbeat pulses | **on 1s** | Felt, not seen |

In Blender: character F-curves to **Constant** interpolation + a **Step** modifier (2 or 3).
Camera and sim curves stay Bézier.

---

## 7. Build order

1. **Test a VRM render on this GPU** (§1). Nothing else starts until this passes.
2. Lock the music. Everything cuts to it.
3. Grey-box all 54 shots with real camera moves → 480p animatic. **Fix timing here**, where it's free. A 3:30 wordless film lives or dies on pacing, and this is the only cheap chance to find the sag.
4. Build both characters in VRoid, retarget Mixamo clips, bake toon materials.
5. Three environments: office, room, street. Keep them simple — shallow DOF hides most of it.
6. **Paper sim last.** Bake, pre-step, cache.
7. Render per shot at 1080p, `film_transparent` where you'll composite.
8. Grade + bloom + speed lines + heartbeat pulse in ffmpeg, per act.
9. Watch it once with the sound **off**. If the story still reads, it works.

---

## 8. Getting the quality — the shader, not the model

A mid-tier model with this shader beats a premium model with default materials. Build it once as
a node group, reuse on everything.

### Base toon ramp
- `Shader to RGB` → `Color Ramp` set to **Constant** interpolation. **Three steps, not two:**
  shadow / mid / light. Two steps reads as cheap; three reads as cel.
- Shadow colour must be a **hue shift, never just darker** — skin shadow goes warm-magenta
  (`#C98A8A`), cloth shadow goes cool (`#6A7A95`). Multiplying by grey is the single most common
  thing that makes 3D toon look wrong.
- Terminator tightness: keep the transition under 2% of the ramp width.

### Skin
- Three-step ramp + a **very slight subsurface** (0.02, radius 0.6) only in the light band.
- Blush is a texture-space gradient on the cheeks, not a light. Drive its opacity with a driver
  so S44 can bloom it over 8 frames.

### Eyes — the single biggest quality lever on an anime character
- Layered: iris gradient → pupil → **radial highlight ring** → a specular dot that tracks the
  key light → a subtle reflection of the environment at 8% opacity.
- The highlight dot must be **hand-placed per shot** in close-ups. Anime eyes lie about physics
  on purpose; a physically correct specular looks dead.
- In S36–S40, scale the iris 3–5% and lift the highlight opacity. Nobody will see it. Everybody
  will feel it.

### Hair
- **Anisotropic specular band**, not a point highlight — a soft horizontal band that slides as
  the head turns. This is the thing that says "anime" more than anything except the eyes.
- Hair shadow must tint the forehead, not darken it.

### Outlines
- **Inverted hull**: Solidify modifier, thickness ~0.003, flipped normals, backface culling,
  emission shader. Drive thickness by camera distance so wides don't get chunky.
- Vary line weight: heavier on the silhouette and under the jaw/chin, lighter on interior
  detail. Use a vertex-colour mask to modulate Solidify thickness.
- **Freestyle only on the 12 hero shots** (§1). Line set: silhouette + border + crease at 130°,
  thickness 1.6 px with a slight taper.

### Lighting
- Three-point per character, but the key is doing almost all the work — anime lighting is flat
  and graphic, not soft and volumetric.
- **Rim light on every shot from Act 4 onward.** As the two palettes converge, warm both rims to
  `#FFD9A0`. It's the visual glue of the second half.
- Use **light linking** so the characters' key doesn't touch the background — you want to control
  them independently for the desaturation in S37.

### Render settings (High tier)
```
Engine            EEVEE Next
Samples           64  (32 is enough on wides)
AO                on, distance 0.3, factor 0.6
Bloom             OFF  →  do it in ffmpeg
Motion blur       OFF  →  hand-authored smears only; real blur fights the 2s stepping
DOF               on, only where §4 calls for it
Colour management Filmic OFF, Standard ON, look = None
                  (Filmic desaturates the flats and kills the cel look — this matters)
Output            PNG RGBA, film_transparent where compositing
Resolution        1920×1080, 100%
```

**`Standard` not `Filmic`** is a small setting with a large effect: Filmic is built for
photographic latitude and it will mush your flat colour bands into gradients.

### ffmpeg finish (per act)
Bloom, glare, grade, vignette, the heartbeat pulse, speed lines and the final fade all happen
here — milliseconds a frame instead of ~3 s in the compositor.

---

*Machine-readable shot list: `shots.json` beside this file.*
