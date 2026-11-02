#!/usr/bin/env python3
"""Generate release/ocha-fts-appeal-funding-trajectory/get_dataset.py from the pins helper.

The download/verify logic is shared across dataset releases; only REPO, TAG and the
EXPECTED digests differ, and those are read from expected_artifact.json - never typed.
"""
import json
import pathlib
import re

REPO = pathlib.Path("/opt/data/dataset-factory")
PINS = REPO / "release/pins-planning-appeal-outcome/get_dataset.py"
OUT = REPO / "release/ocha-fts-appeal-funding-trajectory/get_dataset.py"
EXP = json.loads((REPO / "candidates/ocha-fts-appeal-funding-trajectory/baseline/"
                  "expected_artifact.json").read_text())

LAYOUT = {
    "public/train.csv": "public-train.csv",
    "public/eval.csv": "public-eval.csv",
    "private/holdout.csv": "private-holdout.csv",
    "meta.json": "meta.json",
    "quality.json": "quality.json",
}

expected = {}
for rel, info in EXP["files"].items():
    expected[LAYOUT[rel]] = {"bytes": info["bytes"], "sha256": info["sha256"]}

text = PINS.read_text()
text = text.replace('REPO = "earino/pins-planning-appeal-outcome"',
                    'REPO = "earino/ocha-fts-appeal-funding-trajectory"')
text = text.replace('TAG = "v2026.10"', 'TAG = "v2026.11"')
text = re.sub(r"EXPECTED = \{.*?\n\}\n", "", text, flags=re.S)
entries = ",\n".join(
    f'    "{flat}": {{"bytes": {v["bytes"]},\n'
    f'                      "sha256": "{v["sha256"]}"}}'
    for flat, v in sorted(expected.items())
)
block = "EXPECTED = {\n" + entries + ",\n}\n"
text = re.sub(r"(# Recorded at packaging time from the gate's artifact block; the manifest is the authority\.\n)",
              r"\1" + block, text, count=1)
assert "ocha-fts" in text and "v2026.11" in text and "public-train.csv" in text
OUT.write_text(text)
print("wrote", OUT, len(text), "bytes")
for k, v in sorted(expected.items()):
    print(f"  {k}: {v['bytes']} B {v['sha256'][:16]}...")
