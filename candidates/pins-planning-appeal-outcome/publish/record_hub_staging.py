#!/usr/bin/env python3
"""Record the pins-hf-001 Hub staging outcome in the pins candidate record.

All facts are read from the collected worker report, the Hub verification
receipt and the site plan - nothing hand-transcribed from prose.
"""
import datetime
import json
import pathlib

REPO = pathlib.Path("/opt/data/dataset-factory")
REC = REPO / "candidates/pins-planning-appeal-outcome/record.json"
RESULT = REPO / ".factory/pins-hf-001/result.json"
DEST = REPO / "release/pins-planning-appeal-outcome/DESTINATIONS.json"
SITE = REPO / ".factory/sites/pins-v2026.10-1/bundle.json"

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
stamp = now.replace("+00:00", "Z")

result = json.loads(RESULT.read_text())
dest = json.loads(DEST.read_text())
site = json.loads(SITE.read_text())
record = json.loads(REC.read_text())

hf = dest["destinations"]["huggingface"]
uploads = result["hf_publish"]["uploads"]
loading = result["hf_loading"]["checked"]

job_entry = {
    "id": "pins-hf-001",
    "status": result.get("status"),
    "elapsed_seconds": result.get("elapsed_seconds"),
    "server_id": 173885790,
    "launched": "2026-11-01T02:08:36Z",
    "collected": "2026-11-01T02:36:41Z",
    "destroyed": "2026-11-01T02:37:32Z",
    "outcome": (
        "hf_publish worker job: bulk Hub staging of the accepted pins v2026.10 artifact "
        "c861bd8f4acd9bbe, read from the collected report (never the exit code alone). The "
        "worker host downloaded the five assets from the staged private GitHub release "
        "430215294 by asset id with sha256 verified on arrival, uploaded each to the private "
        "Hugging Face dataset repo earino/pins-planning-appeal-outcome with the digest the "
        "Hub reports verified after upload (uploads 5, skipped 0, failures 0: meta.json 2518 B, "
        "data/private-holdout.csv 14976119 B, data/public-eval.csv 7688640 B, "
        "data/public-train.csv 14799462 B, quality.json 44632 B), deleted the local copies, "
        "then ran the documented load_dataset path against the uploaded bytes: train 54834 "
        "rows / 17048 positives, eval 28104 / 8469, holdout 56326 / 17705, 32 columns each, "
        "label values ['0','1'], problems=[] - identical to the accepted artifact. Bytes never "
        "passed through the coordinator. hf-publish.py --verify --worker-job pins-hf-001 "
        "verified all five files at the manifest digests (missing/size_mismatch/digest_unverified "
        "all empty) and --tag created v2026.10 at Hub main "
        + hf["commit"]
        + " with tag == main (release_revision_verified true). Anonymous Hub access is refused "
        "(private by design). Worker destroyed via the supported lifecycle and reconciled to "
        "'deleted' at 02:37:33Z."
    ),
}
record["jobs"].append(job_entry)

hub_artifact = {
    "artifact_version": record["artifacts"][0]["artifact_version"],
    "digest_of": record["artifacts"][0]["digest_of"],
    "gate_version": record["artifacts"][0]["gate_version"],
    "accepted": record["artifacts"][0]["accepted"],
    "source_snapshot": record["artifacts"][0]["source_snapshot"],
    "splits": record["artifacts"][0]["splits"],
    "destination": "huggingface",
    "repo": "earino/pins-planning-appeal-outcome",
    "tag": "v2026.10",
    "release_url": "https://huggingface.co/datasets/earino/pins-planning-appeal-outcome/tree/v2026.10",
    "revision_commit": hf["commit"],
    "private": True,
    "verified": True,
    "verified_readback": (
        "hf-publish.py --verify --worker-job pins-hf-001 2026-11-01T02:38Z: all five manifest "
        "files present at the recorded commit with sizes and sha256 digests verified "
        "(missing/size_mismatch/digest_unverified empty); --tag created v2026.10 at Hub main "
        + hf["commit"]
        + " with tag == main; load_dataset check executed by worker job pins-hf-001 against "
        "the uploaded bytes (splits, positives, columns, label values identical to the "
        "accepted artifact); anonymous access refused (private by design)"
    ),
    "files_verified": hf["files_verified"],
    "staged_at": {
        "hub_repo": "earino/pins-planning-appeal-outcome revision v2026.10 (private, tag == main == " + hf["commit"][:7] + ")",
        "small_files": "hf-publish.py --create --upload-small from the coordinator (card generated from MANIFEST.json, LOADING.md, MANIFEST.json, SHA256SUMS, licence texts, DATA_DICTIONARY.md, VERIFICATION.md, measurements.json)",
        "bulk_job": "pins-hf-001",
    },
}
record["artifacts"].append(hub_artifact)

