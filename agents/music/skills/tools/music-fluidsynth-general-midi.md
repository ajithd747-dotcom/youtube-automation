---
id: music-fluidsynth-general-midi
name: 'Render real instruments: GM programs, drum map, FluidSynth flags'
category: tools
kind: technique
status: verified
applies_to:
- any
when_to_use: Producing music with real instrument sounds instead of raw synth waves.
triggers:
- fluidsynth
- soundfont
- midi
- instruments
- general midi
- strings
- choir
- timpani
- orchestral
- sf2
source:
- 'own-experience: ada_chain_reaction + reference-clip analysis (2026-09-19)'
version: 1
---
## Procedure
1. `midi_render.build_midi(plan, path)` -> `.mid` (mido, 480 ppq, one tempo event).
2. `fluidsynth -ni -g 0.8 -r 44100 -R 1 -C 1 -F out.wav GeneralUser-GS.sf2 music.mid` (reverb + chorus on) renders faster than real time (12 s in 0.8 s).
3. GM programs: strings 48/49, choir aahs 52, synth voice 54, warm pad 89, synth bass 38/39, acoustic bass 32/33, pizzicato 45, harp 46, celesta 8, glockenspiel 9, timpani 47, taiko 116, reverse cymbal 119. Drums on channel 10: kick 36, snare 38, clap 39, hat 42/46, low tom 41, mid tom 45, crash 49.
4. Layer numpy risers/impacts on top (`compose.render(plan, only=('fx',))`).
## Licences
FluidSynth is LGPL; GeneralUser GS allows commercial use. Downloaded to `agents/tools_bin/`.
