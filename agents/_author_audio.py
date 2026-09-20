"""Creates the specs, registry entries and starter skill libraries of the music and voice agents (re-runnable)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from core import SK, register  # noqa: E402

SRC_ADA = "own-experience: ada_chain_reaction + reference-clip analysis (2026-09-19)"
SRC_ANIME = "video:blender-grease-pencil-practice-fantasy-anime-scene (audio analysis)"
SRC_MEME = "video:can-you-relate-4k-memes-animation-shorts (audio analysis)"

# ----------------------------------------------------------------------------- agent specs
MUSIC = {
    "name": "music", "title": "Music agent", "kind": "hybrid",
    "role": "Plans and produces background music: mood/tempo/key from the script and shot plan, real instruments via FluidSynth (or a numpy synth), risers/impacts on the cuts, reference matching, ducking under narration, loudness mastering",
    "inputs": ["shot plan + durations", "script text", "optional reference audio"], "outputs": ["music wav (44.1 kHz stereo, -14 LUFS)", "music plan json", "comparison report"],
    "tools": [{"name": "analyze", "file": "tools/analyze.py", "description": "tempo, key, spectrum, energy curve, hits, LUFS of any audio/video"},
              {"name": "synth", "file": "tools/synth.py", "description": "numpy pads/bass/plucks/bells/drums/risers/impacts/reverb"},
              {"name": "compose", "file": "tools/compose.py", "description": "MusicPlan -> layered arrangement"},
              {"name": "midi_render", "file": "tools/midi_render.py", "description": "MusicPlan -> MIDI -> FluidSynth + GeneralUser GS soundfont"},
              {"name": "mix", "file": "tools/mix.py", "description": "wav I/O, sidechain ducking, loudnorm, spectral EQ matching, dynamics matching"}],
    "skill_categories": ["mood", "arrangement", "sync", "mixing", "reference-matching", "tools"],
    "quality_gates": ["python agents/cli.py verify music", "compare(): score < 1.0 vs reference", "final LUFS within 1 dB of target"],
    "external_software": ["FluidSynth 2.6.1 (LGPL) in agents/tools_bin", "GeneralUser GS soundfont (permissive licence) in agents/tools_bin", "ffmpeg"], "llm": True}
VOICE = {
    "name": "voice", "title": "Voice agent", "kind": "hybrid",
    "role": "Chooses the narrator (engine, voice, speed, pitch) from the content and skills, produces word-timed narration (local Kokoro or edge-tts), matches a reference narrator's pitch and pace, builds word-highlight captions",
    "inputs": ["segment texts", "style/content type", "optional reference audio"], "outputs": ["narration audio per segment", "word timings", "ASS captions", "voice choice report"],
    "tools": [{"name": "tts", "file": "tools/tts.py", "description": "Kokoro (local) and edge-tts engines with word timestamps"},
              {"name": "measure", "file": "tools/measure.py", "description": "wpm, median pitch, pause ratio, LUFS"},
              {"name": "captions", "file": "tools/captions.py", "description": "1-3 word chunks; karaoke/hook/plain ASS"}],
    "skill_categories": ["voice-choice", "prosody", "sync", "captions", "quality", "tools"],
    "quality_gates": ["python agents/cli.py verify voice", "measured wpm within 8% of target", "median pitch within 10% of reference"],
    "external_software": ["Kokoro-82M (Apache-2.0, local CPU)", "edge-tts (online neural voices)", "faster-whisper (analysis)", "ffmpeg"], "llm": True}

for spec, cls in ((MUSIC, "MusicAgent"), (VOICE, "VoiceAgent")):
    d = HERE / spec["name"]
    (d / "tests").mkdir(parents=True, exist_ok=True)
    (d / "agent.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    (d / "tests" / f"test_{spec['name']}.py").write_text(
        f'"""Smoke test: spec + skills valid, agent imports."""\nimport sys\nfrom pathlib import Path\n\nsys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))\n'
        f'from core import load_agent\n\nrep = load_agent("{spec["name"]}").self_check()\nassert rep["ok"], rep\nprint("ok", rep)\n', encoding="utf-8")
    register({"name": spec["name"], "title": spec["title"], "kind": spec["kind"], "role": spec["role"], "path": f"agents/{spec['name']}",
              "entry": f"agent.py:{cls}", "skills_dir": f"agents/{spec['name']}/skills", "llm": spec["llm"], "created_by": "manual"})

# ----------------------------------------------------------------------------- skills
def skill(agent, cats, id, name, category, kind, when, triggers, body, source, status="verified", applies=("any",)):
    meta = {"id": id, "name": name, "category": category, "kind": kind, "status": status, "applies_to": list(applies), "when_to_use": when,
            "triggers": triggers, "source": source if isinstance(source, list) else [source], "version": 1}
    with SK.library(HERE / agent / "skills", cats):
        SK.write_skill(SK.SKILLS_DIR / category / f"{id}.md", meta, body)


MC = MUSIC["skill_categories"]
skill("music", MC, "music-mood-tempo-key-map", "Pick tempo, scale and instrumentation from the mood", "mood", "rule",
      "Deciding the overall feel of a background track from the script's tone or the shots' recipes.",
      ["mood", "tempo", "bpm", "key", "scale", "genre", "feel", "epic", "funny", "calm", "tense", "energetic", "background music"],
      """## Procedure
