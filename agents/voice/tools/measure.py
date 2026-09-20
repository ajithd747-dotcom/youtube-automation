"""Measure speech: words/min, median pitch (Hz), pause ratio, loudness. Used to match a reference voice and to QA output."""
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 16000


def load(path, sr=SR):
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(p.stdout, np.float32)


def pitch_track(y, sr=SR, fmin=70, fmax=330, frame=0.04, hop=0.02):
    """Autocorrelation pitch tracker on voiced frames; returns array of f0 in Hz (voiced only)."""
    n, h = int(frame * sr), int(hop * sr)
    lo, hi = int(sr / fmax), int(sr / fmin)
    f0 = []
    for i in range(0, len(y) - n, h):
        x = y[i:i + n]
        if np.sqrt(np.mean(x ** 2)) < 0.01:
            continue
        x = x - x.mean()
        ac = np.correlate(x, x, "full")[n - 1:]
        if ac[0] <= 0:
            continue
        seg = ac[lo:hi]
        k = int(np.argmax(seg))
        if seg[k] / ac[0] > 0.45:
            f0.append(sr / (lo + k))
    return np.array(f0)


def stats(path, n_words=None, words=None):
    y = load(path)
    dur = len(y) / SR
    f0 = pitch_track(y)
    frame = int(0.05 * SR)
    rms = np.array([np.sqrt(np.mean(y[i:i + frame] ** 2)) for i in range(0, len(y) - frame, frame)])
    active = float((rms > 0.02).mean()) if len(rms) else 0
    if words:
        n_words = len(words)
        dur_speech = max(words[-1]["end"] - words[0]["start"], 0.1)
    else:
        dur_speech = dur * active
    out = {"duration": round(dur, 2), "active_ratio": round(active, 2), "f0_median": round(float(np.median(f0)), 1) if len(f0) else None,
           "f0_p10": round(float(np.percentile(f0, 10)), 1) if len(f0) else None, "f0_p90": round(float(np.percentile(f0, 90)), 1) if len(f0) else None}
    if n_words:
        out["words"] = n_words
        out["wpm_speaking"] = round(n_words / (dur_speech / 60), 0)
        out["wpm_overall"] = round(n_words / (dur / 60), 0)
    try:
        r = subprocess.run(["ffmpeg", "-i", str(path), "-vn", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="ignore")
        import re
        m = re.search(r"I:\s+(-?[0-9.]+) LUFS", r.stderr[r.stderr.rfind("Summary"):])
        out["lufs"] = float(m.group(1)) if m else None
    except Exception:
        pass
    return out


if __name__ == "__main__":
    print(stats(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None))
