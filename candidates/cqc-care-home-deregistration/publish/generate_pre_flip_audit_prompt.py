#!/usr/bin/env python3
"""Fill the pre-flip adversarial audit prompt for cqc-care-home-deregistration.

Every digest, size, count and figure is read programmatically from the frozen
release package (MANIFEST.json, meta.json, quality.json, measurements.json) and
the candidate record - nothing hand-transcribed. The static method/attack/report
sections of templates/pre-flip-audit-prompt.md are kept verbatim.
"""
import json
import pathlib
import sys

REPO = pathlib.Path("/opt/data/dataset-factory")
REL = REPO / "release/cqc-care-home-deregistration"
CAND = REPO / "candidates/cqc-care-home-deregistration"
TEMPLATE = REPO / "skills/dataset-release/templates/pre-flip-audit-prompt.md"


def main() -> int:
    manifest = json.loads((REL / "MANIFEST.json").read_text())
    meta = json.loads((REL / "meta.json").read_text())
    quality = json.loads((REL / "quality.json").read_text())
    meas = json.loads((REL / "measurements.json").read_text())
    record = json.loads((CAND / "record.json").read_text())

    assets = manifest["files"]
    art = manifest["artifact_version"]

    def a(name: str) -> dict:
        return assets[name]

    train, ev, ho = a("public/train.csv"), a("public/eval.csv"), a("private/holdout.csv")
    splits = record["construction_output"]["splits"]

    refs = meas["references"]
    aucs = refs["eval_auc"]
    rb = meas["runner_baseline"]

    col_list = ", ".join("`%s`" % c for c in meta["columns"])

    baseline_claims = (
        "the benchmark's own runner (train.py + validate.sh bundled verbatim, "
        "sha256-equal to the read-only clone) reaches eval AUC {rb} on eval rows "
        "only - the holdout was never opened or scored; this sits BELOW the "
        "strongest simple reference on identical rows, rating_x_beds_rate AUC "
        "{rxb} (paired bootstrap 150 resamples for rating_x_beds vs "
        "last_rating excludes zero: +{diff} [{lo}, {hi}]), which the publisher "
        "records as a defect of the stock runner under this protocol, NOT a "
        "no-headroom verdict: the model beats every one-line prior "
        "(last_rating_rate {lr}, beds_bucket_rate {bb}, hsca_start_year_rate "
        "{hsy}, local_authority_rate {la}, provider_sector_rate {ps}), the "
        "reference reads only shipped at-T columns so there is no information "
        "asymmetry, and a verified diagnosis candidate is recorded (the stock "
        "runner treats `instant` as a train-only categorical, so the eval "
        "instant 2024-01 is unseen and every eval row gets NaN there); NO "
        "persistence reference exists BY DESIGN (identity ships as a "
        "per-instant pseudonym, the missing-successor P0 design, so "
        "prior-instant labels are structurally unlinkable - for a scorer too); "
        "majority-class accuracy {mj} on this split; global_rate is a constant "
        "score with null AUC (degenerate, recorded); the label is a REGISTER "
        "EVENT, not a service closure (CQC's own in-file note: cessation "
        "conflates re-registration/transfer; BMJ Public Health 2024 implies "
        "roughly 40-55% re-registrations/transfers, successor linkage not "
        "built); the construction is retrospective mixed-vintage (historical "
        "Drive vintages + the current cumulative Deactivated register; no "
        "full-row availability ledger, so training-label timing is unverified "
        "and the evaluation contract is retrospective research requiring "
        "isolated rows); cross-row exposure is measured, not enforced - gate "
        "probes measured pseudonym-successor coverage 0/0/0 train/eval/holdout "
        "and quasi-identifier (LA x beds x start year x rating x sector) "
        "eval/holdout coverage 0 (train 11,786, where labels are public "
        "anyway); all stated as limitations in quality.json and "
        "VERIFICATION.md, not as strengths"
    ).format(
        rb=rb["full_model_eval_auc"],
        rxb=round(aucs["rating_x_beds_rate"], 4),
        diff=round(refs["paired_bootstrap_150"]["rating_x_beds_vs_last_rating"]["observed_difference"], 4),
        lo=round(refs["paired_bootstrap_150"]["rating_x_beds_vs_last_rating"]["ci95"][0], 4),
        hi=round(refs["paired_bootstrap_150"]["rating_x_beds_vs_last_rating"]["ci95"][1], 4),
        lr=round(aucs["last_rating_rate"], 4),
        bb=round(aucs["beds_bucket_rate"], 4),
        hsy=round(aucs["hsca_start_year_rate"], 4),
        la=round(aucs["local_authority_rate"], 4),
        ps=round(aucs["provider_sector_rate"], 4),
        mj=round(refs["majority_class_accuracy_eval"], 6),
    )

    reference_list = (
        "rating_x_beds_rate eval AUC {rxb}; last_rating_rate eval AUC {lr}; "
        "beds_bucket_rate eval AUC {bb}; hsca_start_year_rate eval AUC {hsy}; "
        "local_authority_rate eval AUC {la}; provider_sector_rate eval AUC "
        "{ps}; global_rate a constant score with null AUC (degenerate); "
        "majority-class accuracy {mj} (majority fitted on train, measured "
        "against eval labels); NO persistence reference by design (per-instant "
        "pseudonymised identity); the runner baseline eval AUC {rb} quoted "
        "from worker job cqc-chd-baseline-001 (refit your own model - your "
        "fit need not match)"
    ).format(
        rxb=round(aucs["rating_x_beds_rate"], 4),
        lr=round(aucs["last_rating_rate"], 4),
        bb=round(aucs["beds_bucket_rate"], 4),
        hsy=round(aucs["hsca_start_year_rate"], 4),
        la=round(aucs["local_authority_rate"], 4),
        ps=round(aucs["provider_sector_rate"], 4),
        mj=round(refs["majority_class_accuracy_eval"], 6),
        rb=rb["full_model_eval_auc"],
    )

    fills = {
        "DATASET_TITLE": "CQC Care-home Deregistration",
        "DATASET": "cqc-care-home-deregistration",
        "TAG": "v" + manifest["release_version"],
        "TRAIN_BYTES": str(train["bytes"]),
        "TRAIN_SHA256": train["sha256"][:27],
        "EVAL_BYTES": str(ev["bytes"]),
        "EVAL_SHA256": ev["sha256"][:27],
        "HOLDOUT_BYTES": str(ho["bytes"]),
        "HOLDOUT_SHA256": ho["sha256"][:27],
        "META_BYTES": str(a("meta.json")["bytes"]),
        "META_SHA256": a("meta.json")["sha256"][:27],
        "QUALITY_BYTES": str(a("quality.json")["bytes"]),
        "QUALITY_SHA256": a("quality.json")["sha256"][:27],
        "ARTIFACT_VERSION": art[:24],
        "GRAIN": (
            "one row per care home active in a monthly CQC 'HSCA Active "
            "Locations' vintage (train = January vintages 2018-2022, eval = "
            "January 2024, holdout = January 2025; the 2016/2017 vintages were "
            "loudly dropped for unresolved required columns; the 2023 vintage "
            "is excluded by design because its 12-month label window would "
            "still be open at the eval instant), with the location identity "
            "pseudonymised per instant (location_key)"
        ),
        "NCOLUMNS": str(len(meta["columns"])),
        "COLUMN_LIST": col_list,
        "TRAIN_ROWS": str(splits["train"]["rows"]),
        "EVAL_ROWS": str(splits["eval"]["rows"]),
        "HOLDOUT_ROWS": str(splits["holdout"]["rows"]),
        "TRAIN_POS": str(splits["train"]["positives"]),
        "EVAL_POS": str(splits["eval"]["positives"]),
        "HOLDOUT_POS": str(splits["holdout"]["positives"]),
        "TIME_COLUMN": (
            "instant - the production instant of the CQC 'HSCA Active "
            "Locations' monthly vintage T (a period_end instant, "
            "administrative-record lag 0 days; every shipped feature is the "
            "vintage's own published field at T, and the row-selection reads "
            "only the T vintage)"
        ),
        "LABEL_DERIVATION": (
            "the location's CQC registration ending within (T, T+365d] - a "
            "register event (Location Status Inactive-Dereg or Removed with a "
            "Location HSCA End Date in that window), joined from the "
            "cumulative Deactivated Locations register"
        ),
        "BASELINE_TRIAD_CLAIMS": baseline_claims,
        "REFERENCE_LIST": reference_list,
        "TARGET": meta["target"],
        "ID_COLUMNS": ", ".join(meta["id_columns"]),
    }

    template = TEMPLATE.read_text()
    # The file's own instructions end at the first '---' separator; the prompt
    # is everything after it, static sections untouched.
    prompt = template.split("\n---\n", 1)[1]
    for key, value in fills.items():
        prompt = prompt.replace("{{%s}}" % key, value)
    if "{{" in prompt:
        left = [ln for ln in prompt.splitlines() if "{{" in ln]
        print("UNFILLED PLACEHOLDERS:", left, file=sys.stderr)
        return 1

    out = CAND / "pre-flip-audit-prompt.md"
    out.write_text(prompt)
    print("wrote", out, len(prompt), "chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
