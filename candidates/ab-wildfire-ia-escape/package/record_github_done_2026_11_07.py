#!/usr/bin/env python3
"""Record the completed GitHub private-staging destination (packaging step).

Adds the abwildfire-publish-001 transfer job to record.jobs, writes
measurements.github_staging_2026_11_07, and narrows next_action to the
remaining steps (consumer job, Hub destination, DESTINATIONS hub block,
packaged + pre-flip audit prompt). Status stays qualified: packaged_at is set
only when both destinations are verified.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAND = ROOT / "candidates" / "ab-wildfire-ia-escape"

job = json.loads((ROOT / "jobs" / "abwildfire-publish-001.json").read_text())
record_path = CAND / "record.json"
record = json.loads(record_path.read_text())

entry = {
    "id": "abwildfire-publish-001",
    "candidate": "ab-wildfire-ia-escape",
    "status": "succeeded",
    "transfer_status": job["result"]["status"],
    "transferred": f"{len(job['result']['transfer']['transferred'])}/5 (failures [])",
    "elapsed_seconds": job["result"]["elapsed_seconds"],
    "server_id": job["server_id"],
    "server_type": job["job"]["server_type"],
    "location": job["job"]["location"],
    "staging_upload_release": f"{job['result']['release_id']} (job reports, private staging)",
    "reservation_eur": job.get("reservation_eur"),
    "collected_at": job.get("collected_at"),
    "deleted_at": job.get("deleted_at"),
    "what": "release-flagged transfer job: 5/5 accepted assets copied from staging release "
            "437132110 into private earino/ab-wildfire-ia-escape release 437179999 (v2026.11) "
            "under flat names, each sha256 verified on arrival and server-side; bytes never "
            "through the coordinator; worker destroyed with provider 404 read-back "
            "(0 servers, 0 primary IPs) re-confirmed by record_github_block_2026_11_07.py",
}
if not any(j["id"] == entry["id"] for j in record.get("jobs", [])):
    record["jobs"].append(entry)

record["measurements"]["github_staging_2026_11_07"] = {
    "date": "2026-11-07",
    "repository": "earino/ab-wildfire-ia-escape (private, id 1448854079)",
    "package_commit": "d610ffe20959ce747635631fc8aba659be3b4823",
    "release": "437179999 (v2026.11, non-draft at main)",
    "files_pushed": 26,
    "assets": "5/5 flat assets server-side digest-equal to MANIFEST.json "
              "(meta.json aeb2ef92..., public-train.csv 575649d5..., public-eval.csv "
              "d099e4cb..., private-holdout.csv 53583f4d..., quality.json 331a4ceb...)",
    "anonymous_read_back": "404 (correctly private)",
    "destinations_block": "release/ab-wildfire-ia-escape/DESTINATIONS.json github block "
                          "written 2026-11-06T23:38:39Z with files_verified as the logical "
                          "path list; huggingface block pending",
    "note": "nothing public; the flip is the operator's single approval and waits for the "
            "independent pre-flip audit verdict unless waived",
}

record["next_action"] = (
    "Private staging continues from the verified GitHub destination (repo "
    "earino/ab-wildfire-ia-escape, release 437179999, tag v2026.11 == main == d610ffe2, "
    "DESTINATIONS.json github block written): (1) the fresh-consumer worker job on the "
    "released bytes (cqc/cpcb consumer pattern; fetch block from release 437179999: "
    "meta.json 718800868-mapped, public-train.csv, public-eval.csv, private-holdout.csv, "
    "quality.json at the flat asset names; digests from MANIFEST.json) - gate 1.5.0 re-run, "
    "exact-byte --accept c2c8ceb5, get_dataset.py + sha256sum -c, baseline reproduce (both "
    "AUC prints 0.9554, CONTRACT OK, holdout never copied into a workdir), score.py references "
    "recomputed equal to measurements.json (fixed-seed CIs reproduce exactly), then APPEND the "
    "consumer check to the DESTINATIONS github block (merge, never replace); (2) "
    "hf-publish.py --plan, --create --upload-small, the hf_publish worker job, --verify, "
    "--tag LAST, then the DESTINATIONS huggingface block; (3) record -> packaged with "
    "packaged_at + structured artifacts[0] + awaiting_operator TRUE only after the pre-flip "
    "adversarial audit prompt is generated from the frozen manifest "
    "(skills/dataset-release/templates/pre-flip-audit-prompt.md, digests filled "
    "programmatically); then check-candidate --all, check-package, check-suitability, suite, "
    "CI for the exact commit. The flip is the operator's single approval. The cpcb flip "
    "remains the operator's."
)

record_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
print("record updated: publish job + github staging measurement; next_action narrowed")
