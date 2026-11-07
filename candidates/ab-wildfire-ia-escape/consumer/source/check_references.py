#!/usr/bin/env python3
"""Compare the recomputed score.py report against the recorded measurements.

Every numeric figure the shipped measurements.json records must be recomputed
equal by the shipped code/score.py on the released bytes: the four triad
entries (majority constant - AUC, Brier and eval accuracy; persistence
analogue - AUC with the undefined-Brier note preserved as null; calendar
prior and full-feature logistic - AUC and Brier), the three deterministic
fixed-seed day-cluster bootstrap intervals with their medians and resample
counts, the per-year eval breakdown (rows, positives, positive rate and the
three per-year AUCs), and the split row counts and positive rates. Prose keys
are skipped; numbers must match to 1e-9 (the bootstrap is a fixed-seed LCG
and the logistic fit is deterministic, so recomputation is exact).

Usage: check_references.py <references.json> <measurements.json>
"""
import json
import sys
from pathlib import Path

TOLERANCE = 1e-9
PROSE = {"note", "brier_note", "definition", "protocol", "measured_on",
         "full_model_note", "accepted_report"}


def compare(want, got, path, bad, checked):
    if isinstance(want, bool) or isinstance(got, bool):
        if want != got:
            bad.append(f"{path}: recomputed {got} != recorded {want}")
        else:
            checked[0] += 1
        return
    if isinstance(want, (int, float)) or isinstance(got, (int, float)):
        if want is None or got is None:
            if want is not None or got is not None:
                bad.append(f"{path}: recomputed {got} != recorded {want}")
            else:
                checked[0] += 1
            return
        if abs(float(got) - float(want)) > TOLERANCE:
            bad.append(f"{path}: recomputed {got} != recorded {want}")
        else:
            checked[0] += 1
        return
    if isinstance(want, dict) and isinstance(got, dict):
        for key in want:
            if key in PROSE:
                continue  # prose, not a measurement
            if key not in got:
                bad.append(f"{path}.{key}: absent from the recomputed report")
            else:
                compare(want[key], got[key], f"{path}.{key}", bad, checked)
        return
    if want != got:
        bad.append(f"{path}: recomputed {got!r} != recorded {want!r}")


def main() -> int:
    report = json.loads(open(sys.argv[1]).read())
    measurements = json.loads(open(sys.argv[2]).read())
    # the recomputed artifact identity must still equal the released one
    manifest = json.loads((Path(sys.argv[2]).parent / "MANIFEST.json").read_text())
    recorded_triad = measurements["references"]["construction_triad"]
    recorded_years = measurements["references"]["eval_per_year"]
    splits = measurements["splits"]
    references = report["references"]
    bad: list[str] = []
    checked = [0]

    if not report.get("ok"):
        bad.append("report.ok: the recomputed report did not pass")
    if report.get("artifact_version") != manifest["artifact_version"]:
        bad.append(f"artifact_version: recomputed {report.get('artifact_version')} "
                   f"!= manifest {manifest['artifact_version']}")

    for name in sorted(recorded_triad):
        if name not in references:
            bad.append(f"{name}: absent from the recomputed report")
            continue
        compare(recorded_triad[name], references[name], name, bad, checked)

    # the per-year breakdown (structural-shift visibility) must reproduce too
    years = report.get("eval_per_year") or {}
    for year, want in sorted(recorded_years.items()):
        if year not in years:
            bad.append(f"eval_per_year.{year}: absent from the recomputed report")
            continue
        compare(want, years[year], f"eval_per_year.{year}", bad, checked)

    # row counts and positive rates must equal the recorded splits exactly
    for split in ("train", "eval"):
        want = splits[split]
        key_rows = f"{split}_rows"
        if report.get(key_rows) != want["rows"]:
            bad.append(f"{key_rows}: recomputed {report.get(key_rows)} != recorded {want['rows']}")
        else:
            checked[0] += 1
        key_rate = f"{split}_positive_rate"
        if abs(float(report.get(key_rate)) - float(want["positive_rate"])) > TOLERANCE:
            bad.append(f"{key_rate}: recomputed {report.get(key_rate)} "
                       f"!= recorded {want['positive_rate']}")
        else:
            checked[0] += 1

    print(f"  {checked[0]} figures and row counts recomputed equal to measurements.json")
    print(f"  persistence {references['persistence_assessment_hectares']['auc']:.4f}, "
          f"calendar {references['calendar_identity_only']['auc']:.4f}, "
          f"logistic {references['full_feature_logistic']['auc']:.4f}, "
          f"majority accuracy {references['majority_constant']['accuracy_on_eval']:.4f}")
    if bad:
        print("REFERENCE MISMATCH:", *bad, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
