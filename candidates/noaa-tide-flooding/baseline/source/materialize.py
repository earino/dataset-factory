#!/usr/bin/env python3
"""Give each level the runner's task.json.

The runner reads `task.json` for `target`, `positive_label` and `id_columns`, and drops those
columns from the feature matrix. The artifact's own `quality.json` declares some columns as
*carry* columns - present for interpretation, not features - and the runner has no such concept, so
those columns must be added to `id_columns` or a string column reaches the model. `station_name` is
the one that matters here: it is a description of the station, not a predictor.
"""

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: materialize.py <extract-dir>")
    extract = Path(sys.argv[1])
    for level in ("temporal", "station_disjoint"):
        meta_path = extract / level / "meta.json"
        quality_path = extract / level / "quality.json"
        if not meta_path.is_file():
            raise SystemExit(f"{meta_path} is missing")
        meta = json.loads(meta_path.read_text())
        quality = json.loads(quality_path.read_text()) if quality_path.is_file() else {}
        drop = list(meta.get("id_columns", []))
        for column in quality.get("carry_columns", []):
            if column not in drop:
                drop.append(column)
        task = dict(meta)
        task["id_columns"] = drop
        task["carry_columns"] = quality.get("carry_columns", [])
        (extract / level / "task.json").write_text(json.dumps(task, indent=2) + "\n")
        features = [c for c in meta.get("columns", []) if c not in drop]
        print(f"{level}: task.json written; {len(drop)} columns dropped, {len(features)} features")
        print(f"  dropped: {drop}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())