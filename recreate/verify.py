"""Check every shot for the failures that do not raise.

Most of the bugs in this pipeline produced a plausible-looking frame rather than an
error: a black render, an invisible fill, a held glow, a missing frame at the end of a
shot.  This sweeps for those directly so they cannot reach the final cut unnoticed.

  python recreate/verify.py recreate/flip_script3.json --shots 0-12
"""
import argparse
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent


def expand(spec):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        elif part.strip():
            out.append(int(part))
    return out


def check_shot(sh, work, ref_frames, scores_dir):
    i = sh["idx"]
    bad = []
    fin = work / f"s{i:02d}"
    raw = work / f"s{i:02d}_raw"

    for name, d in (("cels", work.parent / "cels" / f"shot{i:02d}.pkl"),
                    ("plate", work.parent / "bg" / f"shot{i:02d}_bg.png")):
        if not d.exists():
            bad.append(f"missing {name}")

    got = sorted(fin.glob("f_*.png"))
    if len(got) != sh["n"]:
        bad.append(f"frames {len(got)}/{sh['n']}")
    if not got:
        return bad, {}

    # sample frames across the shot and look for the silent failure modes
    idxs = sorted({0, len(got) // 4, len(got) // 2, 3 * len(got) // 4, len(got) - 1})
    blacks = flats = alpha_empty = 0
    means = []
    for j in idxs:
        im = cv2.imread(str(got[j]))
        if im is None:
            bad.append(f"unreadable {got[j].name}")
            continue
        means.append(float(im.mean()))
        if im.mean() < 3.0:
            blacks += 1
        if float(im.std()) < 4.0:
            flats += 1
        r = raw / got[j].name
        if r.exists():
            a = cv2.imread(str(r), cv2.IMREAD_UNCHANGED)
            if a is not None and a.shape[2] == 4 and a[:, :, 3].max() == 0:
                alpha_empty += 1
    if blacks:
        bad.append(f"{blacks}/{len(idxs)} near-black frames")
    if flats:
        bad.append(f"{flats}/{len(idxs)} featureless frames")
    if alpha_empty == len(idxs) and alpha_empty:
        bad.append("cel render fully transparent (nothing drawn)")

    sc = scores_dir / f"shot{i:02d}_scores.json"
    info = {}
    if sc.exists():
        d = json.loads(sc.read_text(encoding="utf-8"))
        info = {"ssim": d["mean"]["ssim"], "mae": d["mean"]["mae"], "n": d["n"]}
        if d["mean"]["ssim"] < 0.75:
            bad.append(f"ssim {d['mean']['ssim']:.3f} below 0.75")
        if d["n"] != sh["n"]:
            bad.append(f"scored {d['n']}/{sh['n']}")
    else:
        bad.append("no score")
    return bad, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--shots", default="0-12")
    ap.add_argument("--work", default="recreate/out")
    ap.add_argument("--frames", default="recreate/ref_analysis/flip_hd")
    a = ap.parse_args()

    scr = json.loads((ROOT / a.script).read_text(encoding="utf-8"))
    work = ROOT / a.work
    want = set(expand(a.shots))
    shots = [s for s in scr["shots"] if s["idx"] in want]

    nbad = 0
    rows = []
    for sh in shots:
        bad, info = check_shot(sh, work, ROOT / a.frames, work / "cmp")
        tag = "OK  " if not bad else "FAIL"
        s = f"  {tag} S{sh['idx']:02d} {sh['kind']:10s}"
        if info:
            s += f" {info['n']:3d}f ssim={info['ssim']:.4f} mae={info['mae']:6.2f}"
            rows.append((sh["idx"], info["n"], info["ssim"], info["mae"]))
        if bad:
            nbad += 1
            s += "  << " + "; ".join(bad)
        print(s)

    if rows:
        n = sum(r[1] for r in rows)
        wa = sum(r[2] * r[1] for r in rows) / n
        wm = sum(r[3] * r[1] for r in rows) / n
        print(f"\n  {len(rows)} shots  {n} frames ({n / scr['fps']:.2f}s)  "
              f"weighted ssim={wa:.4f}  mae={wm:.2f}")
    print(f"  {nbad} shot(s) with problems" if nbad else "  all shots clean")
    return 1 if nbad else 0


if __name__ == "__main__":
    sys.exit(main())
