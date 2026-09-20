"""Layer A audio measurements, one row per video frame (the audio inside that frame's time slice).

Everything is computed from the decoded waveform. `speech_band_ratio` is an energy ratio in the speech band, NOT a speech
detector: real speech spans come from the Whisper transcript, and the per-shot script keeps the two apart.
"""
import numpy as np
import soundfile as sf
from scipy import signal

BANDS_HZ = ((20, 250), (250, 2000), (2000, 8000))
SPEECH_BAND_HZ = (300, 3400)


def r(x, n=4):
    return None if x is None else round(float(x), n)


def measure_audio_per_frame(wav_path, fps, n_frames):
    """List of n_frames dicts. Frames beyond the end of the audio get None values (NOT MEASURED)."""
    x, sr = sf.read(str(wav_path), always_2d=True)
    x = x.mean(axis=1).astype(np.float32)
    nper, hop = 2048, 512
    freqs, times, S = signal.stft(x, fs=sr, nperseg=nper, noverlap=nper - hop, boundary=None)
    mag = np.abs(S) + 1e-9
    power = mag ** 2
    logmag = np.log(mag)
    onset = np.maximum(np.diff(logmag, axis=1), 0).sum(axis=0)          # spectral flux per STFT hop
    onset = np.concatenate([[0.0], onset])
    band_idx = [(freqs >= lo) & (freqs < hi) for lo, hi in BANDS_HZ]
    speech_idx = (freqs >= SPEECH_BAND_HZ[0]) & (freqs < SPEECH_BAND_HZ[1])
    centroid = (freqs[:, None] * mag).sum(axis=0) / mag.sum(axis=0)
    flatness = np.exp(logmag.mean(axis=0)) / mag.mean(axis=0)

    peaks, _ = signal.find_peaks(onset, height=onset.mean() + onset.std(), distance=int(0.12 * sr / hop))
    beat_time = times[peaks] if len(peaks) else np.array([])

    rows = []
    for i in range(n_frames):
        t0, t1 = i / fps, (i + 1) / fps
        s0, s1 = int(t0 * sr), int(t1 * sr)
        cols = (times >= t0) & (times < t1)
        if s0 >= len(x) or not cols.any():
            rows.append({k: None for k in ("rms_db", "onset_strength", "beat_onset", "spectral_centroid_hz", "low_share", "mid_share",
                                           "high_share", "speech_band_ratio", "spectral_flatness")})
            continue
        seg = x[s0:s1]
        pw = power[:, cols].sum(axis=1)
        tot = pw.sum() + 1e-12
        rows.append({
            "rms_db": r(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9), 2),
            "onset_strength": r(onset[cols].mean(), 3),
            "beat_onset": bool(((beat_time >= t0) & (beat_time < t1)).any()),
            "spectral_centroid_hz": r(centroid[cols].mean(), 1),
            "low_share": r(pw[band_idx[0]].sum() / tot), "mid_share": r(pw[band_idx[1]].sum() / tot), "high_share": r(pw[band_idx[2]].sum() / tot),
            "speech_band_ratio": r(pw[speech_idx].sum() / tot), "spectral_flatness": r(flatness[cols].mean()),
        })
    return rows
