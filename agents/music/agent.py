"""Music agent - plans and produces background music for a video: mood/tempo/key from the script + shot plan (skills),
real instruments via FluidSynth (or the numpy synth), cinematic risers/impacts on the cuts, reference matching, ducking."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE / "tools"))
from core import Agent  # noqa: E402

import analyze as A  # noqa: E402
import compose as C  # noqa: E402
import mix as M  # noqa: E402
import midi_render as R  # noqa: E402

# recipe -> (style hint, intensity 0..1, hit at shot start?)
RECIPE_FEEL = {"robot_intro": ("uplifting", 0.40, "swell"), "workshop_walk": ("ambient", 0.35, None), "glass_showcase": ("ambient", 0.45, None),
               "domino_run": ("cinematic-action", 0.65, "swell"), "crate_smash": ("cinematic-action", 1.0, "impact"),
               "cloth_banner": ("uplifting", 0.5, None), "fireworks": ("uplifting", 0.9, "impact"), "jelly_pit": ("neon", 0.7, None),
               "finale_confetti": ("uplifting", 0.85, "impact")}
MOOD_TEMPO = {"comedy": 118, "uplifting": 108, "cinematic-action": 96, "tense": 84, "ambient": 76, "neon": 118}
MOOD_SCALE = {"comedy": "major", "uplifting": "major", "cinematic-action": "minor", "tense": "phrygian", "ambient": "dorian", "neon": "minor"}


class MusicAgent(Agent):
    """Plans + renders background music; see agents/music/skills for the rules it follows."""

    # ------------------------------------------------------------------ planning
    def plan_for_video(self, shots, durations, script_text="", style=None):
        """Music plan for a planned video: one intensity section per shot, impact/swell cues on the shots that ask for them."""
        total = float(sum(durations))
        guide = self.skills(script_text or " ".join(s.get("recipe", "") for s in shots), k=3)
        feels = [RECIPE_FEEL.get(s.get("recipe"), ("cinematic-action", 0.5, None)) for s in shots]
        style = style or max(set(f[0] for f in feels), key=[f[0] for f in feels].count)
        sections, hits, t = [], [], 0.0
        for (st, inten, hit), d, s in zip(feels, durations, shots):
            sections.append((round(t, 2), round(t + d, 2), inten))
            if hit:
                off = 1.5 if s.get("recipe") == "crate_smash" else 0.0  # the smash lands ~1.5 s into its shot
                hits.append((round(t + off, 2) if t + off > 0.3 else 0.3, hit))
            t += d
        bpm = MOOD_TEMPO.get(style, 100)
        plan = C.MusicPlan(bpm=bpm, root=57, scale=MOOD_SCALE.get(style, "minor"), duration=total, style=style, sections=sections, hits=hits)
        plan._skills = [s.id for _, s in guide]
        return plan

    def plan_from_reference(self, ref_audio, duration=None):
        """Copy tempo, key, energy contour and impact times from a reference track."""
        a = A.describe(ref_audio)
        dur = duration or a["duration"]
        e = a["energy_db_per_0.25s"]
        per = 4
        e4 = [sum(e[i:i + per]) / len(e[i:i + per]) for i in range(0, len(e) - per + 1, per)]
        lo, hi = min(e4), max(e4)
        secs = [(float(i), float(i + 1), round(0.3 + 0.7 * (v - lo) / (hi - lo + 1e-9), 2)) for i, v in enumerate(e4)]
        bpm = a["bpm"] or 100
        while bpm > 130:  # detectors lock on double time; musical tempo is the half
            bpm /= 2
        note, mode = a["key"].split()
        root = 48 + ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"].index(note)
        hits = [(t, "impact" if s >= 0.8 else "hit") for t, s in a["hits"]]
        style = "cinematic-action" if a["centroid_hz"] < 2500 else "comedy"
        plan = C.MusicPlan(bpm=round(bpm, 2), root=root, scale=mode, duration=dur, style=style, sections=secs, hits=hits)
        return plan, a

    # ------------------------------------------------------------------ rendering
    def render(self, plan, out_wav, engine="auto", reference=None, workdir=None):
        """engine: auto (FluidSynth if installed) | fluidsynth | numpy. reference: analysis dict -> EQ/dynamics/loudness matching."""
        workdir = Path(workdir or Path(out_wav).parent)
        workdir.mkdir(parents=True, exist_ok=True)
        use_fs = engine in ("auto", "fluidsynth") and R.available()
        if use_fs:
            import numpy as np
            from scipy.io import wavfile
            mid = R.build_midi(plan, workdir / "music.mid")
            wav = R.render_wav(mid, workdir / "music_fs.wav")
            sr, y = wavfile.read(str(wav))
            y = (y.T.astype("float32") / 32768.0)
            n = int(plan.duration * sr)
            y = y[:, :n] if y.shape[1] >= n else np.pad(y, ((0, 0), (0, n - y.shape[1])))
            fx = C.render(plan, only=("fx",))[:, :n]
            y = y + fx * 0.8
        else:
            y = C.render(plan)
        if reference:
            y = M.eq_match(y, reference["band_share"])
            y = M.match_dynamics(y, reference["energy_db_per_0.25s"])
        raw = M.write_wav(workdir / "music_raw.wav", y)
        target = (reference or {}).get("lufs") or -16.0
        M.loudnorm(raw, out_wav, lufs=target)
        return {"path": str(out_wav), "engine": "fluidsynth" if use_fs else "numpy", "plan": plan.to_json()}

    def refine_to_reference(self, plan, ref_analysis, out_wav, rounds=3, engine="auto"):
        """Render -> analyse -> compare -> adjust brightness/bass -> repeat. Returns the best result and its distance report."""
        best = None
        for r in range(rounds):
            self.render(plan, out_wav, engine=engine, reference=ref_analysis)
            a = A.describe(out_wav)
            rep = compare(a, ref_analysis)
            if best is None or rep["score"] < best[1]["score"]:
                best = (dict(plan.__dict__), rep)
            # adjust knobs from the largest mismatch
            if a["centroid_hz"] and ref_analysis["centroid_hz"]:
                plan.brightness = max(0.4, min(2.5, plan.brightness * (ref_analysis["centroid_hz"] / a["centroid_hz"]) ** 0.6))
            sub_ratio = (a["band_share"]["sub(<100)"] + 1e-3) / (ref_analysis["band_share"]["sub(<100)"] + 1e-3)
            plan.low_boost = max(0.3, min(2.0, plan.low_boost / sub_ratio ** 0.4))
        return best

    def mix_under_voice(self, music_wav, voice_audio, out_wav, duck_db=-13):
        return M.duck(music_wav, voice_audio, out_wav, amount_db=duck_db)

    def run(self, task="", **kw):
        return {"task": task, "note": "use plan_for_video / plan_from_reference + render"}


def compare(a, ref):
    """Distance between two analyses (0 = identical). Components are normalised so each is ~0..1."""
    def rel(x, y):
        return abs((x or 0) - (y or 0)) / (abs(y or 1) + 1e-6)
    bands = sum(abs(a["band_share"][k] - ref["band_share"][k]) for k in ref["band_share"]) / 2
    ea, er = a["energy_db_per_0.25s"], ref["energy_db_per_0.25s"]
    n = min(len(ea), len(er))
    import numpy as np
    corr = float(np.corrcoef(ea[:n], er[:n])[0, 1]) if n > 4 else 0.0
    parts = {"bands_l1": round(bands, 3), "centroid_rel": round(min(rel(a["centroid_hz"], ref["centroid_hz"]), 1), 3),
             "lufs_db": round(abs((a["lufs"] or 0) - (ref["lufs"] or 0)), 2), "lra_db": round(abs((a["lra"] or 0) - (ref["lra"] or 0)), 2),
             "energy_corr": round(corr, 3), "bpm_rel": round(min(rel(a["bpm"], ref["bpm"]), rel(a["bpm"] * 2, ref["bpm"])), 3),
             "key_match": a["key"] == ref["key"]}
    score = bands + parts["centroid_rel"] + parts["lufs_db"] / 6 + parts["lra_db"] / 10 + (1 - corr) / 2 + parts["bpm_rel"] + (0 if parts["key_match"] else 0.3)
    return {"score": round(score, 3), **parts}
