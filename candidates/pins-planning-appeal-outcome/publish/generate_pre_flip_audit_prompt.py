#!/usr/bin/env python3
"""Fill the pre-flip adversarial audit prompt for pins-planning-appeal-outcome.

Every digest, size, count and figure is read programmatically from the frozen
release package (MANIFEST.json, meta.json, quality.json, measurements.json) and
the candidate record - nothing hand-transcribed. The static method/attack/report
sections of templates/pre-flip-audit-prompt.md are kept verbatim.
"""
import json
import pathlib
import sys

REPO = pathlib.Path("/opt/data/dataset-factory")
REL = REPO / "release/pins-planning-appeal-outcome"
CAND = REPO / "candidates/pins-planning-appeal-outcome"
TEMPLATE = REPO / "skills/dataset-release/templates/pre-flip-audit-prompt.md"


def main() -> int:
    manifest = json.loads((REL / "MANIFEST.json").read_text())
    meta = json.loads((REL / "meta.json").read_text())
    quality = json.loads((REL / "quality.json").read_text())
    meas = json.loads((REL / "measurements.json").read_text())
    record = json.loads((CAND / "record.json").read_text())

    assets = manifest["assets"]
    art = manifest["artifact_version"]

    def a(name: str) -> dict:
        return assets[name]

    train, ev, ho = a("public/train.csv"), a("public/eval.csv"), a("private/holdout.csv")
    splits = record["artifacts"][0]["splits"]

    refs = meas["references"]
    aucs = refs["aucs"]
    briers = refs["briers"]
    rb = meas["runner_baseline"]

    col_list = ", ".join("`%s`" % c for c in meta["columns"])

    baseline_claims = (
        "the benchmark's own runner (train.py + validate.sh bundled verbatim, "
        "sha256-equal to the read-only clone) reaches eval AUC {rb} on eval rows only - "
        "the holdout was never opened or scored; the simple references on the same "
        "{rows} eval rows are procedure_type_rate AUC {pt} (Brier {ptb}), "
        "lpa_hist_rate AUC {lh} (Brier {lhb}), persistence_last_outcome AUC {pe} "
        "(Brier {peb}); majority-class accuracy {mj} on this split; the "
        "calendar-identity control collapsed exactly onto lpa_hist_rate (eval "
        "validation years 2020/2021 have no train-era valid-year support, so every "
        "eval row fell back to its LPA's train rate - a degenerate control, recorded, "
        "never independent confirmation); year_rate and global_rate are constant "
        "scores with null AUC (degenerate, recorded); per-validation-year eval AUCs "
        "are reported (2020 and 2021 separately) and reference differences carry an "
        "LPA-clustered bootstrap (resamples 150); the population is decided-cases-only "
        "by publisher design, the vintage is the single current-snapshot 2026-10-22 "
        "edition, and split-label timing is declared unverified - all stated as "
        "limitations in quality.json and VERIFICATION.md, not as strengths"
    ).format(
        rb=rb["eval_auc_from_train_py"],
        rows=refs["eval_rows"],
        pt=round(aucs["procedure_type_rate"], 4),
        ptb=round(briers["procedure_type_rate"], 6),
        lh=round(aucs["lpa_hist_rate"], 4),
        lhb=round(briers["lpa_hist_rate"], 6),
        pe=round(aucs["persistence_last_outcome"], 4),
        peb=round(briers["persistence_last_outcome"], 6),
        mj=round(refs["majority_class_accuracy_this_split"], 6),
    )

    reference_list = (
        "procedure_type_rate eval AUC {pt} and Brier {ptb}; lpa_hist_rate eval AUC "
        "{lh} and Brier {lhb}; persistence_last_outcome eval AUC {pe} and Brier "
        "{peb}; majority-class accuracy {mj} (majority fitted on train, measured "
        "against eval labels); per-validation-year eval AUCs (2020: rows {r20} "
        "positives {p20}, 2021: rows {r21} positives {p21}); the runner baseline "
        "eval AUC {rb} quoted from worker job pins-planning-baseline-002 "
        "(refit your own model - your fit need not match)"
    ).format(
        pt=round(aucs["procedure_type_rate"], 4),
        ptb=round(briers["procedure_type_rate"], 6),
        lh=round(aucs["lpa_hist_rate"], 4),
        lhb=round(briers["lpa_hist_rate"], 6),
        pe=round(aucs["persistence_last_outcome"], 4),
        peb=round(briers["persistence_last_outcome"], 6),
        mj=round(refs["majority_class_accuracy_this_split"], 6),
        r20=refs["per_validation_year_eval"]["2020"]["rows"],
        p20=refs["per_validation_year_eval"]["2020"]["positives"],
        r21=refs["per_validation_year_eval"]["2021"]["rows"],
        p21=refs["per_validation_year_eval"]["2021"]["positives"],
        rb=rb["eval_auc_from_train_py"],
    )

    fills = {
        "DATASET_TITLE": "UK Planning Appeal Outcome",
        "DATASET": "pins-planning-appeal-outcome",
        "TAG": manifest["release_tag"],
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
            "one row per decided s78_core planning-permission-family appeal (PINS "
            "casework type 'Planning Appeal' or 'Householder (HAS)'), validated "
            "2012-06-01..2026-08-21, cross-file deduplicated (3,110 counted "
            "duplicates) and restricted to binary decisions in {Allowed, Dismissed}"
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
            "valid_date - the appeal's PINS validation instant (an event_time "
            "instant; every feature field is recorded at or before registration/"
            "validation from the appeal submission, an administrative record)"
        ),
        "LABEL_DERIVATION": (
            "the final PINS decision (publisher Decision field, Allowed vs "
            "Dismissed, issued on the Decision Date 91-365 days after validation "
            "for 74% of measured cases) - an event"
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
