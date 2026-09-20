#!/usr/bin/env bash
# Finishing pass for Act 6: bloom, the notch flare, grade, vignette -> mp4.
#
# All of this is deliberately here rather than in Blender's compositor: on this machine
# compositor glare costs about 3 s/frame and ffmpeg does the same work in milliseconds.
#
#   bash build/paper_heart/finish_act6.sh [in_dir] [out.mp4]
set -eu
cd "$(dirname "${BASH_SOURCE[0]}")/../.."   # repo root, wherever it is checked out
IN="${1:-renders/paper_heart/act6}"
OUT="${2:-renders/paper_heart/act6_finished.mp4}"
FPS=24
START=4465

# Bloom: isolate what is already bright, blur it twice at different radii, screen it back.
# Two radii is what separates a soft romantic glow from a cheap uniform haze.
BLOOM="[0:v]split=3[base][b1][b2];
 [b1]format=gbrp,lutrgb=r='if(gt(val,150),val,0)':g='if(gt(val,150),val,0)':b='if(gt(val,150),val,0)',gblur=sigma=14[g1];
 [b2]format=gbrp,lutrgb=r='if(gt(val,190),val,0)':g='if(gt(val,190),val,0)':b='if(gt(val,190),val,0)',gblur=sigma=42[g2];
 [base][g1]blend=all_mode=screen:all_opacity=0.42[t1];
 [t1][g2]blend=all_mode=screen:all_opacity=0.30[bloomed]"

# Grade: lift the warmth the colour script calls for in Act 6 (rose gold), keep blacks black -
# never touch the shadow terms of colorbalance on footage with real silhouettes in it.
GRADE="[bloomed]eq=saturation=1.12:contrast=1.06:gamma=1.02,
 colorbalance=rm=0.04:gm=0.01:bm=-0.03:rh=0.05:gh=0.02:bh=-0.04[graded]"

# A gentle vignette so the eye stays on the heart.
VIGN="[graded]vignette=angle=PI/5:mode=forward[out]"

ffmpeg -y -framerate "$FPS" -start_number "$START" -i "$IN/f_%04d.png" \
  -filter_complex "${BLOOM};${GRADE};${VIGN}" -map "[out]" \
  -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow "$OUT"

echo "finished -> $OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height,r_frame_rate \
  -of default=noprint_wrappers=1 "$OUT"
