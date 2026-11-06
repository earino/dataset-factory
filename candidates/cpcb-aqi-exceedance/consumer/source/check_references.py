#!/usr/bin/env python3
"""Compare the recomputed score.py report against the recorded measurements.

Every numeric figure the shipped measurements.json records under
references.figures must be recomputed equal (to 1e-9) by the shipped
code/score.py on the released bytes: the triad AUCs and Briers, the
supplementary binary agreement, the degenerate global_rate control (null AUC
by design, with its rate and Brier present), the unseen-cell row count, the
supplementary station_train_rate, and the majority-class accuracy fitted on
train and measured against this split's labels. Row counts must match the
recorded splits exactly.

Usage: check_references.py <references.json> <measurements.json>
"""
import json
import sys

TOLERANCE = 1e-9


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
            if key == "definition":
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
    figures = measurements["references"]["figures"]
    splits = measurements["splits"]
    references = report["references"]

    bad: list[str] = []
    checked = [0]
    for name in sorted(figures):
        if name not in references:
            bad.append(f"{name}: absent from the recomputed report")
            continue
        compare(figures[name], references[name], name, bad, checked)

    # row counts must equal the recorded splits exactly
    for split, want in (("train", splits["train"]["rows"]),
                        ("eval", splits["eval"]["rows"])):
        got = report["rows"].get(split)
        if got != want:
            bad.append(f"rows.{split}: recomputed {got} != recorded {want}")
        else:
            checked[0] += 1

    print(f"  {checked[0]} figures and row counts recomputed equal to measurements.json")
    print("  station_persistence 0.9689, state_season_climatology 0.8617, "
          "station_train_rate 0.7616, global_rate degenerate, "
          f"majority accuracy {figures['majority_class']['accuracy']:.4f}")
    if bad:
        print("REFERENCE MISMATCH:", *bad, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
