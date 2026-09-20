"""Blender video agent: paste a script, get an animated video.

    python blender_agent/agent.py path/to/script.json            # or .md / .txt
    python blender_agent/agent.py --paste                        # paste script in the terminal, finish with a line: END
    python blender_agent/agent.py --clipboard                    # use whatever script text is on the clipboard
    python blender_agent/agent.py --text "First sentence. Second sentence."
    options: --style auto|stickman|kinetic|3d   --format normal|shorts   --preview   --engine auto|eevee|workbench|cycles
             --voice <edge-tts voice>   --name <out name>   --replan   --no-custom   --no-tts (silent, text-timed)

Pipeline: parse script -> voiceover per segment (edge-tts) -> director plans a shot per segment (LLM, validated DSL,
heuristic fallback) -> optional LLM-written bpy code for special effects (RAG over Blender docs + self-repair) ->
headless Blender renders each shot -> ffmpeg adds audio + captions and joins everything into one mp4.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import blender_runner  # noqa: E402
import coder  # noqa: E402
import director  # noqa: E402

FORMATS = {"normal": (1280, 720), "shorts": (720, 1280)}
PREVIEW = {"normal": (640, 360), "shorts": (360, 640)}
CTA_RE = re.compile(r"subscribe|like this|hit like|comment|follow|thanks for watching|see you", re.I)


# ----------------------------------------------------------------------------- script input
def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "script"


def split_plain(text: str):
    """Plain pasted text -> (kind, topic, text) segments: paragraphs, or ~2-sentence groups."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) < 3:
        sents = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
        paras, cur = [], ""
        for s in sents:
            if cur and len(cur) + len(s) > 230:
                paras.append(cur)
                cur = s
            else:
                cur = (cur + " " + s).strip()
        if cur:
            paras.append(cur)
    out = []
    for i, p in enumerate(paras):
        p = re.sub(r"\s+", " ", p)
        kind = "hook" if i == 0 else ("outro" if i == len(paras) - 1 and CTA_RE.search(p) else "segment")
        out.append((kind, "", p))
    return out


def load_script(args):
    """Returns (name, title, segments)."""
    if args.text or args.paste or args.clipboard:
        if args.text:
            text = args.text
        elif args.clipboard:
            text = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"], capture_output=True,
                                  text=True, encoding="utf-8").stdout
        else:
            print("Paste your script, then type END on its own line (or press Ctrl+Z, Enter):")
            lines = []
            for line in sys.stdin:
                if line.strip() == "END":
                    break
                lines.append(line)
            text = "".join(lines)
        text = text.strip()
        if not text:
            sys.exit("No script text received.")
        name = args.name or slugify(" ".join(text.split()[:6]))
        (HERE / "scripts_in").mkdir(exist_ok=True)
        (HERE / "scripts_in" / f"{name}.txt").write_text(text, encoding="utf-8")
        if text.lstrip().startswith("{"):
            data = json.loads(text)
            segs = [(s.get("kind", "segment"), s.get("topic", ""), s["text"]) for s in data.get("segments", []) if s.get("text")]
            return name, data.get("title", name), segs
        return name, name, split_plain(text)

    path = Path(args.script)
    if not path.exists():
        sys.exit(f"Script file not found: {path}")
    name = args.name or path.stem.replace("_script", "")
    if path.suffix.lower() == ".txt":
        return name, name, split_plain(path.read_text(encoding="utf-8"))
    from video.assemble import parse_segments  # existing parser for the pipeline's .json/.md scripts
    title = name
    if path.suffix.lower() == ".json":
        title = json.loads(path.read_text(encoding="utf-8")).get("title", name)
    return name, title, parse_segments(path)


# ----------------------------------------------------------------------------- media helpers
def ffmpeg(*a):
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, a)], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode:
        raise RuntimeError("ffmpeg failed: " + r.stderr[-600:])


