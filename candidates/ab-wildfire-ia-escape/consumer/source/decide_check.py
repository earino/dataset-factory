#!/usr/bin/env python3
"""Recompute the pre-registered deciding check on the released bytes.

measurements.json records, under "comparison", the pre-registered deciding
check the baseline job computed: the runner-contract model against every
triad member on the identical eval rows. This script recomputes it from the
released artifact, never reimplementing anything:

  * the model's per-row eval scores come from the shipped baseline/train.py
    through the same predict_proba path the runner's own validate.py uses -
    the runner is not modified;
  * every triad definition (persistence analogue = assessment_hectares,
    calendar/identity prior from train) and the day-cluster paired bootstrap
    come from the shipped code/score.py (fixed-seed LCG, deterministic);
  * the single-vector day-cluster AUC CI mirrors score.bootstrap_diff's LCG
    exactly as the baseline job's report.py did (seed 12345);
  * every expected figure is read from the shipped measurements.json, never
    restated by hand (the model AUC comes from the comparison ladder).

Headroom is demonstrated ONLY if the model beats both non-degenerate members
with a CI excluding zero in its favour and its own AUC CI lies entirely
above 0.5 (the degenerate majority constant). The private holdout is never
read. Usage:

    decide_check.py <repo> <task> <workdir> <out-dir> <measurements.json>
"""
import json
import os
import runpy
import sys
from collections import defaultdict
from pathlib import Path

repo, task, work, out = (Path(a) for a in sys.argv[1:5])
measurements = json.loads(Path(sys.argv[5]).read_text())
comparison = measurements["comparison"]
triad = measurements["references"]["construction_triad"]
splits = measurements["splits"]
model_auc_recorded = float(comparison["ladder"][0][1])   # "0.9554"

sys.path.insert(0, str(repo / "code"))
import score  # noqa: E402  (the shipped reference definitions)

import pandas as pd  # noqa: E402

BOOTSTRAP_RESAMPLES = 500


def cluster_bootstrap_auc(labels, scores, clusters, resamples=BOOTSTRAP_RESAMPLES):
    """Day-cluster bootstrap of a single score vector's AUC.

    Mirrors score.bootstrap_diff's fixed-seed LCG (seed 12345) so the interval
    is deterministic and reproducible from the artifact alone - the same
    helper the baseline job's report.py used.
    """
    by_cluster = defaultdict(list)
    for label, value, cluster in zip(labels, scores, clusters):
        by_cluster[cluster].append((label, value))
    keys = sorted(by_cluster)
    aucs = []
    seed = 12345
    for _ in range(resamples):
        seed = (seed * 1103515245 + 12345) % (2 ** 31)
        sampled = []
        for _ in range(len(keys)):
            seed = (seed * 1103515245 + 12345) % (2 ** 31)
            sampled.extend(by_cluster[keys[seed % len(keys)]])
        value = score.auc([r[0] for r in sampled], [r[1] for r in sampled])
        if value is not None:
            aucs.append(value)
    if not aucs:
        return None
    aucs.sort()
    return {"resamples": len(aucs),
            "auc_ci95_low": round(aucs[min(int(0.025 * len(aucs)), len(aucs) - 1)], 4),
            "auc_ci95_high": round(aucs[min(int(0.975 * len(aucs)), len(aucs) - 1)], 4)}


