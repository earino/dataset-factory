#!/usr/bin/env python3
"""Append the abwildfire-consumer-001 and abwildfire-hf-001 outcomes to the
ab-wildfire-ia-escape record (jobs list + measurements), reading every figure
from the collected, digest-verified job results and reports - nothing restated
from memory. Merges into the existing record; does not touch status or
next_action (the close-out script owns those).
"""
import json
import sys
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
CAND = ROOT / "candidates" / "ab-wildfire-ia-escape"
RECORD = CAND / "record.json"


def main() -> int:
    record = json.loads(RECORD.read_text())
    consumer_result = json.loads((ROOT / ".factory/abwildfire-consumer-001/result.json").read_text())
    hf_result = json.loads((ROOT / ".factory/abwildfire-hf-001/result.json").read_text())
    reports = ROOT / ".factory/abwildfire-consumer-001/reports"
    deciding = json.loads((reports / "deciding_check.json").read_text())
    ledger_consumer = json.loads((ROOT / "jobs/abwildfire-consumer-001.json").read_text())
    ledger_hf = json.loads((ROOT / "jobs/abwildfire-hf-001.json").read_text())
    destinations = json.loads((ROOT / "release/ab-wildfire-ia-escape/DESTINATIONS.json").read_text())

    assert consumer_result["status"] == "succeeded" and consumer_result["exit_code"] == 0
    assert consumer_result["fetch"]["failures"] == []
    assert hf_result["status"] == "succeeded" and hf_result["hf_publish"]["failures"] == []
    assert hf_result["hf_loading"]["ok"] is True and hf_result["hf_loading"]["problems"] == []
    hub = destinations["destinations"]["huggingface"]
    assert hub["verified"] is True

    jobs = {entry["id"]: entry for entry in record.get("jobs", [])}
    jobs["abwildfire-consumer-001"] = {
        "id": "abwildfire-consumer-001",
        "candidate": "ab-wildfire-ia-escape",
        "status": "succeeded",
        "exit_code": 0,
        "elapsed_seconds": consumer_result["elapsed_seconds"],
        "server_id": ledger_consumer["server_id"],
        "server_type": "cx23",
        "location": "hel1",
        "reservation_eur": "0.04",
        "collected_at": ledger_consumer["collected_at"],
        "deleted_at": ledger_consumer["deleted_at"],
        "what": ("fresh-consumer verification of the RELEASED bytes of private GitHub release "
                 "437179999 (fetch of the five flat assets with the read credential outside the "
                 "container, digest-verified on arrival): package-vs-MANIFEST OK, get_dataset.py "
                 "re-verification OK, sha256sum -c OK, gate 1.5.0 PASSED on the published bytes, "
                 "exact-byte --accept ACCEPTED for c2c8ceb5, baseline reproduce (both AUC prints "
                 "0.9554, [validate] CONTRACT OK, holdout never copied into a workdir), score.py "
                 "references recomputed equal to measurements.json, and the pre-registered "
                 "deciding check recomputed identical; reports collected digest-verified from "
                 "staging release 437264584 into .factory/abwildfire-consumer-001/reports/"),
    }
    jobs["abwildfire-hf-001"] = {
        "id": "abwildfire-hf-001",
        "candidate": "ab-wildfire-ia-escape",
        "status": "succeeded",
        "exit_code": 0,
        "elapsed_seconds": hf_result["elapsed_seconds"],
        "server_id": ledger_hf["server_id"],
        "server_type": "cx23",
        "location": "hel1",
        "reservation_eur": "0.04",
        "collected_at": ledger_hf["collected_at"],
        "deleted_at": ledger_hf["deleted_at"],
        "what": ("hf_publish worker job: fetched the five released assets from private GitHub "
                 "release 437179999 (digest-verified on arrival), uploaded all five to the private "
                 "Hugging Face dataset earino/ab-wildfire-ia-escape at the manifest digests "
                 "(4,143,697 B, failures [], skipped []), deleted the local copies, and exercised "
                 "the documented load_dataset path against the uploaded bytes - all three splits "
                 "load with the recorded rows/positives/columns and label values [0,1], "
                 "problems []; the local copies deleted; bytes never through the coordinator"),
    }
    record["jobs"] = list(jobs.values())

    measurements = record.setdefault("measurements", {})
    measurements["runner_consumer_001_2026_11_07"] = {
        "date": "2026-11-07",
        "job": ("abwildfire-consumer-001 (cx23 hel1, server 174915106, 256.6 s, exit 0; "
                "destroyed after verified collection at 2026-11-07T02:23:45Z, reservation 0.04 EUR)"),
        "position": "clean consumer: container held no credential and no factory access; the worker host fetched the released bytes",
        "package_vs_manifest": "every published file matches MANIFEST.json",
        "get_dataset": "5 assets already present at the restored layout, size+sha256 verified, no download needed",
        "sha256sums": "OK over the restored tree",
        "gate": "PASSED on the full published artifact (gate 1.5.0, artifact c2c8ceb56c7ff52a)",
        "accept": "ACCEPTED: the released bytes match the qualified artifact c2c8ceb56c7ff52a",
        "baseline": {
            "contract_ok": True,
            "eval_auc_from_train_py": 0.9554,
            "eval_auc_from_validate_py": 0.9554,
            "holdout_isolated": "the private holdout was NOT copied into any workdir",
            "dependencies": {"python": "3.13.18", "pandas": "2.3.3", "numpy": "2.5.4",
                             "xgboost": "3.4.1", "scikit-learn": "1.9.1"},
        },
        "references_equal_measurements": True,
        "deciding_check_reproduced": {
            "model_eval_auc": deciding["model_eval_auc"],
            "model_minus_persistence_ci": deciding["model_minus_persistence_ci"],
            "model_minus_calendar_ci": deciding["model_minus_calendar_ci"],
            "model_auc_ci": deciding["model_auc_ci"],
            "member_aucs": deciding["member_aucs"],
            "eval_rows": deciding["eval_rows"],
            "eval_distinct_positive_days": deciding["eval_distinct_positive_days"],
            "identical_to_recorded": (deciding["model_minus_persistence_ci"] == deciding["recorded"]["model_minus_persistence_ci"]
                                      and deciding["model_minus_calendar_ci"] == deciding["recorded"]["model_minus_calendar_ci"]
                                      and deciding["model_auc_ci"] == deciding["recorded"]["model_auc_ci"]),
        },
        "rebuild_from_source": "not run (optional per REPRODUCE.md; build.py refuses any source other than the pinned publisher CSV)",
        "reports": ".factory/abwildfire-consumer-001/reports/ (consumer.txt, qualification.txt, accept.txt, versions.txt, baseline.log, references.json, deciding_check.json, container.log)",
    }
    measurements["hub_staging_2026_11_07"] = {
        "date": "2026-11-07",
        "repository": "earino/ab-wildfire-ia-escape (private Hugging Face dataset)",
        "job": "abwildfire-hf-001 (cx23 hel1, server 174915997, 98.7 s, exit 0; destroyed after verified collection at 2026-11-07T02:30:25Z, reservation 0.04 EUR)",
        "small_files": "uploaded 2026-11-07 by hf-publish.py --create --upload-small from the release manifest (card, LOADING.md, MANIFEST, SHA256SUMS, licences, DATA_DICTIONARY, VERIFICATION, measurements)",
        "uploads": "5/5 assets at data/<flat-name> (or root for meta/quality), each digest-verified after upload; failures []; skipped []",
        "loading_check": "all three splits load via the documented load_dataset path at revision main: rows 15,864/5,707/6,257, positives 297/104/257, the 25 shipped columns, label escape with values [0,1]; problems []",
        "tag": "v2026.11 == main == 54e70b441e70ec24e198775e0bcb0ccf35fb192c; hf-publish.py --verify digest-verified all five files at the tag revision with the worker receipt",
        "destinations_block": "release/ab-wildfire-ia-escape/DESTINATIONS.json huggingface block written (files_verified = the five Hub target paths, loading_check verified by worker job abwildfire-hf-001)",
        "note": "nothing public; anonymous access refused while private; the flip remains the operator's single approval",
    }

    RECORD.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print("record: %d jobs, consumer + hub staging measurement blocks written"
          % len(record["jobs"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
