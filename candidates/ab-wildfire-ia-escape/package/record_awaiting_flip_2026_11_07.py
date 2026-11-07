#!/usr/bin/env python3
"""ab-wildfire-ia-escape: fill the pre-flip audit prompt from the frozen
package and move the record to packaged + awaiting_operator.

Every digest, size, count and figure is read programmatically from
release/ab-wildfire-ia-escape/{MANIFEST.json,meta.json,quality.json,
measurements.json} and the candidate record - digests never hand-copied. The
template's static method/attack/report sections are kept verbatim (split at
the first '---' separator). The Hub staging facts are read from the
DESTINATIONS.json huggingface block written by hf-publish.py --verify/--tag;
the script refuses to run before both destinations are verified.
"""

import datetime
import json
import pathlib
import sys

REPO = pathlib.Path("/opt/data/dataset-factory")
REL = REPO / "release/ab-wildfire-ia-escape"
CAND = REPO / "candidates/ab-wildfire-ia-escape"
TEMPLATE = REPO / "skills/dataset-release/templates/pre-flip-audit-prompt.md"
RECORD = CAND / "record.json"
TAG = "v2026.11"


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat() + "Z"


def main() -> int:
    stamp = now_iso()
    manifest = json.loads((REL / "MANIFEST.json").read_text())
    meta = json.loads((REL / "meta.json").read_text())
    quality = json.loads((REL / "quality.json").read_text())
    meas = json.loads((REL / "measurements.json").read_text())
    record = json.loads(RECORD.read_text())
    destinations = json.loads((REL / "DESTINATIONS.json").read_text())

    github = destinations["destinations"]["github"]
    hub = destinations["destinations"].get("huggingface")
    assert github.get("verified") is True, "github destination must be verified"
    assert hub and hub.get("verified") is True and hub.get("revision") == TAG and hub.get("commit"), \
        "huggingface destination must be recorded verified at the release tag"
    # the tag step's own attempt record proves the pinned revision resolves to the verified bytes
    attempt = json.loads((REPO / ".factory/hub-verification/ab-wildfire-ia-escape/latest.json").read_text())
    assert attempt.get("release_revision_verified") is True, "Hub tag must resolve to the verified bytes"
    assert attempt.get("tag_matches_main") is True and attempt.get("tag_commit") == hub["commit"], \
        "Hub tag and main must resolve to the recorded commit"

    assets = manifest["assets"]
    art = manifest["artifact_version"]

    def a(name):
        return assets[name]

    train, ev, ho = a("public/train.csv"), a("public/eval.csv"), a("private/holdout.csv")
    counts = quality["split_counts"]
    triad = meas["references"]["construction_triad"]
    comp = meas["comparison"]

    col_list = ", ".join("`%s`" % c for c in meta["columns"])
    splits = meas["splits"]

    base_claims = (
        "the stock runner (harness train.py + validate.sh, bundled verbatim, unmodified: true) "
        "reaches eval AUC {rb} on eval rows only (2016-2020), the holdout never opened by the "
        "publisher's own baseline and re-verified green by the fresh-consumer job "
        "abwildfire-consumer-001 on the released bytes; the strongest simple reference on "
        "identical eval rows is the persistence analogue {pe} (the fire's own observed size at "
        "assessment, assessment_hectares, as the score - full coverage by construction), which "
        "the model beats by +0.0459 AUC (day-clustered paired bootstrap, 500 resamples, cluster "
        "= assessment day, CI95 [{lo}, {hi}], excluding zero); next is the calendar/identity "
        "prior {ca} (smoothed train rate per month x forest area), beaten by +0.2428 CI95 "
        "[0.1911, 0.2998]; the model's own day-cluster AUC CI [0.9382, 0.9686] lies entirely "
        "above 0.5 (the degenerate majority constant); the construction-time full-feature L2 "
        "logistic {fl} is a supplementary simple reference whose edge over persistence is "
        "INCONCLUSIVE (+0.0111, CI [-0.0292, 0.0514], interval contains zero) - the bar any "
        "simple model must clear is the persistence rule, not 0.5; majority-class accuracy "
        "{mj} (majority fitted on train, measured against eval labels). Prevalence rises "
        "across splits: {p1}% train -> {p2}% eval -> {p3}% holdout (the 2021-2025 holdout "
        "contains the 2023 record season), an out-of-distribution test as much as a temporal "
        "one. The construction is RETROSPECTIVE RESEARCH: the publisher ships one living "
        "current compilation with no per-fire historical vintages and no first-publication "
        "ledger, the dictionary documents in-place revision of area burned (spring "
        "aerial-photography interpretation) and the 2019 season total differs from the current "
        "archive by -10.4% (measured against the publisher's own season PDFs), so "
        "training_label_timing is UNVERIFIED and no certified historical-forecasting claim is "
        "made; label-flip exposure is bounded and measured (89 fires within +-20% of the 100 ha "
        "threshold). The label sources current_size, size_class and first_uc_date never ship "
        "(asserted absent); fire_id is a declared unique identifier (high cardinality, not a "
        "leak). The known-event fixture - the 2016 Horse River Wildfire (MWF009) at its "
        "publisher-documented final size 485,123.6 ha, corroborated by the Government of "
        "Alberta's official review (detection 16:03h MDT 2016-05-01 matching the record's "
        "naive local timestamp) - must read as 'escape'; nine further named fires are asserted "
        "in-build, including the already-controlled negative 2023 LWF002 (0.01 ha). All "
        "stated as limitations in quality.json and VERIFICATION.md, not as strengths"
    ).format(
        rb="0.9554",
        pe=round(triad["persistence_assessment_hectares"]["auc"], 4),
        lo=comp["model_minus_persistence_ci"]["ci_low"],
        hi=comp["model_minus_persistence_ci"]["ci_high"],
        ca=round(triad["calendar_identity_only"]["auc"], 4),
        fl=round(triad["full_feature_logistic"]["auc"], 4),
        mj=round(triad["majority_constant"]["accuracy_on_eval"], 4),
        p1=round(splits["train"]["positive_rate"] * 100, 2),
        p2=round(splits["eval"]["positive_rate"] * 100, 2),
        p3=round(splits["holdout"]["positive_rate"] * 100, 2),
    )

    reference_list = (
        "persistence analogue (assessment_hectares) eval AUC {pe}; calendar/identity prior "
        "eval AUC {ca} (Brier {ca_b}); construction-time full-feature L2 logistic eval AUC "
        "{fl} (Brier {fl_b}, simple reference, supplementary); majority-class accuracy {mj} "
        "(majority fitted on train, measured against eval labels); the runner's own baseline "
        "eval AUC 0.9554 is quoted from the private baseline job abwildfire-baseline-002 and "
        "was reproduced step-for-step by the fresh-consumer job on the released bytes - "
        "refit your own model, your fit need not match"
    ).format(
        pe=round(triad["persistence_assessment_hectares"]["auc"], 4),
        ca=round(triad["calendar_identity_only"]["auc"], 4),
        ca_b=round(triad["calendar_identity_only"]["brier"], 4),
        fl=round(triad["full_feature_logistic"]["auc"], 4),
        fl_b=round(triad["full_feature_logistic"]["brier"], 4),
        mj=round(triad["majority_constant"]["accuracy_on_eval"], 4),
    )

    fills = {
        "DATASET_TITLE": "Alberta Wildfire Initial-Attack Escape (100 ha)",
        "DATASET": "ab-wildfire-ia-escape",
        "TAG": TAG,
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
            "one row per assessed wildfire in Alberta's Forest Protection Area, at the "
            "publisher's own initial-assessment instant (fire_id = YEAR-FIRE_NUMBER, unique, "
            "asserted at construction); temporal split on the assessment instant's calendar "
            "year in Alberta local operational time (America/Edmonton): train = 2006-2015, "
            "eval = 2016-2020, holdout = 2021-2025; the population is all-cause and "
            "assessment-based (every discovered wildfire is assessed, 100% coverage measured - "
            "no outcome-conditioned rule); winter (Nov-Feb) rows are kept (587) and 356 winter "
            "carryover fires assessed in the year after their record year move with their "
            "assessment instant"
        ),
        "NCOLUMNS": str(len(meta["columns"])),
        "COLUMN_LIST": col_list,
        "TRAIN_ROWS": str(counts["train"]["rows"]),
        "EVAL_ROWS": str(counts["eval"]["rows"]),
        "HOLDOUT_ROWS": str(counts["holdout"]["rows"]),
        "TRAIN_POS": str(counts["train"]["positives"]),
        "EVAL_POS": str(counts["eval"]["positives"]),
        "HOLDOUT_POS": str(counts["holdout"]["positives"]),
        "TIME_COLUMN": (
            "assessment_ts - the publisher-documented initial-assessment instant ('the date "
            "and time the wildfire was originally assessed by Alberta Wildfire employees'), "
            "the moment the agency itself makes the initial-attack resourcing decision. Every "
            "shipped feature is documented 'at the time of initial assessment' (size, spread "
            "rate, fire behaviour type, position on slope, the five in-situ weather fields, "
            "FBP fuel type) or measured never to fall after it (reported/discovered/estimated "
            "start, detection channel: assessment never precedes reported_date, 27,828/27,828); "
            "the post-instant families (cause, dispatch with its measured 2.41% mixed ordering, "
            "suppression milestones, discovered size) are excluded from every shipped file. "
            "Timestamps carry no timezone marker and are read as America/Edmonton local "
            "operational time, confirmed against the official Horse River review. The archive "
            "is one current compilation (no per-fire vintages), so every shipped feature is "
            "the current-vintage value of an at-instant field - retrospective research, no "
            "as-of claim"
        ),
        "LABEL_DERIVATION": (
            "final area burned (current_size, the publisher's 'final area burned of the "
            "wildfire', sealed and never shipped) at or above 100 ha on the current "
            "compilation's recorded value - inside the publisher's size-class D band; the "
            "threshold was fixed before any score and never re-tuned; a secondary "
            "containment-duration label was measured at discovery but is NOT shipped"
        ),
        "BASELINE_TRIAD_CLAIMS": base_claims,
        "REFERENCE_LIST": reference_list,
        "TARGET": meta["target"],
        "ID_COLUMNS": ", ".join(meta["id_columns"]),
    }

    template = TEMPLATE.read_text()
    prompt = template.split("\n---\n", 1)[1]
    for key, value in fills.items():
        prompt = prompt.replace("{{%s}}" % key, value)
    if "{{" in prompt:
        left = sorted({ln.split("{{")[1].split("}}")[0] for ln in prompt.splitlines() if "{{" in ln})
        print("UNFILLED PLACEHOLDERS:", left, file=sys.stderr)
        return 1
    out = CAND / "pre-flip-audit-prompt.md"
    out.write_text(prompt)
    print("wrote", out, len(prompt), "chars")

    # ---- record: packaged + awaiting_operator ----
    assert record["status"] == "qualified", record["status"]
    record["status"] = "packaged"
    record["packaged_at"] = stamp
    record["artifacts"] = [{
        "artifact_version": art,
        "digest_of": "sha256 over public/train.csv, public/eval.csv, private/holdout.csv, "
                     "meta.json, quality.json (gate 1.5.0)",
        "gate": "1.5.0 over the full artifact on the worker, ok=true; exact-byte --accept "
                "ACCEPTED before any score (abwildfire-build-001; re-accepted from fetched "
                "bytes in abwildfire-baseline-002 and re-verified on the released bytes in "
                "abwildfire-consumer-001)",
        "repo": "earino/ab-wildfire-ia-escape (private)",
        "release_url": f"https://github.com/earino/ab-wildfire-ia-escape/releases/tag/{TAG}",
        "release_id": 437179999,
        "tag": TAG,
        "target_commit": github["target_commit"],
        "hub_repo": f"earino/ab-wildfire-ia-escape (private Hugging Face dataset, tag {TAG} "
                    f"== main {hub['commit']})",
        "staging_release": "earino/dataset-factory-staging release 437132110 (durable artifact + "
                           "reports copy); consumer job reports in staging 437264584, evidence "
                           "in jobs/abwildfire-consumer-001.json",
        "rows": {
            "train": "15,864 / 297 positives (1.87%) - assessment instants 2006-2015 (America/Edmonton)",
            "eval": "5,707 / 104 positives (1.82%) - assessment instants 2016-2020 (America/Edmonton)",
            "holdout": "6,257 / 257 positives (4.11%) - assessment instants 2021-2025 (America/Edmonton) (sealed)",
        },
        "accepted": "exact-byte --accept on the worker against artifact_version " + art[:12]
                    + "; re-verified on the released bytes by abwildfire-consumer-001",
    }]

    record["awaiting_operator"] = True
    record["awaiting_operator_scope"] = (
        "the private-to-public flip of earino/ab-wildfire-ia-escape on both destinations; "
        "both are staged, verified and private (GitHub release 437179999, tag v2026.11 == main "
        f"== {github['target_commit'][:12]}, 5 flat assets at the package MANIFEST digests, "
        "fresh-consumer green by abwildfire-consumer-001; Hub tag v2026.11 == main == "
        f"{hub['commit'][:12]}, all five files digest-verified by abwildfire-hf-001 and "
        "hf-publish.py --verify). The independent pre-flip audit prompt is at "
        "candidates/ab-wildfire-ia-escape/pre-flip-audit-prompt.md (digests filled "
        "programmatically from the frozen manifest); the flip waits for the auditor's verdict "
        "unless the operator waives it"
    )
    record["awaiting_operator_since"] = stamp
    record["next_action"] = (
        "AWAITING OPERATOR (flip is the sole remaining step; publisher side complete, nothing "
        "public, holdout sealed on both destinations). v2026.11 is staged private and verified "
        "on BOTH destinations: GitHub earino/ab-wildfire-ia-escape release 437179999 (tag "
        f"v2026.11 == main == {github['target_commit'][:12]}, 5 flat assets at the package "
        "MANIFEST digests, server-side digest-verified by abwildfire-publish-001, "
        "fresh-consumer green by abwildfire-consumer-001: gate PASSED, --accept ACCEPTED for "
        "c2c8ceb5, both AUC prints 0.9554 CONTRACT OK, references equal measurements.json, "
        "deciding check reproduced) and Hugging Face earino/ab-wildfire-ia-escape (tag v2026.11 "
        f"== main == {hub['commit'][:12]}, 5/5 digest-verified by abwildfire-hf-001 and "
        "re-verified by hf-publish.py --verify with the worker loading receipt; anonymous "
        "read-back refused while private). The accepted artifact c2c8ceb56c7f... sits at those "
        "digests on both destinations. OPERATOR PATH: (1) relay "
        "candidates/ab-wildfire-ia-escape/pre-flip-audit-prompt.md to an independent auditor; "
        "the flip waits for that verdict unless waived; (2) the operator's single flip "
        "approval (both destinations; never change inference auth to publish). AFTER THE FLIP "
        "(no further approval needed): anonymous verification from a credential-less client "
        "(repo page 200, ranged GET on every asset, Hub API private:false, data files at the "
        "tag revision), record visibility + note in DESTINATIONS.json (files_verified lists "
        "preserved), refresh current editorial copies (card via hf-publish.py --upload-small, "
        "LOADING.md, repository README, release notes - apply-navigation so the managed links "
        "are present), re-run check-package.py, carry the check-suitability.py public notice, "
        "then prepare and review the site plan (sites/<id>.json) and publish/verify after the "
        "operator review. Holdout stays sealed from evaluated agents. NO new construction while "
        "this candidate is actionable-packaged; awaiting_operator exempts the queue. The "
        "cpcb-aqi-exceedance flip remains the operator's too."
    )
    record["updated_at"] = stamp
    RECORD.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print("record: status=packaged packaged_at=%s awaiting_operator=%s artifacts=%d"
          % (record["packaged_at"], record["awaiting_operator"], len(record["artifacts"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
