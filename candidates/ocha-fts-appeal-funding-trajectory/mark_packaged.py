#!/usr/bin/env python3
"""Mark ocha-fts-appeal-funding-trajectory packaged: the package is built and check-package passes.

Sets status/packaged_at and rewrites next_action to the remaining private-staging
steps, with the staging-release asset ids read from the recorded fetch block
(never typed).
"""
import datetime
import json
import pathlib

REPO = pathlib.Path("/opt/data/dataset-factory")
REC = REPO / "candidates/ocha-fts-appeal-funding-trajectory/record.json"
FETCH = REPO / "candidates/ocha-fts-appeal-funding-trajectory/baseline/job.json"

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
stamp = now.isoformat().replace("+00:00", "Z")

fetch = json.loads(FETCH.read_text())
ids = ", ".join(
    f"{a['dest'].split('/')[-1]}={a['asset_id']}" for a in fetch["fetch"]["assets"]
)
release_id = fetch["fetch"]["release"]

record = json.loads(REC.read_text())
record["status"] = "packaged"
record["packaged_at"] = stamp
record["next_action"] = (
    "PACKAGE BUILT AND VERIFIED (2026-11-02): release/ocha-fts-appeal-funding-trajectory/ carries the "
    "v2026.11 package - the accepted artifact ac529cd4 bytes (meta.json + quality.json copied "
    "digest-asserted from staging release 431492902), the fts-appeal-003 gate report, code/ (build.py, "
    "run.sh, score.py, materialize.py, the canonical gate 1.5.0), baseline/ (the benchmark runner files "
    "verbatim + reproduce script), the docs (README, DATA_DICTIONARY, LICENSE, REPRODUCE, RELEASE_NOTES, "
    "VERIFICATION, measurements.json), get_dataset.py (digests generated from expected_artifact.json), "
    "MANIFEST.json + SHA256SUMS via release-manifest.py. check-package rc=0. Recorded finding carried in "
    "the package: stock runner 0.6452 vs persistence 0.7171136653895275 on the identical 139 eval rows - "
    "no demonstrated headroom under this protocol, with the information-asymmetry note. NEXT STEPS, in "
    "order (all private; nothing public): (1) GitHub staging - create private repo "
    "earino/ocha-fts-appeal-funding-trajectory, commit the package documents as the initial commit, "
    f"create draft release v2026.11, then a release-flagged worker transfer job copying the five accepted "
    f"assets from staging release {release_id} into it (source asset ids already resolved in "
    f"baseline/job.json's fetch block: {ids}); verify name/size/server-side digest per asset; "
    "(2) DESTINATIONS.json github block (files_verified as the five logical manifest paths) + consumer "
    "check: get_dataset.py end-to-end against the private release (5 files, sizes + sha256 verified, "
    "runner layout) and gate --accept on the downloaded tree, per the unhcr/pins precedent; "
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
print("record: status=packaged packaged_at=" + stamp)
print("staging release", release_id, "asset ids:", ids)
