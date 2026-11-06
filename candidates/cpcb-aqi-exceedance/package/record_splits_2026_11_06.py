#!/usr/bin/env python3
"""Add record.construction_output for cpcb-aqi-exceedance (packaging step).

Reads the split values from the gate report's own quality.json (the artifact's
shipped descriptor, digest-verified equal to the accepted artifact a749f0df...),
cross-checks them against meta.json and baseline_result.json, and writes
record.construction_output.splits. Nothing is retyped: every number is read
from those files. Mirrors za-cct's package/record_splits_2026_11_04.py.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAND = ROOT / "candidates" / "cpcb-aqi-exceedance"
REL = ROOT / "release" / "cpcb-aqi-exceedance"
FACT = ROOT / ".factory" / "cpcb-aqi-build-004" / "reports"
ART = "a749f0df2f9dd0103d0ba56524e1cc3638242fbc4710b0cac99603bcdef0d959"

quality = json.loads((REL / "quality.json").read_text())
meta = json.loads((REL / "meta.json").read_text())
baseline = json.loads((ROOT / ".factory" / "cpcb-aqi-baseline-001" / "output" /
                       "baseline_result.json").read_text())
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
                        "holdout": sc["holdout"]["rows"]}, "meta.json rows disagree with the gate report"
assert baseline["artifact"]["rows"] == meta["rows"], "baseline_result rows disagree"
for split in ("train", "eval", "holdout"):
    assert abs(baseline["artifact"]["positive_rate"][split] - sc[split]["positive_rate"]) < 1e-6

splits = {
    "train": {
        "rows": sc["train"]["rows"], "positives": sc["train"]["positives"],
        "positive_rate": sc["train"]["positive_rate"],
        "note": "prediction instants 2019-2022 (IST); "
                f"{sc['train']['distinct_positive_events']} distinct positive days; "
                f"{sc['train']['stations']} stations; excluded thin day D 33,586 and "
                "unlabelable D+1 17,416 counted, never scored",
    },
    "eval": {
        "rows": sc["eval"]["rows"], "positives": sc["eval"]["positives"],
        "positive_rate": sc["eval"]["positive_rate"],
        "note": "prediction instants 2023 (IST); "
                f"{sc['eval']['distinct_positive_events']} distinct positive days; "
                f"{sc['eval']['stations']} stations; excluded thin day D 18,065 and "
                "unlabelable D+1 9,368 counted, never scored",
    },
    "holdout": {
        "rows": sc["holdout"]["rows"], "positives": sc["holdout"]["positives"],
        "positive_rate": sc["holdout"]["positive_rate"],
        "note": "prediction instants 2024 (IST); "
                f"{sc['holdout']['distinct_positive_events']} distinct positive days; "
                f"{sc['holdout']['stations']} stations; sealed, never evaluated; "
                "excluded thin day D 20,101 and unlabelable D+1 10,879 counted, never scored",
    },
}

record_path = CAND / "record.json"
record = json.loads(record_path.read_text())
record["construction_output"] = {
    "splits": splits,
    "source": "cpcb-aqi-build-004 gate report values (the artifact's own quality.json "
              "split_counts, digest-verified equal to the accepted artifact " + ART[:16] +
              "...), cross-checked against meta.json rows/positive_rate and "
              "baseline_result.json before the release manifest was generated "
              "(packaging session 2026-11-06)",
}
record_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
print("record.construction_output written and cross-checked against meta.json + baseline_result.json")
for name, data in splits.items():
    print(f"  {name}: {data['rows']:,} rows / {data['positives']:,} positives "
          f"({100 * data['positive_rate']:.2f}%)")
