"""Audio analysis with numpy/scipy + ffmpeg only (no heavy dependencies): tempo, beats, key, brightness, energy curve, hits.

    python agents/music/tools/analyze.py <audio-or-video-file> [--json]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import signal

SR = 22050
NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Krumhansl-Schmuckler key profiles
MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def load_audio(path, sr=SR, stereo=False):
    ch = 2 if stereo else 1
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-vn", "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True)
    y = np.frombuffer(p.stdout, np.float32)
    return y.reshape(-1, 2).T if stereo else y


def loudness(path):
    r = subprocess.run(["ffmpeg", "-i", str(path), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="ignore")
    tail = r.stderr[r.stderr.rfind("Summary"):] if "Summary" in r.stderr else ""
    import re
    g = lambda pat: (lambda m: float(m.group(1)) if m else None)(re.search(pat, tail))
    return {"lufs": g(r"I:\s+(-?[0-9.]+) LUFS"), "lra": g(r"LRA:\s+(-?[0-9.]+) LU"), "true_peak_db": g(r"Peak:\s+(-?[0-9.]+) dBFS")}


def onset_envelope(y, sr=SR, hop=512):
    f, t, Z = signal.stft(y, sr, nperseg=1024, noverlap=1024 - hop)
    S = np.log1p(10 * np.abs(Z))
    flux = np.maximum(np.diff(S, axis=1), 0).sum(axis=0)
    flux = np.concatenate([[0], flux])
    return flux / (flux.max() + 1e-9), t


def tempo(y, sr=SR, lo=60, hi=180):
    """BPM by autocorrelation of the onset envelope (weighted towards 90-140 BPM). Returns (bpm, confidence, beat_times)."""
    env, t = onset_envelope(y, sr)
    if len(env) < 50:
        return None, 0.0, []
    dt = t[1] - t[0]
    env = env - env.mean()
    ac = np.correlate(env, env, "full")[len(env) - 1:]
    ac /= ac[0] + 1e-9
    lags = np.arange(len(ac)) * dt
    best, best_s = None, 0
    for bpm in np.arange(lo, hi + 0.5, 0.5):
        lag = 60.0 / bpm
        i = int(round(lag / dt))
        if i + 1 >= len(ac):
            continue
        s = ac[i] + 0.5 * (ac[min(2 * i, len(ac) - 1)])
        s *= 1.0 - 0.25 * abs(np.log2(bpm / 110.0))  # prior: most music sits near 110
        if s > best_s:
            best, best_s = bpm, s
    if best is None:
        return None, 0.0, []
    period = 60.0 / best
    # beat phase: the offset with the highest summed onset strength
    offs = np.arange(0, period, dt)
    phase = max(offs, key=lambda o: sum(env[int((o + k * period) / dt)] for k in range(int(len(env) * dt / period)) if int((o + k * period) / dt) < len(env)))
    beats = list(np.arange(phase, len(env) * dt, period))
    return float(best), float(best_s), [round(b, 3) for b in beats]


def key_estimate(y, sr=SR):
    f, t, Z = signal.stft(y, sr, nperseg=4096, noverlap=3072)
    mag = np.abs(Z) ** 2
    chroma = np.zeros(12)
    for i, fr in enumerate(f):
        if 55 < fr < 2000:
            chroma[int(round(12 * np.log2(fr / 440.0) + 69)) % 12] += mag[i].sum()
    chroma /= chroma.sum() + 1e-12
    best = (None, -2)
    for k in range(12):
        for mode, prof in (("major", MAJ), ("minor", MIN)):
            c = np.corrcoef(chroma, np.roll(prof, k))[0, 1]
            if c > best[1]:
                best = ((NOTE[k], mode), c)
    return best[0], float(best[1]), chroma.round(3).tolist()


def energy_curve(y, sr=SR, step=0.25):
    n = int(step * sr)
    rms = np.array([np.sqrt(np.mean(y[i:i + n] ** 2) + 1e-12) for i in range(0, len(y) - n, n)])
    return (20 * np.log10(rms + 1e-9)).round(1).tolist()


def hits(y, sr=SR, k=6):
    """Strongest transients (impacts, drops) as (time, strength)."""
    env, t = onset_envelope(y, sr)
    pk, _ = signal.find_peaks(env, height=0.35, distance=int(0.35 / (t[1] - t[0])))
    top = sorted(pk, key=lambda i: -env[i])[:k]
    return sorted((round(float(t[i]), 2), round(float(env[i]), 2)) for i in top)


def spectral(y, sr=SR):
    f, t, Z = signal.stft(y, sr, nperseg=2048, noverlap=1536)
    mag = np.abs(Z)
    cen = (f[:, None] * mag).sum(0) / (mag.sum(0) + 1e-9)
    bands = {"sub(<100)": (20, 100), "low(100-300)": (100, 300), "mid(300-2k)": (300, 2000), "high(2k-6k)": (2000, 6000), "air(>6k)": (6000, sr / 2)}
    tot = (mag ** 2).sum() + 1e-12
    share = {n: round(float(((mag[(f >= a) & (f < b)]) ** 2).sum() / tot), 3) for n, (a, b) in bands.items()}
    return {"centroid_hz": round(float(np.mean(cen)), 0), "band_share": share}


def describe(path):
    path = Path(path)
    y = load_audio(path)
    if y.size < SR:
        return {"file": path.name, "duration": round(len(y) / SR, 2), "silent": True}
    bpm, conf, beats = tempo(y)
    (kn, mode), kc, chroma = key_estimate(y)
    ys = load_audio(path, stereo=True)
    width = float(np.mean(np.abs(ys[0] - ys[1])) / (np.mean(np.abs(ys[0] + ys[1])) + 1e-9)) if ys.ndim == 2 and ys.shape[1] else 0
    return {"file": path.name, "duration": round(len(y) / SR, 2), **loudness(path), "bpm": bpm, "tempo_confidence": round(conf, 2),
            "beats": beats[:64], "key": f"{kn} {mode}", "key_confidence": round(kc, 2), "chroma": chroma, **spectral(y),
            "energy_db_per_0.25s": energy_curve(y), "hits": hits(y), "stereo_width": round(width, 2),
            "dynamic_range_db": round(float(np.percentile(energy_curve(y), 95) - np.percentile(energy_curve(y), 10)), 1)}


if __name__ == "__main__":
    for s in (sys.stdout,):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    d = describe(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(d))
    else:
        for k, v in d.items():
            if k not in ("beats", "chroma", "energy_db_per_0.25s"):
                print(f"{k}: {v}")
        print("energy curve (dB / 0.25s):", d.get("energy_db_per_0.25s", [])[:60])
