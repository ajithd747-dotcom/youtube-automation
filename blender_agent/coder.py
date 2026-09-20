"""Coder: writes extra Blender Python for effects the declarative shot can't express, grounded in the
knowledge base (retrieval-augmented), then test-runs it headless and repairs it from the traceback.

Loop: retrieve docs -> LLM writes code -> static safety check -> Blender `check` run -> on error,
retrieve docs for the error + ask LLM to fix -> repeat (max attempts). A fix that worked after a
failure is stored in knowledge/learned.jsonl so the agent gets better with use.
"""
import ast
import re

import blender_runner
import llm

BANNED_IMPORTS = {"os", "sys", "subprocess", "socket", "shutil", "requests", "urllib", "http", "ctypes", "pathlib", "importlib", "builtins"}
BANNED_CALLS = {"exec", "eval", "open", "compile", "__import__", "input", "globals", "locals", "getattr", "setattr", "delattr"}
BANNED_OPS = re.compile(r"bpy\.ops\.(wm|render|script|screen|preferences|scene\.delete|outliner)\.")

SYSTEM = """You write short Python snippets for Blender {version} (bpy) that ADD an effect to an already-built scene.
Rules:
- The code runs AFTER the base scene exists; do not reset/clear the scene, do not render, do not save files.
- Available without importing: bpy, math, and these helpers from scene_lib: W(), H, frame(t), end_t(), key(obj, frame, loc=, rot=, scale=, interp=),
  empty(name, parent, loc), part(kind, parent, color, loc, scale, rot, flat), prism(parent, pts, depth, color), text_part(parent, text, color, height, max_width, wrap, extrude, loc),
  sample(t0, t1, None, step), rgba(hex), make_material(hex). `import random` is allowed.
- Coordinates: x = right, z = UP, y = depth (the camera looks along +y). Frame height is H (=10) world units, width W().
  All animation must fit within end_t() seconds. Rotation in the picture plane is rotation about the Y axis: rot=(0, angle, 0).
- Prefer the scene_lib helpers over raw bpy.ops. Never import os/sys/subprocess/socket; never call open/exec/eval.
- Keep it under 60 lines. Reply with ONE ```python code block and nothing else.

Reference documentation retrieved for this task (verified against the installed Blender; trust it over your memory):
{context}
"""


def static_check(code: str):
    """Return an error string if the code uses anything outside the sandbox contract, else None."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"SyntaxError: {e}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in BANNED_IMPORTS:
                    return f"forbidden import: {a.name}"
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in BANNED_IMPORTS:
                return f"forbidden import: {node.module}"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
            return f"forbidden call: {node.func.id}()"
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return f"forbidden dunder attribute: {node.attr}"
    m = BANNED_OPS.search(code)
    if m:
        return f"forbidden operator namespace: {m.group(0)}"
    return None


def write_custom_code(request: str, shot: dict, job_base: dict, kb, blender_version="4.x", attempts=3, log=print):
    """Returns working code (str) or None if it could not be made to run."""
    style = shot.get("style", "kinetic")
    ctx = kb.context(f"{request} {style} keyframe animation scene_lib", k=6, budget=5500)
    try:
        import skills as _sk
        sc = _sk.context_for(request, k=2, style=style, kinds=["technique", "pitfall", "rule"], budget=2500)
        if sc:
            ctx = "PROVEN SKILLS (from finished videos / reference material; prefer these procedures):\n" + sc + "\n\n" + ctx
    except Exception:
        pass
    system = SYSTEM.format(version=blender_version, context=ctx)
    prompt = (f"Effect requested: {request}\nExisting shot (already built): style={style}, "
              f"objects={[(o['type'], o['pos']) for o in shot['objects']]}\nWrite the code.")
    code, first_error = None, None
    for attempt in range(1, attempts + 1):
        try:
            code = llm.extract_code(llm.ask(prompt, system))
        except Exception as e:
            log(f"    [coder] LLM unavailable: {str(e)[:80]}")
            return None
        err = static_check(code)
        if err:
            res = {"ok": False, "error": err, "traceback": ""}
        else:
            res = blender_runner.run_job(dict(job_base, mode="check", custom_code=code), timeout=180)
        if res.get("ok"):
            log(f"    [coder] custom code OK (attempt {attempt})")
            if first_error:
                import knowledge.kb as kbmod
                kbmod.remember(first_error, code, note=f"Request: {request}")
            return code
        first_error = first_error or res.get("error", "unknown error")
        log(f"    [coder] attempt {attempt} failed: {res.get('error', '')[:120]}")
        fix_ctx = kb.context(f"{res.get('error', '')} {res.get('traceback', '')[-400:]}", k=4, budget=3500)
        prompt = (f"Effect requested: {request}\nYour code:\n```python\n{code}\n```\nIt failed with:\n{res.get('error')}\n"
                  f"{res.get('traceback', '')}\n\nRelevant docs:\n{fix_ctx}\n\nFix it. Reply with the full corrected code block only.")
    return None
