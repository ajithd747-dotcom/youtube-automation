"""Word-timed captions: group word timings into 1-3 word chunks and write karaoke (word-highlight) or plain ASS subtitles.

Implements the skill `word-highlight-captions` (reference: vertical comedy short - white bold text, current word in yellow;
tutorial hook - huge yellow outlined 2-3 words).
"""
import re


def chunks(words, max_words=3, max_chars=16, gap=0.45):
    """[{text,start,end,words:[{text,start,end}]}]; breaks on punctuation, long pauses, or size."""
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or len(" ".join(x["text"] for x in cur + [w])) > max_chars or w["start"] - cur[-1]["end"] > gap):
            out.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?,;:]$", w["text"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [{"text": " ".join(x["text"] for x in c), "start": c[0]["start"], "end": c[-1]["end"], "words": c} for c in out]


def _t(s):
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def _clean(s):
    return s.replace("{", "(").replace("}", ")")


def write_ass(path, words, w, h, offset=0.0, style="karaoke", font="Arial", size_pct=None, position="lower", max_words=3):
    """style: 'karaoke' (white text, current word yellow), 'hook' (huge yellow, thick black outline), 'plain' (white, shadow)."""
    size = int(h * (size_pct or {"karaoke": 0.055 if w > h else 0.045, "hook": 0.08 if w > h else 0.06, "plain": 0.05 if w > h else 0.04}[style]))
    outline = {"karaoke": 4, "hook": 7, "plain": 3}[style]
    primary = {"karaoke": "&H00FFFFFF", "hook": "&H0000E0FF", "plain": "&H00FFFFFF"}[style]     # BGR: yellow = 00E0FF
    secondary = "&H0000E0FF"
    align, mv = (2, int(h * (0.08 if position == "lower" else 0.3))) if position != "mid" else (5, 0)
    head = (f"[Script Info]\nScriptType: v4.00+\nWrapStyle: 0\nPlayResX: {w}\nPlayResY: {h}\n\n[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
            f"Style: Cap,{font},{size},{primary},{secondary},&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{outline},1,{align},{int(w * 0.06)},{int(w * 0.06)},{mv},1\n\n"
            "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
    lines = []
    for c in chunks(words, max_words=max_words):
        t0, t1 = c["start"] + offset, c["end"] + offset + 0.08
        if style == "karaoke":
            txt = "".join(f"{{\\kf{max(1, int(round((x['end'] - x['start']) * 100)))}}}{_clean(x['text'])} " for x in c["words"]).strip()
        else:
            txt = _clean(c["text"])
        lines.append(f"Dialogue: 0,{_t(t0)},{_t(t1)},Cap,,0,0,0,,{txt}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(head + "\n".join(lines) + "\n")
    return path
