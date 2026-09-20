"""Smoke test for the visual-qa agent: spec + skills are valid and run() answers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from core import load_agent  # noqa: E402

agent = load_agent("visual-qa")
report = agent.self_check()
assert report["ok"], report
print("ok", report)
