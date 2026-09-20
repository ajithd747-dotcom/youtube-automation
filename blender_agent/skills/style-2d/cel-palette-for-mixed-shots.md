---
id: cel-palette-for-mixed-shots
name: 'Mixed two-tone/colour shots: add to the palette, never substitute'
category: style-2d
kind: rule
status: verified
applies_to:
- 2d
- anime
- cel
when_to_use: Building a per-shot k-means palette for a 2D shot that mixes stark two-tone
  impact drawings with ordinary colour drawings.
triggers:
- palette
- k-means
- quantise
- colour quantization
- shot palette
- grey ramp
- flat colour
- impact frame
- cel colours
tags:
- 2d
- colour
- reference-recreation
source:
- 'own-experience: FlipaClip anime-clip recreation (2026-09-20)'
version: 1
---
## Rules
k-means goes by pixel count, so in a shot that is mostly two-tone the black and white
frames win every centroid. Rebuild the colour part from the colour drawings alone, then
**concatenate** - shot palette + colour palette + grey ramp:

```python
if n_mono and n_mono < len(keys):
    colour_imgs = [small(frames[k]) for k, m in zip(keys, mono_flags) if not m]
    pal = np.vstack([pal, shot_palette(colour_imgs, k=len(pal))])   # add, do not replace
ramp = np.linspace(4, 252, 22, dtype=np.float32)
pal = np.vstack([pal, np.repeat(ramp[:, None], 3, axis=1)])
```

## Why not substitute
Both frame types need their own colours and they do not overlap:
- the colour drawings need hues that pixel-count k-means never gave them (one shot came
  out with 28 pure greys and **no teal at all**, so its two colour drawings could only
  render grey);
- the two-tone drawings need fine grey levels to quantise onto.

Replacing the palette wins the first and loses the second. Measured: rebuilding from the
colour drawings alone took ssim 0.668 -> 0.618 while fixing the colour; concatenating gave
0.677 with the colour fix kept, and the two-tone frames scored exactly as they had with
the original greys.

## Knock-on effect
A coarse gap-filling pass under the detail pass is only a win once the greys are present -
against the ramp alone its blobs land on mid-grey and read as smudge against a crisply
bimodal frame (0.656, or 0.616 restricted to the frame's two extremes). With the full
palette the same pass gave the largest single gain on that shot: **0.677 -> 0.723 ssim,
mae 18.1 -> 14.0**.

## Sanity check
Print the palette for any shot that renders flat or grey. Thirty-odd entries that are all
neutral is the signature.
