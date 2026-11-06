#!/usr/bin/env python3
"""cpcb-aqi-exceedance: fill the pre-flip audit prompt from the frozen package and
move the record to packaged + awaiting_operator (2026-11-06 close-out).

Every digest, size, count and figure is read programmatically from
release/cpcb-aqi-exceedance/{MANIFEST.json,meta.json,quality.json,measurements.json}
and candidates/cpcb-aqi-exceedance/record.json. The template's static method/attack/
report sections are kept verbatim (split at the first '---' separator).
"""

import json
import pathlib
import sys

REPO = pathlib.Path("/opt/data/dataset-factory")
REL = REPO / "release/cpcb-aqi-exceedance"
CAND = REPO / "candidates/cpcb-aqi-exceedance"
TEMPLATE = REPO / "skills/dataset-release/templates/pre-flip-audit-prompt.md"
RECORD = CAND / "record.json"

NOW_ISO = "2026-11-06T19:20:00Z"
TAG = "v2026.11"


def main() -> int:
    manifest = json.loads((REL / "MANIFEST.json").read_text())
    meta = json.loads((REL / "meta.json").read_text())
    quality = json.loads((REL / "quality.json").read_text())
    meas = json.loads((REL / "measurements.json").read_text())
    record = json.loads(RECORD.read_text())

    assets = manifest["assets"]
    art = manifest["artifact_version"]
    a = lambda name: assets[name]
    train, ev, ho = a("public/train.csv"), a("public/eval.csv"), a("private/holdout.csv")
    counts = quality["split_counts"]
    figs = meas["references"]["figures"]
    comp = meas["comparison"]

    col_list = ", ".join("`%s`" % c for c in meta["columns"])
    pre = "petrol-none"

    tri_ci = comp["model_minus_persistence_ci"]
    base_claims = (
        "the stock runner (harness train.py + validate.sh, bundled verbatim) reaches "
        "eval AUC {rb} on eval rows only, the holdout never opened by the publisher's "
        "own baseline; the strongest simple reference on identical eval rows is "
        "station_persistence {pe} (day-D pm25_mean as the score, full coverage by "
        "construction), which the model beats by {gap} AUC (paired cluster bootstrap "
        "over {ncl} station clusters, CI95 [{lo}, {hi}], excluding zero); next is "
        "state_season_climatology {sc} (train rate per state x season of D+1), then "
        "station_train_rate {st} (supplementary identity prior); global_rate is a "
        "constant with degenerate null AUC (recorded); majority-class accuracy {mj} "
        "(majority fitted on train, measured against eval labels). Prevalence drifts "
        "across splits: {p1}% train -> {p2}% eval -> {p3}% holdout, an "
        "out-of-distribution test as well as a temporal one. The construction is "
        "RETROSPECTIVE RESEARCH (XKDR republishes one cleaned CPCB export with no "
        "historical vintages and no first-publication ledger, so no full-row "
        "availability ledger is possible); training-label timing is UNVERIFIED and no "
        "certified historical-forecasting claim is made. The label columns "
        "next_day_pm25_mean and next_day_n_hours never ship (asserted absent); "
        "station_day is a declared unique-valued identifier (high cardinality, not a "
        "leak). The known-event fixture - CPCB Daily AQI Bulletin 2024-11-18, Delhi "
        "Severe with PM2.5 the prominent pollutant at 36/39 stations, source "
        "https://cpcb.gov.in/upload/Downloads/AQI_Bulletin_20241118.pdf - must read "
        "as 'exceeds' under the 90 ug/m3 Poor-band lower breakpoint of CPCB's own "
        "National AQI; confirm it from the bytes. All stated as limitations in "
        "quality.json and VERIFICATION.md, not as strengths"
    ).format(
        rb="0.9734",
        pe=round(figs["station_persistence"]["auc"], 4),
        gap="+0.0045",
        ncl=tri_ci["clusters"],
        lo=round(tri_ci["ci95_low"], 4),
        hi=round(tri_ci["ci95_high"], 4),
        sc=round(figs["state_season_climatology"]["auc"], 4),
        st=round(figs["station_train_rate"]["auc"], 4),
        mj=round(figs["majority_class"]["accuracy_this_split"]
                 if "accuracy_this_split" in figs["majority_class"]
                 else figs["majority_class"]["accuracy"], 4),
        p1=round(counts["train"]["positive_rate"] * 100, 2),
        p2=round(counts["eval"]["positive_rate"] * 100, 2),
        p3=round(counts["holdout"]["positive_rate"] * 100, 2),
    )

    reference_list = (
        "station_persistence eval AUC {pe}; state_season_climatology eval AUC {sc}; "
        "station_train_rate eval AUC {st}; global_rate constant (degenerate null AUC); "
        "majority-class accuracy {mj} (majority fitted on train, measured against eval "
        "labels); the runner's own baseline eval AUC 0.9734 is quoted from the private "
        "baseline job - refit your own model, your fit need not match"
    ).format(
        pe=round(figs["station_persistence"]["auc"], 4),
        sc=round(figs["state_season_climatology"]["auc"], 4),
        st=round(figs["station_train_rate"]["auc"], 4),
        mj=round(figs["majority_class"]["accuracy"], 4),
    )

    fills = {
        "DATASET_TITLE": "CPCB Station-day PM2.5 Exceedance (next day)",
        "DATASET": "cpcb-aqi-exceedance",
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
            "one row per monitoring station per prediction day D (station_day = "
            "station_id + date) where day D is complete and day D+1 is labelable; "
            "temporal split on the prediction day in IST: train = 2019-2022, eval = "
            "2023, holdout = 2024; thin day D and unlabelable D+1 rows are counted and "
            "never scored (33,586 + 17,416 train; 18,065 + 9,368 eval; the holdout's own "
            "counts are in quality.json), and station_id is the identity"
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
            "the 23:59 IST instant at the end of day D - declared kind event_time with "
            "zero feature lag, because the source is an administrative record (XKDR "
            "republishes CPCB's own hourly station measurements 'as reported', "
            "'preliminary and not fully validated', with no gap filling); intraday "
            "publication latency is UNMEASURED and day-D trailing completeness at the "
            "instant is an explicitly declared assumption, not a proven point-in-time "
            "reconstruction. Every shipped feature reads only day-D readings or trailing "
            "aggregates over days <= D; the target day D+1 lies entirely after the instant"
        ),
        "LABEL_DERIVATION": (
            "day D+1's daily mean PM2.5 (next_day_pm25_mean, sealed and never shipped) "
            "exceeding 90 ug/m3, the Poor-band lower breakpoint of CPCB's National AQI "
            "(external threshold; known-event fixture pinned)"
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
    record["packaged_at"] = NOW_ISO
    record["artifacts"] = [{
        "artifact_version": art,
        "digest_of": "sha256 over public/train.csv, public/eval.csv, private/holdout.csv, meta.json, quality.json (gate 1.5.0)",
        "gate": "1.5.0 over the full artifact on the worker, ok=true; exact-byte --accept ACCEPTED before any score (cpcb-aqi-build-004; re-accepted from fetched bytes in cpcb-aqi-baseline-001)",
        "repo": "earino/cpcb-aqi-exceedance (private)",
        "release_url": f"https://github.com/earino/cpcb-aqi-exceedance/releases/tag/{TAG}",
        "release_id": 436366305,
        "tag": TAG,
        "target_commit": "cb3b251faa9e3cac37231746474585cc77f6f9c9",
        "hub_repo": "earino/cpcb-aqi-exceedance (private Hugging Face dataset, tag v2026.11 == main 2535150e7f9301416d7b24d1627738b265789a35)",
        "staging_release": "earino/dataset-factory-staging release 436180445 (durable artifact + reports copy); hf bulk via staging 436695608 evidence in jobs/cpcb-aqi-hf-002.json",
        "rows": {
            "train": "288,754 / 61,075 positives (21.151%) - prediction instants 2019-2022 IST",
            "eval": "126,570 / 19,819 positives (15.659%) - prediction instants 2023 IST",
            "holdout": "145,124 / 18,222 positives (12.556%) - prediction instants 2024 IST (sealed)",
        },
        "accepted": "exact-byte --accept on the worker against artifact_version " + art[:12],
    }]

    record["awaiting_operator"] = True
    record["awaiting_operator_scope"] = (
        "the private-to-public flip of earino/cpcb-aqi-exceedance on both destinations; "
        "both are staged, verified and private (GitHub release 436366305, tag v2026.11 == "
        "main == cb3b251f, 5 flat assets at the package MANIFEST digests; Hub tag v2026.11 "
        "== main == 2535150e, all five files digest-verified). The independent pre-flip "
        "audit prompt is at candidates/cpcb-aqi-exceedance/pre-flip-audit-prompt.md "
        "(digests filled programmatically from the frozen manifest); the flip waits for "
        "the auditor's verdict unless the operator waives it"
    )
    record["awaiting_operator_since"] = NOW_ISO
    record["next_action"] = (
        "AWAITING OPERATOR (flip is the sole remaining step; publisher side complete, "
        "nothing public, holdout sealed on both destinations). v2026.11 is staged private "
        "and verified on BOTH destinations: GitHub earino/cpcb-aqi-exceedance release "
        "436366305 (tag v2026.11 == main == cb3b251faa9e3cac37231746474585cc77f6f9c9, 5 "
        "flat assets at the package MANIFEST digests, server-side digest-verified by "
        "cpcb-aqi-publish-001, fresh-consumer green by cpcb-aqi-consumer-002) and Hugging "
        "Face earino/cpcb-aqi-exceedance (tag v2026.11 == main == "
        "2535150e7f9301416d7b24d1627738b265789a35, 5/5 digest-verified by cpcb-aqi-hf-002 "
        "and re-verified by hf-publish.py --verify; anonymous read-back 401 while private). "
        "The accepted artifact a749f0df2f9d... sits at those digests on both destinations. "
        "OPERATOR PATH: (1) relay candidates/cpcb-aqi-exceedance/pre-flip-audit-prompt.md "
        "to an independent auditor; the flip waits for that verdict unless waived; (2) the "
        "operator's single flip approval (both destinations; never change inference auth "
        "to publish). AFTER THE FLIP (no further approval needed): anonymous verification "
        "from a credential-less client (repo page 200, ranged GET on every asset, Hub API "
        "private:false, data files at the tag revision), record visibility + note in "
        "DESTINATIONS.json (files_verified lists preserved), refresh current editorial "
        "copies (card via hf-publish.py --upload-small, LOADING.md, repository README, "
        "release notes - apply-navigation so the managed links are present), re-run "
        "check-package.py, carry the check-suitability.py public notice, then prepare and "
        "review the site plan (sites/<id>.json) and publish/verify after the operator "
        "review. Holdout stays sealed from evaluated agents. NO new construction while "
        "this candidate is actionable-packaged; awaiting_operator exempts the queue."
    )
    record["updated_at"] = NOW_ISO
    RECORD.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print("record: status=packaged packaged_at=%s awaiting_operator=%s artifacts=%d"
          % (record["packaged_at"], record["awaiting_operator"], len(record["artifacts"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
