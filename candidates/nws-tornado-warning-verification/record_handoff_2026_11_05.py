#!/usr/bin/env python3
"""Close-out record update for the 2026-11-05 advancement session: the
nws-tornado-build-001 job is still running at session close (34 min in; the
run-time budget stopped the session before collection). This writes the
handoff facts into the record: job id, server, launch time, expected reports
and the next acceptance checks - exactly what record.next_action already
documents, so a fresh session or the watcher follow-up can collect."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORD = HERE / "record.json"
r = json.loads(RECORD.read_text())

r["jobs"].append({
    "id": "nws-tornado-build-001",
    "launched_at": "2026-11-05T14:38:05Z",
    "server_id": 174626604,
    "ipv4": "2.29.159.168",
    "server_type": "cx23",
    "location": "hel1",
    "reservation_eur": "0.04",
    "status_at_session_close": "running",
    "session_close_at": "2026-11-05T15:12:00Z",
    "note": (
        "still running 34 min in at the session's run-time budget stop "
        "(17 national cow year-pulls at the measured 40-75 s each plus "
        "parse + gate + accept + references; job timeout 45 min, worker "
        "lifetime 60 min from 14:38:05Z). The running job IS the handoff: "
        "collect with `sh scripts/scout-factory worker collect "
        "nws-tornado-build-001` once terminal, verify the ladder in "
        "/output (summary.json -> qualification-nws-tornado-warning-"
        "verification.json ok:true -> acceptance ACCEPTED -> references "
        "json), then destroy with provider read-back, then apply the "
        "pre-registered deciding-rule protocol in next_action (the full "
        "model is the separate baseline job)."),
})

r["next_action"] = (
    "COLLECT nws-tornado-build-001 (launched 2026-11-05T14:38:05Z, server "
    "174626604, still running at the 15:12Z run-time budget stop - the "
    "running job is the handoff): (1) `sh scripts/scout-factory worker "
    "status nws-tornado-build-001` until terminal, then `worker collect "
    "nws-tornado-build-001`; (2) verify the ladder IN THE COLLECTED BYTES, "
    "not prose: /output/summary.json (17 years fetched, per-year ledger, "
    "fixtures 5/5 asserted, anchors 1832/441 + 2531/656 exact, split "
    "stats), qualification-nws-tornado-warning-verification.json ok:true "
    "failed_checks=[], acceptance txt ACCEPTED, references json (majority, "
    "persistence_same_wfo_30min, calendar_identity_wfo_doy_hour on "
    "identical eval rows, per-issue-year tables, day-clustered bootstrap); "
    "(3) destroy the worker with provider 404 read-back; (4) if the gate "
    "failed or the build refused: diagnose from build_error/qualification "
    "diagnostics, record, ONE rebuild per structural defect class; (5) "
    "then the FULL MODEL baseline job on the accepted artifact (the "
    "za-cct-baseline/cqc-chd-baseline pattern: fetch the five gate-digest "
    "assets, exact-byte --accept, stock train.py+validate.py verbatim, "
    "holdout never opened) and apply the PRE-REGISTERED deciding rule: "
    "headroom ONLY if the full model beats EVERY simple reference on "
    "identical eval rows with the day-clustered paired bootstrap 95% CI "
    "excluding zero in the model's favour; reference dominance with CI "
    "excluding zero on the deficit side -> DROP (wb-loan/unhcr precedent); "
    "inconclusive -> HOLD with the negative finding preserved; NO "
    "re-tuning of splits, population, features or label after any score. "
    "If the worker expired uncollected: `worker status` reconciles it as "
    "deleted after expiry + grace, then relaunch as nws-tornado-build-002 "
    "(the ONE changed retry an infrastructure expiry is entitled to, "
    "bundle otherwise unchanged).")

RECORD.write_text(json.dumps(r, indent=1) + "\n")
print("record updated: jobs:", len(r["jobs"]), "next_action:",
      r["next_action"][:80])
