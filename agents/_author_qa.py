import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from core import SK

CATS = ["check", "fix", "workflow"]
def skill(id, name, cat, when, triggers, body):
    meta = {"id": id, "name": name, "category": cat, "kind": "rule", "status": "verified", "applies_to": ["any"], "when_to_use": when,
            "triggers": triggers, "source": ["own-experience: ada_chain_reaction QA findings (2026-09-19)"], "version": 1}
    with SK.library(HERE / "visual-qa" / "skills", CATS):
        SK.write_skill(SK.SKILLS_DIR / cat / f"{id}.md", meta, body)

skill("qa-luminance-thresholds", "Numeric thresholds that flag hazy, dark or clipped shots", "check",
      "Judging a still without looking: washed out, too dark, clipped highlights, flat contrast.",
      ["washed out", "hazy", "too dark", "clipped", "overexposed", "flat contrast", "histogram", "milky", "luminance"],
      """## Rules (calibrated on the ada_chain_reaction shots)
- washed_out: mean luminance > 0.60 and std < 0.14 (the hazy intro: mean 0.84 std 0.135; banner 0.88 / 0.12).
- clipped_highlights: > 10 % of pixels above 0.98 (intro 17 %, domino 23 %).
- too_dark: mean < 0.07 (unless the mood is night/neon by design).
- flat_contrast: p95 - p5 < 0.20.
- Healthy target after fixing: mean 0.30-0.75, std 0.15-0.30, clipped < 8 %, p5 < 0.4.
""")
skill("qa-auto-fix-mapping", "Map QA findings to recipe parameters", "fix",
      "Turning a QA finding into a concrete change to the shot plan.",
      ["fix", "exposure bias", "fog scale", "auto fix", "adjust", "haze", "parameters", "plan"],
      """## Rules
- washed_out -> exposure_bias -0.6 and fog_scale x0.5.  clipped_highlights -> exposure_bias -0.5.  too_dark -> exposure_bias +0.8.  flat_contrast -> fog_scale x0.6.
- Params are written to plan.json (`params.exposure_bias`, `params.fog_scale`) with the evidence under `qa`; recipes read them in `cine_recipes.build`.
- Re-check after each fix (max 2 rounds). Result on the hazy intro: mean 0.84 -> 0.74, std 0.135 -> 0.184, clipped 17 % -> 7 %, no findings left.
""")
skill("qa-before-long-render", "Run QA on a draft still before any render longer than 10 minutes", "workflow",
      "About to start a long cinematic render.",
      ["long render", "before render", "check first", "review shots", "preview", "qa", "quality gate"],
      """## Procedure
1. `python blender_agent/agent.py script.txt --style cinematic --qa --plan-only` (each shot costs ~15-30 s for its draft still + framing test).
2. Read the applied fixes in plan.json (`qa` entries); look at `agents/visual-qa/cache/qa_still.png` for the last checked shot.
3. Then run the full render. Saves the 40+ minutes that re-rendering four bad shots cost in the first ada video.
""")
print("qa skills written")
