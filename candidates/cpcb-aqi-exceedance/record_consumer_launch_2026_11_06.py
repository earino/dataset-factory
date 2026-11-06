#!/usr/bin/env python3
"""Record the 2026-11-06 consumer-job launch and the prepared HF destination
for cpcb-aqi-exceedance. Reads only collected state; touches only the record's
jobs list and next_action."""
import json
from pathlib import Path

RECORD = Path("candidates/cpcb-aqi-exceedance/record.json")


def main() -> int:
    record = json.loads(RECORD.read_text())

    record["jobs"].append({
        "id": "cpcb-aqi-consumer-001",
        "kind": "fresh-consumer verification (running at close-out)",
        "launched_at": "2026-11-06T11:54:20Z",
        "server_id": 174799070,
        "status": "running",
        "reservation_eur": "0.32",
        "what": ("fresh-consumer worker job on the released bytes of private GitHub release "
                 "436366305: package-vs-MANIFEST, get_dataset.py re-verification, sha256sum -c, "
                 "gate 1.5.0 re-run on the full artifact, exact-byte --accept (a749f0df), "
                 "declared imports, baseline reproduce (both AUC prints 0.9734, CONTRACT OK, "
                 "holdout never copied into a workdir), score.py references recomputed equal to "
                 "measurements.json, and the pre-registered deciding check recomputed on the "
                 "released bytes (model-minus-persistence [0.0038, 0.0052], "
                 "model-minus-climatology [0.1002, 0.1252], model AUC CI above 0.5) through the "
                 "shipped train.py + score.py; the optional rebuild-from-export step is not run "
                 "(build.py refuses any changed export; REPRODUCE.md documents it as optional)"),
        "source": ("candidates/cpcb-aqi-exceedance/consumer/source/ (job.json fetch block "
                   "resolved by digest match through the live release API: assets 716781985, "
                   "716782078, 716782178, 716782327, 716782494, sizes equal to MANIFEST.json); "
                   "assembled bundle .factory/jobs/cpcb-aqi-consumer-001"),
    })

    record["next_action"] = (
        "PRIVATE STAGING, GITHUB DONE, CONSUMER JOB RUNNING, HF PREPARED. "
        "(1) cpcb-aqi-consumer-001 (launched 2026-11-06T11:54:20Z, worker 174799070, "
        "reservation EUR 0.32, status running at session close ~12:10Z; expected elapsed "
        "~25-40 min on cpx32): collect with `sh scripts/scout-factory worker collect "
        "cpcb-aqi-consumer-001`, then destroy + provider 404 read-back. ACCEPTANCE: exit 0 "
        "and consumer.txt shows every step green - PACKAGE OK (24 files vs MANIFEST.json), "
        "5 assets host-fetched digest-verified, get_dataset.py re-verification OK, "
        "sha256sum -c 5/5 OK, gate 1.5.0 PASSED on the published bytes, --accept ACCEPTED "
        "a749f0df2f9dd0103d0ba56524e1cc3638242fbc4710b0cac99603bcdef0d959, both AUC prints "
        "0.9734 with CONTRACT OK and the holdout-not-copied marker, references recomputed "
        "equal to measurements.json (check_references.py), deciding check reproduced "
        "(decide_check.py: model-minus-persistence [0.0038, 0.0052], model-minus-climatology "
        "[0.1002, 0.1252], verdict headroom_demonstrated). If it failed: keep the collected "
        "reports, diagnose before any retry (one changed retry per defect); infrastructure "
        "failure is not a verdict. "
        "(2) Hugging Face destination - ALL SOURCES PREPARED AND PLANNED THIS SESSION: "
        "card.md written (test_hf_card 7/7 OK), candidates/cpcb-aqi-exceedance/hf/job.json "
        "written (cpcb-aqi-hf-001, plan OK, reservation EUR 0.04, credential "
        "FACTORY_HF_WRITE_TOKEN_FILE resolved at plan time): after the consumer job is "
        "green and the worker destroyed, run `python3 scripts/hf-publish.py --plan "
        "--candidate cpcb-aqi-exceedance` (already green), then `--create --upload-small` "
        "(private Hub repo, docs, generated card), `sh scripts/scout-factory worker plan "
        "candidates/cpcb-aqi-exceedance/hf/job.json` (already OK) and `launch`, then "
        "`python3 scripts/hf-publish.py --verify --candidate cpcb-aqi-exceedance` "
        "(exit 0 required; use --worker-job cpcb-aqi-hf-001 for the bulk-blob evidence), "
        "then `--tag` LAST (tag v2026.11 == main, idempotent). "
        "(3) release/cpcb-aqi-exceedance/DESTINATIONS.json both blocks (github: release "
        "436366305 verified incl. the consumer job evidence, files_verified = every logical "
        "manifest path; hub: revision, hf_loading, its data/ files_verified list). "
        "(4) record -> packaged: packaged_at + artifacts[0] structured release identity "
        "(check-candidate requires it), generate the pre-flip adversarial audit prompt from "
        "skills/dataset-release/templates/pre-flip-audit-prompt.md with digests filled "
        "programmatically from the frozen manifest, then awaiting_operator TRUE. "
        "(5) checks: check-candidate --all, check-package, check-suitability, full suite; "
        "commit/push and read CI for that exact commit. The flip stays the operator's "
        "single approval and waits for the independent auditor's verdict unless waived. "
        "Holdout sealed; no re-tuning after any score."
    )

    record["updated_at"] = "2026-11-06T12:10:30Z"
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print("record updated: consumer job appended, next_action rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
