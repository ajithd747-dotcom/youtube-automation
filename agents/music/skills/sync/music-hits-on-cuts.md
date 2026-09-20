---
id: music-hits-on-cuts
name: Risers into impacts, hits exactly on the visual event
category: sync
kind: technique
status: verified
applies_to:
- any
when_to_use: A shot has a visual peak (impact, explosion, reveal, burst) that the music must land on.
triggers:
- hit
- impact
- riser
- swell
- explosion
- crash
- reveal
- sync
- on the beat
- cut
- burst
- boom
source:
- 'own-experience: ada_chain_reaction + reference-clip analysis (2026-09-19)'
- video:blender-grease-pencil-practice-fantasy-anime-scene (audio analysis)
version: 1
---
## Procedure
1. Find the event time in the final timeline: shot start + event offset (crate smash lands 1.5 s into its shot; domino trigger 0.9 s; fireworks bursts every (T-1.5)/n s).
2. `impact`: timpani (GM 47) at root-24, crash cymbal (49), kick (36) at velocity 127, plus a numpy boom (sub sweep 128->38 Hz + lowpassed noise, ~2.4 s tail).
3. `riser`: band-passed noise sweeping 300 -> 6000 Hz with an accelerating gain curve (t^2.2), 0.5-1.6 s long, ending exactly at the impact.
4. `swell` (softer) at shot starts that introduce a new scene; `hit` for minor accents (velocity 95).
5. Keep 1 s of relative quiet before a big impact so it reads.
## Measured (reference anime clip)
Strongest transient at 4.2 s (strength 1.0), others 6.1 s (0.89), 0.8 s, 8.0 s: 4 impacts in 12 s.
