---
id: qa-auto-fix-mapping
name: Map QA findings to recipe parameters
category: fix
kind: rule
status: verified
applies_to:
- any
when_to_use: Turning a QA finding into a concrete change to the shot plan.
triggers:
- fix
- exposure bias
- fog scale
- auto fix
- adjust
- haze
- parameters
- plan
source:
- 'own-experience: ada_chain_reaction QA findings (2026-09-19)'
version: 1
---
## Rules
- washed_out -> exposure_bias -0.6 and fog_scale x0.5.  clipped_highlights -> exposure_bias -0.5.  too_dark -> exposure_bias +0.8.  flat_contrast -> fog_scale x0.6.
- Params are written to plan.json (`params.exposure_bias`, `params.fog_scale`) with the evidence under `qa`; recipes read them in `cine_recipes.build`.
- Re-check after each fix (max 2 rounds). Result on the hazy intro: mean 0.84 -> 0.74, std 0.135 -> 0.184, clipped 17 % -> 7 %, no findings left.
