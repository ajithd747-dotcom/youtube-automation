"""Entry point executed by Blender:  blender -b --python render_shot.py -- <job.json>

job.json: {shot, width, height, fps, duration, engine, out, custom_code (optional),
           mode: "render" | "check" | "still", result: path to write the result json}

  check  - build the scene + run custom code, report errors, do NOT render (fast; used by the repair loop)
  still  - render only the middle frame to a PNG (`out`) for quick visual checks
  render - render the full shot to an mp4 (`out`)
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import scene_lib  # noqa: E402


def run_custom(code):
    """Exec LLM-written code with the scene_lib helpers in scope. Returns None or an error dict."""
    ns = {"bpy": bpy, "scene_lib": scene_lib, "math": __import__("math"), "H": scene_lib.H}
    try:  # cinematic helpers (materials, lights, camera, physics) are available too when that mode is in use
        import cine_lib
        ns["C"] = cine_lib
        for name in dir(cine_lib):
            if not name.startswith("_") and name not in ns:
                ns[name] = getattr(cine_lib, name)
    except Exception:
        pass
    for name in dir(scene_lib):
        if not name.startswith("_"):
            ns[name] = getattr(scene_lib, name)
    try:
        exec(compile(code, "<custom>", "exec"), ns)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()[-1800:]}
    return None


def main():
    job = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
    result = {"ok": False}
    try:
        cinematic = job["shot"].get("style") in ("cinematic", "anime")
        if job["shot"].get("style") == "anime":
            import anime_recipes
            name = anime_recipes.build(job["shot"], job["width"], job["height"], job["fps"], job["duration"], job.get("quality", "standard"))
            chosen, roots = bpy.context.scene.render.engine, list(bpy.data.objects)
            result["recipe"], result["mood"] = name, "anime"
        elif cinematic:
            import cine_recipes
            name, mood = cine_recipes.build(job["shot"], job["width"], job["height"], job["fps"], job["duration"],
                                            job.get("quality", "standard"))
            chosen, roots = bpy.context.scene.render.engine, list(bpy.data.objects)
            result["recipe"], result["mood"] = name, mood
        else:
            chosen, roots = scene_lib.build_shot(job["shot"], job["width"], job["height"], job["fps"], job["duration"],
                                                 job.get("engine", "auto"))
        if job["shot"].get("style") == "anime":  # exact frame count: the build keeps one extra end key frame, the render must not
            sc0 = bpy.context.scene
            sc0.frame_end = sc0.frame_start + int(round(job["duration"] * job["fps"])) - 1
        result["engine"] = chosen
        result["objects"] = len(roots)
        if job.get("custom_code"):
            err = run_custom(job["custom_code"])
            if err:
                result.update(err)
                return result
        sc = bpy.context.scene
        mode = job.get("mode", "render")
        if mode == "check":
            result["ok"] = True
            return result
        if mode == "still":
            mid = (sc.frame_start + sc.frame_end) // 2
            for fr in range(sc.frame_start, mid + 1):  # step frames in order so physics caches are simulated
                sc.frame_set(fr)
            sc.render.image_settings.file_format = "PNG"
            sc.render.filepath = job["out"]
            bpy.ops.render.render(write_still=True)
        else:
            if cinematic:
                # Rigid-body physics is only simulated in the *active* (viewport) depsgraph, so a plain animation render shows
                # frozen objects. Step every frame once first: this fills the physics caches, which the render then replays.
                for fr in range(sc.frame_start, sc.frame_end + 1):
                    sc.frame_set(fr)
                sc.frame_set(sc.frame_start)
            sc.render.image_settings.file_format = "FFMPEG"
            sc.render.ffmpeg.format = "MPEG4"
            sc.render.ffmpeg.codec = "H264"
            sc.render.ffmpeg.constant_rate_factor = "HIGH" if cinematic else "MEDIUM"
            sc.render.ffmpeg.ffmpeg_preset = "GOOD"
            sc.render.filepath = job["out"]
            bpy.ops.render.render(animation=True)
        result["ok"] = True
    except Exception as exc:
        result.update(error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc()[-1800:])
    return result


if __name__ == "__main__":
    res = main()
    with open(json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))["result"], "w", encoding="utf-8") as fh:
        json.dump(res, fh)
