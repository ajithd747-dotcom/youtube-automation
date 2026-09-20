---
id: vertical-blurred-background-fill
name: Fit 16:9 footage into 9:16 with a blurred, zoomed copy behind it
category: composition
kind: technique
status: reference
applies_to:
- any
when_to_use: Repurposing landscape animation for Shorts/Reels, or any letterboxed content in a vertical frame.
triggers:
- shorts
- vertical
- '9:16'
- blurred background
- letterbox
- repurpose
- reels
- fill
tags:
- ffmpeg
- shorts
source:
- video:videoplayback-8@0:01-0:13
version: 1
---
## Evidence
videoplayback (8): the animation plays in a 16:9-ish band in the middle; the same picture, enlarged and heavily blurred, fills the top and bottom areas; the title sits over the top band.

## Procedure (ffmpeg)
`[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2`
Then add the top title banner and captions below the picture band. Natively vertical renders (`--format shorts`) do not need this.
