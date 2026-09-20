---
id: preview-first-render-workflow
name: 'Plan, preview, then render: review before the long render'
category: workflow
kind: rule
status: verified
applies_to:
- any
when_to_use: Starting any new video, especially cinematic ones that take an hour or more.
triggers:
- preview
- draft
- plan
- review
- long render
- workflow
- iterate
- test render
tags:
- workflow
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
1. `agent.py script.txt --style cinematic --plan-only` -> voiceover + `work/<name>/plan.json` (recipe / mood / title per shot).
2. Edit plan.json by hand if a choice is wrong (the edit is remembered as a preference).
3. `--quality draft --preview` for a fast look (640x360, 12 fps).
4. Full render in the background; look at each finished `work/<name>/segNN_*.mp4` as it appears and fix problems in that shot only.
5. To force one shot to re-render after a code change, change its plan entry (e.g. `"params": {"v": 2}`): the cache key hashes the shot dict, quality, size and duration - not code.

## Pitfalls
- Wait for physics shots before trusting the plan: verify motion in the finished shot (frozen physics looked fine in stills).
