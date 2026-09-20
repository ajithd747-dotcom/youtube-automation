"""Second pass over every shot, then cut the film.

The slow stages (plates, cel decomposition) are already done and stay valid; this
re-measures the per-frame background grade, re-renders from Blender and re-composites,
which is where the later fixes landed.

  python recreate/finalize.py recreate/flip_script3.json --shots 0-12
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "blender_agent"))
from blender_runner import find_blender  # noqa: E402

BLENDER = find_blender()


def sh(cmd):
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore")


def expand(spec):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        elif part.strip():
            out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--shots", default="0-12")
    ap.add_argument("--frames", default="recreate/ref_analysis/flip_hd")
    ap.add_argument("--bloom", type=float, default=0.25)
    ap.add_argument("--skip-grade", action="store_true")
    a = ap.parse_args()

    idx = expand(a.shots)
    scr = json.loads((ROOT / a.script).read_text(encoding="utf-8"))
    have = {s["idx"] for s in scr["shots"]}
    idx = [i for i in idx if i in have]

    if not a.skip_grade:
        r = sh([sys.executable, "recreate/grade.py", a.script, a.frames, "recreate/bg",
                "--shots", ",".join(str(i) for i in idx)])
        for ln in r.stdout.strip().splitlines():
            print(ln, flush=True)

    rows = []
    for i in idx:
        cels = ROOT / "recreate" / "cels" / f"shot{i:02d}.pkl"
        bg = ROOT / "recreate" / "bg" / f"shot{i:02d}_bg.png"
        if not cels.exists() or not bg.exists():
            print(f"  S{i:02d} skipped (missing cels or plate)", flush=True)
            continue
        job = {"cels": cels.as_posix(),
               "out": (ROOT / "recreate" / "out" / f"s{i:02d}_raw").as_posix() + "/f_",
               "save_blend": (ROOT / "recreate" / "out" / f"s{i:02d}.blend").as_posix(),
               "fps": scr["fps"], "ink_width_scale": 1.0}
        jp = ROOT / "recreate" / "out" / f"_job{i:02d}.json"
        jp.write_text(json.dumps(job), encoding="utf-8")
        sh([BLENDER, "-b", "--factory-startup", "--python", "recreate/gp_build.py",
            "--", str(jp)])
        sh([sys.executable, "recreate/post.py", a.script, str(i),
            f"recreate/out/s{i:02d}_raw", str(bg), f"recreate/out/s{i:02d}",
            "--bloom", str(a.bloom)])
        r = sh([sys.executable, "recreate/compare.py", a.script, str(i), a.frames,
                f"recreate/out/s{i:02d}", "recreate/out/cmp"])
        line = (r.stdout.strip().splitlines() or ["?"])[0]
        print("  " + line, flush=True)
        sc = ROOT / "recreate" / "out" / "cmp" / f"shot{i:02d}_scores.json"
        if sc.exists():
            d = json.loads(sc.read_text(encoding="utf-8"))
            rows.append((i, d["n"], d["mean"]["ssim"], d["mean"]["mae"]))

    if rows:
        n = sum(r[1] for r in rows)
        wa = sum(r[2] * r[1] for r in rows) / n
        wm = sum(r[3] * r[1] for r in rows) / n
        print(f"\n{len(rows)} shots, {n} frames ({n / scr['fps']:.2f}s)"
              f"  weighted ssim={wa:.4f}  mae={wm:.2f}", flush=True)


if __name__ == "__main__":
    main()
