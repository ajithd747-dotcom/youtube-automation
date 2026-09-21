---
id: match-reference-character-voice-japanese
name: Re-voice a reference's character lines in Japanese - Kokoro ja voice chosen by measured F0, stretched, pitched and levelled per line
category: voice-choice
kind: technique
status: verified
applies_to:
- any
when_to_use: Recreating the spoken lines of a reference video (anime trailer, dialogue) with matching timing, pitch and level,
  especially Japanese-language references.
triggers:
- recreate voice
- character voice
- japanese voice
- voice-over
- match speaker
- dub
tags:
- recreation
- kokoro
- japanese
source:
- 'own-experience: training/recreate_audio.py on Fragrant Flower (24 lines) and Blue Box (20 lines), 2026-09-21 (training/PROGRESS.md)'
version: 1
---
## Procedure

1. Split the reference audio with Demucs (`python -m demucs --two-stems vocals -n htdemucs -d cpu`): measure speakers on the
   vocals stem, never on the mix (music drags pyin F0 and RMS).
2. Per Whisper segment: median F0 with `librosa.pyin(fmin=70, fmax=500)`, RMS dB, duration.
3. Voice: `jm_kumo` if F0 < 165 Hz, else the `jf_*` voice whose own measured F0 is closest (measure each voice once and cache).
   Kokoro Japanese needs `misaki[ja]` deps: install `pyopenjtalk-plus` (prebuilt wheel; plain `pyopenjtalk` fails to build here),
   `fugashi jaconv mojimoji unidic-lite`, then `KPipeline(lang_code="j")`.
4. Trim silence, `time_stretch` to the segment length (rate clipped 0.6-1.8), `pitch_shift` by 12*log2(F0_ref/F0_voice)
   semitones (clipped +-5), scale to the segment's RMS, place at the segment start.
5. Score: Whisper `small` language `ja` on the recreated track vs the reference transcript, character accuracy (NFKC,
   alphanumerics only). Ceiling = the same Whisper on the reference vocals stem.

## Evidence

| video | lines | character accuracy (ceiling) | speech-envelope corr | median F0 error |
|---|---|---|---|---|
| Fragrant Flower | 24 | 0.846 (0.888) | 0.615 | 0.41 st |
| Blue Box | 20 | 0.838 (0.838) | 0.478 | 0.80 st |

## Limits

Timbre and acting (emotion, breath, shouting) are not matched; only pitch, pace, level and words.
