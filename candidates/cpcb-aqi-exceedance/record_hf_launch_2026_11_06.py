#!/usr/bin/env python3
"""Record the 2026-11-06 HF-destination progress for cpcb-aqi-exceedance:
--create --upload-small done (private Hub repo, 10 small files), bulk job
cpcb-aqi-hf-001 launched and running at close-out. Touches only the record's
jobs list and next_action."""
import json
from pathlib import Path

RECORD = Path("candidates/cpcb-aqi-exceedance/record.json")


def main() -> int:
    record = json.loads(RECORD.read_text())

    record["jobs"].append({
        "id": "cpcb-aqi-hf-001",
        "kind": "hf_publish (running at close-out)",
        "launched_at": "2026-11-06T14:43:40Z",
        "server_id": 174825952,
        "status": "running",
        "reservation_eur": "0.04",
        "what": ("bulk Hub upload for the HF destination: fetch the five released "
                 "assets of private GitHub release 436366305 at their recorded asset "
                 "ids (digests equal to MANIFEST.json), verify each sha256 on "
                 "arrival, upload each to the private Hub repo "
                 "earino/cpcb-aqi-exceedance with the Hub-reported digest verified "
                 "after upload, delete the local copy, and run the documented "
                 "load_dataset path against the uploaded bytes (splits train "
                 "288754/61075 pos, eval 126570/19819, holdout 145124/18222). "
                 "Bytes never pass through the coordinator; peak worker disk is one "
                 "asset (88.8 MB total)."),
        "source": ("candidates/cpcb-aqi-exceedance/hf/job.json (assembled bundle "
                   "source_sha256 7ba877cea13d5e9a0b87b6c047ce0ed6f7a6d07d1912658dd9815ba783029578, "
                   "plan rc=0, 0 cloud calls); expires ~2026-11-06T16:23:40Z"),
    })

    record["next_action"] = (
        "PRIVATE STAGING, GITHUB DONE, CONSUMER GREEN, HF SMALL FILES UPLOADED, "
        "BULK HF JOB RUNNING. (1) CLOSED 2026-11-06: consumer-002 green on the "
        "released bytes (see measurements.consumer_002_fresh_consumer_2026_11_06). "
        "(2) PARTLY DONE 2026-11-06 (this session): hf-publish.py --plan green "
        "(artifact a749f0df, tag v2026.11); --create --upload-small DONE with the "
        "write credential file - private Hub repo earino/cpcb-aqi-exceedance "
        "created (acting account earino, token role write, private: true "
        "confirmed in the API answer) and 10 small files uploaded "
        "(DATA_DICTIONARY.md, LICENSE-CC0-1.0.txt, LICENSE-MIT.txt, LICENSE.md, "
        "LOADING.md, MANIFEST.json, README.md, SHA256SUMS, VERIFICATION.md, "
        "measurements.json). REMAINING in (2): collect cpcb-aqi-hf-001 "
        "(launched 2026-11-06T14:43:40Z, worker 174825952, reservation EUR 0.04, "
        "status running at close ~15:20Z, timeout 40 min so it self-terminates by "
        "~15:23:40Z if hung): `sh scripts/scout-factory worker collect "
        "cpcb-aqi-hf-001`, ACCEPTANCE = exit 0 and the job report shows all five "
        "assets fetched at the manifest digests, each uploaded with the "
        "Hub-reported digest verified, local copies deleted, and the "
        "load_dataset check green (splits/positives/columns/label equal to "
        "hf/job.json verify_loading). If it failed: keep the collected reports, "
        "diagnose before any retry (one changed retry per defect); infrastructure "
        "failure is not a verdict. Then destroy the worker with provider 404 "
        "read-back, then `python3 scripts/hf-publish.py --verify --candidate "
        "cpcb-aqi-exceedance --worker-job cpcb-aqi-hf-001 --token-file "
        "/opt/data/.secrets/huggingface-write.token` (exit 0 required; writes the "
        "huggingface block of DESTINATIONS.json), then `--tag` LAST (tag v2026.11 "
        "== verified main commit, idempotent). "
        "(3) release/cpcb-aqi-exceedance/DESTINATIONS.json github block (write "
        "programmatically, same shape as eutl): repo earino/cpcb-aqi-exceedance, "
        "release_id 436366305, tag v2026.11, target_commit cb3b251faa9e3cac37231746474585cc77f6f9c9 "
        "re-read from the API, private true, verified true + now timestamp, "
        "files_verified = every logical manifest path (public/train.csv, "
        "public/eval.csv, private/holdout.csv, meta.json, quality.json), checks "
        "citing the transfer job cpcb-aqi-publish-001 (5/5, failures []), the "
        "live server-side read-back and the consumer-002 evidence; top-level "
        "artifact_version a749f0df2f9dd0103d0ba56524e1cc3638242fbc4710b0cac99603bcdef0d959. "
        "(4) record -> packaged: packaged_at + artifacts[0] structured release "
        "identity (kind destination_release repo earino/cpcb-aqi-exceedance id "
        "436366305 tag v2026.11 commit cb3b251f... + kind destination_hub_repo "
        "revision v2026.11, both with artifact_version a749f0df), generate the "
        "pre-flip adversarial audit prompt from "
        "skills/dataset-release/templates/pre-flip-audit-prompt.md with digests "
        "filled programmatically from the frozen manifest, then "
        "awaiting_operator TRUE. (5) checks: check-candidate --all, "
        "check-package release/cpcb-aqi-exceedance, check-suitability, full "
        "suite; commit/push and read CI for that exact commit. The flip stays "
        "the operator's single approval and waits for the independent auditor's "
        "verdict unless waived. Holdout sealed; no re-tuning after any score.")

    record["updated_at"] = "2026-11-06T15:20:00Z"
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print("record updated: jobs +cpcb-aqi-hf-001 (running), next_action -> collect hf-001")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
