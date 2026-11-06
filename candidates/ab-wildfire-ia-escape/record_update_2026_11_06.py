#!/usr/bin/env python3
"""Record the abwildfire-build-001 result in the candidate record (2026-11-06).

One-shot, idempotent-by-assertion: refuses to run twice. Reads the collected
reports (committed beside this script) and writes status=qualified with the
qualification evidence, the job entry and the reference-triad measurements.
"""
import json
from pathlib import Path

RECORD = Path("candidates/ab-wildfire-ia-escape/record.json")
QUAL = json.loads(Path("candidates/ab-wildfire-ia-escape/qualification-abwildfire-build-001.json").read_text())
REFS = json.loads(Path("candidates/ab-wildfire-ia-escape/references-abwildfire-build-001.json").read_text())

assert QUAL["gate_version"] == "1.5.0" and QUAL["ok"] and not QUAL["failed_checks"]
assert REFS["ok"] and REFS["artifact_version"] == QUAL["artifact"]["artifact_version"]["digest"]

record = json.loads(RECORD.read_text())
if record.get("status") == "qualified":
    raise SystemExit("record already updated; refusing to run twice")
assert record["status"] == "ready"

artifact = QUAL["artifact"]["artifact_version"]["digest"]
record["status"] = "qualified"
record["construction_script"] = (
    "candidates/ab-wildfire-ia-escape/source/build.py, executed by worker job "
    "abwildfire-build-001 (entrypoint source/run.sh: construct -> qualify -> "
    "exact-byte accept -> pre-registered references; build.py computes no "
    "performance metric, score.py runs post-acceptance on eval rows only and "
    "never opens private/holdout.csv)"
)
record["split_strategy"] = (
    "Temporal, disjoint by the ASSESSMENT instant's calendar year (the time "
    "column; America/Edmonton local operational time): train 2006-2015 "
    "(15,864 fires), eval 2016-2020 (5,707), holdout 2021-2025 (6,257). 356 "
    "winter carryover fires assessed in the year after their record year move "
    "with their assessment; label-side counts are identical under the record-"
    "year rule (positives 297/104/257 = 1.87%/1.82%/4.11%; distinct positive "
    "assessment dates 156/79/128; containment>72h 514/189/611). Winter (Nov-Feb) "
    "rows kept and counted (587 total). The holdout escape rate is higher "
    "because 2021-2025 contains the 2023 record season - documented "
    "non-stationarity, recorded in quality.json limitations."
)
record.setdefault("measurements", {})
record["measurements"]["construction_abwildfire_build_001"] = {
    "date": "2026-11-06",
    "job": "abwildfire-build-001 (cx23 hel1, server 174889543, 102.1 s, exit 0; "
           "destroyed after verified collection at 2026-11-06T22:43:56Z, reservation 0.04 EUR)",
    "source": "staged pinned CSV earino/dataset-factory-staging release "
              "source-abwildfire-001 (437116894, asset 718748383), fetched by the "
              "executor with sha256 verification and asserted again in-build: "
              "8b6ed447ab0f958dbe845a53dc15362b8ef5c0810ad9420d2143f9f5ee010a72",
    "artifact_version": artifact,
    "split_sha256": {
        "train": QUAL["artifact"]["train"]["sha256"],
        "eval": QUAL["artifact"]["eval"]["sha256"],
        "holdout": QUAL["artifact"]["holdout"]["sha256"],
    },
    "fixtures": "10 named fires asserted at publisher-documented final sizes "
                "(incl. Horse River 2016 485,123.6 ha; already-controlled negative "
                "LWF002 2023), size-class consistency 0, publisher season-hectares "
                "deltas 2020-2024 <= 1.1% and 2019 -10.4% (documented revision)",
    "timezone_confirmation": "official 2016 Horse River review: detected 16:03h MDT "
                             "2016-05-01 = the record's naive local 16:03; "
                             "under-control 2016-07-04 and extinguished 2017-08-02 match",
}
record["measurements"]["reference_triad_eval_2016_2020"] = {
    "protocol": "pre-registered (source/score.py): rank AUC on identical eval rows "
                "(5,707 rows, 104 positives); day-cluster bootstrap (cluster = "
                "assessment_date) 500 resamples for paired differences; holdout never "
                "opened; simple L2 logistic reference is not a tuned model",
    "majority_constant": {"auc": 0.5, "accuracy_on_eval": 0.9818},
    "persistence_assessment_hectares": {"auc": 0.9096},
    "calendar_identity_only": {"auc": 0.7130},
    "full_feature_logistic": {"auc": 0.9206},
    "full_minus_persistence": {"observed": 0.0111, "ci": [-0.0292, 0.0514],
                               "finding": "INCONCLUSIVE - the interval contains zero; "
                                          "the full-feature logistic reference does NOT "
                                          "demonstrably beat the one-feature persistence "
                                          "rule (observed size at assessment) under "
                                          "day-cluster resampling"},
    "full_minus_calendar": {"observed": 0.2077, "ci": [0.1551, 0.2644]},
    "persistence_minus_calendar": {"observed": 0.1966, "ci": [0.1371, 0.2694]},
    "reading": "any quoted AUC must carry this comparison: the bar on eval is ~0.91 "
               "from assessment size alone; the added features' measured contribution "
               "over that rule is +0.011 with an interval containing zero. Not a "
               "tuning target: no label, threshold, window or feature may change to "
               "widen it. A richer model may still beat it - that question is the "
               "benchmark's, and the calendar-only prior is clearly beaten.",
    "eval_per_year": REFS["eval_per_year"],
}
record["qualification"] = {
    "gate_version": "1.5.0",
    "artifact_version": artifact,
    "result": "ALL CHECKS GREEN on the FULL artifact on the worker "
              "(failed_checks []); exact-byte --accept re-verified on the worker: "
              "'ACCEPTED: /output/extract matches the qualified artifact c2c8ceb56c7ff52a'",
    "report": "candidates/ab-wildfire-ia-escape/qualification-abwildfire-build-001.json "
              "(sha256 16697cd8aef51394f84b125964104adea5bf9dd8536f4fde291f817469cb07bb)",
    "references_report": "candidates/ab-wildfire-ia-escape/references-abwildfire-build-001.json "
                         "(sha256 ab720e3b07aa0df3c6d3e701875317af20e24ede4fe6c099950a26299301b45d)",
    "full_extract": "earino/dataset-factory-staging private draft release 437132110 "
                    "(job-abwildfire-build-001): public/train.csv 2,351,953 B "
                    "(575649d52c304d2f...), public/eval.csv 838,515 B "
                    "(d099e4cb9da999e3...), private/holdout.csv 930,923 B "
                    "(53583f4d2dff386b...), meta.json, quality.json, summary.json",
    "scope": "retrospective_research, isolated_rows access, training_label_timing "
             "unverified (single current compilation); gate 1.5 evaluation_contract "
             "declared in quality.json with the vintage, timezone, cluster and "
             "public-event-identifiability limitations",
}
record["jobs"] = [{
    "id": "abwildfire-build-001",
    "candidate": "ab-wildfire-ia-escape",
    "status": "succeeded",
    "exit_code": 0,
    "elapsed_seconds": 102.1,
    "server_id": 174889543,
    "server_type": "cx23",
    "location": "hel1",
    "image": "python:3.13-slim (sha256:09a17cad02668ae61ece136b4fd36ac3849e14f670ebedb637ea3e15580525bc)",
    "staging_release": "437132110 (private earino/dataset-factory-staging, tag job-abwildfire-build-001)",
    "source_staging": "437116894 (source-abwildfire-001, asset 718748383, pinned CSV "
                      "sha256 8b6ed447... verified on fetch and in-build)",
    "reservation_eur": "0.04",
    "collected_at": "2026-11-06T22:41:30Z",
    "deleted_at": "2026-11-06T22:43:56Z",
    "what": "full construction + gate 1.5.0 + exact-byte accept + pre-registered "
            "reference triad; see job record .factory/jobs/abwildfire-build-001 and "
            "jobs/ ledger",
}]
record["next_action"] = (
    "Package with dataset-release: build release/ab-wildfire-ia-escape from the "
    "staged extract (staging release 437132110) - README and dataset card "
    "(derived-not-official labelling per the OGL-Alberta non-endorsement clause), "
    "LICENSE.md with the required attribution sentence verbatim, MIT for our code, "
    "CC0 for our compilation rights, data dictionary (the verbatim transcript), "
    "REPRODUCE with the browser fetch procedure, the reference-triad comparison "
    "beside every AUC, release-manifest, check-package, then the pre-flip audit "
    "prompt before any flip. The full-minus-persistence difference is INCONCLUSIVE "
    "(+0.0111, CI [-0.029, +0.051]) and must appear next to any quoted number. "
    "Secondary containment formulation (42% already-controlled-at-assessment "
    "stratum decision) is a possible separate task instance, deliberately not "
    "shipped here."
)

RECORD.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"ok": True, "status": record["status"], "artifact_version": artifact}))
