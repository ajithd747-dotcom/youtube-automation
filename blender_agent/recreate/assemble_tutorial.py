"""Assemble the tutorial recreation: intro reel (our anime hero clip + word-highlight hook captions) + real Blender GUI recording +
outro, over the matched narration, on the reference's timeline; then benchmark against the reference.

    python blender_agent/recreate/assemble_tutorial.py [--compare]
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BA = HERE.parent
ROOT = BA.parent
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "agents" / "voice" / "tools"))
import captions as CAP  # noqa: E402

WORK = BA / "work" / "recreate_tutorial"
REF = ROOT / "reference vedios" / "vedios" / "blender reference vedios" / "vidssave.com Blender 2D Animation Basics for Beginners - Grease Pencil Effects and Compositing 720P.mp4"
OUT = ROOT / "video" / "recreation_tutorial_blender_2d.mp4"
ANIME = ROOT / "video" / "recreation_anime_action.mp4"
FINALE = BA / "skills" / "exemplars" / "finale_confetti.mp4"
W, H, FPS = 1280, 720, 24
T_INTRO, T_GUI, T_TOTAL = 41.0, 499.0, 587.7          # intro reel 0:00-0:41, GUI recording 0:41-9:00, outro 9:00-end


def run(*a, **kw):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, a)], check=True, **kw)


def intro(words):
    out = WORK / "seg_intro.mp4"
    ass = WORK / "intro_caps.ass"
    hook = [w for w in words if w["start"] < 38.0]
    CAP.write_ass(ass, hook, W, H, style="hook", position="lower", max_words=3)
    # our anime action clip, looped and slowly pushed in, graded; the last 3 s become the 'Get the source files' card
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},zoompan=z='1+0.0006*on':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
          f"subtitles={ass.name}")
    run("-stream_loop", "5", "-i", ANIME, "-t", "38", "-an", "-vf", vf, "-r", FPS, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", WORK / "intro_a.mp4", cwd=WORK)
    card = (f"color=c=0x0d1117:s={W}x{H}:d=3:r={FPS},drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='Get the source files':fontcolor=0xFFE000:"
            f"fontsize=84:bordercolor=black:borderw=6:x=(w-text_w)/2:y=(h-text_h)/2")
    run("-f", "lavfi", "-i", card, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", WORK / "intro_b.mp4")
    (WORK / "c_intro.txt").write_text("file 'intro_a.mp4'\nfile 'intro_b.mp4'\n", encoding="utf-8")
    run("-f", "concat", "-safe", "0", "-i", "c_intro.txt", "-c", "copy", out, cwd=WORK)
    return out


def gui():
    raw = WORK / "gui_raw.mp4"
    off = float((WORK / "gui_offset.txt").read_text())
    out = WORK / "seg_gui.mp4"
    run("-ss", f"{off:.2f}", "-i", raw, "-t", T_GUI, "-an", "-vf", f"scale={W}:{H},fps={FPS}", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", out)
    return out


def outro():
    out = WORK / "seg_outro.mp4"
    dur = T_TOTAL - T_INTRO - T_GUI
    vf = (f"scale={W}:{H}:flags=lanczos,fade=t=in:st=0:d=0.5,fade=t=out:st={dur - 0.8:.2f}:d=0.8")
    run("-stream_loop", "12", "-i", FINALE, "-t", f"{dur:.2f}", "-an", "-vf", vf, "-r", FPS, "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", out)
    return out


def main():
    words = json.loads((WORK / "narration_words.json").read_text(encoding="utf-8"))
    parts = [intro(words), gui(), outro()]
    lst = WORK / "concat_all.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    video = WORK / "video_all.mp4"
    run("-f", "concat", "-safe", "0", "-i", lst.name, "-c", "copy", video, cwd=WORK)
    audio = WORK / "narration.wav"
    run("-i", video, "-i", audio, "-filter_complex", "[1:a]apad,aformat=channel_layouts=stereo,loudnorm=I=-14.7:TP=-1.0:LRA=9[a]", "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{T_TOTAL}", OUT)
    print("written", OUT)
    if "--compare" in sys.argv:
        subprocess.run([sys.executable, str(BA / "benchmark" / "compare.py"), str(REF), str(OUT), str(WORK / "compare")], check=True)


if __name__ == "__main__":
    main()
