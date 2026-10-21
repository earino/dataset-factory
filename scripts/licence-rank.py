#!/usr/bin/env python3
"""Rank the construction queue by whether a dataset can actually be published.

Licence triage used to happen *after* a candidate had been probed, sometimes after a build: 18 of
31 parked candidates were parked for licence or terms reasons. That is the expensive order. This
ranker makes the licence disposition the first sort key, so a session spends its time on sources
that can ship.

Classes (record.licence_class):
  A  explicit open licence permitting redistribution AND derivatives
     (OGL v3, CC BY 4.0, CC0, US federal public domain)
  B  open, but conditional - attribution-plus-sharealike, or a compilation licence sitting on a
     source with its own terms (publish, but say plainly what the conditions are)
  C  unclear, unstated, or requires written permission (do not build, do not wait - drop)
  D  prohibits redistribution or derivatives, or needs an authorisation we do not hold

Usage:
  python3 scripts/licence-rank.py            # the queue
  python3 scripts/licence-rank.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "unclassified": 4}
LABEL = {
    "A": "open licence, redistribution and derivatives permitted",
    "B": "open with conditions - publish and state them",
    "C": "licence unresolved - not a candidate; drop it",
    "D": "does not permit redistribution or derivatives - do not build",
    "unclassified": "no licence triage recorded yet",
}
# Only these states have construction ahead of them.
BUILDABLE = {"ready", "investigating"}


def read(record: dict) -> tuple[str, str]:
    licence = str(record.get("licence_class") or "unclassified").strip().upper()
    if licence not in ORDER:
        licence = "unclassified"
    return licence, LABEL[licence]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root)
    rows = []
    for path in sorted((root / "candidates").glob("*/record.json")):
        record = json.loads(path.read_text())
        licence, label = read(record)
        rows.append({
            "id": record.get("id") or path.parent.name,
            "status": record.get("status"),
            "jurisdiction": (record.get("jurisdiction") or {}).get("country")
                            if isinstance(record.get("jurisdiction"), dict) else None,
            "licence_class": licence,
            "licence": label,
            "note": str(record.get("licence_note") or "")[:140],
        })

    rows.sort(key=lambda row: (ORDER[row["licence_class"]],
                               row["status"] not in BUILDABLE,
                               row["id"]))
    queue = [row for row in rows if row["status"] in BUILDABLE]

    if args.json:
        print(json.dumps({"queue": queue, "all": rows}, indent=2))
        return 0

    print("Construction queue, licence first\n")
    for row in queue:
        print(f"  [{row['licence_class']}] {row['id']:<38} {row['status']:<13} "
              f"{row['jurisdiction'] or '--'}")
        if row["note"]:
            print(f"        {row['note']}")
    if not queue:
        print("  (empty)")

    counts = {}
    for row in rows:
        counts[row["licence_class"]] = counts.get(row["licence_class"], 0) + 1
    print("\nBy class: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    blocked = [row for row in rows
               if row["licence_class"] in ("C", "D", "unclassified")
               and row["status"] in BUILDABLE]
    if blocked:
        print(f"\n{len(blocked)} buildable-looking candidate(s) stop at licence triage. "
              "Classify before probing further.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
