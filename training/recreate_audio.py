"""Audio half of the recreation: character voice-over + background music, rebuilt from measurements and scored.

    .venv/bin/python training/recreate_audio.py <slug> [--music-rounds 3]

1. separate   the reference audio into vocals / everything-else with Demucs (htdemucs, two stems), cached in reference/<slug>/stems/
2. measure    every Whisper speech segment on the vocals stem: median F0 (pyin), loudness (RMS dB), duration
3. voice      synthesise each segment's text with Kokoro Japanese voices (male voice if the measured F0 < 165 Hz, else the female
              voice whose own F0 is closest), then time-stretch to the segment's length, pitch-shift to its F0, scale to its level
4. music      plan tempo / key / energy contour / hits from the no-vocals stem (agents/music plan_from_reference) and render
              with FluidSynth, refined toward the stem's spectrum and loudness (refine_to_reference)
5. score      voice: Whisper (small, ja) on the recreated vocals vs the reference transcript -> character accuracy; speech-envelope
              correlation; per-segment F0 error.  music: agents/music compare() distance.  mix: loudness-curve correlation, LUFS gap.

Writes training/runs/<slug>/audio/{voice.wav, music.wav, mix.wav, report.json}. Everything derived from the reference stays local.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "agents" / "music"))
sys.path.insert(0, str(ROOT / "agents" / "music" / "tools"))

SR = 44100
MALE_BELOW_HZ = 165.0
JA_VOICES = ["jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo"]
VOICE_CACHE = HERE / "runs" / "kokoro_ja_voice_f0.json"


def find_reference(fragment):
    hits = [p for p in (HERE / "reference").iterdir() if p.is_dir() and fragment in p.name]
    if len(hits) != 1:
        sys.exit(f"'{fragment}' matches {[h.name for h in hits]}")
    return hits[0]


def load_mono(path, sr=SR):
    import librosa
    y, _ = librosa.load(str(path), sr=sr, mono=True)
    return y.astype(np.float32)


def separate(D):
    out = D / "stems"
    voc, rest = out / "vocals.wav", out / "no_vocals.wav"
    if voc.exists() and rest.exists():
        return voc, rest
    tmp = out / "_demucs"
    subprocess.run([sys.executable, "-m", "demucs", "--two-stems", "vocals", "-n", "htdemucs", "-d", "cpu", "-o", str(tmp), str(D / "audio.wav")],
                   check=True, capture_output=True, text=True)
    got = next(tmp.rglob("vocals.wav")).parent
    (got / "vocals.wav").rename(voc)
    (got / "no_vocals.wav").rename(rest)
    return voc, rest


def median_f0(y, sr):
    import librosa
    if len(y) < sr * 0.2:
        return None
    f0, voiced, _ = librosa.pyin(y, fmin=70, fmax=500, sr=sr, frame_length=2048)
    f0 = f0[voiced & np.isfinite(f0)]
    return float(np.median(f0)) if len(f0) > 5 else None


def rms_db(y):
    return float(20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-9))


_PIPE = {}


def kokoro_ja(text, voice):
    from kokoro import KPipeline
    if "j" not in _PIPE:
        _PIPE["j"] = KPipeline(lang_code="j", repo_id="hexgrad/Kokoro-82M")
    parts = [np.asarray(r.audio) for r in _PIPE["j"](text, voice=voice)]
    return np.concatenate(parts).astype(np.float32) if parts else np.zeros(2400, np.float32)


def voice_f0_table():
    """Each Kokoro Japanese voice's own median F0, measured once on a fixed sentence."""
    if VOICE_CACHE.exists():
        return json.loads(VOICE_CACHE.read_text(encoding="utf-8"))
    import librosa
    tab = {}
    for v in JA_VOICES:
        y = librosa.resample(kokoro_ja("今日はいい天気ですね。一緒に帰りましょう。", v), orig_sr=24000, target_sr=SR)
        tab[v] = median_f0(y, SR)
    VOICE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    VOICE_CACHE.write_text(json.dumps(tab, indent=1), encoding="utf-8")
    return tab


def choose_voice(f0, table):
    if f0 is None:
        return "jf_alpha"
    if f0 < MALE_BELOW_HZ:
        return "jm_kumo"
    fem = {v: t for v, t in table.items() if v.startswith("jf") and t}
    return min(fem, key=lambda v: abs(np.log2(fem[v] / f0)))


def build_voice_track(segments, vocals, n, table):
    import librosa
    track = np.zeros(n, np.float32)
    rows = []
    for s in segments:
        a, b = int(s["start"] * SR), min(int(s["end"] * SR), n)
        if b - a < SR * 0.2 or not s["text"].strip():
            continue
        ref = vocals[a:b]
        f0_ref, lvl = median_f0(ref, SR), rms_db(ref)
        voice = choose_voice(f0_ref, table)
        y = librosa.resample(kokoro_ja(s["text"], voice), orig_sr=24000, target_sr=SR)
        y, _ = librosa.effects.trim(y, top_db=35)
        rate = float(np.clip(len(y) / (b - a), 0.6, 1.8))                  # >1 speeds up
        y = librosa.effects.time_stretch(y, rate=rate)
        semis = 0.0
        if f0_ref and table.get(voice):
            semis = float(np.clip(12 * np.log2(f0_ref / table[voice]), -5, 5))
            y = librosa.effects.pitch_shift(y, sr=SR, n_steps=semis)
        y = y * 10 ** ((lvl - rms_db(y)) / 20)
        m = min(len(y), n - a)
        track[a:a + m] += y[:m]
        f0_got = median_f0(y[:m], SR)
        rows.append({"start": s["start"], "end": s["end"], "text": s["text"], "voice": voice, "f0_ref_hz": f0_ref and round(f0_ref, 1),
                     "f0_rec_hz": f0_got and round(f0_got, 1), "stretch_rate": round(rate, 3), "pitch_shift_semitones": round(semis, 2),
                     "level_db": round(lvl, 1)})
    return track, rows