def audio_seconds(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def estimate_seconds(text: str) -> float:
    return max(2.5, len(text.split()) / 2.6)  # ~156 wpm


def write_ass(path: Path, text: str, duration: float, w: int, h: int):
    size = int(h * (0.052 if w > h else 0.03))
    clean = re.sub(r"\s+", " ", text).replace("{", "(").replace("}", ")")
    t = lambda s: f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nWrapStyle: 0\nPlayResX: %d\nPlayResY: %d\n\n[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        "Style: Cap,Arial,%d,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,0,2,%d,%d,%d,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
        "Dialogue: 0,%s,%s,Cap,,0,0,0,,%s\n" % (w, h, size, int(w * 0.09), int(w * 0.09), int(h * 0.06), t(0), t(duration), clean),
        encoding="utf-8")


# ----------------------------------------------------------------------------- main pipeline
def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Turn a script into an animated video with Blender.")
    ap.add_argument("script", nargs="?", help="script file (.json/.md/.txt)")
    ap.add_argument("--text"), ap.add_argument("--paste", action="store_true"), ap.add_argument("--clipboard", action="store_true")
    ap.add_argument("--style", default="auto", choices=["auto", "stickman", "kinetic", "3d", "cinematic"])
    ap.add_argument("--format", default="normal", choices=list(FORMATS))
    ap.add_argument("--engine", default="auto", choices=["auto", "eevee", "workbench", "cycles"])
    ap.add_argument("--preview", action="store_true", help="low-res, 12 fps quick draft")
    ap.add_argument("--quality", default=None, choices=["draft", "standard", "final"], help="cinematic render quality (default standard; draft with --preview)")
    ap.add_argument("--voice", default=None), ap.add_argument("--name", default=None)
    ap.add_argument("--replan", action="store_true", help="ignore a saved plan and ask the director again")
    ap.add_argument("--no-custom", action="store_true", help="skip LLM-written custom bpy effects")
    ap.add_argument("--no-tts", action="store_true", help="skip voiceover; time shots from word count")
    ap.add_argument("--qa", action="store_true", help="visual-qa agent: still-check every cinematic shot and auto-fix exposure/haze before the long render")
    ap.add_argument("--plan-only", action="store_true", help="write voiceover + plan.json, then stop (review the plan before a long render)")
    ap.add_argument("--max-segments", type=int, default=0, help="only render the first N segments (testing)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if not (args.script or args.text or args.paste or args.clipboard):
        ap.error("give a script file, or use --paste / --clipboard / --text")

    t_start = time.time()
    name, title, segments = load_script(args)
    if args.max_segments:
        segments = segments[:args.max_segments]
    if not segments:
        sys.exit("No segments found in the script.")
    portrait = args.format == "shorts"
    width, height = (PREVIEW if args.preview else FORMATS)[args.format]
    fps = 12 if args.preview else 24
    work = HERE / "work" / name
    work.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else ROOT / "video" / f"{name}_blender{'_preview' if args.preview else ''}.mp4"
    print(f"[agent] '{title}': {len(segments)} segments, {width}x{height}@{fps}, blender={blender_runner.find_blender()}")

    # 1) voiceover + durations
    durations = []
    for i, (kind, topic, text) in enumerate(segments):
        text = director_text = re.sub(r"\s+", " ", text).strip()
        mp3 = work / f"seg{i:02d}.mp3"
        if args.no_tts:
            durations.append(estimate_seconds(text))
            continue
        if not mp3.exists():
            from video.tts import VOICES, generate_voiceover
            print(f"[{i + 1}/{len(segments)}] voiceover...")
            generate_voiceover(text, str(mp3), voice=args.voice or VOICES["default"])
        durations.append(audio_seconds(mp3) + 0.35)

    # 2) plan shots (cached in plan.json so you can hand-edit it, then re-run)
    plan_file = work / "plan.json"
    plan = None
    if plan_file.exists() and not args.replan:
        cached = json.loads(plan_file.read_text(encoding="utf-8"))
        if cached.get("segments") == [list(s) for s in segments]:
            plan = cached
            print(f"[agent] reusing saved plan {plan_file} (use --replan to regenerate)")
    if plan is None:
        style = args.style if args.style != "auto" else director.pick_style(title, segments)
        print(f"[agent] style: {style}")
        shots, prev = [], ""
        for i, (kind, topic, text) in enumerate(segments):
            print(f"[{i + 1}/{len(segments)}] directing ({kind})...")
            used = [x.get("recipe") for x in shots if x.get("recipe")]
            shot = director.plan_shot(kind, topic, text, durations[i], style, portrait, not args.no_custom, prev, used)
            prev = director.summarize(shot)
            shots.append(shot)
        plan = {"title": title, "style": style, "segments": [list(s) for s in segments], "shots": shots}
        plan_file.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        (work / "plan.auto.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")  # untouched copy: human edits to plan.json become preferences

    if args.qa and plan.get("style") == "cinematic":
        sys.path.insert(0, str(ROOT / "agents"))
        from core import load_agent
        print("[agent] visual QA on the plan ...", flush=True)
        n = load_agent("visual-qa").review(plan_file, durations=durations, log=lambda m: print(m, flush=True))
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
        print(f"[agent] visual QA applied {n} fix(es)", flush=True)

    if args.plan_only:
        print(f"[agent] plan written to {plan_file}; re-run without --plan-only to render", flush=True)
        for i, shot in enumerate(plan["shots"]):
            print(f"  {i + 1:2d}. {durations[i]:4.1f}s  {director.summarize(shot)}  title={shot.get('title', '')!r}")
        return

    # 3) knowledge base (only needed if some shot asks for custom effects)
    kb, bver = None, "4.x"
    if any(s.get("custom") for s in plan["shots"]) and not args.no_custom and plan.get("style") != "cinematic":
        from knowledge.kb import KB
        kb = KB()

    # 4) render each shot
    seg_files = []
    for i, ((kind, topic, text), shot) in enumerate(zip(segments, plan["shots"])):
        dur = durations[i]
        quality = args.quality or ("draft" if args.preview else "standard")
        base = {"shot": shot, "width": width, "height": height, "fps": fps, "duration": dur, "engine": args.engine, "quality": quality}
        custom_code = None
        if shot.get("custom") and kb and not args.no_custom:
            print(f"[{i + 1}/{len(segments)}] custom effect: {shot['custom']}")
            custom_code = coder.write_custom_code(shot["custom"], shot, base, kb, bver, log=print)
            (work / f"seg{i:02d}_custom.py").write_text(custom_code or "# (custom effect failed; shot rendered without it)", encoding="utf-8")
        key = hashlib.sha1(json.dumps([shot, custom_code, width, height, fps, round(dur, 2), args.engine, quality], sort_keys=True).encode()).hexdigest()[:10]
        raw = work / f"seg{i:02d}_{key}_raw.mp4"
        if not raw.exists():
            print(f"[{i + 1}/{len(segments)}] rendering {shot['style']} shot ({dur:.1f}s)...")
            t0 = time.time()
            res = blender_runner.run_job(dict(base, mode="render", out=str(raw), custom_code=custom_code))
            if not res.get("ok") and shot.get("style") == "cinematic" and quality != "draft":
                print(f"    render failed ({str(res.get('error'))[:100]}); retrying this shot at draft quality", flush=True)
                raw.unlink(missing_ok=True)
                res = blender_runner.run_job(dict(base, quality="draft", mode="render", out=str(raw), custom_code=custom_code))
            if not res.get("ok"):
                sys.exit(f"Render failed for segment {i}: {res.get('error')}\n{res.get('traceback', '')}")
            found = raw if raw.exists() else next(iter(sorted(work.glob(raw.stem + "*.mp4"))), None)
            if found is None:
                sys.exit(f"Blender finished but produced no file for segment {i}\n{res.get('log_tail', '')}")
            if found != raw:
                found.replace(raw)
            print(f"    engine={res.get('engine')} objects={res.get('objects')} render={time.time() - t0:.0f}s")

        # 5) mux: audio + burned-in captions
        final = work / f"seg{i:02d}_{key}.mp4"
        if not final.exists():
            ass = work / f"seg{i:02d}.ass"
            write_ass(ass, text, dur, width, height)
            cmd = ["-i", raw.name]
            mp3 = work / f"seg{i:02d}.mp3"
            if mp3.exists() and not args.no_tts:
                cmd += ["-i", mp3.name]
            else:
                cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
            vf = f"subtitles={ass.name}"
            if shot.get("style") == "cinematic":  # film-style finishing: vignette, gentle grade, short dip-to-black between shots
                vf = (f"vignette=PI/5,eq=contrast=1.06:saturation=1.12,fade=t=in:st=0:d=0.18,"
                      f"fade=t=out:st={max(0.0, dur - 0.18):.2f}:d=0.18," + vf)
            cmd += ["-vf", vf, "-af", "apad", "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-r", str(fps), final.name]
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *cmd], cwd=work, check=True)
        seg_files.append(final)

    # 6) join
    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{f.name}'\n" for f in seg_files), encoding="utf-8")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing.name, "-c", "copy",
                    "-movflags", "+faststart", str(out_path)], cwd=work, check=True)
    if kb:  # fold any newly learned fixes into the index for next time
        from knowledge.kb import LEARNED, build
        if LEARNED.exists():
            build(with_api=True)
    try:  # skill library: usage statistics + retrospective (candidate skills from human plan edits, etc.)
        import skills as SKL
        ids = [sid for sh in plan["shots"] for sid in sh.get("skills", [])]
        rs = {r: sk.id for r, sk in SKL.recipe_skills("cinematic").items()}
        ids += [rs[sh["recipe"]] for sh in plan["shots"] if sh.get("recipe") in rs]
        if ids:
            SKL.record_use(ids, name)
        SKL.learn_from_run(work, name, log=lambda m: print(m, flush=True))
    except Exception as e:
        print(f"[skills] retrospective skipped: {e}")
    print(f"[agent] done in {time.time() - t_start:.0f}s -> {out_path}")


if __name__ == "__main__":
    main()
