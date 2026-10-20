#!/usr/bin/env python3
"""Tell the operator when a dataset is packaged and waiting only on the public flip.

Runs as a script-only cron job. Prints nothing unless there is a candidate the operator has
not been told about, so it is silent by default. Dedupe key is `id@packaged_at`: re-packaging
the same dataset produces a new message, a repeated tick does not.
"""
import json
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
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
        if record.get("status") != "packaged" or not record.get("awaiting_operator"):
            continue
        key = f"{record.get('id') or path.parent.name}@{record.get('packaged_at') or 'undated'}"
        if key in seen:
            continue
        name = record.get("id") or path.parent.name
        messages.append(
            f"Ready for the flip: *{name}*\n"
            f"Packaged and verified. Nothing is public yet.\n"
            f"Reply `flip {name}` and I will publish it to GitHub, Hugging Face and the site, "
            f"then verify every asset anonymously."
        )
        seen[key] = True

    if messages:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(seen, indent=1))
        print("\n\n".join(messages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
