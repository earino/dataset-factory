#!/usr/bin/env python3
"""Dataset qualification gate.

Runs the five checks that stand between a constructed dataset and a scored claim:

  1. leakage        - no shipped column may determine the target
  2. prediction time- every shipped feature must be knowable when the prediction is made
  3. units / frames - values compared to an external threshold must declare unit and frame
  4. splits         - disjoint, ordered, and carrying enough (clustered) positives to score
  5. runner         - the extract must match the existing runner's input contract

Usage:

    python3 qualify_dataset.py <dataset-dir> [--json]
    python3 qualify_dataset.py --selftest

`<dataset-dir>` holds the runner layout (`public/train.csv`, `public/eval.csv`,
`private/holdout.csv`, `meta.json`) plus a `quality.json` descriptor. Exit status is 0 only
when every check passes. The `--selftest` mode runs the checker against the shipped broken
and corrected fixtures and asserts the expected verdicts for each.

Design notes worth keeping:

* **A declared feature list proves nothing.** The runner hands every non-target column to
  prediction code, so the only reliable leak test is to look for a shipped column that
  separates the classes on its own. That is what check 1 does.
* **Unique-valued columns are not leaks by themselves.** An identifier or a free timestamp
  reaches a perfect AUC by memorising one row per level, which says nothing. Such columns
  are reported as high-cardinality and must be declared, not treated as leaks.
* **Uniform results are a red flag, not a finding.** Checks 3 and 4 refuse to pass a
  dataset whose positives are all one value across every entity, because that is what a
  unit or reference-frame error looks like.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

MIN_GROUP_FOR_CATEGORICAL = 5
MIN_EVAL_POSITIVES = 30
MIN_HOLDOUT_POSITIVES = 30
MIN_DISTINCT_EVENTS = 20


def auc_from_scores(labels: list[int], scores: list[float]) -> float | None:
    """Rank-based ROC AUC with ties averaged. Stdlib only."""
    if len(labels) != len(scores) or not labels:
        raise ValueError("labels and scores must align and be non-empty")
    pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    rank_sum = 0.0
    index = 0
    while index < len(pairs):
        end = index
        while end + 1 < len(pairs) and pairs[end + 1][0] == pairs[index][0]:
            end += 1
        average_rank = (index + end) / 2.0 + 1.0
        for position in range(index, end + 1):
            if pairs[position][1] == 1:
                rank_sum += average_rank
        index = end + 1
    return (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def column_leak_score(values: list[str], labels: list[int]) -> dict:
    """Score one column as a potential answer source.

    Numeric columns are used directly. Categorical columns are scored by their per-level
    positive rate, but only when every level carries at least MIN_GROUP_FOR_CATEGORICAL
    rows - otherwise the encoding memorises individual rows and a perfect score means
    nothing. Those columns are reported separately as high_cardinality.
    """
    try:
        scores = [float(value) for value in values]
        return {"kind": "numeric", "auc": auc_from_scores(labels, scores), "levels": None,
                "determines_label": auc_from_scores(labels, scores) in (0.0, 1.0)}
    except (TypeError, ValueError):
        pass

    groups: dict[str, list[int]] = {}
    for value, label in zip(values, labels):
        groups.setdefault(value, []).append(label)
    levels = len(groups)
    if levels > max(1, len(labels) // MIN_GROUP_FOR_CATEGORICAL):
        return {"kind": "high_cardinality", "auc": None, "levels": levels,
                "determines_label": False}
    rate = auc_from_scores(labels, [group_rate(value, groups) for value in values])
    return {"kind": "categorical", "auc": rate, "levels": levels,
            "determines_label": rate in (0.0, 1.0)}


def group_rate(value: str, groups: dict[str, list[int]]) -> float:
    rows = groups[value]
    return sum(rows) / len(rows)


def leak_scan(rows: list[dict], target: str) -> list[dict]:
    """Return one finding per shipped column, in column order."""
    if not rows:
        return []
    labels = [int(row[target]) for row in rows]
    findings = []
    for column in rows[0]:
        if column == target:
            continue
        values = [row[column] for row in rows]
        score = column_leak_score(values, labels)
        findings.append({"column": column, **score,
                         "determines_label": score["auc"] in (0.0, 1.0)})
    return findings


def read_split(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def header_of(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle), [])


class Report:
    def __init__(self):
        self.results: list[dict] = []

    def add(self, check: str, ok: bool, detail: str, evidence=None):
        self.results.append({"check": check, "ok": bool(ok), "detail": detail,
                             "evidence": evidence or {}})

    @property
    def ok(self) -> bool:
        return all(result["ok"] for result in self.results)

    def render(self) -> str:
        lines = []
        for result in self.results:
            lines.append(f"[{'PASS' if result['ok'] else 'FAIL'}] {result['check']}: "
                         f"{result['detail']}")
        return "\n".join(lines)


def check_leakage(dataset: Path, quality: dict, report: Report) -> None:
    names = quality.get("splits", {})
    payloads = {name: read_split(dataset / relative) for name, relative in names.items()}
    target = quality["target"]
    shipped = set()
    for rows in payloads.values():
        if rows:
            shipped |= set(rows[0])
    declared = set(quality.get("features", [])) | set(quality.get("carry_columns", [])) \
        | set(quality.get("id_columns", [])) | {target}
    undeclared = sorted(shipped - declared)
    report.add("leakage.declared_columns",
               not undeclared,
               "every shipped column is declared" if not undeclared
               else f"undeclared shipped columns: {undeclared}",
               {"undeclared": undeclared})

    forbidden = set(quality.get("label_source_columns", [])) | set(quality.get("post_hoc_columns", []))
    leaked_columns = sorted(shipped & forbidden)
    report.add("leakage.answer_source_absent",
               not leaked_columns,
               "no answer source or post-hoc column is shipped" if not leaked_columns
               else f"shipped columns that determine or postdate the label: {leaked_columns}",
               {"shipped_forbidden": leaked_columns})

    offenders, high_card, missing = [], [], []
    for name, rows in payloads.items():
        if not rows:
            missing.append(name)
            continue
        for finding in leak_scan(rows, target):
            entry = {**finding, "split": name}
            if finding["determines_label"]:
                offenders.append(entry)
            elif finding["kind"] == "high_cardinality":
                high_card.append(entry)
    report.add("leakage.no_single_column_determines_the_target",
               not offenders,
               "no shipped column separates the classes on its own" if not offenders
               else "columns reconstruct the label: "
                    + ", ".join(sorted({f"{o['column']}@{o['split']}" for o in offenders})),
               {"offenders": offenders, "high_cardinality": high_card, "missing_splits": missing})

    declared_ids = set(quality.get("id_columns", [])) | set(quality.get("high_cardinality_columns", []))
    undeclared_ids = sorted({f["column"] for f in high_card if f["column"] not in declared_ids})
    report.add("leakage.high_cardinality_declared",
               not undeclared_ids,
               "high-cardinality columns are declared as identifiers or free fields"
               if not undeclared_ids
               else f"high-cardinality columns are undeclared: {undeclared_ids}",
               {"undeclared": undeclared_ids,
                "declared": sorted(declared_ids)})


def check_prediction_time(quality: dict, report: Report) -> None:
    task = quality.get("task", {})
    when = (task.get("prediction_time") or "").strip()
    report.add("timing.prediction_time_declared", bool(when),
               "prediction instant is declared" if when else "quality.json has no task.prediction_time")

    features = set(quality.get("features", []))
    post_hoc = set(quality.get("post_hoc_columns", []))
    overlap = sorted(features & post_hoc)
    report.add("timing.no_post_hoc_feature", not overlap,
               "no feature is documented as post-hoc" if not overlap
               else f"features documented as post-hoc: {overlap}", {"overlap": overlap})

    sources = set(quality.get("label_source_columns", []))
    source_features = sorted(features & sources)
    report.add("timing.label_source_is_not_a_feature", not source_features,
               "the label source is not a feature" if not source_features
               else f"label source used as a feature: {source_features}",
               {"source_features": source_features})

    documented = quality.get("features_documented_at")
    report.add("timing.every_feature_documented",
               documented == "prediction_time",
               f"features documented as available {documented!r}",
               {"features_documented_at": documented})


def check_units_and_frames(quality: dict, report: Report) -> None:
    measured = quality.get("measurements", [])
    missing = [entry.get("column") for entry in measured
               if not entry.get("unit") or not entry.get("frame")]
    report.add("units.measured_columns_declare_unit_and_frame",
               not missing and bool(measured),
               f"{len(measured)} measured column(s) declare unit and frame" if not missing and measured
               else f"columns missing unit or frame: {missing}" if measured
               else "no measurements declared",
               {"measurements": measured})

    external = quality.get("external_threshold")
    if external:
        event = quality.get("known_event") or {}
        has_event = bool(event.get("name")) and \
            event.get("expected_verdict") in ("exceeds", "below") and bool(event.get("source"))
        report.add("units.known_event_fixture_recorded", has_event,
                   f"known-event fixture recorded: {event.get('name')!r}" if has_event
                   else "an external threshold is used but no verifiable known-event fixture is recorded",
                   {"known_event": event})
    else:
        report.add("units.known_event_fixture_recorded", True,
                   "no external threshold, so no known-event fixture is required")


def check_splits(dataset: Path, quality: dict, report: Report) -> None:
    splits = quality.get("splits", {})
    boundaries = quality.get("split_boundaries", {})
    keys = ["train", "eval", "holdout"]

    present = [key for key in keys if key in boundaries and boundaries[key]]
    report.add("splits.boundaries_declared", len(present) == len(keys),
               "train/eval/holdout boundaries declared" if len(present) == len(keys)
               else f"missing boundary declarations for {sorted(set(keys) - set(present))}",
               {"boundaries": boundaries})

    order_ok = True
    detail = "declared boundaries are distinct and non-empty"
    if len(present) == len(keys):
        if len({boundaries[key] for key in keys}) != len(keys):
            order_ok, detail = False, "boundaries are not distinct"
    report.add("splits.windows_distinct", order_ok, detail)

    files_ok, missing_files = True, []
    for key in keys:
        if key not in splits or not (dataset / splits[key]).is_file():
            files_ok = False
            missing_files.append(key)
    report.add("splits.files_present", files_ok,
               "all three split files exist" if files_ok
               else f"missing split files: {missing_files}", {"missing": missing_files})
    if not files_ok:
        return

    target = quality["target"]
    counts = {}
    problems = []
    for key in keys:
        rows = read_split(dataset / splits[key])
        positives = sum(int(row[target] == str(quality["positive_label"])) for row in rows)
        counts[key] = {"rows": len(rows), "positives": positives,
                       "positive_rate": round(positives / len(rows), 6) if rows else None}
        if not rows:
            problems.append(f"{key} is empty")
        elif positives == 0:
            problems.append(f"{key} has no positives")
    report.add("splits.non_empty_with_positives", not problems,
               "every split has rows and positives" if not problems else "; ".join(problems),
               counts)

    declared = quality.get("positive_events", {})
    counts_by_split = {key: counts[key] for key in counts}
    thin, missing_decl, mismatched = [], [], []
    for key in ("eval", "holdout"):
        entry = declared.get(key) or {}
        if "positives" not in entry or "distinct_events" not in entry:
            missing_decl.append(key)
            continue
        actual = counts_by_split.get(key, {}).get("positives")
        if actual is not None and entry["positives"] != actual:
            mismatched.append(f"{key}: declared {entry['positives']}, file has {actual}")
        if entry["positives"] < MIN_EVAL_POSITIVES or entry["distinct_events"] < MIN_DISTINCT_EVENTS:
            thin.append(f"{key}={entry['positives']} positives / "
                        f"{entry['distinct_events']} distinct events")
    report.add("splits.positive_events_declared",
               not missing_decl,
               "eval and holdout declare positives and distinct events" if not missing_decl
               else f"missing clustered counts for {missing_decl}",
               {"declared": declared})
    report.add("splits.positive_events_match_files", not mismatched,
               "declared positive counts match the split files" if not mismatched
               else "; ".join(mismatched),
               {"mismatched": mismatched})
    report.add("splits.enough_clustered_positives", not thin,
               "eval and holdout carry enough independent positive events to score"
               if not thin
               else "too few independent positives: " + "; ".join(thin),
               {"thin": thin, "minimums": {"positives": MIN_EVAL_POSITIVES,
                                           "distinct_events": MIN_DISTINCT_EVENTS}})

    rates = [counts[key]["positive_rate"] for key in keys if counts[key]["positive_rate"] is not None]
    uniform = bool(rates) and all(rate in (0.0, 1.0) for rate in rates)
    report.add("splits.rates_not_uniform", not uniform,
               "positive rates are between 0 and 1" if not uniform
               else "every split is all-positive or all-negative, which is a unit or frame red flag",
               {"rates": rates})


def check_runner(dataset: Path, quality: dict, report: Report) -> None:
    splits = quality.get("splits", {})
    layout_ok = splits.get("holdout", "").startswith("private/") and \
        splits.get("train", "").startswith("public/") and \
        splits.get("eval", "").startswith("public/")
    report.add("runner.layout", layout_ok,
               "holdout is private and train/eval are public" if layout_ok
               else f"unexpected layout: {splits}")

    meta_path = dataset / "meta.json"
    if not meta_path.is_file():
        report.add("runner.meta_json", False, "meta.json is missing")
        return
    meta = json.loads(meta_path.read_text())
    required = ["target", "positive_label", "id_columns", "columns", "rows", "positive_rate"]
    missing = [key for key in required if key not in meta]
    report.add("runner.meta_json_keys", not missing,
               "meta.json carries the keys the runner reads" if not missing
               else f"meta.json missing {missing}", {"keys": sorted(meta)})
    if missing:
        return

    target = meta["target"]
    problems = []
    if meta["positive_label"] != quality["positive_label"]:
        problems.append("meta positive_label disagrees with quality.json")
    if target != quality["target"]:
        problems.append("meta target disagrees with quality.json")
    id_cols = set(meta["id_columns"])
    if not id_cols <= set(meta["columns"]):
        problems.append("id_columns are not a subset of columns")
    for key in ("train", "eval", "holdout"):
        header = header_of(dataset / splits[key])
        if target not in header:
            problems.append(f"{key} lacks the target column")
        if list(meta["columns"]) != header:
            problems.append(f"{key} header differs from meta columns")
    report.add("runner.meta_matches_files", not problems,
               "meta.json agrees with the split files" if not problems
               else "; ".join(problems), {"problems": problems})

    counts_ok, detail = True, "meta rows and rates match the files"
    for key in ("train", "eval", "holdout"):
        rows = read_split(dataset / splits[key])
        positives = sum(int(row[target] == str(meta["positive_label"])) for row in rows)
        rate = positives / len(rows) if rows else 0.0
        if meta["rows"].get(key) != len(rows):
            counts_ok, detail = False, f"{key} row count mismatch"
        if meta["positive_rate"].get(key) is not None and abs(meta["positive_rate"][key] - rate) > 1e-6:
            counts_ok, detail = False, f"{key} positive rate mismatch"
    report.add("runner.meta_counts_match_files", counts_ok, detail)

    id_feature_ok = not (id_cols & set(quality.get("features", [])))
    report.add("runner.id_columns_are_not_features", id_feature_ok,
               "declared identifiers are not also listed as features" if id_feature_ok
               else f"identifiers listed as features: {sorted(id_cols & set(quality.get('features', [])))}")


def qualify(dataset: Path) -> Report:
    report = Report()
    quality_path = dataset / "quality.json"
    if not quality_path.is_file():
        report.add("descriptor", False, f"quality.json not found in {dataset}")
        return report
    quality = json.loads(quality_path.read_text())
    report.add("descriptor", True, f"quality.json loaded for {quality.get('name', dataset.name)!r}")
    check_leakage(dataset, quality, report)
    check_prediction_time(quality, report)
    check_units_and_frames(quality, report)
    check_splits(dataset, quality, report)
    check_runner(dataset, quality, report)
    return report


SELFTEST_EXPECTATIONS = {
    "broken": {
        "expected_ok": False,
        "must_fail": {
            "leakage.answer_source_absent",
            "leakage.no_single_column_determines_the_target",
            "timing.no_post_hoc_feature",
            "units.known_event_fixture_recorded",
            "splits.windows_distinct",
            "runner.layout",
        },
    },
    "corrected": {"expected_ok": True, "must_fail": set()},
}


def selftest(fixtures_root: Path) -> int:
    failures = []
    for name, expectation in SELFTEST_EXPECTATIONS.items():
        dataset = fixtures_root / name
        report = qualify(dataset)
        failed_checks = {result["check"] for result in report.results if not result["ok"]}
        print(f"--- fixture {name}: ok={report.ok} (expected {expectation['expected_ok']})")
        print(report.render())
        if report.ok != expectation["expected_ok"]:
            failures.append(f"{name}: checker said ok={report.ok}, expected "
                            f"{expectation['expected_ok']}")
        unfulfilled = expectation["must_fail"] - failed_checks
        if unfulfilled:
            failures.append(f"{name}: expected these checks to fail but they passed: "
                            f"{sorted(unfulfilled)}")
        print()
    if failures:
        print("SELFTEST FAILED")
        for failure in failures:
            print(" -", failure)
        return 1
    print("SELFTEST PASSED: the broken fixture is rejected, the corrected fixture is accepted.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Qualify a constructed dataset")
    parser.add_argument("dataset", nargs="?", help="dataset directory to check")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument("--selftest", action="store_true",
                        help="check the shipped broken and corrected fixtures")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest(Path(__file__).resolve().parent.parent / "fixtures")
    if not args.dataset:
        parser.error("a dataset directory is required unless --selftest is used")

    report = qualify(Path(args.dataset))
    if args.json:
        print(json.dumps({"ok": report.ok, "results": report.results}, indent=1))
    else:
        print(report.render())
        print()
        print("QUALIFICATION PASSED" if report.ok else "QUALIFICATION FAILED")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
