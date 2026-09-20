---
id: qa-before-long-render
name: Run QA on a draft still before any render longer than 10 minutes
category: workflow
kind: rule
status: verified
applies_to:
- any
when_to_use: About to start a long cinematic render.
triggers:
- long render
- before render
- check first
- review shots
- preview
- qa
- quality gate
source:
- 'own-experience: ada_chain_reaction QA findings (2026-09-19)'
version: 1
---
## Procedure
1. `python blender_agent/agent.py script.txt --style cinematic --qa --plan-only` (each shot costs ~15-30 s for its draft still + framing test).
2. Read the applied fixes in plan.json (`qa` entries); look at `agents/visual-qa/cache/qa_still.png` for the last checked shot.
3. Then run the full render. Saves the 40+ minutes that re-rendering four bad shots cost in the first ada video.
