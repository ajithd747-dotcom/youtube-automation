"""Category-specific script prompt templates. Each category needs a different
structure/tone -- a generic "write a YouTube script" prompt produces generic,
unfocused results, which is exactly what we're trying to avoid.
"""

# NOTE: uses __EXTRA_FIELDS__ + str.replace (not str.format) so the JSON braces
# stay doubled ({{ }}) all the way through to the single .format(notes=...) call
# that happens later in generate_script.py -- calling .format() on this in two
# passes was collapsing the braces early and breaking the second pass.
BASE_JSON_SCHEMA = """Respond with ONLY valid JSON (no markdown fences, no commentary) in exactly this shape:
{{
  "title": "catchy video title",
  "segments": [
    {{"kind": "hook", "topic": "", "text": "spoken hook text, first 5-10 seconds, must grab attention"}},
    {{"kind": "segment", "topic": "short 1-3 word subject for this segment", "text": "spoken text for this segment"}},
    {{"kind": "recap", "topic": "", "text": "spoken recap text"}},
    {{"kind": "outro", "topic": "", "text": "spoken call-to-action / outro text"}}
  ]__EXTRA_FIELDS__
}}
Include as many "segment" entries as the content needs. Each "text" is spoken narration only --
no stage directions, no labels, no markdown, no emojis. The "kind" field MUST be exactly one of:
"hook", "segment", "recap", "outro" -- no other values (not "intro", not "conclusion", etc).
Exactly one "hook" (first) and exactly one "outro" (last); everything between is "segment" or
one "recap" near the end."""


def _schema(extra_fields: str = "") -> str:
    return BASE_JSON_SCHEMA.replace("__EXTRA_FIELDS__", extra_fields)

PROMPTS = {
    "explainer": """You are writing a short, factual explainer video script for the topic below.
Ground every claim in the research notes provided -- do not invent statistics, dates, or facts
that aren't in the notes. If the notes don't cover something, keep the script general rather
than making it up.

Research notes:
---
{notes}
---

Structure: hook poses the question compellingly, segments build the explanation logically
(simple to more detailed), recap reinforces the key takeaway, outro invites engagement.
Tone: clear, curious, confident -- like a good teacher, not a textbook.

""" + _schema(),

    "comedy_stickman": """You are writing a short comedic stickman video script (15-40 seconds) based
on this premise:
---
{notes}
---

Structure: hook is the setup, 1-3 segments build the comedic situation, the final segment (kind
"outro") IS the punchline -- land it clean, no explaining the joke. Keep it tight; comedy dies
if it drags. Tone: playful, visual-gag-friendly (the stickman will act out gestures matching
each line).

CRITICAL: the "text" field is fed directly to a text-to-speech engine and read aloud verbatim.
It must contain ONLY the words a narrator/character would actually say out loud. NEVER include
sound effects ("Whoosh"), visual/stage directions ("Flash sticky note:", "Zoom into screen"),
captions-on-screen text, or meta-commentary like "quick visual punch" -- none of that belongs in
"text". If a beat has no dialogue, either skip it or write a one-line narration for it instead.

""" + _schema(),

    "crime_news": """You are writing a short true-crime/scam case-study video script based on this
research:
---
{notes}
---

Structure: hook teases the case without spoiling the outcome, segments walk through what
happened / how they were caught / the investigation, recap states the culprit and their
sentence clearly, outro is a brief closing thought (not preachy). Stick strictly to facts
in the research notes -- do not invent names, dates, or sentence lengths that aren't there.
If the culprit's full name is known from the research, include it verbatim in "subject_name".

CRITICAL: never attribute a motive, method detail, or cause to anyone unless it's explicitly
in the research notes. This is a real legal case about real people -- do not speculate or
embellish beyond what's sourced.

""" + _schema(',\n  "subject_name": "full name of the culprit/subject if known from research, else empty string"'),

    "world_news": """You are writing a short, warm/funny world-news recap video script based on
this research:
---
{notes}
---

Structure: hook teases what happened, segments tell the story with genuine warmth or humor
as fits the story, outro is a light closing line. Tone: like a friend telling you an
interesting story they read, not a formal news anchor.

CRITICAL: do not state a cause, motive, or explanation for any event unless it is explicitly
written in the research notes. If the notes don't say WHY something happened, don't guess or
infer a plausible-sounding reason (e.g. do not attribute a separation/event to "the pandemic",
"budget cuts", etc. unless that's literally in the notes) -- just describe what happened.

""" + _schema(),
}

CRITIQUE_PROMPT = """You are a demanding YouTube script editor. Review this draft script (JSON) written
for the "{category}" category, based on the research notes below.

Research notes:
---
{notes}
---

Draft script:
---
{draft}
---

Critique it against this rubric, being specific and harsh where warranted:
1. Hook strength -- does the first line actually earn attention in the first 3 seconds?
2. Factual accuracy -- go sentence by sentence and check every specific claim (names, numbers,
   dates, causes, motives) against the research notes. Flag ANY detail not explicitly present in
   the notes, especially invented causes/explanations (e.g. attributing an event to "the
   pandemic" or similar when the notes don't say that) -- these are the most common and most
   damaging kind of error.
3. Pacing -- any segment that drags, repeats itself, or is filler?
4. Category fit -- does tone/structure match a "{category}" video specifically?
5. Ending -- does it land (punchline/CTA/closing thought) instead of trailing off?

Respond with ONLY a short list of concrete, actionable fixes (not a rewrite). If something is
already strong, don't comment on it. Be terse."""

REVISE_PROMPT = """Revise this draft script to address the critique below. Keep what already works;
fix only what the critique flags. Output the complete revised script.

Original research notes:
---
{notes}
---

Draft:
---
{draft}
---

Critique:
---
{critique}
---

Respond with ONLY valid JSON (no markdown fences, no commentary), same shape as the draft above
(including "subject_name" if the draft had it)."""
