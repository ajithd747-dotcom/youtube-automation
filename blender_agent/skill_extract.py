"""Turn reference material (videos, books/PDFs, notes) into an EVIDENCE PACK that skills are distilled from.

    python blender_agent/skill_extract.py video "<path.mp4>" [--model base.en] [--sheet-every 20]
    python blender_agent/skill_extract.py text  "<book.pdf|.txt|.md>"          # chunk a book/article by page/section
    python blender_agent/skill_extract.py frame "<path.mp4>" <seconds> [...]   # full-resolution frame(s) to look at
    python blender_agent/skill_extract.py distill <source-slug>                # LLM drafts CANDIDATE skills from a pack
    python blender_agent/skill_extract.py all                                  # every file in "reference vedios/"

A pack lives in blender_agent/skills/sources/<slug>/ and contains:
  evidence.md     metadata, pacing statistics, transcript grouped by minute, contact-sheet index
  transcript.json word-level-ish segments (start, end, text)      metrics.json  cuts, shot lengths, motion curve, loudness
  sheets/         contact sheets with timestamps burned in (look at these to see what the video actually shows)

Video analysis is local (ffmpeg + faster-whisper on CPU + numpy); nothing is uploaded. `distill` is the only step that
calls an LLM (through the project's router) and its output is saved as *candidates* that are never used until verified.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCES = HERE / "skills" / "sources"
REF_DIR = ROOT / "reference vedios"
VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".m4v"}


def slug(p: Path) -> str:
    s = re.sub(r"^vidssave\.com\s*", "", p.stem, flags=re.I)
    s = re.sub(r"\b(1080P|720P|480P)\b", "", s, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "source"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", **kw)


def fmt(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


# ----------------------------------------------------------------------------- video analysis
def probe(path: Path) -> dict:
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    n, dd = (v.get("r_frame_rate") or "0/1").split("/")
    return {"duration": float(d.get("format", {}).get("duration") or 0), "width": v.get("width"), "height": v.get("height"),
            "fps": round(float(n) / float(dd), 2) if float(dd) else 0, "has_audio": a is not None,
            "orientation": "vertical" if (v.get("height") or 0) > (v.get("width") or 0) else "landscape",
            "size_mb": round(int(d.get("format", {}).get("size") or 0) / 1e6, 1)}


def scene_cuts(path: Path, threshold=0.28):
    r = run(["ffmpeg", "-i", str(path), "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"])
    return [float(m) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def motion_curve(path: Path, fps=2):
    """Mean absolute frame difference per sample = how much the picture changes (0..255). Cheap pacing/energy signal."""
    w, h = 160, 90
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", str(path), "-vf", f"fps={fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE)
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
    return out


def loudness(path: Path):
    r = run(["ffmpeg", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"])
    m = re.search(r"I:\s+(-?[0-9.]+) LUFS", r.stderr[r.stderr.rfind("Summary"):] if "Summary" in r.stderr else "")
    return float(m.group(1)) if m else None


def transcribe(path: Path, out_json: Path, model_name="base.en"):
    if out_json.exists():
        return json.loads(out_json.read_text(encoding="utf-8"))
    wav = out_json.with_suffix(".wav")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=2)
    # English-only models must be told English; multilingual ones (small, medium...) detect the language, which the
    # Japanese-language trailers in reference vedios/ need
    segs, info = model.transcribe(str(wav), vad_filter=True, beam_size=1, language="en" if model_name.endswith(".en") else None)
    print(f"[whisper] {path.name}: detected language {getattr(info, 'language', '?')} (p={getattr(info, 'language_probability', 0):.2f})")
    out = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
    out_json.write_text(json.dumps(out, indent=1), encoding="utf-8")
    wav.unlink(missing_ok=True)
    return out


def contact_sheets(path: Path, out_dir: Path, every: float, duration: float, cols=3, rows=3, tile_w=560):
    """Contact sheets with the timestamp burned into every tile. Returns [(sheet_name, [times])]."""
    from PIL import Image, ImageDraw
    out_dir.mkdir(parents=True, exist_ok=True)
    times = [t for t in np.arange(1.0, max(duration - 0.5, 1.5), every)]
    sheets, per = [], cols * rows
    for i in range(0, len(times), per):
        chunk = times[i:i + per]
        tiles = []
        for t in chunk:
            tmp = out_dir / "_t.jpg"
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={tile_w}:-2", str(tmp)])
            if tmp.exists():
                im = Image.open(tmp).convert("RGB")
                ImageDraw.Draw(im).text((8, 6), fmt(t), fill=(255, 255, 0))
                tiles.append(im.copy())
                tmp.unlink()
        if not tiles:
            continue
        w, h = tiles[0].size
        sheet = Image.new("RGB", (w * cols, h * rows), (0, 0, 0))
        for k, im in enumerate(tiles):
            sheet.paste(im, ((k % cols) * w, (k // cols) * h))
        name = f"sheet_{i // per:02d}.jpg"
        sheet.save(out_dir / name, quality=82)
        sheets.append((name, chunk))
    return sheets


def analyse_video(path: Path, model="base.en", sheet_every=20.0):
    d = SOURCES / slug(path)
    d.mkdir(parents=True, exist_ok=True)
    meta = probe(path)
    print(f"[extract] {path.name}: {meta['duration']:.0f}s {meta['width']}x{meta['height']}@{meta['fps']} audio={meta['has_audio']}", flush=True)
    sheet_every = min(sheet_every, max(1.0, meta["duration"] / 9))  # short clips: ~9 tiles, still readable
    cuts = scene_cuts(path)
    edges = [0.0] + cuts + [meta["duration"]]
    shots = [b - a for a, b in zip(edges, edges[1:]) if b - a > 0.05]
    motion = motion_curve(path)
    lufs = loudness(path) if meta["has_audio"] else None
    transcript = transcribe(path, d / "transcript.json", model) if meta["has_audio"] else []
    sheets = contact_sheets(path, d / "sheets", sheet_every, meta["duration"])
    metrics = {**meta, "cuts": [round(c, 2) for c in cuts], "shot_count": len(shots),
               "shot_len_mean": round(float(np.mean(shots)), 2) if shots else 0, "shot_len_median": round(float(np.median(shots)), 2) if shots else 0,
               "shot_len_min": round(min(shots), 2) if shots else 0, "shot_len_max": round(max(shots), 2) if shots else 0,
               "cuts_per_minute": round(len(cuts) / max(meta["duration"] / 60, 0.01), 1),
               "motion_mean": round(float(np.mean(motion)), 2) if motion else 0, "motion_curve_0.5s": [round(m, 1) for m in motion],
               "loudness_lufs": lufs, "words": sum(len(s["text"].split()) for s in transcript)}
    (d / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")

    lines = [f"# Evidence pack: {path.stem}", "", f"- file: `{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}`",
             f"- {meta['duration']:.0f}s, {meta['width']}x{meta['height']} ({meta['orientation']}), {meta['fps']} fps, {meta['size_mb']} MB, audio: {meta['has_audio']}, loudness: {lufs} LUFS",
             f"- pacing: {metrics['shot_count']} shots, {metrics['cuts_per_minute']} cuts/min, shot length mean {metrics['shot_len_mean']}s / median {metrics['shot_len_median']}s "
             f"(min {metrics['shot_len_min']}s, max {metrics['shot_len_max']}s); mean picture motion {metrics['motion_mean']}",
             f"- speech: {metrics['words']} words" + (f" (~{metrics['words'] / max(meta['duration'] / 60, 0.01):.0f} wpm)" if metrics['words'] else ""),
             f"- cut times (s): {metrics['cuts'][:80]}", ""]
    if sheets:
        lines += ["## Contact sheets (timestamp burned into each tile; open the images)", ""]
        lines += [f"- `sheets/{n}`: {', '.join(fmt(t) for t in ts)}" for n, ts in sheets]
        lines.append("")
    if transcript:
        lines += ["## Transcript (grouped by 30 s)", ""]
        bucket, cur = -1, []
        for s in transcript:
            b = int(s["start"] // 30)
            if b != bucket and cur:
                lines.append(f"**[{fmt(bucket * 30)}]** " + " ".join(cur))
                cur = []
            bucket = b
            cur.append(s["text"])
        if cur:
            lines.append(f"**[{fmt(bucket * 30)}]** " + " ".join(cur))
    (d / "evidence.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[extract] pack written: {d / 'evidence.md'}", flush=True)
    return d


# ----------------------------------------------------------------------------- books / text
def analyse_text(path: Path, chunk_chars=3500):
    d = SOURCES / slug(path)
    d.mkdir(parents=True, exist_ok=True)
    pages = []
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        for i, pg in enumerate(PdfReader(str(path)).pages, 1):
            pages.append((i, pg.extract_text() or ""))
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
        pages = [(i + 1, text[k:k + 3000]) for i, k in enumerate(range(0, len(text), 3000))]
    chunks, cur, start = [], "", None
    for pno, txt in pages:
        if start is None:
            start = pno
        cur += f"\n[p{pno}] " + re.sub(r"\s+", " ", txt)
        if len(cur) >= chunk_chars:
            chunks.append((start, pno, cur.strip()))
            cur, start = "", None
    if cur.strip():
        chunks.append((start or pages[-1][0], pages[-1][0], cur.strip()))
    (d / "chunks.json").write_text(json.dumps([{"from": a, "to": b, "text": t} for a, b, t in chunks]), encoding="utf-8")
    md = [f"# Evidence pack: {path.stem}", "", f"- {len(pages)} pages/sections, {len(chunks)} chunks (~{chunk_chars} chars each)", ""]
    md += [f"## pages {a}-{b}\n{t}\n" for a, b, t in chunks]
    (d / "evidence.md").write_text("\n".join(md), encoding="utf-8")
    print(f"[extract] pack written: {d / 'evidence.md'} ({len(chunks)} chunks)")
    return d


# ----------------------------------------------------------------------------- LLM distillation (candidates only)
DISTILL_PROMPT = """You extract reusable ANIMATION-PRODUCTION SKILLS for an AI agent that builds videos in Blender (bpy, headless).
From the source excerpt below, list only techniques that are concrete and repeatable. For each skill reply with a JSON object:
{{"id": "kebab-case", "name": "...", "category": one of {cats}, "when_to_use": "one sentence: the situation in a script/shot that calls for it",
  "triggers": ["keywords/phrases in a script or shot description that should activate it"], "steps": ["imperative steps, with concrete numbers where the source gives them"],
  "pitfalls": ["mistakes to avoid"], "evidence": "what in the source supports this (quote/time/page)"}}
