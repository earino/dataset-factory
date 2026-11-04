#!/usr/bin/env python3
"""Apply the recorded unhcr drop decision's mechanical marking (2026-11-04 session).

The operator decision was applied 2026-11-02 (see record next_action): the v2026.10
panel package is DROPPED and never to be flipped. This session executed the recorded
marking step on both destinations:

  - GitHub: release 426752344 renamed "v2026.10" -> "v2026.10 - DROPPED, DO NOT
    PUBLISH" (gh api -X PATCH, then read back; matches the nhs-ae v2026.12 precedent).
  - Hugging Face: a "DROPPED - DO NOT PUBLISH" banner prepended to README.md on
    editorial main (idempotent script mark_hub_superseded_2026_11_04.py; tag v2026.10
    untouched at 77aa1fad..., repo private, main advanced to 0c2d3cf8... by exactly
    the banner commit).

This script then:
  1. adds the `superseded` list to release/unhcr-refugee-data-finder/DESTINATIONS.json
     (the recorded convention from the dataset-release skill), and
  2. moves the candidate record to status=parked with the decision as the terminal
     reason, clearing the now-false operator_decision_pending marker (the decision is
     applied and mechanically executed; parked status exempts the preemption guard
     naturally).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECORD = ROOT / "candidates" / "unhcr-refugee-data-finder" / "record.json"
DEST = ROOT / "release" / "unhcr-refugee-data-finder" / "DESTINATIONS.json"

NOW_ISO = "2026-11-04T14:06:30Z"

REJECTION_REASON = (
    "Operator decision applied 2026-11-02: the v2026.10 panel package 6bd0c307 is "
    "DROPPED - never to be flipped in this form. Two independent audits (the 2026-10-28 "
    "Codex pre-flip audit and the 2026-11-01 queue re-audit) found the panel "
    "self-answers by construction: a label-year T+1 row ships the year-T total that is "
    "the T row's label operand (frozen recoveries reached eval AUC 0.975325 / holdout "
    "0.983034), and the leak is the task's core quantity - removing it means killing "
    "the momentum features (the only real signal) or one-shotting corridors. Reopen "
    "condition: a redesigned task that keeps corridor momentum WITHOUT adjacent "
    "corridor-years both shipping (e.g. a one-shot per-corridor design, or an "
    "aggregate-outcome label), constructed and audited fresh from the source."
)

NEXT_ACTION = (
    "PARKED on the reopen condition; the drop decision's mechanical marking is APPLIED "
    "(2026-11-04). Both destinations stay PRIVATE indefinitely and are marked so no "
    "later session can mistake the staging for flippable: GitHub release 426752344 "
    "(earino/unhcr-refugee-data-finder) is renamed \"v2026.10 - DROPPED, DO NOT "
    "PUBLISH\" (API read-back confirmed), and the Hugging Face repo carries a "
    "\"DROPPED - DO NOT PUBLISH\" banner on editorial main (README.md, main advanced "
    "to 0c2d3cf8... by exactly that commit; the data tag v2026.10 stays frozen at "
    "77aa1fad...; repo private). release/unhcr-refugee-data-finder/DESTINATIONS.json "
    "records both markings under `superseded`; the frozen package bytes, digests and "
    "tag are untouched. REOPEN (only path): a redesigned task per the recorded "
    "condition - constructed and audited fresh from the source, as a new artifact with "
    "a fresh attempt ID; the v2026.10 package itself is never published, and the "
    "corrected package's honest documents remain the recorded truth about what the "
    "data is. The staged .factory/sites/unhcr-v2026.10-1 site plan is void with the "
    "drop and must never be published."
)

SUPERSEDED = [
    {
        "marked_at": NOW_ISO,
        "decision": ("operator decision applied 2026-11-02: the v2026.10 panel package "
                     "6bd0c307 is dropped - never to be flipped in this form (two "
                     "independent audits found the panel self-answers by construction)"),
        "github": {
            "repo": "earino/unhcr-refugee-data-finder",
            "release_id": 426752344,
            "release_tag": "v2026.10",
            "release_name_now": "v2026.10 - DROPPED, DO NOT PUBLISH",
            "renamed_by": "gh api -X PATCH repos/earino/unhcr-refugee-data-finder/releases/426752344 "
                          "-f name=\"v2026.10 - DROPPED, DO NOT PUBLISH\" (github-publish credential)",
            "verified_by": "GitHub API read-back 2026-11-04T14:06Z: name is "
                           "\"v2026.10 - DROPPED, DO NOT PUBLISH\", tag v2026.10, non-draft, repo private",
        },
        "huggingface": {
            "repo": "earino/unhcr-refugee-data-finder",
            "revision": "v2026.10",
            "tag_commit_unchanged": "77aa1fad752b84063b92c209e449c8c382e6827f",
            "editorial_main_after_banner": "0c2d3cf8f33b226c5f13148f4387066aa75b10de",
            "banner": "DROPPED - DO NOT PUBLISH block prepended to README.md on editorial main "
                      "(candidates/unhcr-refugee-data-finder/mark_hub_superseded_2026_11_04.py; "
                      "idempotent; banner verified by re-download)",
            "repo_private": True,
        },
        "note": ("Both destinations stay private indefinitely. The tag, the pinned bytes and "
                 "their digests are preserved untouched as historical staging evidence; only "
                 "the release title (GitHub) and the editorial main README (Hub) carry the "
                 "marking. The candidate record is parked on its reopen condition."),
    }
]


def main() -> int:
    dest = json.loads(DEST.read_text())
    assert "superseded" not in dest, "superseded already recorded"
    dest["superseded"] = SUPERSEDED
    DEST.write_text(json.dumps(dest, indent=2) + "\n")

    record = json.loads(RECORD.read_text())
    assert record["status"] == "packaged", record["status"]
    assert record.get("operator_decision_pending") is True
    record["status"] = "parked"
    record["rejection_reason"] = REJECTION_REASON
    record["operator_decision_pending"] = False
    record["awaiting_operator"] = False
    for stale in ("awaiting_operator_scope", "awaiting_operator_since"):
        record.pop(stale, None)
    record["next_action"] = NEXT_ACTION
    record["updated_at"] = NOW_ISO
    RECORD.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print("record: status=%s operator_decision_pending=%s awaiting_operator=%s"
          % (record["status"], record["operator_decision_pending"], record["awaiting_operator"]))
    print("destinations: superseded entries recorded: %d" % len(dest["superseded"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
