#!/usr/bin/env python3
"""Compact evidence for the baseline: one JSON under /output, and nothing bulk.

Records, per level: the eval AUC the runner's train.py reported, the result of the contract check,
the counts and positive rates it trained on, and the sha256 of every runner file as bundled - so
"the existing runner, unmodified" is checkable rather than asserted.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

LEVELS = ("temporal", "station_disjoint")
AUC = re.compile(r"Eval AUC[:\s]+([0-9.]+)")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: report.py <extract-dir> <out-dir>")
    extract, out = Path(sys.argv[1]), Path(sys.argv[2])
    report = {"levels": {}, "runner": {}, "note": (
        "The benchmark's own train.py and validate.py, copied verbatim; the contract only, with no "
        "coding agent and no harness comparison implied.")}

    for name in ("train.py", "validate.py", "validate.sh"):
        path = Path("/workspace") / name
        if path.is_file():
            report["runner"][name] = {"sha256": digest(path), "bytes": path.stat().st_size}

    for level in LEVELS:
        meta_path = extract / level / "meta.json"
        meta = json.loads(meta_path.read_text()) if meta_path.is_file() else {}
        entry = {"rows": meta.get("rows"), "positive_rate": meta.get("positive_rate")}
        for kind in ("train", "validate"):
            log = out / f"{kind}-{level}.log"
            text = log.read_text() if log.is_file() else ""
            found = AUC.search(text)
            entry[f"{kind}_auc"] = float(found.group(1)) if found else None
            # "CONTRACT OK" is validate.py's line, not train.py's: reading it from the training log
            # reported the contract as unmet on runs that passed it.
            entry[f"{kind}_contract_ok"] = "CONTRACT OK" in text if kind == "validate" else None
            entry[f"{kind}_log_present"] = log.is_file()
            entry[f"{kind}_tail"] = text.strip().splitlines()[-3:] if text else []
        report["levels"][level] = entry

    (out / "baseline.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({level: {"eval_auc": entry.get("train_auc"),
                              "contract_ok": entry.get("validate_contract_ok")}
                      for level, entry in report["levels"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())