Return a JSON list. Skip generic advice; skip anything not about making animation/video. If nothing qualifies return [].

SOURCE ({name}, {where}):
{text}
"""


def distill(slug_name: str, max_chunks=12):
    sys.path.insert(0, str(HERE))
    import llm
    import skills as S
    d = SOURCES / slug_name
    if (d / "chunks.json").exists():
        parts = [(f"pages {c['from']}-{c['to']}", c["text"]) for c in json.loads((d / "chunks.json").read_text(encoding="utf-8"))]
    else:
        ev = (d / "evidence.md").read_text(encoding="utf-8")
        body = ev.split("## Transcript", 1)[-1]
        parts = [(f"transcript part {i + 1}", body[i:i + 3500]) for i in range(0, len(body), 3500)]
    out = []
    for where, text in parts[:max_chunks]:
        try:
            raw = llm.ask(DISTILL_PROMPT.format(cats=S.CATEGORIES, name=slug_name, where=where, text=text))
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
            items = json.loads(raw[raw.index("["):raw.rindex("]") + 1])
        except Exception as e:
            print(f"[distill] {where}: skipped ({str(e)[:80]})")
            continue
        for it in items:
            if isinstance(it, dict) and it.get("id") and it.get("steps"):
                it["source"] = f"{slug_name} ({where})"
                out.append(it)
    n = S.save_candidates(out, origin=f"distilled from {slug_name}")
    print(f"[distill] {len(out)} proposals -> {n} new candidate skills in skills/candidates/ (unverified, not used by the agent)")


def frames(path: Path, times, out_dir: Path = None):
    out_dir = out_dir or (SOURCES / slug(path) / "frames")
    out_dir.mkdir(parents=True, exist_ok=True)
    for t in times:
        f = out_dir / f"t{int(t):04d}.jpg"
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", str(path), "-frames:v", "1", "-q:v", "3", str(f)])
        print(f)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(0)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    cmd = a[0]
    model = a[a.index("--model") + 1] if "--model" in a else "base.en"
    every = float(a[a.index("--sheet-every") + 1]) if "--sheet-every" in a else 20.0
    if cmd == "video":
        analyse_video(Path(a[1]), model, every)
    elif cmd == "text":
        analyse_text(Path(a[1]))
    elif cmd == "frame":
        frames(Path(a[1]), [float(x) for x in a[2:]])
    elif cmd == "distill":
        distill(a[1])
    elif cmd == "all":
        for f in sorted(REF_DIR.rglob("*")):
            if f.suffix.lower() in VIDEO_EXT:
                analyse_video(f, model, every)
            elif f.suffix.lower() in (".pdf", ".epub", ".txt", ".md"):
                analyse_text(f)
    else:
        print(__doc__)
