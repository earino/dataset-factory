#!/usr/bin/env python3
"""Compact evidence: the eval AUC the runner reported per level, and the contract result."""
import json
import re
from pathlib import Path

OUT = Path("/output")
result = {"job": "noaa-baseline-002",
          "source": "the accepted artifact, fetched from staging and measured directly",
          "levels": {}}
for level in ("temporal", "station_disjoint"):
    meta = json.loads((Path("/data") / level / "meta.json").read_text())
    train = (OUT / f"train-{level}.log").read_text() if (OUT / f"train-{level}.log").is_file() else ""
    validate = (OUT / f"validate-{level}.log").read_text() if (OUT / f"validate-{level}.log").is_file() else ""
    aucs = re.findall(r"Eval AUC:\s*([0-9.]+)", train)
    vaucs = re.findall(r"eval AUC[^:]*:\s*([0-9.]+)", validate)
    result["levels"][level] = {
        "rows": meta["rows"], "positive_rate": meta["positive_rate"], "target": meta["target"],
        "train_auc": float(aucs[0]) if aucs else None,
        "validate_auc": float(vaucs[0]) if vaucs else None,
        "contract_ok": "CONTRACT OK" in validate,
        "train_tail": train.strip().splitlines()[-3:],
        "validate_tail": validate.strip().splitlines()[-3:],
    }
    print(level, result["levels"][level]["validate_auc"], "contract",
          result["levels"][level]["contract_ok"])
(OUT / "baseline.json").write_text(json.dumps(result, indent=2) + "\n")
