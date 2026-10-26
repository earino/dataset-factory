#!/usr/bin/env python3
"""As-of sector fixture probe (read-only, coordinator scratch).

Purpose: pin the register's current-vintage caseSectors for the pre-2008
cases used in the build-time sector-fixture check, so construction can
assert the register still codes them the same way against the OJ evidence.

Usage: python3 probe_merger_asof_fixture.py <case-data-M.json> [CASE ...]
(default cases: M.4731, M.4439, M.877)

Prints, for each requested case number: caseTitle, caseType,
caseNotificationDate, caseRegulation and caseSectors (code + label).
No labels, no counts, no performance numbers: this is a field-lookup only.
The fetched JSON is deleted by the caller after evidence extraction.
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    wanted = sys.argv[2:] or ["M.4731", "M.4439", "M.877"]
    with open(path, encoding="utf-8") as handle:
        loaded = json.load(handle)
    records = None
    if isinstance(loaded, list):
        records = loaded
    elif isinstance(loaded, dict):
        # top level is keyed by case number: {"M.4731": {metadata, ...}, ...}
        records = [loaded[key] for key in sorted(loaded)]
        if not records or not isinstance(records[0], dict):
            print(json.dumps({"error": "no case records under top-level keys"}))
            return 3
    else:
        print(json.dumps({"error": "unexpected top-level type",
                          "top_level_type": type(loaded).__name__}))
        return 3
    index = {}
    for case in records:
        meta = case.get("metadata") or {}
        # metadata values are list-wrapped in this feed
        def first(value):
            if isinstance(value, list):
                return value[0] if value else None
            return value
        number = first(meta.get("caseNumber"))
        if number:
            index[str(number)] = meta
    for number in wanted:
        meta = index.get(number)
        if meta is None:
            print(json.dumps({"case": number, "found": False}))
            continue
        sectors = meta.get("caseSectors")
        if isinstance(sectors, list) and sectors and isinstance(sectors[0], list):
            sectors = [s for group in sectors for s in group]
        print(json.dumps({
            "case": number,
            "found": True,
            "caseTitle": meta.get("caseTitle"),
            "caseType": meta.get("caseType"),
            "caseNotificationDate": meta.get("caseNotificationDate"),
            "caseRegulation": meta.get("caseRegulation"),
            "caseSectors": sectors,
        }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
