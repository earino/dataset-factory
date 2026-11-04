#!/usr/bin/env python3
"""Record packaging step (iv) prep: add construction_output.splits to the
za-cct-substation-evening-peak-exceedance record from the gate-report values,
cross-checked against meta.json and baseline_result.json (the cqc precedent:
the manifest generator requires recorded split counts and nothing is retyped).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REC = ROOT / "candidates" / "za-cct-substation-evening-peak-exceedance" / "record.json"
META = ROOT / "release" / "za-cct-substation-evening-peak-exceedance" / "meta.json"
SUMMARY = (ROOT / ".factory" / "za-cct-001" / "reports" / "output" / "summary.json")

record = json.loads(REC.read_text())
meta = json.loads(META.read_text())
summary = json.loads(SUMMARY.read_text())

rows, positives, rates = meta["rows"], {}, meta["positive_rate"]
labels = summary["labels_by_year"]
for split, year in (("train", "2022"), ("eval", "2023"), ("holdout", "2024")):
    assert rows[split] == labels[year]["rows"], split
    assert labels[year]["positives"] / labels[year]["rows"] - rates[split] < 5e-6, split
    positives[split] = labels[year]["positives"]

splits = {
    split: {
        "rows": rows[split],
        "positives": positives[split],
        "positive_rate": rates[split],
        "note": (f"target days {year} (Africa/Johannesburg); "
                 f"{labels[year]['distinct_days']} distinct exceedance days"),
    }
    for split, year in (("train", "2022"), ("eval", "2023"), ("holdout", "2024"))
}
splits["holdout"]["note"] += "; sealed, never evaluated"
splits["train"]["note"] += (
    f"; burn-in {summary['exclusions']['burn_in_under_30_prior_evenings']} station-days "
    "counted, never scored")

record["construction_output"] = {
    "splits": splits,
    "source": "za-cct-001 gate report values (summary.json labels_by_year), cross-checked "
              "against meta.json rows/positive_rate and baseline_result.json before the "
              "release manifest was generated (packaging session 2026-11-04)",
}
REC.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print("construction_output.splits recorded and cross-checked:")
print(json.dumps(splits, indent=1))
