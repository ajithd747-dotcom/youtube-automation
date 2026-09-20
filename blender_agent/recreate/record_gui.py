"""Launch Blender's GUI with tutorial_gui.py on a virtual display (Xvfb) and screen-record it with ffmpeg (x11grab).

    python blender_agent/recreate/record_gui.py [--speed 1.0] [--out work/recreate_tutorial/gui_raw.mp4]

The server has no monitor, so the GUI runs on a private 1920x1080 Xvfb display: nothing else is affected and the
machine stays usable while the tour (~9 minutes at speed 1) is recorded. Use --speed 20 for a quick 30 s dry run that
shows whether every step works. The virtual display, xdotool and software OpenGL live in blender_agent/tools_bin/ and are
installed on first use by setup_virtual_display.sh.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent / "work" / "recreate_tutorial"
TOOLS = HERE.parent / "tools_bin"
DISPLAY = ":99"
SCREEN = "1920x1080"
CONTINUE_BUTTON = (958, 747)   # Blender's first-run splash 'Continue', centred on the 1920x1080 display


def ensure_virtual_display_tools():
    if not (TOOLS / "Xvfb").exists() or not (TOOLS / "blender-gui").exists():
        print("virtual display tools missing: running setup_virtual_display.sh (downloads ~40 MB, no root needed)")
        subprocess.run(["bash", str(HERE / "setup_virtual_display.sh")], check=True)


def start_virtual_display() -> subprocess.Popen:
    xvfb = subprocess.Popen([str(TOOLS / "Xvfb"), DISPLAY, "-screen", "0", f"{SCREEN}x24", "+extension", "GLX"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):   # ready when the display answers
        if subprocess.run([str(TOOLS / "xdotool"), "getdisplaygeometry"], env={**os.environ, "DISPLAY": DISPLAY},
                          capture_output=True).returncode == 0:
            return xvfb
        time.sleep(0.2)
    xvfb.kill()
    raise RuntimeError("Xvfb did not come up on " + DISPLAY)


def xdotool(*args):
    subprocess.run([str(TOOLS / "xdotool"), *map(str, args)], env={**os.environ, "DISPLAY": DISPLAY}, capture_output=True)


def main():
    speed = float(sys.argv[sys.argv.index("--speed") + 1]) if "--speed" in sys.argv else 1.0
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else WORK / ("gui_raw.mp4" if speed == 1 else "gui_dry.mp4")
    WORK.mkdir(parents=True, exist_ok=True)
    log = WORK / "gui_steps.log"
    for f in (log, Path(str(log) + ".done")):
        f.unlink(missing_ok=True)
    fps = 24
    ensure_virtual_display_tools()
    xvfb = start_virtual_display()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "x11grab", "-framerate", str(fps), "-draw_mouse", "0",
                           "-video_size", SCREEN, "-i", DISPLAY,
                           "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)],
                          stdin=subprocess.PIPE)
    ff_start = time.time()
    bl = subprocess.Popen([str(TOOLS / "blender-gui"), "--python", str(HERE / "tutorial_gui.py"), "--", str(speed), str(log)],
                          env={**os.environ, "DISPLAY": DISPLAY})
    time.sleep(6)   # dismiss Blender's first-run splash: move the pointer away, then click 'Continue'
    xdotool("mousemove", 30, 1000)
    time.sleep(0.6)
    xdotool("mousemove", 1800, 300)
    time.sleep(0.4)
    xdotool("mousemove", *CONTINUE_BUTTON, "click", 1)
    xdotool("mousemove", 1860, 1040)   # park the pointer in a corner
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
    xvfb.terminate()
    tour_start = None
    for line in log.read_text(encoding="utf-8").splitlines() if log.exists() else []:
        if "TOUR START" in line:
            tour_start = float(line.split()[0])
    off = (tour_start - ff_start) if tour_start else 0.0
    (WORK / "gui_offset.txt").write_text(f"{off:.3f}", encoding="utf-8")
    print(f"recorded {out} (tour starts {off:.1f}s into the capture); steps log: {log}")


if __name__ == "__main__":
    main()
