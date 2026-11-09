#!/usr/bin/env python3
"""One-shot worker-allowance reset, scheduled for 2026-12-01T00:00Z.

Restores config/local.json monthly_budget_eur 45 -> 20 ONLY when it still
equals 45; any other value is reported and left untouched. Prints only the
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
        print(f"allowance reset: cannot read config: {exc}")
        return 1
    current = config.get("monthly_budget_eur")
    if current == 45:
        config["monthly_budget_eur"] = 20
        write_json(path, config)
        print("allowance reset: monthly_budget_eur 45 -> 20 restored")
        return 0
    print(f"allowance reset: monthly_budget_eur is {current!r}, not 45; no change made")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]) if len(sys.argv) > 1 else main())
