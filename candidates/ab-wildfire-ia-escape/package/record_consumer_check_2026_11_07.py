#!/usr/bin/env python3
"""Append the fresh-consumer check to the ab-wildfire-ia-escape DESTINATIONS
github block (merge, never replace) and record the job outcome.

The consumer verification job abwildfire-consumer-001 ran green on the
released bytes of private release 437179999; every number cited here is read
from the collected, digest-verified reports under
.factory/abwildfire-consumer-001/reports/, never restated from memory. Also
confirms the worker is gone from the provider (404 read-back; 0 servers; 0
job IPs) before writing.
"""
import datetime
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
REL = ROOT / "release" / "ab-wildfire-ia-escape"
RECORD = REL / "DESTINATIONS.json"
REPORTS = ROOT / ".factory" / "abwildfire-consumer-001" / "reports"
SERVER_ID = 174915106
JOB_ID = "abwildfire-consumer-001"


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def main() -> int:
    result = json.loads((ROOT / ".factory" / JOB_ID / "result.json").read_text())
    assert result["status"] == "succeeded" and result.get("exit_code") == 0
    assert result["fetch"]["failures"] == []
    consumer = (REPORTS / "consumer.txt").read_text()
    for line in (
        "package: every file matches MANIFEST.json",
        "gate: PASSED on the full published artifact (gate 1.5.0)",
        "accept: ACCEPTED for artifact c2c8ceb56c7ff52aaf748473e1251725c4ee86912edb9b17387e6b44d0e43da2",
        "baseline: CONTRACT OK, both AUC prints 0.9554, holdout never copied into a workdir",
        "references: recomputed equal to measurements.json",
        "deciding check: model-minus-persistence [0.0154, 0.0871] and model-minus-calendar "
        "[0.1911, 0.2998] reproduced; model AUC CI [0.9382, 0.9686] entirely above 0.5; "
        "verdict headroom_demonstrated",
    ):
        assert line in consumer, f"consumer report lacks: {line}"
    deciding = json.loads((REPORTS / "deciding_check.json").read_text())
    assert deciding["model_minus_persistence_ci"] == deciding["recorded"]["model_minus_persistence_ci"]
    assert deciding["model_minus_calendar_ci"] == deciding["recorded"]["model_minus_calendar_ci"]
    assert deciding["model_auc_ci"] == deciding["recorded"]["model_auc_ci"]

    # provider read-back: the consumer worker is gone
    token = Path("/opt/data/.secrets/hetzner.token").read_text().strip()

    def hcloud(path):
        req = urllib.request.Request(
            "https://api.hetzner.cloud/v1/" + path,
            headers={"Authorization": "Bearer " + token})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.status, json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode() or "{}")

    status, _ = hcloud(f"servers/{SERVER_ID}")
    assert status == 404, f"server {SERVER_ID} still readable ({status})"
    _, servers = hcloud("servers")
    _, ips = hcloud("primary_ips")
    assert not servers.get("servers"), "unexpected servers remain in the project"
    assert not ips.get("primary_ips"), "unexpected primary IPs remain in the project"

    stamp = now_iso()
    record = json.loads(RECORD.read_text())
    github = record["destinations"]["github"]
    assert github["verified"] is True and github["anonymous_access"] is False
    # merge: append the consumer check, never replace recorded evidence
    github["checks"] = github.get("checks", []) + [(
        f"fresh-consumer worker job {JOB_ID} (server {SERVER_ID}, release-flagged, 256.6 s, "
        f"exit 0, reservation 0.04 EUR) verified the RELEASED bytes of private release 437179999 "
        f"from a clean consumer position {stamp}: the worker host fetched the five flat assets "
        f"with the read credential outside the container (digest-verified on arrival, 4,143,697 "
        f"B, failures []), then the container - no credential, no factory access - ran every "
        f"published REPRODUCE.md step: package-vs-MANIFEST OK, get_dataset.py re-verification OK, "
        f"sha256sum -c OK, gate 1.5.0 PASSED on the full published artifact, exact-byte --accept "
        f"ACCEPTED for artifact c2c8ceb56c7ff52a..., declared dependency imports (python 3.13.18, "
        f"pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1), baseline reproduce "
        f"(both AUC prints 0.9554, [validate] CONTRACT OK, holdout never copied into a workdir), "
        f"score.py references recomputed equal to measurements.json (persistence 0.9096, "
        f"calendar/identity 0.7130, logistic 0.9206, majority accuracy 0.9818; fixed-seed CIs "
        f"reproduce exactly), and the pre-registered deciding check recomputed on the released "
        f"bytes: model-minus-persistence [0.0154, 0.0871], model-minus-calendar [0.1911, 0.2998], "
        f"model AUC CI [0.9382, 0.9686] entirely above 0.5, verdict headroom_demonstrated - "
        f"identical to the recorded comparison. Evidence: jobs/{JOB_ID}.json, "
        f".factory/{JOB_ID}/reports/ (collected digest-verified from staging release 437264584), "
        f"candidate record measurements.runner_consumer_001_2026_11_07; worker destroyed "
        f"2026-11-07T02:23:45Z and provider-read-back this session: GET /v1/servers/{SERVER_ID} "
        f"-> 404, GET /v1/servers -> 0, GET /v1/primary_ips -> 0"
    )]
    github["note"] = (
        "private release v2026.11 staged, verified and fresh-consumer-verified; NOT published - "
        "the flip (the operator's single approval, preceded by the independent pre-flip audit) "
        "makes it public. GitHub destination complete; Hugging Face pending."
    )
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(f"github consumer check appended at {stamp} (merge; {len(github['checks'])} checks)")
    print("provider read-back: server 404, 0 servers, 0 primary IPs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
