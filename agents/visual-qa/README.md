# Visual Qa

Checks every planned shot before the long render (still render -> exposure/haze/clipping metrics + subject-in-frame test) and auto-applies fixes (exposure bias, fog scale) to the shot plan

- kind: `algorithmic`
- spec: `agent.json` - tools in `tools/` - skills in `skills/` (grown with `python agents/cli.py create-skill ...`)
- health check: `python agents/cli.py verify visual-qa`
