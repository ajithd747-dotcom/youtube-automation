---
id: voice-engines-free-tools
name: Free voice software and its limits
category: tools
kind: rule
status: verified
applies_to:
- any
when_to_use: Choosing or installing a TTS / speech tool.
triggers:
- free
- tts
- kokoro
- piper
- edge-tts
- whisper
- espeak
- xtts
- licence
- offline
source:
- 'own-experience: ada_chain_reaction + reference-clip analysis (2026-09-19)'
version: 1
---
## Procedure
- **Kokoro-82M** (Apache-2.0): local, CPU, natural, word timestamps. First run downloads ~330 MB. ~2x real time on this laptop.
- **edge-tts**: free online Microsoft neural voices; unofficial endpoint, needs internet, retry on 'No audio was received'.
- **Piper** (MIT, offline): installed as `piper-tts`; voices are separate ~60 MB downloads (rhasspy/piper-voices) - use as a light fallback.
- **faster-whisper** (MIT): transcription/analysis of references and word timings.
- Cloning models (XTTS: non-commercial licence; F5-TTS/OpenVoice) are not used: consent + licence issues.
