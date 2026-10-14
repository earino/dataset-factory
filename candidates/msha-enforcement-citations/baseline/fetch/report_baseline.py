#!/usr/bin/env python3
"""Compact evidence: the eval AUC the runner reported for the baselined config, and the
contract result. Written by the job itself, read back by the coordinator on collection."""
import json
import re
from pathlib import Path

OUT = Path("/output")
CONFIG = "sec_56_12004"
result = {"job": "msha-baseline-001",
          "config": CONFIG,
          "section": "56.12004",
          "source": "the accepted artifact's sec_56_12004 files, fetched from staging release "
                    "410471211 (job msha-002) and measured in place; these are the bytes being released",
          "levels": {}}

meta = json.loads((Path("/data") / CONFIG / "meta.json").read_text())
train = (OUT / f"train-{CONFIG}.log").read_text() if (OUT / f"train-{CONFIG}.log").is_file() else ""
validate = (OUT / f"validate-{CONFIG}.log").read_text() if (OUT / f"validate-{CONFIG}.log").is_file() else ""
aucs = re.findall(r"Eval AUC:\s*([0-9.]+)", train)
vaucs = re.findall(r"eval AUC[^:]*:\s*([0-9.]+)", validate)
result["levels"][CONFIG] = {
    "rows": meta["rows"], "positive_rate": meta["positive_rate"], "target": meta["target"],
    "train_auc": float(aucs[0]) if aucs else None,
    "validate_auc": float(vaucs[0]) if vaucs else None,
    "contract_ok": "CONTRACT OK" in validate,
    "train_tail": train.strip().splitlines()[-3:],
    "validate_tail": validate.strip().splitlines()[-3:],
}
print(CONFIG, result["levels"][CONFIG]["validate_auc"], "contract", result["levels"][CONFIG]["contract_ok"])
(OUT / "baseline.json").write_text(json.dumps(result, indent=2) + "\n")
