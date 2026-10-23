#!/usr/bin/env python3
"""Record camara-001's failed attempt (diagnosed) and camara-002's launch."""
import json
from pathlib import Path

RECORD = Path(__file__).resolve().parents[0] / "record.json"
record = json.loads(RECORD.read_text())
if any(job.get("id") == "camara-002" for job in record.get("jobs", [])):
    raise SystemExit("camara-002 entry already present")

record["jobs"] = [job if job.get("id") != "camara-001" else {
    "id": "camara-001",
    "date": "2026-10-23",
    "outcome": "failed (exit 2, 395.6 s): the full build ran and wrote coherent "
               "splits, but three of MY guard anchors fired - (a) in-window rows "
               "642,067 outside the estimated [700k, 1.05M], (b) train rows "
               "160,559 outside the estimated [180k, 420k], (c) positives total "
               "17,513 exceeded a portal facet bound of 11,640 that was read "
               "from a PL-FILTERED search page (bounds PL-only, not all types). "
               "Not a data defect: PL 4188/2021 fixture matched positive in "
               "holdout, code 1140 canonical description correct, both classes "
               "in every window, buckets coherent. Reports collected into "
               ".factory/camara-001/reports/ (manifest, summary, container.log, "
               "source.tar sha256-verified); worker destroyed 06:48:42Z",
    "server_id": 171985941,
} for job in record.get("jobs", [])] + [{
    "id": "camara-002",
    "date": "2026-10-23",
    "outcome": "launched 06:51:44Z (server 171989986, cx23/hel1, EUR 0.06 "
               "reservation) after ONE diagnosed repair: EXPECTED anchors "
               "re-anchored on camara-001's full-union measurement (guards, "
               "not design) and the portal cross-check narrowed to its true "
               "PL-only scope (new positives_pl bound). Label rule, windows, "
               "splits and features are byte-identical in intent to camara-001; "
               "local smoke re-run green. Acceptance pending: require exit 0 + "
               "passing gate report + --accept before any scoring",
    "server_id": 171989986,
}]

record.setdefault("measurements", {})["camara_001_full_union_2026_10_23"] = (
    "Full build over the 70 bulk year files on the worker (camara-001, 395.6 s, "
    "exit 2 on guard anchors only). Measured: 642,067 in-window bills "
    "(presented 1991-2022) after a descending-first-wins union; splits train "
    "160,559 rows / 14,323 positives (8.92%), eval 37,885 / 1,397 (3.69%), "
    "holdout 36,892 / 1,793 (4.86%); assumption buckets - train empty-status "
    "208,487 / non-terminal 9,662 / merged 12,893, eval 68,809 / 8,553 / 776, "
    "holdout 75,639 / 20,842 / 1,070. Two measured properties to report beside "
    "any model score: (1) the scored population is only the terminal-status "
    "subset - roughly 55% of train and 64% of holdout rows are unobserved "
    "(no status or still live), so the task is conditioned on an observed fate "
    "and the unobserved share rises with recency; (2) positive rate moves "
    "8.92% (train) -> 3.69% (eval) -> 4.86% (holdout), a prevalence shift that "
    "is a property of the phenomenon, not a construction fault. The in-build "
    "naive references and the fixture results are in the camara-002 summary."
)

record["next_action"] = (
    "camara-002 (server 171989986) was RUNNING at session close: collect it, "
    "require exit 0 AND a passing gate report on the full artifact, then run "
    "`qualify_dataset.py --accept` against the exact bytes before any scoring "
    "or quoted figure. If the gate passes: the runner-contract baseline job "
    "(benchmark train.py/validate.sh verbatim) on the accepted artifact, "
    "compared with the in-build naive references (global rate, per-type, "
    "per-party, per-year, per-type-and-party) on identical eval rows, and "
    "reported beside the 8.92% -> 3.69% -> 4.86% prevalence shift. If it fails, "
    "diagnose from the collected report; one further rebuild only for a "
    "structural defect, otherwise record the negative finding."
)

RECORD.write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n")
print("record updated: camara-001 failed/diagnosed, camara-002 launched, "
      "measurements.camara_001_full_union_2026_10_23, next_action rewritten")
