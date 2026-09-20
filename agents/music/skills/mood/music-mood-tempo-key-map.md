---
id: music-mood-tempo-key-map
name: Pick tempo, scale and instrumentation from the mood
category: mood
kind: rule
status: verified
applies_to:
- any
when_to_use: Deciding the overall feel of a background track from the script's tone or the shots' recipes.
triggers:
- mood
- tempo
- bpm
- key
- scale
- genre
- feel
- epic
- funny
- calm
- tense
- energetic
- background music
source:
- 'own-experience: ada_chain_reaction + reference-clip analysis (2026-09-19)'
- video:blender-grease-pencil-practice-fantasy-anime-scene (audio analysis)
version: 1
---
## Procedure
| feel | style | BPM | scale | instruments |
|---|---|---|---|---|
| comedy / playful | comedy | 118 | major | pizzicato/marimba arp, light kit, bells |
| hopeful / celebration | uplifting | 108 | major | strings, choir, harp arp, pop kit, bells |
| epic action | cinematic-action | 90-96 | minor (or major for heroic) | strings + choir pad, synth bass, pizzicato arp, clap, taiko/toms, timpani |
| suspense | tense | 84 | phrygian | low strings, sparse taiko, dark choir |
| calm explainer / product | ambient | 76 | dorian | warm pad, sparse bells, no drums |
| neon / club | neon | 118 | minor | synth pad, saw lead arp, four-on-floor |
Detectors report double tempo for fast cues: use the half (reference anime clip: detected 178 -> musical 89).
