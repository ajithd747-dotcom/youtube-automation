"""Locate Blender and run headless jobs (render_shot.py) as subprocesses."""
import glob
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

SIDE = Path(__file__).resolve().parent / "blender_side"


def find_blender() -> str:
    env = os.environ.get("BLENDER_PATH")
    if env and Path(env).exists():
        return env
    found = shutil.which("blender")
    if found:
        return found
    pats = [r"C:\Program Files\Blender Foundation\Blender *\blender.exe",
            r"C:\Program Files (x86)\Blender Foundation\Blender *\blender.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Blender Foundation\Blender *\blender.exe"),
            "/Applications/Blender.app/Contents/MacOS/Blender", "/usr/bin/blender", "/snap/bin/blender"]
    for pat in pats:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    raise FileNotFoundError("Blender not found. Install it (winget install BlenderFoundation.Blender.LTS.4.5) "
                            "or set BLENDER_PATH to blender.exe")


def run_job(job: dict, timeout=7200) -> dict:
    """Run one render_shot.py job. Returns the result dict ({ok, error?, traceback?, engine?, ...})."""
    with tempfile.TemporaryDirectory() as td:
        job = dict(job, result=str(Path(td) / "result.json"))
        jp = Path(td) / "job.json"
        jp.write_text(json.dumps(job), encoding="utf-8")
        cmd = [find_blender(), "-b", "--factory-startup", "--python", str(SIDE / "render_shot.py"), "--", str(jp)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="ignore")
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"Blender timed out after {timeout}s"}
        rp = Path(job["result"])
        if rp.exists():
            res = json.loads(rp.read_text(encoding="utf-8"))
        else:
            res = {"ok": False, "error": "Blender exited without a result", "traceback": (proc.stderr or proc.stdout)[-1500:]}
        res["log_tail"] = (proc.stdout or "")[-600:]
        return res
