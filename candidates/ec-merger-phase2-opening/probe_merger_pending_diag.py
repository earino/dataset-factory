#!/usr/bin/env python3
"""Pending-case diagnostics for the ec-merger build rules (coordinator scratch).

For the cases the current maturity rule censors (no opener, no terminal
decision), prints the distinct decision-type sets and their counts by era,
plus M.3333's full decision list. Read-only evidence for finalising the
terminal-decision list; no artifact is constructed and no rate is computed.
The fetched JSON is deleted by the caller.

Usage: python3 probe_merger_pending_diag.py <case-data-M.json>
"""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "source" / "build.py"


def load_build():
    spec = importlib.util.spec_from_file_location("ec_build", SOURCE)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise SystemExit("cannot load build.py")
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    build = load_build()
    loaded = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    pending_sets = Counter()
    pending_era = Counter()
    for number in sorted(loaded):
        case = loaded[number]
        metadata = case.get("metadata") or {}
        row = build.build_row(number, metadata)
        if row is None:
            continue
        facts, _ = build.decision_facts(case)
        label, bucket, _diag = build.label_of(number, facts, row["notification_date"])
        if bucket != "pending":
            continue
        era = ("1990s" if row["notification_year"] < 2000
               else "2000s" if row["notification_year"] < 2010
               else "2010s" if row["notification_year"] < 2020
               else "2020s")
        types = tuple(sorted({t for _, ts in facts for t in ts}))
        pending_sets[types] += 1
        pending_era[(era, types)] += 1

    print("pending decision-type sets (count, era breakdown):")
    for types, count in pending_sets.most_common(20):
        eras = Counter()
        for (era, ts), n in pending_era.items():
            if ts == types:
                eras[era] += n
        print(f"  {count:4d}  {dict(eras)}  {list(types)}")

    m3333 = loaded.get("M.3333") or {}
    facts, _ = build.decision_facts(m3333)
    print("\nM.3333 decisions:")
    for adopted, types in facts:
        print(f"  {adopted}  {sorted(types)}")

    m4731 = loaded.get("M.4731") or {}
    facts, _ = build.decision_facts(m4731)
    print("\nM.4731 decisions:")
    for adopted, types in facts:
        print(f"  {adopted}  {sorted(types)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
