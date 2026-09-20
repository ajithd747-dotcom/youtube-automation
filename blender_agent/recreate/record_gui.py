"""Launch Blender's GUI with tutorial_gui.py and screen-record it with ffmpeg (gdigrab).

    python blender_agent/recreate/record_gui.py [--speed 1.0] [--out work/recreate_tutorial/gui_raw.mp4]

The GUI takes over the screen (fullscreen) for the length of the tour (~9 minutes at speed 1): do not touch the machine meanwhile.
Use --speed 20 for a quick 30 s dry run that shows whether every step works.
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent / "work" / "recreate_tutorial"
BLENDER = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"


def main():
    speed = float(sys.argv[sys.argv.index("--speed") + 1]) if "--speed" in sys.argv else 1.0
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else WORK / ("gui_raw.mp4" if speed == 1 else "gui_dry.mp4")
    WORK.mkdir(parents=True, exist_ok=True)
    log = WORK / "gui_steps.log"
    for f in (log, Path(str(log) + ".done")):
        f.unlink(missing_ok=True)
    fps = 24
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "gdigrab", "-framerate", str(fps), "-draw_mouse", "0", "-i", "desktop",
                           "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)],
                          stdin=subprocess.PIPE)
    ff_start = time.time()
    bl = subprocess.Popen([BLENDER, "--python", str(HERE / "tutorial_gui.py"), "--", str(speed), str(log)])
    try:  # dismiss Blender's first-run splash: move the pointer away, then click where 'Continue' would be
        import ctypes
        time.sleep(6)
        u = ctypes.windll.user32
        u.SetCursorPos(30, 1000)
        time.sleep(0.6)
        u.SetCursorPos(1800, 300)
        time.sleep(0.4)
        u.SetCursorPos(960, 795)
        u.mouse_event(2, 0, 0, 0, 0)
        u.mouse_event(4, 0, 0, 0, 0)
        u.SetCursorPos(1860, 1040)   # park the pointer in a corner
    except Exception as e:
        print("could not dismiss splash:", e)
    deadline = time.time() + 540 / speed + 120
    done = Path(str(log) + ".done")
    while time.time() < deadline and not done.exists() and bl.poll() is None:
        time.sleep(1)
    time.sleep(2)
    try:
        ff.stdin.write(b"q")
        ff.stdin.flush()
    except Exception:
        pass
    try:
        ff.wait(timeout=30)
    except Exception:
        ff.kill()
    if bl.poll() is None:
        bl.terminate()
    tour_start = None
    for line in log.read_text(encoding="utf-8").splitlines() if log.exists() else []:
        if "TOUR START" in line:
            tour_start = float(line.split()[0])
    off = (tour_start - ff_start) if tour_start else 0.0
    (WORK / "gui_offset.txt").write_text(f"{off:.3f}", encoding="utf-8")
    print(f"recorded {out} (tour starts {off:.1f}s into the capture); steps log: {log}")


if __name__ == "__main__":
    main()
