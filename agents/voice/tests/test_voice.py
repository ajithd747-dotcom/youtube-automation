"""Smoke test: spec + skills valid, agent imports."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from core import load_agent

rep = load_agent("voice").self_check()
assert rep["ok"], rep
print("ok", rep)