| feel | style | BPM | scale | instruments |
|---|---|---|---|---|
| comedy / playful | comedy | 118 | major | pizzicato/marimba arp, light kit, bells |
| hopeful / celebration | uplifting | 108 | major | strings, choir, harp arp, pop kit, bells |
| epic action | cinematic-action | 90-96 | minor (or major for heroic) | strings + choir pad, synth bass, pizzicato arp, clap, taiko/toms, timpani |
| suspense | tense | 84 | phrygian | low strings, sparse taiko, dark choir |
| calm explainer / product | ambient | 76 | dorian | warm pad, sparse bells, no drums |
| neon / club | neon | 118 | minor | synth pad, saw lead arp, four-on-floor |
Detectors report double tempo for fast cues: use the half (reference anime clip: detected 178 -> musical 89).
""", [SRC_ADA, SRC_ANIME])

skill("music", MC, "music-follow-shot-intensity", "One intensity section per shot; layers switch on by intensity", "arrangement", "technique",
      "Building the arrangement so the music rises and falls with the shots (physics climax loud, walk/glass calm).",
      ["intensity", "arrangement", "layers", "build", "climax", "drop", "section", "energy curve", "follow the picture"],
      """## Procedure
1. One (t0, t1, intensity 0-1) section per shot: robot_intro 0.40, workshop_walk 0.35, glass 0.45, domino 0.65, crate_smash 1.0, cloth 0.5, fireworks 0.9, jelly 0.7, finale 0.85.
2. Layers by intensity: pad always; bass > 0.25; kick > 0.35; hats > 0.4 (16ths when > 0.6); arp > 0.45; snare/clap > 0.5; taiko/toms > 0.7; choir > 0.7.
3. Velocity/level scales with intensity: pad 0.55+0.35i, bass 0.5+0.4i, snare 0.5+0.3i.
4. Never change more than two layers at a section edge: it sounds like a cut, not music.
5. From a reference: sections = the reference's energy per second normalised to 0.3-1.0.
""", [SRC_ADA, SRC_ANIME])

skill("music", MC, "music-hits-on-cuts", "Risers into impacts, hits exactly on the visual event", "sync", "technique",
      "A shot has a visual peak (impact, explosion, reveal, burst) that the music must land on.",
      ["hit", "impact", "riser", "swell", "explosion", "crash", "reveal", "sync", "on the beat", "cut", "burst", "boom"],
      """## Procedure
