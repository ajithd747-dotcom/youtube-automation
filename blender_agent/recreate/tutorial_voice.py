"""Voice-over for the tutorial recreation: same script (from the reference transcript), a stock TTS voice matched to the reference
narrator's pitch/pace by the Voice agent, every sentence placed at its original start time so the timeline is identical.

    python blender_agent/recreate/tutorial_voice.py [--engine kokoro|edge] [--limit-seconds N]

Outputs work/recreate_tutorial/narration.wav (mono 24 kHz, -14.7 LUFS), narration_words.json (global word times), voice_choice.json.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BA = HERE.parent
ROOT = BA.parent
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "agents" / "voice" / "tools"))
from core import load_agent  # noqa: E402
import measure as MEA  # noqa: E402

REF_VIDEO = ROOT / "reference vedios" / "vedios" / "blender reference vedios" / "vidssave.com Blender 2D Animation Basics for Beginners - Grease Pencil Effects and Compositing 720P.mp4"
PACK = BA / "skills" / "sources" / "blender-2d-animation-basics-for-beginners-grease-pencil-effe"
WORK = BA / "work" / "recreate_tutorial"
SR = 24000
REF_LUFS = json.loads((PACK / "metrics.json").read_text(encoding="utf-8")).get("loudness_lufs") or -14.7  # stereo programme loudness of the reference

FIXES = [(r"\bgreaspencil\b", "Grease Pencil"), (r"\bgrease pencil\b", "Grease Pencil"), (r"\bEevee\b", "EEVEE"), (r"\bEV4F\b", "EEVEE"),
         (r"\bhell around\b", "halo around"), (r"\bgreen\b(?= )", "grain"), (r"\bvoltage D\b", "1080p"), (r"\bthough for cinematic\b", "depth of field for cinematic"),
         (r"\bthrough\b(?= for cinematic)", "depth of field"), (r"\bchromatic considerations\b", "chromatic aberration"),
         (r"\bthink to your liking\b", "tweak to your liking"), (r"\bDavinci Resolve\b", "DaVinci Resolve")]


def sentences():
    """Reference transcript -> [{start,end,text}] one per sentence (timing interpolated by character position inside its segment)."""
    segs = json.loads((PACK / "transcript.json").read_text(encoding="utf-8"))
    out = []
    for s in segs:
        text = s["text"].strip()
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
        total = sum(len(p) for p in parts) or 1
        t = s["start"]
        for p in parts:
            d = (s["end"] - s["start"]) * len(p) / total
            out.append({"start": round(t, 2), "end": round(t + d, 2), "text": p})
            t += d
    for o in out:
        for a, b in FIXES:
            o["text"] = re.sub(a, b, o["text"], flags=re.I if a[:2] != r"\b" or a.lower() == a else 0)
    return out


def main():
    engine = sys.argv[sys.argv.index("--engine") + 1] if "--engine" in sys.argv else "kokoro"
    limit = float(sys.argv[sys.argv.index("--limit-seconds") + 1]) if "--limit-seconds" in sys.argv else None
    WORK.mkdir(parents=True, exist_ok=True)
    sents = sentences()
    if limit:
        sents = [s for s in sents if s["start"] < limit]
    (WORK / "script.json").write_text(json.dumps(sents, indent=1), encoding="utf-8")
    voice = load_agent("voice")

    # --- match the reference narrator (pitch + pace), never clone
    ref_wav = WORK / "ref_narration.wav"
    if not ref_wav.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(REF_VIDEO), "-vn", "-ac", "1", "-ar", "16000", str(ref_wav)], check=True)
    n_words = sum(len(s["text"].split()) for s in sents)
    ref = MEA.stats(ref_wav, n_words=n_words)
    print("reference narrator:", ref, flush=True)
    cal = voice.calibrate_voices()
    best = min(cal.items(), key=lambda kv: abs((kv[1]["f0_median"] or 0) - (ref["f0_median"] or 0)))
    v, m = best
    speed = max(0.75, min(1.3, ref["wpm_speaking"] / m["wpm_speaking"]))
    import math
    semis = max(-4.0, min(4.0, 12 * math.log2(ref["f0_median"] / m["f0_median"]))) if ref["f0_median"] and m["f0_median"] else 0.0
    choice = {"engine": engine, "voice": v, "speed": round(speed, 3), "pitch_semitones": round(semis, 2), "reference": ref, "voice_stats": m}
    (WORK / "voice_choice.json").write_text(json.dumps(choice, indent=1), encoding="utf-8")
    print("voice choice:", {k: choice[k] for k in ("voice", "speed", "pitch_semitones")}, flush=True)

    # --- synthesize sentence by sentence, place at the original start times
    total = max(s["end"] for s in sents) + 2
    track = np.zeros(int(total * SR), np.float32)
    words_out, t0 = [], time.time()
    for i, s in enumerate(sents):
        f = WORK / f"s{i:03d}.wav"
        if not f.exists():
            r = voice.speak(s["text"], f, engine, v, speed, semis)
            json.dump(r["words"], open(f.with_suffix(".json"), "w"))
        r_words = json.load(open(f.with_suffix(".json")))
        y = MEA.load(f, SR)
        slot = (sents[i + 1]["start"] if i + 1 < len(sents) else s["end"] + 2) - s["start"]
        if len(y) / SR > slot * 1.02:                     # too long for its slot: tempo up to fit (max 1.3x), keeps timeline aligned
            k = min(1.3, len(y) / SR / slot)
            g = WORK / f"s{i:03d}_fit.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(f), "-af", f"atempo={k:.4f}", "-ar", str(SR), str(g)], check=True)
            y = MEA.load(g, SR)
            r_words = [dict(w, start=w["start"] / k, end=w["end"] / k) for w in r_words]
        a = int(s["start"] * SR)
        track[a:a + len(y)] += y[: len(track) - a]
        words_out += [{"text": w["text"], "start": round(w["start"] + s["start"], 3), "end": round(w["end"] + s["start"], 3)} for w in r_words]
        if i % 20 == 0:
            print(f"  {i + 1}/{len(sents)} sentences ({time.time() - t0:.0f}s)", flush=True)
    raw = WORK / "narration_raw.wav"
    import soundfile as sf
    sf.write(str(raw), track, SR)
    out = WORK / "narration.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af", f"loudnorm=I={REF_LUFS}:TP=-1.0:LRA=9", "-ar", str(SR), str(out)], check=True)
    (WORK / "narration_words.json").write_text(json.dumps(words_out), encoding="utf-8")
    print("narration:", out, "words:", len(words_out), "measured:", MEA.stats(out, words=words_out), flush=True)


if __name__ == "__main__":
    main()
