---
id: music-avoid-sub-heavy-mix
name: 'Synth/drum mixes come out bass-heavy: check the spectrum'
category: mixing
kind: pitfall
status: verified
applies_to:
- any
when_to_use: A generated track sounds boomy or thin compared with a professional reference.
triggers:
- boomy
- bass heavy
- muddy
- thin
- spectrum
- eq
- low end
- sub bass
source:
- 'own-experience: ada_chain_reaction + reference-clip analysis (2026-09-19)'
- video:blender-grease-pencil-practice-fantasy-anime-scene (audio analysis)
version: 1
---
## Measured
First numpy render: 77 % of the energy below 100 Hz (reference 14 %). FluidSynth render: 48 %. Kick + synth bass + timpani all live in the sub band.
## Procedure
- Keep `bass_cut` <= 520 Hz and `low_boost` 0.4-0.8; high-pass pads at 120 Hz; do the final `eq_match` against the target band shares (max +-14 dB).
- Judge by band shares and centroid, not by ear on laptop speakers.
