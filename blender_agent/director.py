"""Director: turns one script segment (+ its narration length) into a validated "shot" dict for scene_lib.

Primary path: an LLM writes the shot as JSON in a small declarative DSL (robust: it can only use
known object types/animations). If the LLM is unavailable or returns junk, a keyword heuristic still
produces a sensible shot, so the pipeline never stops.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "blender_side"))
from dsl import ACTIONS, CAMERAS, ENTRIES, ICONS, LOOPS, MOODS, RECIPES, SHAPES, STYLES, TYPES  # noqa: E402

import llm  # noqa: E402

try:
    import skills as SK  # noqa: E402
except Exception:  # the director must keep working without the skill library
    SK = None

CINE_SYSTEM = """You are a film director. For ONE narrated script segment choose the best cinematic 3D scene from this catalogue.
Reply with ONLY a JSON object: {"style":"cinematic","recipe":<name>,"mood":<mood>,"title":<short text or "">}

Recipes (name: what it shows):
""" + "\n".join(f"- {k}: {v[1]}" for k, v in RECIPES.items()) + f"""

Moods: {MOODS} (day = bright sky, sunset = warm backlight, night = dark with glow, studio = dark with softboxes, neon = magenta/cyan club light).
Rules: match the recipe to the MEANING of the narration; vary recipes between consecutive segments (do not repeat one that was just used);
"title" is an optional 1-4 word on-screen headline (shown as glowing 3D text) - use it for hooks/outros and key statements, else "".
"""

PALETTES = {
    "cinematic": "",
    "stickman": "bg #f4f1ea (paper), stickman #111111, accents #e63946 #457b9d #f4a261, text #111111",
    "kinetic": "bg #101826 (dark navy), text #ffffff, accents #ffd23f #3bceac #ff4d6d #4d9de0",
    "3d": "bg #dfe9f5 (soft sky), objects saturated #ff6b6b #4ecdc4 #ffd93d #6c5ce7, text #1b2a41",
}

SYSTEM = f"""You are an animation director. You convert one narrated script segment into ONE shot for a Blender scene builder.
Reply with ONLY a JSON object (no prose, no markdown).

Frame: pos = [x, z] each in -1..1 (x right, z up; [0,0] is the centre). size = fraction of frame height (0.05..1.0).
Do not overlap objects; keep everything inside -0.9..0.9. Use 3-5 objects (fewer is better; portrait 9:16 frames are narrow: stack objects vertically). The spoken words are shown as captions
separately, so on-screen text must be a SHORT key phrase (1-5 words), never the whole sentence.

