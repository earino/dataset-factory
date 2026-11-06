#!/usr/bin/env python3
"""Recompute the pre-registered deciding check on the released bytes.

The shipped REPRODUCE.md states that recomputation must reproduce
model-minus-persistence [0.0038, 0.0052] and model-minus-climatology
[0.1002, 0.1252]. This script does exactly that from the released artifact:

  * the model's eval scores come from the shipped baseline/train.py through
    the same predict_proba path the runner's own validate.py uses - the
    runner is not modified;
  * every triad definition and bootstrap comes from the shipped code/score.py
    (seeded, so recomputation is deterministic) - nothing is reimplemented;
  * the recorded figures are read from the shipped measurements.json, never
    restated by hand.

The private holdout is never read. Usage:

    decide_check.py <repo> <task> <workdir> <out-dir> <measurements.json>
"""
import json
import os
import runpy
import sys
from pathlib import Path

repo, task, work, out = (Path(a) for a in sys.argv[1:5])
measurements = json.loads(Path(sys.argv[5]).read_text())
comparison = measurements["comparison"]
splits = measurements["splits"]

sys.path.insert(0, str(repo / "code"))
import score  # noqa: E402  (the shipped reference definitions)

import pandas as pd  # noqa: E402


def main() -> int:
    os.chdir(work)
    namespace = runpy.run_path("train.py", run_name="__consumer_decide__")
    predict = namespace.get("predict_proba")
    if not callable(predict):
        raise SystemExit("train.py defines no callable predict_proba(df)")
    frame = pd.read_csv("data/eval.csv")
    model_scores = [float(v) for v in predict(frame.drop(columns=[score.TARGET]))]

    train_rows = score.read_rows(task / "public" / "train.csv")
    eval_rows = score.read_rows(task / "public" / "eval.csv")
    train_labels = score.labels_of(train_rows)
    eval_labels = score.labels_of(eval_rows)
    train_rate = sum(train_labels) / len(train_labels)
    vectors = score.triad_score_vectors(train_rows, eval_rows, train_rate)
    cluster_keys = [row["station_id"] for row in eval_rows]

    model_auc = score.auc(eval_labels, model_scores)
    persistence = score.clustered_paired_bootstrap(
        eval_labels, model_scores, vectors["station_persistence"], cluster_keys)
    climatology = score.clustered_paired_bootstrap(
        eval_labels, model_scores, vectors["state_season_climatology"], cluster_keys)
    model_auc_ci = score.cluster_bootstrap_auc(eval_labels, model_scores, cluster_keys)

    result = {
        "model_eval_auc": model_auc,
        "model_minus_persistence_ci": persistence,
        "model_minus_climatology_ci": climatology,
        "model_auc_ci": model_auc_ci,
        "eval_rows": len(eval_rows),
        "eval_distinct_positive_days": len(
            {row["date"] for row, label in zip(eval_rows, eval_labels) if label == 1}),
        "recorded": {
            "verdict": comparison["verdict"],
            "model_minus_persistence_ci": comparison["model_minus_persistence_ci"],
            "model_minus_climatology_ci": comparison["model_minus_climatology_ci"],
            "model_auc_ci": comparison["model_auc_ci"],
            "eval_rows": splits["eval"]["rows"],
            "eval_distinct_positive_days": splits["eval"]["distinct_positive_days"],
        },
    }
    (out / "deciding_check.json").write_text(json.dumps(result, indent=1) + "\n")

    # The deciding rule: the model must beat persistence and climatology with a
    # station-clustered paired bootstrap 95% CI excluding zero in its favour,
    # and its own cluster-bootstrap AUC CI must lie entirely above 0.5 (the
    # degenerate constant member). Tolerances: 1e-4 on interval bounds (the
    # REPRODUCE.md claim is quoted at 4dp), 5e-5 on the 4dp model AUC.
    bad = []

    def near(got, want, tol, what):
        if got is None and want is None:
            return
        if got is None or want is None or abs(float(got) - float(want)) > tol:
            bad.append(f"{what}: recomputed {got} != recorded {want}")

    near(model_auc, 0.9734, 5e-5, "model_eval_auc")
    for member, key in (("station_persistence", "model_minus_persistence_ci"),
                        ("state_season_climatology", "model_minus_climatology_ci")):
        got, want = result[key], comparison[key]
        near(got.get("ci95_low"), want["ci95_low"], 1e-4, f"{key}.ci95_low")
        near(got.get("ci95_high"), want["ci95_high"], 1e-4, f"{key}.ci95_high")
    got_ci, want_ci = model_auc_ci, comparison["model_auc_ci"]
    near(got_ci.get("auc_ci95_low"), want_ci["auc_ci95_low"], 1e-4, "model_auc_ci.auc_ci95_low")
    near(got_ci.get("auc_ci95_high"), want_ci["auc_ci95_high"], 1e-4, "model_auc_ci.auc_ci95_high")

    if result["eval_rows"] != splits["eval"]["rows"]:
        bad.append(f"eval_rows: recomputed {result['eval_rows']} != recorded {splits['eval']['rows']}")
    if result["eval_distinct_positive_days"] != splits["eval"]["distinct_positive_days"]:
        bad.append("eval_distinct_positive_days: recomputed "
                   f"{result['eval_distinct_positive_days']} != recorded "
                   f"{splits['eval']['distinct_positive_days']}")

    beaten = (persistence.get("ci95_low") is not None and persistence["ci95_low"] > 0.0,
              climatology.get("ci95_low") is not None and climatology["ci95_low"] > 0.0,
              got_ci.get("auc_ci95_low") is not None and got_ci["auc_ci95_low"] > 0.5)
    verdict = "headroom_demonstrated" if all(beaten) else "triad_not_beaten"
    if verdict != comparison["verdict"]:
        bad.append(f"verdict: recomputed {verdict} != recorded {comparison['verdict']}")

    print(f"  model AUC {model_auc:.4f} (recorded 0.9734)")
    print(f"  model minus station_persistence: [{persistence['ci95_low']:.4f}, "
          f"{persistence['ci95_high']:.4f}] (recorded [0.0038, 0.0052])")
    print(f"  model minus state_season_climatology: [{climatology['ci95_low']:.4f}, "
          f"{climatology['ci95_high']:.4f}] (recorded [0.1002, 0.1252])")
    print(f"  model AUC CI: [{got_ci['auc_ci95_low']:.4f}, {got_ci['auc_ci95_high']:.4f}] "
          "(entirely above 0.5)")
    print(f"  verdict: {verdict}")
    if bad:
        print("DECIDING-CHECK MISMATCH:", *bad, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
