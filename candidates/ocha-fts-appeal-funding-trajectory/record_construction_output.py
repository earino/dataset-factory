#!/usr/bin/env python3
"""Add construction_output.splits to the ocha-fts record, read from the gate report.

release-manifest.py needs recorded split counts; the authority is the gate
report beside the artifact (splits.non_empty evidence, recomputed from the
rows). Read from there, never typed.
"""
import json
import pathlib

REPO = pathlib.Path("/opt/data/dataset-factory")
REC = REPO / "candidates/ocha-fts-appeal-funding-trajectory/record.json"
REPORT = REPO / "candidates/ocha-fts-appeal-funding-trajectory/baseline/qualification.json"

report = json.loads(REPORT.read_text())
assert report["ok"] is True and not report["failed_checks"]
counts = None
for item in report["results"]:
    if item.get("check") == "splits.non_empty":
        counts = item["evidence"]
if counts is None:
    raise SystemExit("gate report carries no splits.non_empty evidence")
assert counts["train"]["rows"] == 437 and counts["eval"]["rows"] == 139 and counts["holdout"]["rows"] == 182

record = json.loads(REC.read_text())
splits = {name: {"rows": data["rows"], "positives": data["positives"],
                 "positive_rate": data["positive_rate"]}
          for name, data in counts.items()}
record["construction_output"] = {
    "splits": splits,
    "source": "fts-appeal-003 gate 1.5.0 report splits.non_empty evidence, recomputed from the artifact rows",
}
record["updated_at"] = record.get("updated_at")  # unchanged this pass
REC.write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n")
print("construction_output.splits recorded:", json.dumps(splits))