1. Find the event time in the final timeline: shot start + event offset (crate smash lands 1.5 s into its shot; domino trigger 0.9 s; fireworks bursts every (T-1.5)/n s).
2. `impact`: timpani (GM 47) at root-24, crash cymbal (49), kick (36) at velocity 127, plus a numpy boom (sub sweep 128->38 Hz + lowpassed noise, ~2.4 s tail).
3. `riser`: band-passed noise sweeping 300 -> 6000 Hz with an accelerating gain curve (t^2.2), 0.5-1.6 s long, ending exactly at the impact.
4. `swell` (softer) at shot starts that introduce a new scene; `hit` for minor accents (velocity 95).
5. Keep 1 s of relative quiet before a big impact so it reads.
## Measured (reference anime clip)
Strongest transient at 4.2 s (strength 1.0), others 6.1 s (0.89), 0.8 s, 8.0 s: 4 impacts in 12 s.
""", [SRC_ADA, SRC_ANIME])

skill("music", MC, "music-duck-under-voice", "Sidechain duck the music and master to -14 LUFS", "mixing", "rule",
      "Mixing music with narration.",
      ["duck", "sidechain", "voice over", "narration", "mix", "levels", "loudness", "lufs", "under voice"],
      """## Procedure
1. ffmpeg `sidechaincompress=threshold=0.02:ratio=8:attack=50:release=350` with the narration as the sidechain, then `amix=inputs=2:normalize=0`.
2. Music sits ~13 dB below the voice while speaking, returns in gaps; in a tutorial keep the bed at -15..-20 dB.
3. Final master: two-pass `loudnorm` I=-14, TP=-1.0, LRA=11 (references measured -14.3, -14.4, -14.7 LUFS).
4. Check with `analyze.py`: LUFS within 1 dB of target, true peak <= -0.3 dB.
""", [SRC_ANIME, SRC_MEME, SRC_ADA])

skill("music", MC, "music-fluidsynth-general-midi", "Render real instruments: GM programs, drum map, FluidSynth flags", "tools", "technique",
      "Producing music with real instrument sounds instead of raw synth waves.",
      ["fluidsynth", "soundfont", "midi", "instruments", "general midi", "strings", "choir", "timpani", "orchestral", "sf2"],
      """## Procedure
1. `midi_render.build_midi(plan, path)` -> `.mid` (mido, 480 ppq, one tempo event).
2. `fluidsynth -ni -g 0.8 -r 44100 -R 1 -C 1 -F out.wav GeneralUser-GS.sf2 music.mid` (reverb + chorus on) renders faster than real time (12 s in 0.8 s).
3. GM programs: strings 48/49, choir aahs 52, synth voice 54, warm pad 89, synth bass 38/39, acoustic bass 32/33, pizzicato 45, harp 46, celesta 8, glockenspiel 9, timpani 47, taiko 116, reverse cymbal 119. Drums on channel 10: kick 36, snare 38, clap 39, hat 42/46, low tom 41, mid tom 45, crash 49.
4. Layer numpy risers/impacts on top (`compose.render(plan, only=('fx',))`).
## Licences
FluidSynth is LGPL; GeneralUser GS allows commercial use. Downloaded to `agents/tools_bin/`.
""", [SRC_ADA])

skill("music", MC, "music-reference-matching", "Match a reference track: tempo, key, energy contour, spectrum, loudness", "reference-matching", "technique",
      "Recreating or imitating an existing video's music feel (benchmarking, 'make it sound like this').",
      ["reference", "match", "same music", "recreate", "sound like", "imitate", "similar track", "benchmark"],
      """## Procedure
1. `analyze.describe(ref)`: bpm (halve if > 130), key, centroid, band shares, energy curve per 0.25 s, hits, LUFS, LRA.
2. `plan_from_reference`: bpm, root/scale from key, sections from the energy curve, hits from transients.
3. Render, then `mix.eq_match(band shares)` (per-band gain toward the reference shares) and `mix.match_dynamics(energy curve)`.
4. `loudnorm` to the reference LUFS; `compare()` gives a 0-3 distance (bands, centroid, LUFS, LRA, energy correlation, tempo, key).
5. Iterate `refine_to_reference` (brightness x (ref/ours centroid)^0.6, bass x (ref/ours sub)^-0.4). Stop when the score stops improving.
## Reference values (anime clip, 12 s)
LUFS -14.4, LRA 2.2, ~89 BPM (F major), centroid 1364 Hz, band shares sub 14 % / low 27 % / mid 56 % / high 3 %, energy range 7 dB, 4 impacts.
""", [SRC_ANIME])

skill("music", MC, "music-avoid-sub-heavy-mix", "Synth/drum mixes come out bass-heavy: check the spectrum", "mixing", "pitfall",
      "A generated track sounds boomy or thin compared with a professional reference.",
      ["boomy", "bass heavy", "muddy", "thin", "spectrum", "eq", "low end", "sub bass"],
      """## Measured
