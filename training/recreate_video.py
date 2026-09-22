"""Recreate a whole reference video: every shot through the rung 3/4 pipeline (scene from the shot script, lights tuned to the
script's measured features, character proxy when the semantic pass names one), joined with the recreated voice + music
(training/recreate_audio.py), encoded, and scored frame by frame against the reference.

    .venv/bin/python training/recreate_video.py <slug> [--rounds 6] [--shots 0-62] [--out video]

Resumable: a shot whose frames are already rendered is skipped. Writes training/runs/<slug>/video/{frames/, shots.json,
recreation.mp4, scores.json}. The recreation is derived from copyrighted work: it stays local (CLAUDE.md rule 3).
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import recreate_level3 as L3  # noqa: E402
from recreate_audio import master_to_reference  # noqa: E402


def expand(spec, n):
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


MEASURED_HAIR_LOCKS = 10        # lock count for hair masses in whole-video runs (tune_hair_masses.py chose 8-16 on FF 27/50/32)


LANDMARK_MIN_SCORE = 0.9          # anime-face-detector box score; below it a keyframe is not a measurement (FF 59: 0.55 on a
                                 # title card; score < 0.9 shots gained nothing from the measured look on the whole trailer)


def apply_character_look(spec, look):
    """look "proxy": rung 3/4 ellipsoids (the default). look "measured": every part drawn from measurements where the script
    has them -- face on the landmarks (face_from_landmarks), hair as the measured outline in the measured hair tones
    (hair_masses), body unlit in its measured colour (flat_proxy). Landmark keyframes scoring below LANDMARK_MIN_SCORE are
    dropped; with none left the shot keeps the lit proxy, since the flat body only belongs with a measured face."""
    if look != "measured" or not spec["character"]:
        return spec
    keys = [k for k in spec.get("landmark_keys") or [] if isinstance(k.get("score"), (int, float)) and k["score"] >= LANDMARK_MIN_SCORE]
    if not keys:
        return {**spec, "landmark_keys": None, "landmarks": None}
    landmarks = min(keys, key=lambda k: abs(k["frame"] - spec["frames"] // 2))["points"]
    has_hair = any(isinstance((k.get("hair_tones") or {}).get("dark_share"), (int, float)) for k in keys)
    return {**spec, "landmark_keys": keys, "landmarks": landmarks, "face_from_landmarks": True,
            "hair_masses": bool(spec.get("outline") and has_hair), "flat_proxy": True}


def run(slug, rounds=6, shots_spec="", out_name="video", look="proxy"):
    D = L3.find_reference(slug)
    meta = json.loads((D / "meta.json").read_text(encoding="utf-8"))
    rect = meta["content_rect_640"]
    W, H = rect[2] - rect[0], rect[3] - rect[1]
    shots = json.loads((D / "shots.json").read_text(encoding="utf-8"))["shots"]
    out = HERE / "runs" / D.name / out_name
    frames_dir = out / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    log_path = out / "shots.json"
    done = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    for i in expand(shots_spec, len(shots)):
        sh = shots[i]
        if str(i) in done and all((frames_dir / f"f_{f + 1:05d}.png").exists() for f in range(sh["start"], sh["end"])):
            continue
        t0 = time.time()
        script = json.loads((D / "shots" / f"shot_{i:02d}.json").read_text(encoding="utf-8"))
        spec = apply_character_look(L3.build_scene_spec(script), look)
        work = out / "work" / f"shot_{i:02d}"
        tlog = []
        params = L3.tune(spec, {**L3.initial_params(script), "hair_locks": MEASURED_HAIR_LOCKS}, rounds, work, tlog)
        paths = L3.render(spec, [params], list(range(spec["frames"])), W, H, work / "final")
        for f in range(spec["frames"]):
            shutil.move(str(paths[(0, f)]), frames_dir / f"f_{sh['start'] + f + 1:05d}.png")
        shutil.rmtree(work, ignore_errors=True)
        done[str(i)] = {"frames": [sh["start"], sh["end"]], "character_proxy": spec["character"] is not None, "look": look,
                        "measured_parts": [k for k in ("face_from_landmarks", "hair_masses", "flat_proxy") if spec.get(k)],
                        "feature_error": tlog[-1]["error"], "seconds": round(time.time() - t0, 1), "params": params}
        log_path.write_text(json.dumps(done, indent=1), encoding="utf-8")
        print(f"shot {i} ({spec['frames']}f) character={spec['character'] is not None} feature_error {tlog[0]['error']:.2f} -> {tlog[-1]['error']:.2f} "
              f"({time.time() - t0:.0f}s)", flush=True)

    n = meta["nb_frames"]
    missing = [f for f in range(n) if not (frames_dir / f"f_{f + 1:05d}.png").exists()]
    if missing:
        print(f"{len(missing)} frames not rendered yet -- not encoding")
        return
    audio = HERE / "runs" / D.name / "audio" / "mix.wav"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", meta["fps_rational"], "-i", str(frames_dir / "f_%05d.png")]
    if audio.exists():
        mastered = out / "mix_mastered.wav"
        lv = master_to_reference(audio, ROOT / "reference vedios" / meta["source"], mastered)
        print(f"audio mastered to the reference: {lv['before_lufs']} -> {lv['after_lufs']} LUFS (target {lv['target_lufs']}, "
              f"gain {lv['gain_db']} dB, {lv['channels']} ch)", flush=True)
        cmd += ["-i", str(mastered), "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(out / "recreation.mp4")]
    subprocess.run(cmd, check=True)
    subprocess.run([sys.executable, str(HERE / "score_recreation.py"), D.name, str(frames_dir), "--start", "0", "--run", out_name], check=True)
    print(f"-> {out / 'recreation.mp4'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--shots", default="")
    ap.add_argument("--out", default="video", help="run folder name under training/runs/<slug>/")
    ap.add_argument("--look", default="proxy", choices=["proxy", "measured"], help="character drawing: rung 3/4 proxies, or measured parts")
    a = ap.parse_args()
    run(a.slug, a.rounds, a.shots, a.out, a.look)


if __name__ == "__main__":
    main()