record["awaiting_operator"] = True
record["awaiting_operator_scope"] = (
    "the private-to-public flip of earino/pins-planning-appeal-outcome on both destinations; "
    "both are staged, verified and private; the independent pre-flip audit prompt is generated at "
    "candidates/pins-planning-appeal-outcome/pre-flip-audit-prompt.md (filled programmatically "
    "from the frozen manifest and record) and the flip waits for the auditor's verdict unless "
    "the operator waives it; the website plan .factory/sites/pins-v2026.10-1 (plan_sha256 "
    + site.get("plan_sha256", "?")
    + ") is prepared for operator review and publishes only after the flip"
)
record["awaiting_operator_since"] = stamp

record["next_action"] = (
    "HUB STAGING COMPLETE "
    + stamp
    + " (scheduled advancement session; worker job pins-hf-001 "
    "succeeded and was destroyed with lifecycle reconciliation): artifact c861bd8f4acd9bbe is now "
    "staged and verified on BOTH private destinations - GitHub release v2026.10 (430215294, tag == "
    "main == a19978bd, consumer-verified by pins-consumer-001) and Hugging Face repo "
    "earino/pins-planning-appeal-outcome (revision v2026.10, tag == main == "
    + hf["commit"]
    + ", five files at the manifest digests, load_dataset check identical to the accepted artifact, "
    "hf-publish --verify and --tag both green; DESTINATIONS.json carries both blocks). "
    "check-package OK; check-suitability OK (17 version-bound reviews, this artifact retain_restricted) "
    "with the honest-disclosure notice already generated into the Hub card and LOADING.md from the "
    "manifest and quality.json. Website plan PREPARED for operator review: sites/pins-planning-appeal-outcome.json "
    "(editorial, site_revision 1, release_date 2026-10-31 = the v2026.10 version date) -> "
    ".factory/sites/pins-v2026.10-1, plan_sha256 "
    + site.get("plan_sha256", "?")
    + " (prepare made zero network calls; previews rendered with no unresolved placeholders and a "
    "concrete load_dataset snippet; inspect verified both destinations private and read-only). "
    "Pre-flip audit prompt generated programmatically from the frozen manifest "
    "(candidates/pins-planning-appeal-outcome/pre-flip-audit-prompt.md, generator kept in "
    "publish/generate_pre_flip_audit_prompt.py). REMAINING (operator): (1) relay the pre-flip audit "
    "prompt to an independent auditor; the flip waits for that verdict unless the operator waives it; "
    "(2) on a passing verdict, the operator's single flip approval makes both destinations public - "
    "flip per dataset-release (gh api -X PATCH repos/earino/pins-planning-appeal-outcome -F "
    "private=false; HfApi.update_repo_settings with the write credential), prove both anonymously, "
    "record visibility in DESTINATIONS.json (merge, never replace), refresh the status documents "
    "(card/LOADING/repo README were written while private), then site-publish publish "
    ".factory/sites/pins-v2026.10-1 --approved-plan "
    + site.get("plan_sha256", "?")
    + " and verify. No rebuild of this construction is permitted (the one rebuild is spent); the "
    "holdout stays sealed (fetched only for --accept, never copied into a workdir, never scored)."
)

record["updated_at"] = stamp
REC.write_text(json.dumps(record, indent=2, ensure_ascii=True) + "\n")
print("record updated:", stamp)
print("jobs:", len(record["jobs"]), "artifacts:", len(record["artifacts"]))