def main() -> int:
    train_rows = score.read_rows(task / "public" / "train.csv")
    eval_rows = score.read_rows(task / "public" / "eval.csv")
    train_labels = [int(r[score.TARGET] == "1") for r in train_rows]
    eval_labels = [int(r[score.TARGET] == "1") for r in eval_rows]

    os.chdir(work)
    namespace = runpy.run_path("train.py", run_name="__consumer_decide__")
    predict = namespace.get("predict_proba")
    if not callable(predict):
        raise SystemExit("train.py defines no callable predict_proba(df)")
    frame = pd.read_csv("data/eval.csv")
    model_scores = [float(v) for v in predict(frame.drop(columns=[score.TARGET]))]

    model_auc = score.auc(eval_labels, model_scores)
    persistence_scores = [score.fnum_or_none(r["assessment_hectares"]) for r in eval_rows]
    calendar_scorer = score.fit_calendar(train_rows)
    calendar_scores = [calendar_scorer(r) for r in eval_rows]
    cluster_keys = [r[score.CLUSTER_COLUMN] for r in eval_rows]

    persistence_boot = score.bootstrap_diff(eval_labels, model_scores,
                                            persistence_scores, cluster_keys)
    calendar_boot = score.bootstrap_diff(eval_labels, model_scores,
                                         calendar_scores, cluster_keys)
    model_auc_ci = cluster_bootstrap_auc(eval_labels, model_scores, cluster_keys)
    persistence_auc = score.auc(eval_labels, persistence_scores)
    calendar_auc = score.auc(eval_labels, calendar_scores)

    result = {
        "model_eval_auc": model_auc,
        "model_minus_persistence_ci": persistence_boot,
        "model_minus_calendar_ci": calendar_boot,
        "model_auc_ci": model_auc_ci,
        "member_aucs": {"persistence_assessment_hectares": persistence_auc,
                        "calendar_identity_only": calendar_auc},
        "eval_rows": len(eval_rows),
        "eval_distinct_positive_days": len(
            {row[score.CLUSTER_COLUMN] for row, label in zip(eval_rows, eval_labels)
             if label == 1}),
        "recorded": {
            "verdict": comparison["verdict"],
            "model_eval_auc": model_auc_recorded,
            "model_minus_persistence_ci": comparison["model_minus_persistence_ci"],
            "model_minus_calendar_ci": comparison["model_minus_calendar_ci"],
            "model_auc_ci": comparison["model_auc_ci"],
            "eval_rows": splits["eval"]["rows"],
            "eval_distinct_positive_days": splits["eval"]["distinct_positive_dates"],
        },
    }
    (out / "deciding_check.json").write_text(json.dumps(result, indent=1) + "\n")

    bad = []

    def near(got, want, tol, what):
        if got is None and want is None:
            return
        if got is None or want is None or abs(float(got) - float(want)) > tol:
            bad.append(f"{what}: recomputed {got} != recorded {want}")

    near(model_auc, model_auc_recorded, 5e-5, "model_eval_auc")
    for key in ("model_minus_persistence_ci", "model_minus_calendar_ci"):
        got, want = result[key], comparison[key]
        near(got.get("ci_low"), want["ci_low"], 1e-4, f"{key}.ci_low")
        near(got.get("ci_high"), want["ci_high"], 1e-4, f"{key}.ci_high")
        near(got.get("median"), want["median"], 1e-4, f"{key}.median")
        if got.get("resamples") != want["resamples"]:
            bad.append(f"{key}.resamples: recomputed {got.get('resamples')} "
                       f"!= recorded {want['resamples']}")
    got_ci, want_ci = model_auc_ci, comparison["model_auc_ci"]
    near(got_ci.get("auc_ci95_low"), want_ci["auc_ci95_low"], 1e-4, "model_auc_ci.auc_ci95_low")
    near(got_ci.get("auc_ci95_high"), want_ci["auc_ci95_high"], 1e-4, "model_auc_ci.auc_ci95_high")

    # the deciding check's member AUCs are the same references score.py
    # measured; cross-check them against the recorded construction triad
    near(persistence_auc, triad["persistence_assessment_hectares"]["auc"], 1e-9,
         "member_aucs.persistence_assessment_hectares")
    near(calendar_auc, triad["calendar_identity_only"]["auc"], 1e-9,
         "member_aucs.calendar_identity_only")

    if result["eval_rows"] != splits["eval"]["rows"]:
        bad.append(f"eval_rows: recomputed {result['eval_rows']} != recorded {splits['eval']['rows']}")
    if result["eval_distinct_positive_days"] != splits["eval"]["distinct_positive_dates"]:
        bad.append("eval_distinct_positive_days: recomputed "
                   f"{result['eval_distinct_positive_days']} != recorded "
                   f"{splits['eval']['distinct_positive_dates']}")

    beaten = (persistence_boot is not None and persistence_boot["ci_low"] > 0.0,
              calendar_boot is not None and calendar_boot["ci_low"] > 0.0,
              model_auc_ci is not None and model_auc_ci["auc_ci95_low"] > 0.5)
    verdict = "headroom_demonstrated" if all(beaten) else "triad_not_beaten"
    if verdict != comparison["verdict"]:
        bad.append(f"verdict: recomputed {verdict} != recorded {comparison['verdict']}")

    print(f"  model AUC {model_auc:.4f} (recorded {model_auc_recorded})")
    print(f"  model minus persistence: [{persistence_boot['ci_low']:.4f}, "
          f"{persistence_boot['ci_high']:.4f}] (recorded "
          f"[{comparison['model_minus_persistence_ci']['ci_low']}, "
          f"{comparison['model_minus_persistence_ci']['ci_high']}])")
    print(f"  model minus calendar: [{calendar_boot['ci_low']:.4f}, "
          f"{calendar_boot['ci_high']:.4f}] (recorded "
          f"[{comparison['model_minus_calendar_ci']['ci_low']}, "
          f"{comparison['model_minus_calendar_ci']['ci_high']}])")
    print(f"  model AUC CI: [{model_auc_ci['auc_ci95_low']:.4f}, "
          f"{model_auc_ci['auc_ci95_high']:.4f}] (entirely above 0.5)")
    print(f"  verdict: {verdict}")
    if bad:
        print("DECIDING-CHECK MISMATCH:", *bad, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
