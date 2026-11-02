#!/usr/bin/env python3
"""Fix the ocha-fts record after check-candidate's correct refusal.

status 'packaged' claims a staged release exists (artifacts[] non-empty). The
GitHub/Hub staging has not run yet, so the record goes back to 'qualified' with
the package-built state named exactly: package built + check-package rc=0, and
staging as the next step. Same order pins used (staging verified 22:30Z, then
packaged_at 22:36Z).
"""
import datetime
import json
import pathlib

REPO = pathlib.Path("/opt/data/dataset-factory")
REC = REPO / "candidates/ocha-fts-appeal-funding-trajectory/record.json"

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
stamp = now.isoformat().replace("+00:00", "Z")

record = json.loads(REC.read_text())
assert record["status"] == "packaged"
record["status"] = "qualified"
record.pop("packaged_at", None)
record["package_built"] = {
    "at": "2026-11-02T15:53:01Z",
    "package": "release/ocha-fts-appeal-funding-trajectory/ (v2026.11)",
    "artifact_version": "ac529cd4e9d4da90f804ecef425e74c94a946b857fe39095fd73a0407506b8c0",
    "check_package": "rc=0 (2026-11-02, after release-manifest.py wrote MANIFEST.json + SHA256SUMS)",
    "packaged_claim_note": "status stays 'qualified' until the private GitHub staging exists: check-candidate's RELEASED-shape rule requires the artifacts entry to carry the staged release. packaged_at is set after staging verifies, the pins order.",
}
record["next_action"] = (
    "PACKAGE BUILT AND VERIFIED (2026-11-02): release/ocha-fts-appeal-funding-trajectory/ carries the "
    "v2026.11 package - the accepted artifact ac529cd4 bytes (meta.json + quality.json copied "
    "digest-asserted from staging release 431492902), the fts-appeal-003 gate report, code/ (build.py, "
    "run.sh, score.py, materialize.py, the canonical gate 1.5.0), baseline/ (the benchmark runner files "
    "verbatim + reproduce script), the docs (README, DATA_DICTIONARY, LICENSE, REPRODUCE, RELEASE_NOTES, "
    "VERIFICATION, measurements.json), get_dataset.py (digests generated from expected_artifact.json), "
    "MANIFEST.json + SHA256SUMS via release-manifest.py. check-package rc=0. Status stays 'qualified' "
    "until staging exists (check-candidate requires artifacts[] non-empty for 'packaged'). Recorded "
    "finding carried in the package: stock runner 0.6452 vs persistence 0.7171136653895275 on the "
    "identical 139 eval rows - no demonstrated headroom under this protocol, with the "
    "information-asymmetry note (model deliberately denied the last prior outcome under the P0 "
    "standard; persistence reads it scorer-side). NEXT STEPS, in order (all private; nothing public): "
    "(1) GitHub staging - create private repo earino/ocha-fts-appeal-funding-trajectory, commit the "
    "package documents as the initial commit, create draft release v2026.11, then a release-flagged "
    "worker transfer job copying the five accepted assets from staging release 431492902 into it "
    "(source asset ids already resolved in baseline/job.json's fetch block: meta.json=701847475, "
    "train.csv=701847723, eval.csv=701847633, holdout.csv=701847549, quality.json=701847792); verify "
    "name/size/server-side digest per asset; publish tag == main == the docs commit; "
    "(2) DESTINATIONS.json github block (files_verified as the five logical manifest paths) + consumer "
    "check: get_dataset.py end-to-end against the private release and gate --accept on the downloaded "
    "tree, per the unhcr/pins precedent; THEN set status=packaged + packaged_at; "
    "(3) Hub staging cycle: hf-publish.py --plan, --create --upload-small (card generated from "
    "MANIFEST.json), hf_publish worker job from the staged GitHub release, --verify --worker-job, "
    "--tag LAST; DESTINATIONS.json hub block (artifact_version == manifest ac529cd4); "
    "(4) suitability: version-bound suitability record for this exact artifact + "
    "scripts/check-suitability.py, public notice into card/LOADING; "
    "(5) regenerate the pre-flip audit prompt programmatically from the frozen manifest "
    "(templates/pre-flip-audit-prompt.md; digests never hand-copied) - the fresh independent audit MUST "
    "re-attack the rebuilt bytes label-blind (the 2026-11-01 queue audit's frozen attack code is the "
    "baseline; it must now find no operand columns) - then set awaiting_operator: true. The flip stays "
    "the operator's single approval. Do not re-run fts-appeal-003 or fts-baseline-002; the holdout stays "
    "sealed. One cx23 worker at a time; November budget month."
)
record["updated_at"] = stamp
REC.write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n")
print("record: status=qualified (package built, staging pending)")