def envelope(y, hop_s=0.25):
    h = int(SR * hop_s)
    k = len(y) // h
    return 20 * np.log10(np.sqrt((y[:k * h].reshape(k, h) ** 2).mean(axis=1)) + 1e-6)


def corr(a, b):
    n = min(len(a), len(b))
    return float(np.corrcoef(a[:n], b[:n])[0, 1]) if n > 4 and np.std(a[:n]) > 0 and np.std(b[:n]) > 0 else 0.0


def char_accuracy(ref_text, hyp_text):
    import unicodedata
    norm = lambda t: [c for c in unicodedata.normalize("NFKC", t) if c.isalnum()]
    r, h = norm(ref_text), norm(hyp_text)
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return max(0.0, 1 - d[len(h)] / max(len(r), 1))


def whisper_text(wav):
    from faster_whisper import WhisperModel
    segs, _ = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=12).transcribe(str(wav), vad_filter=True, beam_size=1, language="ja")
    return " ".join(s.text.strip() for s in segs)


def lufs(path):
    import re
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"I:\s+(-?[0-9.]+) LUFS", r.stderr[r.stderr.rfind("Summary"):])
    return float(m.group(1)) if m else None


def run(slug, music_rounds=3):
    import analyze as A
    from agent import MusicAgent, compare
    D = find_reference(slug)
    out = HERE / "runs" / D.name / "audio"
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    voc_p, rest_p = separate(D)
    print(f"stems ready ({time.time() - t0:.0f}s)", flush=True)
    vocals, full = load_mono(voc_p), load_mono(D / "audio.wav")
    n = len(full)
    segments = json.loads((ROOT / "blender_agent" / "skills" / "sources" / D.name / "transcript.json").read_text(encoding="utf-8"))
    table = voice_f0_table()
    voice, rows = build_voice_track(segments, vocals, n, table)
    sf.write(out / "voice.wav", voice, SR)
    print(f"voice: {len(rows)} lines ({time.time() - t0:.0f}s)", flush=True)

    agent = MusicAgent(ROOT / "agents" / "music")
    plan, ref_an = agent.plan_from_reference(str(rest_p), duration=n / SR)
    plan_best, music_rep = agent.refine_to_reference(plan, ref_an, str(out / "music.wav"), rounds=music_rounds)
    for k, v in plan_best.items():
        setattr(plan, k, v)
    agent.render(plan, str(out / "music.wav"), reference=ref_an, workdir=out / "music_work")
    music = load_mono(out / "music.wav")
    music = np.pad(music, (0, max(0, n - len(music))))[:n]
    print(f"music: {plan.bpm} bpm {plan.root} {plan.scale} ({time.time() - t0:.0f}s)", flush=True)

    mix = voice + music
    peak = float(np.abs(mix).max())
    if peak > 0.99:
        mix = mix * (0.99 / peak)
    sf.write(out / "mix.wav", mix, SR)

    ref_text = " ".join(s["text"] for s in segments)
    hyp_text = whisper_text(out / "voice.wav")
    f0_err = [abs(np.log2(r["f0_rec_hz"] / r["f0_ref_hz"])) * 12 for r in rows if r["f0_ref_hz"] and r["f0_rec_hz"]]
    music_final = compare(A.describe(str(out / "music.wav")), ref_an)
    report = {
        "slug": D.name, "seconds_wall": round(time.time() - t0, 1),
        "voice": {"lines": len(rows), "char_accuracy_whisper_small_ja": round(char_accuracy(ref_text, hyp_text), 3),
                  "speech_envelope_corr": round(corr(envelope(voice), envelope(vocals)), 3),
                  "f0_error_semitones_median": round(float(np.median(f0_err)), 2) if f0_err else "NOT MEASURED",
                  "lufs_rec": lufs(out / "voice.wav"), "lufs_ref_vocals": lufs(voc_p), "hyp_text": hyp_text, "lines_detail": rows},
        "music": {"plan": {"bpm": plan.bpm, "root_midi": plan.root, "scale": plan.scale, "style": plan.style},
                  "distance_to_reference_stem": music_final, "refine_best": music_rep},
        "mix": {"loudness_curve_corr": round(corr(envelope(mix), envelope(full)), 3), "lufs_rec": lufs(out / "mix.wav"), "lufs_ref": lufs(D / "audio.wav")},
    }
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    v, m, x = report["voice"], report["music"]["distance_to_reference_stem"], report["mix"]
    print(f"voice: char_accuracy {v['char_accuracy_whisper_small_ja']}  envelope_corr {v['speech_envelope_corr']}  f0_err {v['f0_error_semitones_median']} st")
    print(f"music: distance {m['score']} (bands {m['bands_l1']}, energy_corr {m['energy_corr']}, bpm_rel {m['bpm_rel']}, key_match {m['key_match']})")
    print(f"mix:   loudness_curve_corr {x['loudness_curve_corr']}  LUFS {x['lufs_rec']} vs {x['lufs_ref']}   ({report['seconds_wall']}s)")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--music-rounds", type=int, default=3)
    a = ap.parse_args()
    run(a.slug, a.music_rounds)


if __name__ == "__main__":
    main()