JSON schema:
{{
  "style": one of {STYLES},
  "bg": "#rrggbb",
  "camera": one of {CAMERAS}   (orbit only for style 3d),
  "objects": [
    {{"type": one of {TYPES},
      "pos": [x, z], "size": 0.05..1.0, "color": "#rrggbb",
      "text": "for type text",
      "icon": one of {ICONS}  (for type icon),
      "action": one of {ACTIONS}  (for type stickman),
      "enter": one of {ENTRIES}, "delay": seconds (stagger objects: 0, 0.4, 0.8 ...),
      "loop": one of {LOOPS},
      "move_to": [x, z] optional (object glides there; stickman + action walk/run walks there), "move_time": seconds}}
  ],
  "custom": "OPTIONAL one sentence describing an extra effect that the basic objects cannot do
             (confetti, counter counting up, typewriter text, bar chart growing, screen shake, speech bubble...).
             Omit unless it clearly improves the shot."
}}
Rect objects use "size": [width_fraction_of_width, height_fraction_of_height].
Style guidance: stickman = comedy/story acted out by a stickman (color #111111) on a light bg;
kinetic = explainer with big text, icons, cards, charts on a dark bg; 3d = solid colored primitives with slow camera orbit.
Sizes: stickman is a FULL-HEIGHT figure, use size 0.5-0.75. Titles/text size 0.08-0.15. Icons 0.2-0.45. Keep text in the
top band (z 0.6..0.9). The bottom 15% (landscape) / 25% (portrait) of the frame is covered by captions: keep every object above it.
Palette for the chosen style: {{palette}}

Example ({{style}}):
{{example}}
"""

EXAMPLES = {
    "stickman": '{"style":"stickman","bg":"#f4f1ea","camera":"push_in","objects":['
                '{"type":"text","text":"Locked out!","pos":[0,0.78],"size":0.12,"color":"#111111","enter":"pop_in"},'
                '{"type":"stickman","pos":[-0.45,-0.05],"size":0.65,"action":"run","enter":"slide_in_left","move_to":[0.05,-0.05],"move_time":2.5},'
                '{"type":"icon","icon":"lock","pos":[0.55,-0.1],"size":0.4,"color":"#e63946","delay":0.6,"loop":"shake"}]}',
    "kinetic": '{"style":"kinetic","bg":"#101826","camera":"push_in","objects":['
               '{"type":"rect","pos":[0,0.62],"size":[0.5,0.012],"color":"#ffd23f","enter":"slide_in_left"},'
               '{"type":"text","text":"3x faster results","pos":[0,0.3],"size":0.16,"color":"#ffffff","delay":0.2},'
               '{"type":"icon","icon":"chart_up","pos":[0,-0.3],"size":0.5,"color":"#3bceac","delay":0.6,"loop":"float"}]}',
    "3d": '{"style":"3d","bg":"#dfe9f5","camera":"orbit","objects":['
          '{"type":"ground","pos":[0,-0.45],"size":1,"color":"#c9d6e6","enter":"none"},'
          '{"type":"text","text":"Meet the future","pos":[0,0.75],"size":0.11,"color":"#1b2a41","delay":0.2},'
          '{"type":"icon","icon":"globe","pos":[0,0.05],"size":0.5,"loop":"spin","delay":0.4},'
          '{"type":"sphere","pos":[-0.6,-0.1],"size":0.16,"color":"#4ecdc4","delay":0.7,"loop":"bounce"}]}',
}


KEYWORD_ICONS = [
    (r"money|cash|price|pay|dollar|earn|profit|free|cost|paid|save", "coin"),
    (r"idea|think|tip|learn|smart|brain|insight|creative", "lightbulb"),
    (r"grow|increase|rise|boost|trend|stat|percent|revenue|sales|chart", "chart_up"),
    (r"fast|speed|quick|power|energy|instant|lightning", "bolt"),
    (r"time|minute|hour|deadline|wait|clock|schedule|week|day", "clock"),
    (r"world|global|internet|web|online|country|international", "globe"),
    (r"laptop|computer|software|code|app|tool|ai |automate|browser", "laptop"),
    (r"phone|mobile|call|text message|scroll", "phone"),
    (r"secure|safe|privacy|lock|password|scam|fraud|protect", "lock"),
    (r"love|heart|family|couple|friend|reunite|kind", "heart"),
    (r"step|process|setting|system|engine|workflow", "gear"),
    (r"question|why|how|what|\?", "question"),
    (r"warning|danger|alert|wow|shock|!", "exclaim"),
    (r"best|top|win|great|star|favorite|award", "star"),
    (r"nature|green|forest|tree|outdoor", "tree"),
    (r"home|house|building|real estate", "house"),
]
KEYWORD_ACTIONS = [
    (r"run|rush|race|chase|hurry", "run"),
    (r"walk|goes|head|enter|leave|arrive", "walk"),
    (r"hello|hi |wave|greet|welcome|meet", "wave"),
    (r"think|wonder|idea|consider|decide|confus|hmm", "think"),
    (r"jump|celebrate|win|success|happy|yay|excite", "jump"),
    (r"sad|cry|fail|lose|stuck|disappoint|tired|bored|procrastinat", "sad"),
    (r"point|look at|show|see|notice|click", "point"),
]
CTA = re.compile(r"subscribe|like|comment|follow|thanks|thank you|see you|bell|share", re.I)


def _hex(c, default):
    return c if isinstance(c, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", c) else default


def _num(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def _pos(v):
    try:
        out = [max(-1.0, min(1.0, float(v[0]))), max(-1.0, min(1.0, float(v[1])))]
        if len(v) > 2:
            out.append(max(-1.0, min(1.0, float(v[2]))))
        return out
    except (TypeError, ValueError, IndexError, KeyError):
        return [0.0, 0.0]


def sanitize(shot: dict, style: str = None, portrait: bool = False) -> dict:
    """Clamp/whitelist everything so scene_lib can never receive out-of-contract values."""
    st = style if style in STYLES else (shot.get("style") if shot.get("style") in STYLES else "kinetic")
    if st == "cinematic":
        rec = shot.get("recipe") if shot.get("recipe") in RECIPES else "robot_intro"
        mood = shot.get("mood") if shot.get("mood") in MOODS else RECIPES[rec][0]
        title = re.sub(r"\s+", " ", str(shot.get("title") or ""))[:40].strip()
        return {"style": "cinematic", "recipe": rec, "mood": mood, "title": title, "params": dict(shot.get("params") or {})}
    default_bg = {"stickman": "#f4f1ea", "kinetic": "#101826", "3d": "#dfe9f5"}[st]
    text_default = "#111111" if st in ("stickman", "3d") else "#ffffff"
    out = {"style": st, "bg": _hex(shot.get("bg"), default_bg),
           "camera": shot.get("camera") if shot.get("camera") in CAMERAS else "static", "objects": []}
    if out["camera"] == "orbit" and st != "3d":
        out["camera"] = "push_in"
    max_objs = 5 if portrait else 6
    for o in (shot.get("objects") or [])[:12]:
        if len(out["objects"]) >= max_objs:
            break
        if not isinstance(o, dict):
            continue
        typ = o.get("type") if o.get("type") in TYPES else ("icon" if o.get("icon") in ICONS else None)
        if typ is None:
            continue
        obj = {"type": typ, "pos": _pos(o.get("pos")), "color": _hex(o.get("color"), text_default if typ == "text" else "#4d9de0"),
               "enter": o.get("enter") if o.get("enter") in ENTRIES else "pop_in",
               "delay": _num(o.get("delay"), 0, 8, 0.0),
               "loop": o.get("loop") if o.get("loop") in LOOPS else "none"}
        if typ == "rect":
            sz = o.get("size")
            obj["size"] = [_num(sz[0], 0.02, 1.0, 0.4), _num(sz[1], 0.005, 0.2, 0.05)] if isinstance(sz, (list, tuple)) and len(sz) == 2 else [0.4, 0.05]
        else:
            cap = {"text": 0.15, "icon": 0.35 if portrait else 0.45, "stickman": 0.75, "ground": 1.0}.get(typ, 0.4)
            obj["size"] = _num(o.get("size"), 0.05, cap, min(0.3, cap))
        if typ == "text":
            obj["text"] = re.sub(r"\s+", " ", str(o.get("text", "")))[:70]
            if not obj["text"].strip():
                continue
        if typ == "icon":
            obj["icon"] = o.get("icon") if o.get("icon") in ICONS else "star"
        if typ == "stickman":
            obj["action"] = o.get("action") if o.get("action") in ACTIONS else "idle"
            obj["color"] = _hex(o.get("color"), "#111111")
            obj["size"] = max(obj["size"], 0.45)  # a full-height figure reads badly when tiny
        if o.get("move_to"):
            obj["move_to"] = _pos(o["move_to"])[:2]
            obj["move_time"] = _num(o.get("move_time"), 0.5, 10, 2.0)
        out["objects"].append(obj)
    custom = shot.get("custom")
    if isinstance(custom, str) and custom.strip():
        out["custom"] = custom.strip()[:300]
    fix_layout(out["objects"], portrait)
    return out


# ----------------------------------------------------------------------------- layout
def _box(o, aspect):
    """Approximate (cx, cz, half_w, half_h) in normalized frame units (frame height = 2)."""
    cx, cz = o["pos"][0] * aspect, o["pos"][1]  # x in "height units" so boxes are isotropic
    if o["type"] == "text":
        wrap = 26 if aspect > 1 else 13  # same wrapping as scene_lib.add_object
        n = len(o["text"])
        lines = max(1, -(-n // wrap))
        widest = min(n, wrap)
        return cx, cz, min(aspect * 0.9, 0.37 * o["size"] * widest), 0.9 * o["size"] * lines
    if o["type"] == "stickman":
        return cx, cz, o["size"] * 0.55, o["size"]
    if o["type"] == "rect":
        return cx, cz, o["size"][0] * aspect, o["size"][1]
    return cx, cz, o["size"], o["size"]


def _hit(a, b, pad=0.04):
    return abs(a[0] - b[0]) < a[2] + b[2] + pad and abs(a[1] - b[1]) < a[3] + b[3] + pad


def fix_layout(objs, portrait=False):
    """Nudge colliding objects (text over a character, icon on a stickman...) to the nearest free spot.
    The bottom band is reserved for burned-in captions, so nothing may extend below `floor`."""
    aspect = 9 / 16 if portrait else 16 / 9
    floor = -0.5 if portrait else -0.72
    fixed = [o for o in objs if o["type"] in ("ground", "rect")]
    movable = [o for o in objs if o not in fixed]
    movable.sort(key=lambda o: {"stickman": 0, "icon": 1}.get(o["type"], 2))  # characters keep their place
    placed = []
    for o in movable:
        if o.get("move_to"):  # gliding objects: only check the start point
            pass
        cands = [tuple(o["pos"][:2])]
        if o["type"] == "text":
            cands += [(0.0, z / 100) for z in range(85, int(floor * 100) - 1, -6)]
        else:
            cands += [(x, z) for z in (0.0, 0.25, -0.25, 0.5) for x in (0.55, -0.55, 0.3, -0.3, 0.75, -0.75)]
        for x, z in cands:
            trial = dict(o, pos=[x, z] + list(o["pos"][2:]))
            b = _box(trial, aspect)
            if b[1] + b[3] <= 1.02 and b[1] - b[3] >= floor and all(not _hit(b, _box(p, aspect)) for p in placed):
                o["pos"] = trial["pos"]
                break
        else:  # nowhere collision-free: at least keep it out of the caption band
            b = _box(o, aspect)
            if b[1] - b[3] < floor:
                o["pos"][1] = round(floor + b[3], 3)
        placed.append(o)


# ----------------------------------------------------------------------------- heuristic fallback
def _first(patterns, text, default):
    low = " " + text.lower() + " "
    for pat, val in patterns:
        if re.search(pat, low):
            return val
    return default


def headline(topic: str, text: str, n=5) -> str:
    if topic and len(topic) < 40:
        return topic
    words = re.findall(r"[A-Za-z0-9'$%+-]+", text)
    return " ".join(words[:n])


CINE_KEYWORDS = [
    (r"domino|chain reaction|one push|momentum|cascade|ripple effect", "domino_run"),
    (r"smash|crash|destroy|collaps|break|wreck|explod|knock|impact|tower|wall of", "crate_smash"),
    (r"flag|banner|wind|victory|proud|success|unfurl", "cloth_banner"),
    (r"firework|night sky|sparkle|finale|celebrat|wonder|magic", "fireworks"),
    (r"jelly|bounce|party|play|fun|wobble|colou?rful|energy", "jelly_pit"),
    (r"glass|gold|treasure|polish|shiny|crystal|chrome|gem|precious|product", "glass_showcase"),
    (r"walk|morning|workshop|journey|travel|route|every day|daily|explor", "workshop_walk"),
    (r"fire|campfire|flame|smoke|ember|burn|bonfire|torch|cozy|warmth", "campfire_smoke"),
    (r"water|splash|liquid|rain|drink|pool|puddle|wave|ocean|pour", "water_splash"),
    (r"fur|fluffy|furry|pet|cute|animal|creature|hair|soft", "fuzzy_creature"),
]


def heuristic_cine(kind: str, topic: str, text: str, used=()) -> dict:
    rec = _first(CINE_KEYWORDS, text, None)
    if kind == "hook" and not rec:
        rec = "robot_intro"
    if kind in ("outro", "recap") or (CTA.search(text) and kind != "hook"):
        rec = "finale_confetti"
    if rec is None or (used and rec == used[-1]):
        rec = next((r for r in RECIPES if r not in list(used)[-3:] and r != "finale_confetti"), "robot_intro")
    title = headline(topic, text, 3) if kind in ("hook", "outro") else ""
    return sanitize({"style": "cinematic", "recipe": rec, "title": title}, "cinematic")


def heuristic_shot(kind: str, topic: str, text: str, style: str, portrait: bool = False, used=()) -> dict:
    if style == "cinematic":
        return heuristic_cine(kind, topic, text, used)
    icon = _first(KEYWORD_ICONS, text, "star")
    head = headline(topic, text)
    if kind in ("outro", "recap") and CTA.search(text):
        head = "Like & Subscribe"
        icon = "heart"
    palette = {"stickman": ("#f4f1ea", "#111111", "#e63946"), "kinetic": ("#101826", "#ffffff", "#ffd23f"),
               "3d": ("#dfe9f5", "#1b2a41", "#ff6b6b")}[style]
    bg, fg, accent = palette
    if style == "stickman":
        action = _first(KEYWORD_ACTIONS, text, "talk")
        objs = [{"type": "stickman", "pos": [-0.35, -0.15], "size": 0.62, "action": action, "enter": "slide_in_left"},
                {"type": "icon", "icon": icon, "pos": [0.42, 0.05], "size": 0.32, "color": accent, "enter": "pop_in", "delay": 0.5, "loop": "float"},
                {"type": "text", "text": head, "pos": [0.0, 0.72], "size": 0.1, "color": fg, "delay": 0.2}]
        if action in ("walk", "run"):
            objs[0]["move_to"] = [0.1, -0.15]
        cam = "push_in"
    elif style == "3d":
        objs = [{"type": "ground", "pos": [0, -0.45], "size": 1, "color": "#c9d6e6", "enter": "none"},
                {"type": "icon", "icon": icon, "pos": [0.0, 0.0], "size": 0.5, "color": accent, "loop": "spin"},
                {"type": "sphere", "pos": [-0.55, -0.15], "size": 0.16, "color": "#4ecdc4", "delay": 0.4, "loop": "bounce"},
                {"type": "cube", "pos": [0.55, -0.15], "size": 0.16, "color": "#ffd93d", "delay": 0.7, "loop": "spin"},
                {"type": "text", "text": head, "pos": [0, 0.72], "size": 0.1, "color": fg, "delay": 0.2}]
        cam = "orbit"
    else:
        objs = [{"type": "rect", "pos": [0, 0.5], "size": [0.6, 0.01], "color": accent, "enter": "slide_in_left"},
                {"type": "text", "text": head, "pos": [0, 0.15 if not portrait else 0.3], "size": 0.16, "color": fg, "delay": 0.15},
                {"type": "icon", "icon": icon, "pos": [0, -0.42], "size": 0.36, "color": accent, "delay": 0.5, "loop": "float"}]
        cam = "push_in"
    return sanitize({"style": style, "bg": bg, "camera": cam, "objects": objs}, style, portrait)


# ----------------------------------------------------------------------------- LLM path
def pick_style(title: str, segments: list) -> str:
    sample = " ".join(t for _, _, t in segments[:4])[:700]
    low = (title + " " + sample).lower()
    guess = "stickman" if re.search(r"stickman|joke|funny|comedy|he sits|she sits", low) else "kinetic"
    try:
        ans = llm.ask(f"Title: {title}\nScript start: {sample}\n\nWhich animation style fits best: stickman (comedy/story acted "
                      f"by a stick figure), kinetic (explainer with animated text/icons/charts), or 3d (product/object showcase)? "
                      f"Answer with exactly one word.").strip().lower()
        for s in STYLES:
            if s in ans:
                return s
    except Exception as e:
        print(f"[director] style pick fell back to heuristic ({str(e)[:80]})")
    return guess


def skill_guidance(query: str, style: str, k=3):
    """Matched skills as prompt text + their ids (for usage statistics). Empty when the library is unavailable."""
    if SK is None:
        return "", []
    try:
        standing = SK.standing_rules()
        hits = [(sc, s) for sc, s in SK.match(query, k=k, style=style) if s.id not in {r.id for r in standing}]
    except Exception:
        return "", []
    picked = standing + [s for _, s in hits]
    return "\n\n".join(s.brief(700) for s in picked), [s.id for s in picked]


def plan_shot(kind: str, topic: str, text: str, duration: float, style: str, portrait: bool = False,
              allow_custom: bool = True, prev_summary: str = "", used=()) -> dict:
    if style == "cinematic":
        guide, ids = skill_guidance(f"{topic} {text}", "cinematic")
        prompt = (f"Segment kind: {kind}. Narration length {duration:.1f}s.\nNarration: \"{text}\"\n"
                  f"Recipes already used (most recent last): {list(used)}.\n"
                  + (f"Skills from the library that match this segment (use their advice; recipe skills name the recipe to pick):\n{guide}\n" if guide else "")
                  + "Reply with the JSON only.")
        try:
            shot = sanitize(llm.ask_json(prompt, CINE_SYSTEM), "cinematic")
            shot["skills"] = ids
            if used and shot["recipe"] == used[-1]:
                raise ValueError("repeated recipe")
            return shot
        except Exception as e:
            print(f"[director] LLM cinematic plan failed ({str(e)[:90]}); using heuristic")
            return heuristic_cine(kind, topic, text, used)
    guide, ids = skill_guidance(f"{topic} {text}", style)
    system = SYSTEM.replace("{palette}", PALETTES[style]).replace("{style}", style).replace("{example}", EXAMPLES[style])
    prompt = (f"Video style: {style}. Frame: {'portrait 9:16' if portrait else 'landscape 16:9'}.\n"
              f"Segment kind: {kind}. Topic label: {topic or '-'}. Narration length: {duration:.1f}s "
              f"(objects with a 'delay' must appear before the narration ends).\n"
              f"Narration: \"{text}\"\n"
              + (f"Previous shot (keep the visual identity consistent): {prev_summary}\n" if prev_summary else "")
              + (f"Skill-library advice that matches this segment:\n{guide}\n" if guide else "")
              + f"Use style \"{style}\" for this shot. Reply with the JSON shot only.")
    try:
        shot = sanitize(llm.ask_json(prompt, system), style, portrait)
        if not shot["objects"]:
            raise ValueError("no valid objects")
        if not allow_custom:
            shot.pop("custom", None)
        shot["skills"] = ids
        return shot
    except Exception as e:
        print(f"[director] LLM plan failed ({str(e)[:90]}); using heuristic shot")
        return heuristic_shot(kind, topic, text, style, portrait)


def summarize(shot: dict) -> str:
    if shot.get("style") == "cinematic":
        return f"cinematic {shot['recipe']} ({shot['mood']})"
    return f"{shot['style']}, bg {shot['bg']}, " + ", ".join(
        f"{o['type']}{'/' + o.get('icon', o.get('action', '')) if o['type'] in ('icon', 'stickman') else ''}" for o in shot["objects"][:6])
