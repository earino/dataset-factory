#!/usr/bin/env python3
"""One-shot worker-allowance expiry, scheduled for 2026-11-20T23:00Z.

Temporary elevated worker allowance authorized by Eduardo on 2026-11-11
(EUR 50 total, after correcting an earlier 450 instruction; 450 was never
applied). Restores config/local.json monthly_budget_eur 50 -> 45 ONLY when
it still equals 50; any other value is reported and left untouched, so a
manual or later change is never overwritten. The 2026-12-01 reset
(45 -> 20, cron job scout-allowance-reset-dec1 / ca002a2e360e) stays
scheduled and takes over normally after this expiry. Prints only the
allowance outcome - never config contents or credentials. Uses the repo's
atomic JSON helpers (factory.common read_json/write_json). No model call.
"""
import sys

REPO = "/opt/data/dataset-factory"
CONFIG = REPO + "/config/local.json"

sys.path.insert(0, REPO)
from factory.common import read_json, write_json  # noqa: E402


def main(path=CONFIG):
    try:
        config = read_json(path)
    except Exception as exc:
        print(f"worker allowance expiry: cannot read config: {exc}")
        return 1
    current = config.get("monthly_budget_eur")
    if current == 50:
        config["monthly_budget_eur"] = 45
        write_json(path, config)
        print("worker allowance expiry: monthly_budget_eur 50 -> 45 restored")
        return 0
    print(f"worker allowance expiry: monthly_budget_eur is {current!r}, not 50; no change made")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]) if len(sys.argv) > 1 else main())
