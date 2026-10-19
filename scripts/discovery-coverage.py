#!/usr/bin/env python3
"""Discovery coverage: where the bench actually comes from, and how it is funnelling.

The routine's blind spot is geography. Federal US sources are the easiest to probe (anonymous
APIs, documented licences, stable identifiers), so every session drifts towards them unless the
absence is measured. This prints the measured answer instead of an impression.

    python3 scripts/discovery-coverage.py
    python3 scripts/discovery-coverage.py --json

Read-only. Counts come from `candidates/*/record.json`; a candidate without a `jurisdiction`
block is reported as `unknown` rather than guessed from its URL, because a guess would hide the
gap this script exists to expose.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CANDIDATES = REPO / "candidates"
# Fixtures and smoke tests are not sources; they must not flatter the coverage numbers.
NOT_A_SOURCE = {"infra-smoke"}


def records():
    for path in sorted(CANDIDATES.glob("*/record.json")):
        record = json.loads(path.read_text())
        if record.get("id") in NOT_A_SOURCE:
            continue
        yield record


def summarise():
    rows = list(records())
    by_country = Counter()
    by_region = Counter()
    unknown = []
    for record in rows:
        jurisdiction = record.get("jurisdiction") or {}
        country = (jurisdiction.get("country") or "").strip().upper()
        region = (jurisdiction.get("region") or "").strip()
        if not country:
            unknown.append(record.get("id"))
            country, region = "UNKNOWN", "UNKNOWN"
        by_country[country] += 1
        by_region[region or "UNKNOWN"] += 1
    live = [r for r in rows if r.get("status") not in ("parked", "dropped")]
    live_non_us = [r for r in live
                   if (r.get("jurisdiction") or {}).get("country", "").upper() not in ("", "US")]
    return {
        "candidates": len(rows),
        "by_country": dict(by_country.most_common()),
        "by_region": dict(by_region.most_common()),
        "unknown_jurisdiction": unknown,
        "live": len(live),
        "live_non_us": len(live_non_us),
        "live_non_us_share": round(len(live_non_us) / len(live), 3) if live else 0.0,
        "by_status": dict(Counter(r.get("status", "?") for r in rows).most_common()),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    data = summarise()
    if args.json:
        print(json.dumps(data, indent=1, sort_keys=True))
        return 0

    print(f"candidates: {data['candidates']}  (live: {data['live']})")
    print("by country: " + ", ".join(f"{k} {v}" for k, v in data["by_country"].items()))
    print("by region:  " + ", ".join(f"{k} {v}" for k, v in data["by_region"].items()))
    print("by status:  " + ", ".join(f"{k} {v}" for k, v in data["by_status"].items()))
    print(f"live non-US: {data['live_non_us']}/{data['live']} "
          f"({data['live_non_us_share']:.0%})")
    if data["unknown_jurisdiction"]:
        print("unknown jurisdiction: " + ", ".join(data["unknown_jurisdiction"]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
