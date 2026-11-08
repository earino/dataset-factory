#!/usr/bin/env python3
"""Tell the operator when a dataset is packaged and waiting only on the public flip.

Runs as a script-only cron job. Prints nothing unless there is a candidate the operator has
not been told about, so it is silent by default. Dedupe key is `id@packaged_at`: re-packaging
the same dataset produces a new message, a repeated tick does not.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from factory.audit_workflow import queue_ready
STATE = ROOT / ".factory" / "release-notified.json"


def main():
    seen = {}
    try:
        seen = json.loads(STATE.read_text())
        if not isinstance(seen, dict):
            seen = {}
    except (OSError, ValueError):
        seen = {}

    messages = []
    for path in sorted((ROOT / "candidates").glob("*/record.json")):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if not queue_ready(ROOT,record):
            continue
        key = f"{record['id']}@{record['autonomous_audit']['sha256']}"
        if key in seen:
            continue
        name = record.get("id") or path.parent.name
        messages.append(
            f"Ready for independent review: *{name}*\n"
            f"Private staging and the internal adversarial audit passed for this version.\n"
            f"The operator-relayed independent audit and digest-bound approval are still required "
            f"before the GitHub/Hugging Face public flip. Website publication needs its reviewed plan."
        )
        seen[key] = True

    if messages:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(seen, indent=1))
        print("\n\n".join(messages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
