"""Visual QA agent - checks a planned shot BEFORE the long render and fixes what it can.

check(shot, ...)  : renders one draft still (mid-shot, physics stepped) and measures luminance/contrast/clipping/haze/colourfulness,
                    then runs a headless framing test (key subject points projected into the camera at first/mid/last frame)
fix(report, shot) : maps findings to recipe params (exposure_bias, fog_scale) - the same params the recipes already understand
review(plan, ...) : runs both over every cinematic shot of a plan and writes the fixes into plan.json (with the evidence)
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "blender_agent"))
from core import Agent  # noqa: E402

import blender_runner  # noqa: E402

FRAMING_TEST = '''
import bpy
from bpy_extras.object_utils import world_to_camera_view
sc = bpy.context.scene
cam = sc.camera
bad = []
for f in (sc.frame_start, (sc.frame_start + sc.frame_end) // 2, sc.frame_end):
    sc.frame_set(f)
    for name in ("head", "l_kn"):
        o = bpy.data.objects.get(name)
        if o is None:
            continue
        v = world_to_camera_view(sc, cam, o.matrix_world.translation)
        if not (0.0 < v.x < 1.0 and 0.0 < v.y < 1.0):
            bad.append((f, name, round(v.x, 2), round(v.y, 2)))
assert not bad, "subject outside frame: %s" % bad
'''


def image_metrics(png):
    from PIL import Image
    im = np.asarray(Image.open(png).convert("RGB")).astype(np.float32) / 255.0
    lum = 0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2]
    mx, mn = im.max(axis=2), im.min(axis=2)
    sat = float(np.mean((mx - mn) / (mx + 1e-6)))
    gy, gx = np.gradient(lum)
    return {"lum_mean": round(float(lum.mean()), 3), "lum_std": round(float(lum.std()), 3), "p5": round(float(np.percentile(lum, 5)), 3),
            "p95": round(float(np.percentile(lum, 95)), 3), "clipped_hi": round(float((lum > 0.98).mean()), 3), "crushed_lo": round(float((lum < 0.02).mean()), 3),
            "saturation": round(sat, 3), "edge_density": round(float(np.hypot(gx, gy).mean()), 4)}


class VisualQaAgent(Agent):
    """See module docstring."""

    def check(self, shot, width=640, height=360, fps=12, duration=3.0, workdir=None):
        workdir = Path(workdir or HERE / "cache")
        workdir.mkdir(parents=True, exist_ok=True)
        png = workdir / "qa_still.png"
        png.unlink(missing_ok=True)
        r = blender_runner.run_job({"shot": shot, "width": width, "height": height, "fps": fps, "duration": duration, "quality": "draft",
                                    "mode": "still", "out": str(png)}, timeout=600)
        if not r.get("ok") or not png.exists():
            return {"ok": False, "findings": [{"id": "render_failed", "detail": r.get("error")}]}
        m = image_metrics(png)
        findings = []
        if m["lum_mean"] > 0.6 and m["lum_std"] < 0.14:
            findings.append({"id": "washed_out", "detail": f"mean {m['lum_mean']} std {m['lum_std']}: hazy / overexposed"})
        if m["lum_mean"] < 0.07:
            findings.append({"id": "too_dark", "detail": f"mean {m['lum_mean']}"})
        if m["clipped_hi"] > 0.10:
            findings.append({"id": "clipped_highlights", "detail": f"{m['clipped_hi'] * 100:.0f}% of pixels near white"})
        if m["crushed_lo"] > 0.55 and shot.get("style") == "cinematic" and shot.get("mood") not in ("night", "neon", "studio"):
            findings.append({"id": "crushed_blacks", "detail": f"{m['crushed_lo'] * 100:.0f}% near black"})
        if m["p95"] - m["p5"] < 0.2:
            findings.append({"id": "flat_contrast", "detail": f"p95-p5 = {m['p95'] - m['p5']:.2f}"})
        fr = blender_runner.run_job({"shot": shot, "width": 320, "height": 180, "fps": fps, "duration": duration, "quality": "draft", "mode": "check",
                                     "custom_code": FRAMING_TEST}, timeout=300)
        if not fr.get("ok") and "outside frame" in str(fr.get("error")):
            findings.append({"id": "subject_out_of_frame", "detail": str(fr.get("error"))[:200]})
        return {"ok": not findings, "metrics": m, "findings": findings, "still": str(png)}

    def fix(self, report, shot):
        """Returns updated params (exposure_bias / fog_scale) for the findings; never touches other parts of the shot."""
        p = dict(shot.get("params") or {})
        ids = {f["id"] for f in report.get("findings", [])}
        if "washed_out" in ids:
            p["exposure_bias"] = round(p.get("exposure_bias", 0.0) - 0.6, 2)
            p["fog_scale"] = round(p.get("fog_scale", 1.0) * 0.5, 2)
        if "clipped_highlights" in ids:
            p["exposure_bias"] = round(p.get("exposure_bias", 0.0) - 0.5, 2)
        if "too_dark" in ids:
            p["exposure_bias"] = round(p.get("exposure_bias", 0.0) + 0.8, 2)
        if "flat_contrast" in ids and "washed_out" not in ids:
            p["fog_scale"] = round(p.get("fog_scale", 1.0) * 0.6, 2)
        return p

    def review(self, plan_file, durations=None, rounds=2, log=print):
        plan = json.loads(Path(plan_file).read_text(encoding="utf-8"))
        changed = 0
        for i, shot in enumerate(plan["shots"]):
            if shot.get("style") != "cinematic":
                continue
            dur = (durations[i] if durations else 3.0)
            for r in range(rounds):
                rep = self.check(shot, duration=dur)
                if rep["ok"] or not rep.get("metrics"):
                    break
                new = self.fix(rep, shot)
                if new == shot.get("params"):
                    break
                log(f"  [qa] shot {i + 1} {shot['recipe']}: {[f['id'] for f in rep['findings']]} -> params {new}")
                shot["params"] = new
                shot.setdefault("qa", []).append({"round": r + 1, "findings": rep["findings"], "metrics": rep["metrics"], "applied": new})
                changed += 1
        Path(plan_file).write_text(json.dumps(plan, indent=2), encoding="utf-8")
        return changed

    def run(self, task="", **kw):
        return {"task": task, "note": "use check / fix / review"}
