"""Every cookbook snippet must run cleanly in headless Blender (they are shown to the LLM as 'known good').
Run:  python blender_agent/tests/test_cookbook.py [--still]   (--still also renders a mid-frame PNG per snippet)"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import blender_runner  # noqa: E402

shot = {"style": "kinetic", "bg": "#101826", "camera": "static",
        "objects": [{"type": "text", "text": "Cookbook", "pos": [0, 0.7], "size": 0.1, "color": "#ffffff"}]}
out = HERE / "work" / "_cookbook"
out.mkdir(parents=True, exist_ok=True)
fails = 0
for f in sorted((HERE / "knowledge" / "cookbook").glob("*.py")):
    st = "3d" if "3d" in f.stem else "kinetic"
    base = {"shot": dict(shot, style=st), "width": 640, "height": 360, "fps": 12, "duration": 3.0, "engine": "workbench",
            "custom_code": f.read_text(encoding="utf-8")}
    res = blender_runner.run_job(dict(base, mode="still" if "--still" in sys.argv else "check", out=str(out / (f.stem + ".png"))), timeout=240)
    ok = res.get("ok")
    fails += not ok
    print(("PASS " if ok else "FAIL ") + f.stem, "" if ok else res.get("error") + "\n" + res.get("traceback", "")[-500:])
sys.exit(1 if fails else 0)
