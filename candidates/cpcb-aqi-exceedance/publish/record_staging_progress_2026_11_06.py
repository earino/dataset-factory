#!/usr/bin/env python3
"""Record the cpcb-aqi-exceedance GitHub private-staging step (2026-11-06).

Adds measurements.private_staging_github_2026_11_06 and rewrites next_action:
the GitHub destination is done and verified; the consumer job, the Hugging
Face destination, DESTINATIONS.json and the packaged/awaiting_operator flip
remain. All identities read from the job ledger and the live API read-back.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAND = ROOT / "candidates" / "cpcb-aqi-exceedance"

job = json.loads((ROOT / "jobs" / "cpcb-aqi-publish-001.json").read_text())
assert job["status"] == "deleted"
res = job["result"]
assert res["status"] == "succeeded" and res["uploaded"] is True
transferred = res["transfer"]["transferred"]
assert len(transferred) == 5 and res["transfer"]["failures"] == []

record_path = CAND / "record.json"
record = json.loads(record_path.read_text())
now = datetime.now(timezone.utc).isoformat(timespec="seconds")

record["measurements"]["private_staging_github_2026_11_06"] = {
    "recorded_at": now,
    "step": "GitHub destination of the private staging (dataset-release); the Hub destination, "
            "the fresh-consumer job, DESTINATIONS.json and the packaged/awaiting_operator "
            "recording have NOT run yet",
    "repo_created": "earino/cpcb-aqi-exceedance, private=true (gh api -X POST /user/repos); "
                    "25 package files committed as the initial commit cb3b251faa9e3cac37231746474585cc77f6f9c9 "
                    "from release/cpcb-aqi-exceedance/; release v2026.11 (436366305) created "
                    "non-draft at main with no assets",
    "transfer_job": {
        "id": "cpcb-aqi-publish-001",
        "server": job["server_id"],
        "reservation_eur": job["reservation_eur"],
        "staging_release_source": 436180445,
        "target_release": 436366305,
        "result": "succeeded, uploaded, 5/5 transferred, failures []",
        "job_reports_release": res.get("release_id"),
        "cleanup": "worker destroyed 2026-11-06T10:36:21Z; provider read-back "
                   "GET /v1/servers/174785899 -> 404 not_found",
        "assets": {t["target_name"]: {"asset_id": t["asset_id"], "bytes": t["bytes"],
                                      "sha256": t["sha256"]} for t in transferred},
    },
    "server_side_verification": "live authenticated read-back: repo private=true, default "
                                "branch main, release 436366305 non-draft tag v2026.11, "
                                "exactly the five flat assets, every GitHub-reported "
                                "sha256 digest equal to the package MANIFEST.json "
                                "(meta.json 1f59e74e, private-holdout.csv 2dae0040, "
                                "public-eval.csv e187f645, public-train.csv 24b03a70, "
                                "quality.json 98250e9d); anonymous API read-back correctly "
                                "404s (private)",
    "bytes_through_coordinator": "none (88.8 MB moved worker-side; only compact metadata "
                                 "was fetched: the 1,197 B meta.json during packaging)",
}

record["updated_at"] = now
record["next_action"] = (
    "PRIVATE STAGING IN PROGRESS - GitHub destination DONE and verified (repo "
    "earino/cpcb-aqi-exceedance private, 25-file initial commit cb3b251, release 436366305 "
    "non-draft tag v2026.11, 5/5 assets server-side digest-equal to MANIFEST.json; "
    "cpcb-aqi-publish-001 succeeded, worker 174785899 destroyed with 404 read-back, job "
    "reports at staging release 436368409). Remaining, in order: (1) the fresh-consumer "
    "worker job on the released bytes (cqc consumer/source pattern, fetch block from "
    "release 436366305 asset ids): package-vs-MANIFEST check, get_dataset.py re-verification, "
    "sha256sum -c, gate 1.5.0 re-run, exact-byte --accept against qualification.json "
    "(a749f0df), declared imports, baseline reproduce (both AUC prints 0.9734, CONTRACT OK, "
    "quoted beside station_persistence 0.9689 / climatology 0.8617), score.py references "
    "recomputed equal to measurements.json; a rebuild-from-export step is NOT required "
    "(the build refuses any changed export; REPRODUCE.md documents it as optional); "
    "(2) hf-publish.py --plan then --create --upload-small (private Hub repo, docs, card), "
    "the hf_publish worker job, --verify, --tag LAST; (3) "
    "release/cpcb-aqi-exceedance/DESTINATIONS.json both blocks (github: verified release "
    "436366305, tag v2026.11, artifact_version a749f0df..., files_verified as the list of "
    "every logical manifest path; hub: revision, hf_loading, its files_verified list); "
    "(4) record -> packaged with packaged_at + artifacts[0] structured release identity "
    "(check-candidate requires it of packaged records), awaiting_operator TRUE only after "
    "the pre-flip adversarial audit prompt is generated (from "
    "skills/dataset-release/templates/pre-flip-audit-prompt.md, digests filled "
    "programmatically from the frozen manifest); then check-candidate --all, check-package, "
    "check-suitability, suite. The flip stays the operator's single approval and waits for "
    "the independent auditor's verdict unless waived. Holdout sealed; no re-tuning after "
    "any score."
)

record_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
print("record updated: measurements.private_staging_github_2026_11_06 + next_action")
print("transfer assets recorded:", sorted(t["target_name"] for t in transferred))
