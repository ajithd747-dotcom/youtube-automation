"""Mixing helpers: write wav, duck music under narration, loudness-normalise with ffmpeg."""
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SR = 44100


def write_wav(path, stereo, sr=SR):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(path), sr, (np.clip(stereo.T, -1, 1) * 32767).astype(np.int16))
    return path


def loudnorm(src, dst, lufs=-14.0, tp=-1.0, lra=11):
    """Two-pass EBU R128 normalisation to `lufs`."""
    import json
    import re
    a = subprocess.run(["ffmpeg", "-i", str(src), "-af", f"loudnorm=I={lufs}:TP={tp}:LRA={lra}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", a.stderr, flags=re.S)
    if not m:
        raise RuntimeError("loudnorm analysis failed")
    d = json.loads(m.group(0))
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA={lra}:measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}"
          f":measured_thresh={d['input_thresh']}:offset={d['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", af, "-ar", str(SR), str(dst)], check=True)
    return dst


def duck(music_wav, voice_audio, out_wav, amount_db=-13, threshold=0.02, attack=0.05, release=0.35):
    """Sidechain-duck the music under the narration (ffmpeg sidechaincompress); voice is mixed on top at unity."""
    fc = (f"[1:a]asplit=2[sc][vo];[0:a][sc]sidechaincompress=threshold={threshold}:ratio=8:attack={attack * 1000:.0f}:release={release * 1000:.0f}"
          f":makeup=1[duck];[duck][vo]amix=inputs=2:normalize=0[out]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(music_wav), "-i", str(voice_audio), "-filter_complex", fc,
                    "-map", "[out]", str(out_wav)], check=True)
    return out_wav


BANDS = {"sub(<100)": (20, 100), "low(100-300)": (100, 300), "mid(300-2k)": (300, 2000), "high(2k-6k)": (2000, 6000), "air(>6k)": (6000, 22050)}


def band_shares(stereo, sr=SR):
    y = stereo.mean(axis=0)
    spec = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / sr)
    tot = spec.sum() + 1e-12
    return {k: float(spec[(f >= a) & (f < b)].sum() / tot) for k, (a, b) in BANDS.items()}


def eq_match(stereo, target_shares, sr=SR, max_gain_db=14):
    """Spectral-balance matching: per-band gain so the band energy shares approach the reference's (smooth crossovers)."""
    cur = band_shares(stereo, sr)
    n = stereo.shape[1]
    f = np.fft.rfftfreq(n, 1 / sr)
    logf = np.log10(np.maximum(f, 10))
    centers = [np.log10(np.sqrt(max(a, 20) * b)) for a, b in BANDS.values()]
    gains = []
    for k in BANDS:
        g = np.sqrt((target_shares.get(k, 1e-4) + 1e-4) / (cur[k] + 1e-4))
        gains.append(np.clip(g, 10 ** (-max_gain_db / 20), 10 ** (max_gain_db / 20)))
    curve = np.interp(logf, centers, np.log(gains))
    curve = np.exp(curve)
    out = np.zeros_like(stereo)
    for c in range(stereo.shape[0]):
        out[c] = np.fft.irfft(np.fft.rfft(stereo[c]) * curve, n)
    return out


def match_dynamics(stereo, target_db_per_step, step=0.25, sr=SR, strength=0.8):
    """Follow a target loudness contour (dB per 0.25 s) - gives the track the same swells and drops as a reference."""
    n = int(step * sr)
    y = stereo.copy()
    steps = min(len(target_db_per_step), y.shape[1] // n)
    cur = np.array([20 * np.log10(np.sqrt(np.mean(y[:, i * n:(i + 1) * n] ** 2)) + 1e-9) for i in range(steps)])
    tgt = np.array(target_db_per_step[:steps], dtype=float)
    tgt = tgt - np.median(tgt) + np.median(cur)  # match shape, not absolute level
    gain_db = np.clip((tgt - cur) * strength, -12, 12)
    g = np.repeat(10 ** (gain_db / 20), n)
    g = np.concatenate([g, np.ones(y.shape[1] - len(g))])
    k = int(0.08 * sr)
    g = np.convolve(g, np.ones(k) / k, mode="same")  # smooth
    return y * g
