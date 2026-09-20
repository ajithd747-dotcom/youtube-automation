"""Compare a recreated video against its reference: numbers + a side-by-side video + a contact sheet.

    python blender_agent/benchmark/compare.py <reference.mp4> <recreation.mp4> <out_dir> [--audio-only|--video-only]

Metrics (all normalised so 1.0 = identical, 0 = unrelated):
  structure : duration ratio, cut-time alignment, motion-energy curve correlation
  look      : per-second SSIM (structural), colour-histogram intersection, mean-colour distance, brightness-curve correlation
  audio     : loudness (LUFS/LRA) difference, energy-curve correlation, tempo, key, spectral band L1 (music);
              speaking rate + pitch + word overlap (speech, when transcripts are given)
The score is a weighted mean and is only meaningful for comparing successive attempts at the same reference.
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "agents" / "music" / "tools"))
sys.path.insert(0, str(ROOT / "blender_agent"))


def frames_at(path, times, size=(320, 180)):
    out = []
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    for t in times:
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(int(t * fps), max(0, int(n) - 1)))
        ok, fr = cap.read()
        out.append(cv2.resize(fr, size, interpolation=cv2.INTER_AREA) if ok else np.zeros((size[1], size[0], 3), np.uint8))
    cap.release()
    return out


def ssim(a, b):
    """Mean SSIM of two BGR images (grayscale, gaussian window)."""
    a, b = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float64), cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float64)
    C1, C2 = 6.5025, 58.5225
    mu1, mu2 = cv2.GaussianBlur(a, (11, 11), 1.5), cv2.GaussianBlur(b, (11, 11), 1.5)
    s1, s2 = cv2.GaussianBlur(a * a, (11, 11), 1.5) - mu1 ** 2, cv2.GaussianBlur(b * b, (11, 11), 1.5) - mu2 ** 2
    s12 = cv2.GaussianBlur(a * b, (11, 11), 1.5) - mu1 * mu2
    m = ((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 ** 2 + mu2 ** 2 + C1) * (s1 + s2 + C2))
    return float(m.mean())


def hist_intersection(a, b, bins=16):
    ha = cv2.calcHist([cv2.cvtColor(a, cv2.COLOR_BGR2HSV)], [0, 1, 2], None, [bins, 4, 4], [0, 180, 0, 256, 0, 256])
    hb = cv2.calcHist([cv2.cvtColor(b, cv2.COLOR_BGR2HSV)], [0, 1, 2], None, [bins, 4, 4], [0, 180, 0, 256, 0, 256])
    ha, hb = ha / (ha.sum() + 1e-9), hb / (hb.sum() + 1e-9)
    return float(np.minimum(ha, hb).sum())


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)], capture_output=True, text=True)
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    return {"duration": float(d["format"]["duration"]), "w": v["width"], "h": v["height"], "has_audio": any(s["codec_type"] == "audio" for s in d["streams"])}


def cuts(path, thr=0.28):
    r = subprocess.run(["ffmpeg", "-i", str(path), "-vf", f"select='gt(scene,{thr})',showinfo", "-an", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    import re
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def motion_curve(path, fps=4):
    w, h = 160, 90
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", str(path), "-vf", f"fps={fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    prev, out = None, []
    while True:
        buf = p.stdout.read(w * h)
        if len(buf) < w * h:
            break
        cur = np.frombuffer(buf, np.uint8).astype(np.int16)
        if prev is not None:
            out.append(float(np.abs(cur - prev).mean()))
        prev = cur
    p.wait()
    return np.array(out)


def corr(a, b):
    n = min(len(a), len(b))
    if n < 4 or np.std(a[:n]) < 1e-6 or np.std(b[:n]) < 1e-6:
        return 0.0
    return float(np.corrcoef(a[:n], b[:n])[0, 1])


def cut_alignment(ca, cb, tol=0.5):
    """Fraction of reference cuts that have a recreation cut within `tol` seconds (and vice versa), F1."""
    if not ca and not cb:
        return 1.0
    if not ca or not cb:
        return 0.0
    rec = sum(1 for t in ca if min(abs(t - u) for u in cb) <= tol) / len(ca)
    prec = sum(1 for u in cb if min(abs(t - u) for t in ca) <= tol) / len(cb)
    return 0.0 if rec + prec == 0 else 2 * rec * prec / (rec + prec)


def compare_video(ref, rec, step=0.5):
    pr, pc = probe(ref), probe(rec)
    dur = min(pr["duration"], pc["duration"])
    times = [t for t in np.arange(0.25, dur - 0.1, step)]
    fa, fb = frames_at(ref, times), frames_at(rec, times)
    ss = [max(0.0, ssim(a, b)) for a, b in zip(fa, fb)]
    hi = [hist_intersection(a, b) for a, b in zip(fa, fb)]
    lum = lambda fr: np.array([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).mean() for f in fr])
    mc = corr(motion_curve(ref), motion_curve(rec))
    cut = cut_alignment(cuts(ref), cuts(rec))
    dur_ratio = min(pr["duration"], pc["duration"]) / max(pr["duration"], pc["duration"])
    mean_col = float(1 - np.mean([np.abs(a.reshape(-1, 3).mean(0) - b.reshape(-1, 3).mean(0)).mean() / 255 for a, b in zip(fa, fb)]))
    res = {"duration_ratio": round(dur_ratio, 3), "cut_alignment_f1": round(cut, 3), "motion_corr": round(max(0.0, mc), 3),
           "ssim_mean": round(float(np.mean(ss)), 3), "hist_intersection": round(float(np.mean(hi)), 3), "mean_colour_similarity": round(mean_col, 3),
           "brightness_corr": round(max(0.0, corr(lum(fa), lum(fb))), 3), "per_time": [{"t": round(float(t), 2), "ssim": round(s, 3), "hist": round(h, 3)} for t, s, h in zip(times, ss, hi)]}
    res["video_score"] = round(0.15 * res["duration_ratio"] + 0.15 * res["cut_alignment_f1"] + 0.15 * res["motion_corr"] + 0.15 * res["ssim_mean"] +
                               0.2 * res["hist_intersection"] + 0.1 * res["mean_colour_similarity"] + 0.1 * res["brightness_corr"], 3)
    return res, (times, fa, fb)


def compare_audio(ref, rec):
    import analyze as A
    a, b = A.describe(ref), A.describe(rec)
    if a.get("silent") or b.get("silent"):
        return {"note": "one side silent", "audio_score": 0.0}
    sys.path.insert(0, str(ROOT / "agents" / "music"))
    from agent import compare as music_compare
    rep = music_compare(b, a)
    rep["audio_score"] = round(max(0.0, 1 - rep["score"] / 2.0), 3)
    rep["ref"] = {k: a[k] for k in ("lufs", "lra", "bpm", "key", "centroid_hz")}
    rep["rec"] = {k: b[k] for k in ("lufs", "lra", "bpm", "key", "centroid_hz")}
    return rep


def _norm_words(text):
    import re
    return re.findall(r"[a-z0-9']+", text.lower())


def _wer(ref, hyp):
    """Word error rate via edit distance."""
    n, m = len(ref), len(hyp)
    d = list(range(m + 1))
    for i in range(1, n + 1):
        prev, d[0] = d[0], i
        for j in range(1, m + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (ref[i - 1] != hyp[j - 1]))
            prev, d[j] = d[j], cur
    return d[m] / max(n, 1)


def compare_speech(ref, rec, ref_transcript_json, model="base.en"):
    """Speech comparison: transcribe the recreation, WER vs the reference transcript, pace, pitch, loudness, speech-timeline correlation."""
    sys.path.insert(0, str(ROOT / "agents" / "voice" / "tools"))
    import measure as MEA
    import analyze as A
    segs = json.loads(Path(ref_transcript_json).read_text(encoding="utf-8"))
    ref_words = _norm_words(" ".join(s["text"] for s in segs))
    from faster_whisper import WhisperModel
    wav = Path(rec).with_suffix(".speech.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(rec), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    hyp_segs, _ = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=2).transcribe(str(wav), vad_filter=True, beam_size=1, language="en")
    hyp = [(s.start, s.end, s.text) for s in hyp_segs]
    hyp_words = _norm_words(" ".join(t for _, _, t in hyp))
    wer = _wer(ref_words, hyp_words)
    rw = A.load_audio(ref, 8000)
    cw = A.load_audio(rec, 8000)
    step = 4000
    env = lambda y: np.array([np.sqrt(np.mean(y[i:i + step] ** 2)) for i in range(0, len(y) - step, step)])
    tl_corr = corr(env(rw), env(cw))
    ms_ref = MEA.stats(REF_WAV if 'REF_WAV' in globals() else ref, n_words=len(ref_words))
    ms_rec = MEA.stats(wav, n_words=len(hyp_words))
    la, lb = A.loudness(ref), A.loudness(rec)
    out = {"wer": round(wer, 3), "word_accuracy": round(max(0.0, 1 - wer), 3), "speech_timeline_corr": round(max(0.0, tl_corr), 3),
           "ref": {"wpm_speaking": ms_ref.get("wpm_speaking"), "f0_median": ms_ref.get("f0_median"), "lufs": la["lufs"], "lra": la["lra"]},
           "rec": {"wpm_speaking": ms_rec.get("wpm_speaking"), "f0_median": ms_rec.get("f0_median"), "lufs": lb["lufs"], "lra": lb["lra"]}}
    pitch_sim = 1 - min(1.0, abs((ms_rec["f0_median"] or 0) - (ms_ref["f0_median"] or 1)) / (ms_ref["f0_median"] or 1))
    lufs_sim = 1 - min(1.0, abs((lb["lufs"] or 0) - (la["lufs"] or 0)) / 6)
    out["audio_score"] = round(0.4 * out["word_accuracy"] + 0.2 * out["speech_timeline_corr"] + 0.2 * pitch_sim + 0.2 * lufs_sim, 3)
    return out


def side_by_side(ref, rec, out, w=640):
    h = 360
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ref), "-i", str(rec), "-filter_complex",
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1[a];[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1[b];[a][b]hstack[v]",
                    "-map", "[v]", "-map", "1:a?", "-shortest", "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)], check=True)


def contact_sheet(times, fa, fb, out, per=8):
    from PIL import Image, ImageDraw
    sel = list(range(0, len(times), max(1, len(times) // per)))[:per]
    w, h = fa[0].shape[1], fa[0].shape[0]
    sheet = Image.new("RGB", (w * 2, h * len(sel)))
    for r, i in enumerate(sel):
        for c, fr in enumerate((fa[i], fb[i])):
            im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
            ImageDraw.Draw(im).text((4, 4), f"{'ref' if c == 0 else 'ours'} {times[i]:.1f}s", fill=(255, 255, 0))
            sheet.paste(im, (c * w, r * h))
    sheet.save(out, quality=88)


def main():
    ref, rec, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    rep = {}
    if "--audio-only" not in sys.argv:
        v, (t, fa, fb) = compare_video(ref, rec)
        rep["video"] = v
        contact_sheet(t, fa, fb, out / "compare_sheet.jpg")
        side_by_side(ref, rec, out / "side_by_side.mp4")
    if "--video-only" not in sys.argv:
        if "--speech" in sys.argv:
            rep["audio"] = compare_speech(ref, rec, sys.argv[sys.argv.index("--speech") + 1])
        else:
            rep["audio"] = compare_audio(ref, rec)
    scores = [rep[k][f"{k}_score"] for k in ("video", "audio") if k in rep and f"{k}_score" in rep[k]]
    rep["overall"] = round(float(np.mean(scores)), 3) if scores else 0.0
    (out / "report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk != "per_time"} if isinstance(v, dict) else v) for k, v in rep.items()}, indent=1))


if __name__ == "__main__":
    main()
