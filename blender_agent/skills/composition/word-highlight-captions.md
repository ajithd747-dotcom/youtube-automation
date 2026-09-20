---
id: word-highlight-captions
name: Word-by-word highlighted captions (karaoke) and bold outlined hook captions
category: composition
kind: technique
status: verified
applies_to:
- any
when_to_use: Shorts / vertical comedy or any video where captions should carry energy and retention.
triggers:
- captions
- subtitles
- karaoke
- word by word
- highlight
- shorts
- tiktok
- reels
- bold text
- yellow
tags:
- captions
- shorts
source:
- video:videoplayback-7@0:01-0:27
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe@0:01,0:41
- video:how-to-create-viral-stickman-animations-with-ai-100-free@9:00
- 'own-experience: tutorial recreation benchmark (2026-09-19)'
version: 2
---
## Evidence
- videoplayback (7): 1-3 words at a time near 60-70% of frame height; white bold outlined text with the **current word in yellow** ("I'm *finally*", "a *job*,", "you made *it!*").
- Blender tutorial intro (0:01, 0:41): 2-3 huge yellow (`#FFE000`) words with a thick black outline in the lower third ("a few clever tweaks", "Get the Source files").
- Stickman tutorial sample: white bold, 2-4 words, bottom-centre with soft shadow.

## Procedure
1. Get word timings: edge-tts `WordBoundary` events (offset/duration) or faster-whisper word timestamps.
2. Group into 1-3 word chunks (<= ~14 characters), each shown from its first word start to its last word end.
3. ASS karaoke: `\k<centiseconds>` per word with `PrimaryColour` white and `SecondaryColour` yellow, outline 4-6 px black, Arial Black/Impact-like bold, size ~5-6% of height.
4. Keep captions out of faces and keep the title banner separate (see shorts-top-title-banner).

## Implemented (verified)
`agents/voice/tools/captions.py` (karaoke / hook / plain ASS from word timings). Used for the tutorial intro hook captions.
