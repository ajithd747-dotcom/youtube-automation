---
id: voice-choose-by-content
name: Pick voice, speed and engine from the content type
category: voice-choice
kind: rule
status: verified
applies_to:
- any
when_to_use: Selecting a narrator for a script.
triggers:
- voice
- narrator
- narration
- tts
- explainer
- calm
- psychology
- comedy
- news
- story
- kids
source:
- video:how-to-create-viral-stickman-animations-with-ai-100-free@8:00
- 'own-experience: ada_chain_reaction + reference-clip analysis (2026-09-19)'
version: 1
---
## Procedure
| content | Kokoro voice / speed | edge voice |
|---|---|---|
| explainer / tutorial | am_michael 1.00-1.02 | AndrewNeural |
| calm, psychology, self-improvement | am_adam 0.92 | EricNeural |
| comedy, stickman jokes | am_puck 1.08 | GuyNeural |
| news / crime | am_fenrir 1.00 | ChristopherNeural |
| story / documentary | bm_george 0.98 | EricNeural |
| kids | af_sky 1.05 | JennyNeural |
Prefer Kokoro (local, natural, Apache-2.0); use edge-tts when Kokoro is unavailable or for quick drafts.
