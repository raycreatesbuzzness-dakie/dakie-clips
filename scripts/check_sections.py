"""Quick check: report whether each clip's source.mp4 is complete (has enough length and audio).

Usage: python check_sections.py <project_dir>
"""
import json
import sys
from pathlib import Path

from dakie.clip import _section_problem

proj = Path(sys.argv[1])
info = json.loads((proj / "info.json").read_text())
print("info duration:", info.get("duration"))
for d in sorted((proj / "clips").glob("clip_*")):
    src = d / "source.mp4"
    prep = d / "prep.json"
    want = 36.0
    if prep.exists():
        p = json.loads(prep.read_text())
        want = p["source_end"] - p["source_start"]
    print(d.name, (_section_problem(src, want) or "OK") if src.exists() else "missing")