First numpy render: 77 % of the energy below 100 Hz (reference 14 %). FluidSynth render: 48 %. Kick + synth bass + timpani all live in the sub band.
## Procedure
- Keep `bass_cut` <= 520 Hz and `low_boost` 0.4-0.8; high-pass pads at 120 Hz; do the final `eq_match` against the target band shares (max +-14 dB).
- Judge by band shares and centroid, not by ear on laptop speakers.
""", [SRC_ADA, SRC_ANIME])

skill("music", MC, "music-free-tools-and-licences", "Free music tools and which are safe for monetised videos", "tools", "rule",
      "Choosing software or models to generate/obtain music.",
      ["free", "licence", "license", "royalty free", "monetize", "copyright", "musicgen", "suno", "soundfont", "pixabay"],
      """## Procedure
- Safe & used here: own composition (numpy synth + MIDI) rendered with FluidSynth (LGPL) and GeneralUser GS (permissive).
- Free DAWs/synthesis for more: LMMS, Ardour, MuseScore (notation -> audio), SuperCollider, Csound, VCV Rack.
- AI models: MusicGen weights are CC-BY-NC (non-commercial - avoid for monetised channels); check every model's licence.
- Free libraries: YouTube Audio Library, Pixabay Music, Free Music Archive; keep the licence text with the project.
- Never reuse a reference video's soundtrack: recreate the feel, do not copy the audio.
""", [SRC_ADA])

VC = VOICE["skill_categories"]
skill("voice", VC, "voice-choose-by-content", "Pick voice, speed and engine from the content type", "voice-choice", "rule",
      "Selecting a narrator for a script.",
      ["voice", "narrator", "narration", "tts", "explainer", "calm", "psychology", "comedy", "news", "story", "kids"],
      """## Procedure
| content | Kokoro voice / speed | edge voice |
|---|---|---|
| explainer / tutorial | am_michael 1.00-1.02 | AndrewNeural |
| calm, psychology, self-improvement | am_adam 0.92 | EricNeural |
| comedy, stickman jokes | am_puck 1.08 | GuyNeural |
| news / crime | am_fenrir 1.00 | ChristopherNeural |
| story / documentary | bm_george 0.98 | EricNeural |
| kids | af_sky 1.05 | JennyNeural |
Prefer Kokoro (local, natural, Apache-2.0); use edge-tts when Kokoro is unavailable or for quick drafts.
""", ["video:how-to-create-viral-stickman-animations-with-ai-100-free@8:00", SRC_ADA])

skill("voice", VC, "voice-speaking-rate-targets", "Speaking-rate targets and how to hit them", "prosody", "rule",
      "Setting narration speed or checking that it is neither rushed nor slow.",
      ["speed", "pace", "wpm", "words per minute", "rate", "slow", "fast", "rushed", "tempo of speech"],
      """## Targets (measured on the references)
Tutorial narrator 134 wpm; calm psychology 120-140; explainer 140-160; comedy 160-180; a stumbling-fast 197 wpm sample (stickman tutorial) is too fast to follow.
## Procedure
1. Synthesize, `measure.stats(path, words=words)` -> wpm_speaking (words / speech time, pauses excluded).
2. New speed = old speed x target/measured; Kokoro accepts 0.7-1.4.
3. Add 0.35 s of air after every segment.
""", ["video:blender-2d-animation-basics-for-beginners-grease-pencil-effe (134 wpm)", "video:how-to-create-viral-stickman-animations-with-ai-100-free (197 wpm)"])

skill("voice", VC, "voice-word-timings-for-sync", "Use word timings for captions, cuts and pauses", "sync", "technique",
      "Synchronising visuals or captions to narration.",
      ["word timing", "timestamps", "sync", "lip sync", "align", "captions timing", "cut on the word", "word boundary"],
      """## Procedure
