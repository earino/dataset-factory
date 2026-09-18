#!/usr/bin/env python3
"""Mechanical completeness check over a candidate record.

A claim must be backed by evidence: the check is stage-aware. Every candidate must carry its
identity and its next action; a candidate that claims to be `ready` or beyond must also carry
the evidence that claim implies. Parked and dropped candidates must carry a reason.

Exit status is 0 when the record's claims are backed, 1 when something is missing, 2 on a bad
invocation. Read-only: it never writes to the candidate.

    python3 scripts/check-candidate.py austin-911-response
    python3 scripts/check-candidate.py --all
    python3 scripts/check-candidate.py austin-911-response --json
"""

import argparse
import json
import sys
from pathlib import Path

# Stage vocabulary. `investigating` is where a record starts; `parked` and `dropped` are
# terminal outcomes and are perfectly good places for a candidate to end up.
STAGES = (
    "investigating", "ready", "constructed", "qualified", "packaged", "published",
    "parked", "dropped",
)
# Stages that assert construction happened, and therefore imply construction evidence.
CONSTRUCTED = ("constructed", "qualified", "packaged", "published")
# Stages that assert the data was gated.
QUALIFIED = ("qualified", "packaged", "published")
# Stages that assert a release artifact exists.
RELEASED = ("packaged", "published")
# Terminal stages: no further work is expected, so a reason is required.
TERMINAL = ("parked", "dropped")

IDENTITY_FIELDS = (
    "id", "status", "domain", "prediction_question", "prediction_time", "target_definition",
    "sources", "license_evidence", "next_action",
)


def _nonempty(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    return True


def _entry_has(entry, *keys):
    """True when a list entry (dict) carries at least one non-empty value for `keys`."""
    if isinstance(entry, dict):
        return any(_nonempty(entry.get(k)) for k in keys)
    return _nonempty(entry)


# A licence name on its own ("MIT", "CC0") records nothing a reviewer can check. Evidence is a
# sentence carrying the terms and where they were read, or a structured entry with a quote/url.
MIN_EVIDENCE_CHARS = 40


def _licence_evidence_ok(entry):
    if isinstance(entry, dict):
        return _entry_has(entry, "quote", "url", "terms", "text", "source", "note")
    if isinstance(entry, str):
        return len(entry.strip()) >= MIN_EVIDENCE_CHARS
    return _nonempty(entry)


def check_record(record, notes_present=True):
    """Return (missing, warnings). `missing` is a list of human-readable claims-without-evidence."""
    missing = []
    warnings = []

    for field in IDENTITY_FIELDS:
        if not _nonempty(record.get(field)):
            missing.append(f"{field}: empty - every candidate must state this")

    status = (record.get("status") or "").strip()
    if status and status not in STAGES:
        warnings.append(
            f"status '{status}' is outside the documented vocabulary {STAGES}"
        )

    if not notes_present:
        warnings.append("notes.md is absent - row-level evidence has nowhere to live")

    sources = record.get("sources") or []
    for i, source in enumerate(sources):
        if not _entry_has(source, "url", "landing_page", "api", "endpoint"):
            missing.append(f"sources[{i}]: no url/landing_page/api - identity is not recorded")
        if isinstance(source, dict) and not _entry_has(source, "license", "licence", "terms"):
            warnings.append(
                f"sources[{i}]: licence not stated on the source entry itself"
            )
    for i, evidence in enumerate(record.get("license_evidence") or []):
        if not _licence_evidence_ok(evidence):
            missing.append(
                f"license_evidence[{i}]: a licence name alone is not evidence - record the "
                "terms and where they were read"
            )

    if status in CONSTRUCTED:
        for field in ("construction_script", "split_strategy", "measurements"):
            if not _nonempty(record.get(field)):
                missing.append(
                    f"{field}: empty - status '{status}' claims construction happened"
                )
        jobs = record.get("jobs") or []
        if not jobs:
            warnings.append("no worker job recorded for a constructed candidate")

    if status in QUALIFIED:
        if not _nonempty(record.get("qualification")):
            missing.append(
                f"qualification: empty - status '{status}' claims the gate passed on this artifact"
            )

    if status in RELEASED:
        artifacts = record.get("artifacts") or []
        if not artifacts:
            missing.append(f"artifacts: empty - status '{status}' claims a release exists")
        for i, artifact in enumerate(artifacts):
            if not _entry_has(artifact, "url", "release_url", "tag", "repo", "repository"):
                missing.append(
                    f"artifacts[{i}]: no url/tag/repo - a release nobody can open is not a release"
                )
            if isinstance(artifact, dict) and not _entry_has(artifact, "sha256", "version", "artifact_version"):
                warnings.append(
                    f"artifacts[{i}]: no artifact version or digest recorded"
                )

    if status in TERMINAL:
        if not (_nonempty(record.get("rejection_reason")) or _nonempty(record.get("review"))):
            missing.append(
                f"status '{status}' is terminal - record why, so the same lead is not "
                "re-investigated next month"
            )

    return missing, warnings


def report(root, candidate_id):
    folder = Path(root) / "candidates" / candidate_id
    record_path = folder / "record.json"
    if not record_path.is_file():
        return None, [f"{record_path} not found"], []
    try:
        record = json.loads(record_path.read_text())
    except json.JSONDecodeError as exc:
        return None, [f"{record_path} is not valid JSON: {exc}"], []
    missing, warnings = check_record(record, notes_present=(folder / "notes.md").is_file())
    return record, missing, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", nargs="?", help="candidate id, e.g. austin-911-response")
    parser.add_argument("--all", action="store_true", help="check every candidate record")
    parser.add_argument("--root", default=".", help="project root (default: .)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if args.all:
        ids = sorted(p.parent.name for p in (root / "candidates").glob("*/record.json"))
    elif args.candidate:
        ids = [args.candidate]
    else:
        parser.error("give a candidate id or --all")
        return 2

    results = {}
    failures = 0
    for candidate_id in ids:
        record, missing, warnings = report(root, candidate_id)
        if record is None:
            results[candidate_id] = {"record": "unreadable", "problems": missing, "notes": []}
            failures += 1
            continue
        results[candidate_id] = {
            "status": record.get("status"),
            "problems": list(missing),
            "notes": list(warnings),
        }
        if missing:
            failures += 1

    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for candidate_id, result in results.items():
            state = "OK" if not result["problems"] else f"{len(result['problems'])} problem(s)"
            print(f"{candidate_id}: {state}  (status={result.get('status')})")
            for problem in result["problems"]:
                print(f"  - {problem}")
            for note in result.get("notes", []):
                print(f"  . {note}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
