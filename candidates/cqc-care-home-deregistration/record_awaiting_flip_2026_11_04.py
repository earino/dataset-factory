#!/usr/bin/env python3
"""Record the cqc-care-home-deregistration flip boundary (2026-11-04 session).

The remaining publisher-side steps ran this session:
  1. hf-publish.py --verify --worker-job cqc-hf-001  (all five files digest-verified
     at Hub main fea98b695abd..., repo private)
  2. hf-publish.py --tag                            (tag v2026.11 created at
     tag == main == fea98b695abd..., release_revision_verified true; DESTINATIONS
     hub block now carries revision v2026.11; anonymous Hub API + tag read-back 401)
  3. check-package.py release/cqc-care-home-deregistration -> OK (rc=0, twice:
     after the hub-note refresh and after the artifact_version field addition)
  4. site plan prepared offline: .factory/sites/cqc-v2026.11-1,
     plan_sha256 3a04e87601cbfa5f6cd91c6efcbba0b5aeac80baf2a3f73a0619c6d994b5ac3b,
     prepare made zero network calls; inspect: both destinations private + verified,
     catalogue repo public with Pages, ready_for_publication false by design;
     previews render with no unresolved placeholders and a concrete
     load_dataset('earino/cqc-care-home-deregistration', revision='v2026.11') snippet.
  5. release/cqc-care-home-deregistration/DESTINATIONS.json: stale hub note refreshed
     (verify+tag ran) and the required top-level artifact_version field added
     (afe9ee203f302f3c..., equal to the manifest - the site planner refuses
     without it).

This script:
  3. moves the record to awaiting_operator: true with scope and since-stamp
     (the flip is now the sole remaining step; the flip waits for the
     independent auditor verdict unless the operator waives it)
  4. rewrites next_action so a fresh session knows the flip procedure and
     the website plan pin.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECORD = ROOT / "candidates" / "cqc-care-home-deregistration" / "record.json"

NOW_ISO = "2026-11-04T14:03:00Z"

SCOPE = (
    "the private-to-public flip of earino/cqc-care-home-deregistration on both "
    "destinations; both are staged, verified and private (GitHub release 433767120 "
    "tag v2026.11 == main == 8bc008af; Hub tag v2026.11 == main == fea98b695abd...); "
    "the independent pre-flip audit prompt is at "
    "candidates/cqc-care-home-deregistration/pre-flip-audit-prompt.md (digests filled "
    "programmatically from the frozen manifest) and the flip waits for the auditor's "
    "verdict unless the operator waives it; the website plan .factory/sites/"
    "cqc-v2026.11-1 (plan_sha256 "
    "3a04e87601cbfa5f6cd91c6efcbba0b5aeac80baf2a3f73a0619c6d994b5ac3b) is prepared and "
    "inspected offline and publishes only after the flip with that operator-reviewed plan"
)

NEXT_ACTION = (
    "AWAITING OPERATOR (flip is the sole remaining step; publisher side complete, "
    "nothing public, holdout sealed on both destinations). v2026.11 is staged private "
    "and verified on BOTH destinations: GitHub earino/cqc-care-home-deregistration "
    "release 433767120 (tag v2026.11 == main == 8bc008af, 5 flat assets at the package "
    "MANIFEST digests, server-side digest-verified by cqc-publish-001, fresh-consumer "
    "green end-to-end by cqc-consumer-001) and Hugging Face earino/"
    "cqc-care-home-deregistration (tag v2026.11 == main == fea98b695abd..., all five "
    "files digest-verified by cqc-hf-001 and re-verified by hf-publish.py --verify; "
    "tag created by hf-publish.py --tag 2026-11-04T14:01Z, release_revision_verified "
    "true; anonymous Hub API read-back 401). The accepted artifact afe9ee203f302f3c... "
    "sits at those digests on both destinations. OPERATOR PATH: (1) relay "
    "candidates/cqc-care-home-deregistration/pre-flip-audit-prompt.md to an independent "
    "auditor; the flip waits for that verdict unless the operator waives it; (2) the "
    "operator's single flip approval (both destinations; never change inference auth to "
    "publish). AFTER THE FLIP (no further approval needed): anonymous verification from "
    "a credential-less client (repo page 200, ranged GET on every asset, Hub API "
    "private:false, data files at the tag revision), record visibility + note in "
    "DESTINATIONS.json (files_verified lists preserved), refresh current editorial "
    "copies (card via hf-publish.py --upload-small, LOADING.md, repository README, "
    "release notes - apply-navigation so the managed links are present), re-run "
    "check-package.py, carry the check-suitability.py public notice, then the website "
    "pipeline publish/verify with the operator-reviewed plan sha "
    "3a04e87601cbfa5f6cd91c6efcbba0b5aeac80baf2a3f73a0619c6d994b5ac3b "
    "(.factory/sites/cqc-v2026.11-1). Tag last already satisfied for the data "
    "destinations; the site publishes after the flip. NO new construction while this "
    "candidate is actionable-packaged; after awaiting_operator was set (2026-11-04) "
    "the human wait exempts the queue."
)

def main() -> int:
    record = json.loads(RECORD.read_text())
    assert record["status"] == "packaged", record["status"]
    assert record["packaged_at"] == "2026-11-04T10:51:08Z"
    assert record["awaiting_operator"] is False, "already awaiting"
    record["awaiting_operator"] = True
    record["awaiting_operator_scope"] = SCOPE
    record["awaiting_operator_since"] = NOW_ISO
    record["next_action"] = NEXT_ACTION
    record["updated_at"] = NOW_ISO
    RECORD.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print("record: status=%s packaged_at=%s awaiting_operator=%s since=%s"
          % (record["status"], record["packaged_at"], record["awaiting_operator"],
             record["awaiting_operator_since"]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