- Kokoro returns per-token start/end (seconds) from the model; edge-tts emits WordBoundary events (offset/duration in 100 ns ticks).
- Store `words=[{text,start,end}]` per clip; shift by the clip's start on the timeline for global timing.
- Cut/emphasise on the word that carries the meaning; start a visual event 0.1-0.2 s before its word.
- Mouth movement: derive open/close from the RMS envelope of the audio (0.05 s frames) or from word spans.
""", [SRC_ADA])

skill("voice", VC, "voice-karaoke-captions", "Word-highlight captions from word timings", "captions", "technique",
      "Burning captions into shorts or any video where retention matters.",
      ["captions", "subtitles", "karaoke", "highlight", "word by word", "shorts", "yellow", "outline"],
      """## Procedure
`captions.write_ass(path, words, w, h, style)`: chunks of 1-3 words (<= 16 chars, breaks on punctuation or 0.45 s pauses). Styles: `karaoke` (white bold, the spoken word turns yellow via ASS \\kf), `hook` (huge yellow with 7 px black outline for hooks), `plain` (white + shadow).
Place at 8% from the bottom (landscape) or 30% up (portrait shorts); keep faces clear; title banner stays at the top.
""", ["video:videoplayback-7@0:01-0:27", "video:blender-2d-animation-basics-for-beginners-grease-pencil-effe@0:01"])

skill("voice", VC, "voice-reference-matching", "Match a reference narrator's pitch and pace (never clone a person)", "quality", "technique",
      "Making narration sound like the same kind of voice as a reference video (benchmarks, house style).",
      ["reference voice", "same voice", "match voice", "sound like", "pitch", "narrator", "recreate", "voice over same"],
      """## Procedure
1. Measure the reference: median f0 (autocorrelation, voiced frames), p10/p90, wpm from its transcript, LUFS.
2. `calibrate_voices()`: synthesise a fixed sentence with every candidate voice, cache f0 + wpm.
3. Choose the voice with the nearest f0; speed = ref wpm / voice wpm; pitch shift = 12 log2(ref f0 / voice f0) semitones (clamped +-4) with ffmpeg `asetrate + atempo`.
4. Re-measure and iterate; loudness to the reference LUFS.
## Ethics
This matches *characteristics* with a stock TTS voice. Do not clone a real person's voice from their videos without their consent.
""", ["video:blender-2d-animation-basics-for-beginners-grease-pencil-effe"])

skill("voice", VC, "voice-loudness-and-pauses", "Level, pauses and clean segment edges", "quality", "rule",
      "Final QA of narration audio.",
      ["loudness", "pauses", "silence", "level", "clipping", "clean", "edges", "gaps"],
      """## Rules
- Narration alone at about -16 LUFS so that voice + ducked music master to -14 LUFS.
- Trim leading silence > 0.15 s; keep 0.25-0.4 s between sentences, 0.6 s between ideas.
- Active-speech ratio 0.75-0.9; below 0.7 the delivery drags.
""", [SRC_ADA])

skill("voice", VC, "voice-engines-free-tools", "Free voice software and its limits", "tools", "rule",
      "Choosing or installing a TTS / speech tool.",
      ["free", "tts", "kokoro", "piper", "edge-tts", "whisper", "espeak", "xtts", "licence", "offline"],
      """## Procedure
- **Kokoro-82M** (Apache-2.0): local, CPU, natural, word timestamps. First run downloads ~330 MB. ~2x real time on this laptop.
- **edge-tts**: free online Microsoft neural voices; unofficial endpoint, needs internet, retry on 'No audio was received'.
- **Piper** (MIT, offline): installed as `piper-tts`; voices are separate ~60 MB downloads (rhasspy/piper-voices) - use as a light fallback.
- **faster-whisper** (MIT): transcription/analysis of references and word timings.
- Cloning models (XTTS: non-commercial licence; F5-TTS/OpenVoice) are not used: consent + licence issues.
""", [SRC_ADA])

print("audio agents authored")
