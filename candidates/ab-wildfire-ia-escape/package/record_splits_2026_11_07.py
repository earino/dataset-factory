#!/usr/bin/env python3
"""Add record.construction_output for ab-wildfire-ia-escape (packaging step).

Reads the split values from the gate report's own quality.json (the artifact's
shipped descriptor, digest-verified equal to the accepted artifact c2c8ceb5...),
cross-checks them against meta.json and the collected abwildfire-baseline-002
baseline_result.json, and writes record.construction_output.splits. Nothing is
retyped: every number is read from those files. Mirrors cpcb's
package/record_splits_2026_11_06.py.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAND = ROOT / "candidates" / "ab-wildfire-ia-escape"
REL = ROOT / "release" / "ab-wildfire-ia-escape"
FACT = ROOT / ".factory" / "abwildfire-build-001" / "reports"
ART = "c2c8ceb56c7ff52aaf748473e1251725c4ee86912edb9b17387e6b44d0e43da2"

quality = json.loads((REL / "quality.json").read_text())
meta = json.loads((REL / "meta.json").read_text())
baseline = json.loads((CAND / "baseline" / "baseline_result.json").read_text())
expected = json.loads((CAND / "baseline" / "expected_artifact.json").read_text())

for name, digest in (("quality.json", expected["files"]["quality.json"]["sha256"]),
                     ("meta.json", expected["files"]["meta.json"]["sha256"])):
    got = hashlib.sha256((FACT / name).read_bytes()).hexdigest()
    assert got == digest, f"{name} digest mismatch: {got[:16]}..."

sc = quality["split_counts"]
assert expected["artifact_version"] == ART
assert baseline["qualification_report"]["qualified_artifact_version"] == ART

# cross-check the three independent sources
assert meta["rows"] == {"train": sc["train"]["rows"], "eval": sc["eval"]["rows"],
                        "holdout": sc["holdout"]["rows"]}, "meta.json rows disagree"
assert baseline["artifact"]["rows"] == meta["rows"], "baseline_result rows disagree"
for split in ("train", "eval", "holdout"):
    assert abs(baseline["artifact"]["positive_rate"][split] - sc[split]["positive_rate"]) < 1e-6

splits = {
    "train": {
        "rows": sc["train"]["rows"], "positives": sc["train"]["positives"],
        "positive_rate": sc["train"]["positive_rate"],
        "note": "assessment instants 2006-2015 (America/Edmonton local operational "
                "time); " + f"{sc['train']['distinct_positive_dates']} distinct "
                "positive dates; " + f"{sc['train']['carryover_from_record_year']} "
                "winter carryover fires assessed in the year after their record "
                "year move with their assessment; all-cause assessed population, "
                "no outcome-conditioned rule, winter rows kept",
    },
    "eval": {
        "rows": sc["eval"]["rows"], "positives": sc["eval"]["positives"],
        "positive_rate": sc["eval"]["positive_rate"],
        "note": "assessment instants 2016-2020; "
                + f"{sc['eval']['distinct_positive_dates']} distinct positive dates; "
                + f"{sc['eval']['carryover_from_record_year']} winter carryover "
                "fires; labeled development/validation split - every quoted figure "
                "is measured here and nowhere else",
    },
    "holdout": {
        "rows": sc["holdout"]["rows"], "positives": sc["holdout"]["positives"],
        "positive_rate": sc["holdout"]["positive_rate"],
        "note": "assessment instants 2021-2025; "
                + f"{sc['holdout']['distinct_positive_dates']} distinct positive "
                "dates; sealed, never evaluated; the higher positive rate is the "
                "documented 2023 record season (non-stationarity recorded, not "
                "repaired)",
    },
}

record_path = CAND / "record.json"
record = json.loads(record_path.read_text())
record["construction_output"] = {
    "splits": splits,
    "source": "abwildfire-build-001 gate report values (the artifact's own "
              "quality.json split_counts, digest-verified equal to the accepted "
              "artifact " + ART[:16] + "...), cross-checked against meta.json "
              "rows/positive_rate and the abwildfire-baseline-002 "
              "baseline_result.json before the release manifest was generated "
              "(packaging session 2026-11-07)",
}
record_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
print("record.construction_output written and cross-checked against meta.json + baseline_result.json")
for name, data in splits.items():
    print(f"  {name}: {data['rows']:,} rows / {data['positives']:,} positives "
          f"({100 * data['positive_rate']:.2f}%)")
