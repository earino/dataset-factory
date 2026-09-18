#!/usr/bin/env python3
"""Regenerate the qualification fixtures.

Two fixture datasets, both tiny and synthetic, used by `qualify_dataset.py --selftest`:

* `corrected/` - a clean extract. The gate must accept it.
* `broken/`    - the same shape with six deliberate defects, each of which the gate must
                 catch: a shipped answer source, a post-hoc feature, an unrecorded
                 known-event fixture, overlapping split boundaries, a public holdout, and
                 a declared positive count that disagrees with the file.

The label is deliberately uncorrelated with every shipped column, so a perfect
single-column separation can only come from the injected answer source.

Run from anywhere:  python3 fixtures/build_fixtures.py
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROWS_PER_SPLIT = 60
CATEGORIES = ["Alpha", "Beta", "Gamma"]
SECTORS = ["North", "South", "East", "West"]
TARGET = "late"
POSITIVE = 1
THRESHOLD_SECONDS = 1200
SPLIT_YEARS = {"train": 2024, "eval": 2025, "holdout": 2026}


def label_for(index: int) -> int:
    """Period-4 pattern (0,1,1,1) so 45 of 60 rows are positive."""
    return 0 if index % 4 == 0 else 1


def rows_for(split: str) -> list[dict]:
    year = SPLIT_YEARS[split]
    rows = []
    for index in range(ROWS_PER_SPLIT):
        late = label_for(index)
        rows.append({
            "incident_number": f"{year}{index:07d}",
            "response_datetime": f"{year}-01-01T{index // 60:02d}:{index % 60:02d}:00.000",
            "initial_problem_category": CATEGORIES[index % len(CATEGORIES)],
            "sector": SECTORS[(index // 3) % len(SECTORS)],
            TARGET: late,
            # Present in the raw source, excluded from a correct extract.
            "response_time": 1500 if late else 900,
            # Post-hoc: documented as assigned when the first officer arrives.
            "priority_level": "Priority 2",
        })
    return rows


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in columns})


def meta_for(columns: list[str], splits: dict[str, Path], rows: dict[str, list[dict]],
             id_columns: list[str]) -> dict:
    return {
        "name": "qualification-fixture",
        "target": TARGET,
        "positive_label": POSITIVE,
        "id_columns": id_columns,
        "columns": columns,
        "rows": {name: len(value) for name, value in rows.items()},
        "positive_rate": {name: round(sum(r[TARGET] for r in value) / len(value), 6)
                          for name, value in rows.items()},
    }


def shared_quality() -> dict:
    return {
        "name": "qualification-fixture",
        "task": {
            "question": "Will the first officer arrive more than 20 minutes after the call "
                        "was answered?",
            "prediction_time": "When the call-taker's screen opens (response_datetime).",
        },
        "target": TARGET,
        "positive_label": POSITIVE,
        "threshold_seconds": THRESHOLD_SECONDS,
        "features": ["initial_problem_category", "sector"],
        "features_documented_at": "prediction_time",
        "carry_columns": ["response_datetime"],
        "id_columns": ["incident_number"],
        "high_cardinality_columns": ["response_datetime"],
        "label_source_columns": ["response_time"],
        "post_hoc_columns": ["priority_level", "response_time"],
        "measurements": [
            {"column": "response_time", "unit": "seconds",
             "frame": "portal column, begins when the 911 call was answered"},
        ],
        "external_threshold": {"value": THRESHOLD_SECONDS, "unit": "seconds",
                               "source": "20 minutes, frozen from the training window"},
        "known_event": {
            "name": "record event the method must flag",
            "expected_verdict": "exceeds",
            "source": "recorded fixture",
        },
        "positive_events": {
            "eval": {"positives": 45, "distinct_events": 30},
            "holdout": {"positives": 45, "distinct_events": 30},
        },
        "split_boundaries": {
            "train": "response_datetime < 2025-01-01",
            "eval": "2025-01-01 <= response_datetime < 2026-01-01",
            "holdout": "response_datetime >= 2026-01-01",
        },
    }


def build_corrected(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    columns = ["incident_number", "response_datetime", "initial_problem_category",
               "sector", TARGET]
    splits = {"train": Path("public/train.csv"), "eval": Path("public/eval.csv"),
              "holdout": Path("private/holdout.csv")}
    rows = {}
    for name, relative in splits.items():
        rows[name] = rows_for(name)
        write_csv(root / relative, rows[name], columns)
    quality = shared_quality()
    quality["splits"] = {name: str(relative) for name, relative in splits.items()}
    (root / "meta.json").write_text(
        json.dumps(meta_for(columns, splits, rows, ["incident_number"]), indent=1) + "\n")
    (root / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")


def build_broken(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    # Defect 1: the answer source and a post-hoc column are shipped.
    columns = ["incident_number", "response_datetime", "initial_problem_category",
               "sector", "priority_level", "response_time", TARGET]
    # Defect 5: the holdout is public, so it would reach the agent's workdir.
    splits = {"train": Path("public/train.csv"), "eval": Path("public/eval.csv"),
              "holdout": Path("public/holdout.csv")}
    rows = {}
    for name, relative in splits.items():
        rows[name] = rows_for(name)
        write_csv(root / relative, rows[name], columns)
    quality = shared_quality()
    quality["splits"] = {name: str(relative) for name, relative in splits.items()}
    # Defect 2: a post-hoc column is declared as a feature.
    quality["features"] = ["initial_problem_category", "sector", "priority_level"]
    quality["high_cardinality_columns"] = []  # so response_datetime is undeclared too
    # Defect 3: an external threshold with no known-event fixture.
    quality.pop("known_event")
    # Defect 4: two splits share a boundary.
    quality["split_boundaries"]["eval"] = quality["split_boundaries"]["holdout"]
    # Defect 6: a declared positive count that disagrees with the file.
    quality["positive_events"]["eval"] = {"positives": 7, "distinct_events": 30}
    (root / "meta.json").write_text(
        json.dumps(meta_for(columns, splits, rows, ["incident_number"]), indent=1) + "\n")
    (root / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")


def main() -> int:
    build_corrected(HERE / "corrected")
    build_broken(HERE / "broken")
    print(f"wrote {HERE / 'corrected'} and {HERE / 'broken'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
