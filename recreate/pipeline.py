"""Drive the whole rebuild: plates -> cels -> Blender render -> composite -> score.

One shot or many, resumable, so a long run can be stopped and picked back up.

  python recreate/pipeline.py <script.json> --shots 5,9 --stages all
  python recreate/pipeline.py <script.json> --shots 9 --stages render,post,score
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "blender_agent"))
from blender_runner import find_blender  # noqa: E402

_print = print


def print(*a, **k):  # progress must reach a piped log as it happens, not at exit
    k.setdefault("flush", True)
    _print(*a, **k)

ROOT = Path(__file__).resolve().parent.parent
REC = ROOT / "recreate"
BLENDER = find_blender()
STAGES = ["bg", "cels", "render", "post", "score"]


def run(cmd, **kw):
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="ignore", **kw)
    return r


def main():  # noqa: C901
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--frames", default="recreate/ref_analysis/flip_hd")
    ap.add_argument("--work", default="recreate")
    ap.add_argument("--shots", default="")
    ap.add_argument("--stages", default="all")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--bloom", type=float, default=0.25)
    ap.add_argument("--plate-motion", type=float, default=0.0)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    scr = json.loads((ROOT / a.script).read_text(encoding="utf-8"))
    want = ([int(x) for x in a.shots.split(",") if x.strip()]
            if a.shots else [s["idx"] for s in scr["shots"]])
    stages = STAGES if a.stages == "all" else [s.strip() for s in a.stages.split(",")]
    W = Path(a.work)

    for idx in want:
        sh = next(s for s in scr["shots"] if s["idx"] == idx)
        t0 = time.time()
        print(f"\n=== shot {idx:02d}  f{sh['start']}-{sh['end']}  "
              f"{sh['dur']:.2f}s  {sh['kind']}  {sh['n_drawings']} drawings ===")

        bg = W / "bg" / f"shot{idx:02d}_bg.png"
        cels = W / "cels" / f"shot{idx:02d}.pkl"
        raw = W / "out" / f"s{idx:02d}_raw"
        fin = W / "out" / f"s{idx:02d}"

        if "bg" in stages and (a.force or not bg.exists()):
            r = run([sys.executable, "recreate/background.py", a.script, a.frames,
                     str(W / "bg"), "--shots", str(idx)])
            print("  bg  :", (r.stdout.strip().splitlines() or ["?"])[-1])

        if "cels" in stages and (a.force or not cels.exists()):
            r = run([sys.executable, "recreate/export_cels.py", a.script, a.frames,
                     str(W / "cels"), "--shots", str(idx), "--jobs", str(a.jobs)])
            print("  cels:", (r.stdout.strip().splitlines() or ["?"])[-1])

        if "render" in stages:
            job = {"cels": str((ROOT / cels).as_posix()),
                   "out": str((ROOT / raw).as_posix()) + "/f_",
                   "save_blend": str((ROOT / W / "out" / f"s{idx:02d}.blend").as_posix()),
                   "fps": scr["fps"], "ink_width_scale": 1.0}
            jp = ROOT / "recreate" / "out" / f"_job{idx:02d}.json"
            jp.parent.mkdir(parents=True, exist_ok=True)
            jp.write_text(json.dumps(job), encoding="utf-8")
            r = run([BLENDER, "-b", "--factory-startup", "--python",
                     "recreate/gp_build.py", "--", str(jp)])
            line = [x for x in r.stdout.splitlines() if x.startswith("RESULT")]
            print("  rend:", line[-1] if line else r.stdout[-300:])

        if "post" in stages:
            r = run([sys.executable, "recreate/post.py", a.script, str(idx), str(raw),
                     str(bg), str(fin), "--bloom", str(a.bloom),
                    "--plate-motion", str(a.plate_motion)])
            print("  post:", (r.stdout.strip().splitlines() or ["?"])[-1])

        if "score" in stages:
            r = run([sys.executable, "recreate/compare.py", a.script, str(idx),
                     a.frames, str(fin), str(W / "out" / "cmp")])
            for ln in r.stdout.strip().splitlines():
                print("  ", ln)

        print(f"  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
