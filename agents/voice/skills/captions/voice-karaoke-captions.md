---
id: voice-karaoke-captions
name: Word-highlight captions from word timings
category: captions
kind: technique
status: verified
applies_to:
- any
when_to_use: Burning captions into shorts or any video where retention matters.
triggers:
- captions
- subtitles
- karaoke
- highlight
- word by word
- shorts
- yellow
- outline
source:
- video:videoplayback-7@0:01-0:27
- video:blender-2d-animation-basics-for-beginners-grease-pencil-effe@0:01
version: 1
---
## Procedure
`captions.write_ass(path, words, w, h, style)`: chunks of 1-3 words (<= 16 chars, breaks on punctuation or 0.45 s pauses). Styles: `karaoke` (white bold, the spoken word turns yellow via ASS \kf), `hook` (huge yellow with 7 px black outline for hooks), `plain` (white + shadow).
Place at 8% from the bottom (landscape) or 30% up (portrait shorts); keep faces clear; title banner stays at the top.
