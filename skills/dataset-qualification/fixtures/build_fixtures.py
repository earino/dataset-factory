#!/usr/bin/env python3
"""Regenerate the qualification fixtures.

Four tiny synthetic datasets used by `qualify_dataset.py --selftest`:

* `corrected/`          - a clean extract. The gate must accept it.
* `broken/`             - the general defect set: a shipped answer source, a post-hoc feature,
                          an unrecorded known-event fixture, a public holdout, an undeclared
                          high-cardinality column, and a declared positive count that
                          disagrees with the rows.
* `broken-overlap/`     - **evaluation rows drawn from the training period**, while the
                          declared windows still look correct. This is a false pass the gate
                          must refuse, and it can only be caught by reading the rows.
* `broken-single-class/`- **an evaluation split with no negative examples**, so a reported
                          AUC on it would be meaningless however well declared.

The label is deliberately uncorrelated with every shipped column in the clean extract, so a
perfect single-column separation can only come from an injected answer source.

Run from anywhere:  python3 fixtures/build_fixtures.py
"""
from __future__ import annotations

import csv
import json
import shutil
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROWS_PER_SPLIT = 40
CATEGORIES = ["Alpha", "Beta", "Gamma"]
SECTORS = ["North", "South", "East", "West"]
TARGET = "late"
POSITIVE = 1
THRESHOLD_SECONDS = 1200
TIME_COLUMN = "response_datetime"
SPLIT_YEARS = {"train": 2024, "eval": 2025, "holdout": 2026}
WINDOWS = {
    "train": {"start": None, "end": "2025-01-01T00:00:00.000"},
    "eval": {"start": "2025-01-01T00:00:00.000", "end": "2026-01-01T00:00:00.000"},
    "holdout": {"start": "2026-01-01T00:00:00.000", "end": None},
}


def label_for(index: int) -> int:
    """Period-4 pattern (0,1,1,1) so 30 of 40 rows are positive."""
    return 0 if index % 4 == 0 else 1


def rows_for(split: str, year: int | None = None, force_label: int | None = None,
             id_seed: str = "") -> list[dict]:
    """A batch of rows shaped like the real extract's raw source."""
    year = year if year is not None else SPLIT_YEARS[split]
    rows = []
    for index in range(ROWS_PER_SPLIT):
        late = force_label if force_label is not None else label_for(index)
        # One row per calendar day, so a positive row is also a distinct event.
        moment = date(year, 1, 1) + timedelta(days=index)
        rows.append({
            "incident_number": f"{id_seed}{year}{index:07d}",
            "response_datetime": f"{moment.isoformat()}T00:00:00.000",
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


def meta_for(columns: list[str], rows: dict[str, list[dict]]) -> dict:
    return {
        "name": "qualification-fixture",
        "target": TARGET,
        "positive_label": POSITIVE,
        "id_columns": ["incident_number"],
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
        "time_column": TIME_COLUMN,
        "event_key_column": TIME_COLUMN,
        "features": ["initial_problem_category", "sector"],
        "features_documented_at": "prediction_time",
        "carry_columns": [TIME_COLUMN],
        "id_columns": ["incident_number"],
        "high_cardinality_columns": [TIME_COLUMN],
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
        "split_windows": WINDOWS,
        "positive_events": {
            "eval": {"positives": 30, "distinct_events": 30},
            "holdout": {"positives": 30, "distinct_events": 30},
        },
    }


CLEAN_COLUMNS = ["incident_number", TIME_COLUMN, "initial_problem_category", "sector", TARGET]
DIRTY_COLUMNS = ["incident_number", TIME_COLUMN, "initial_problem_category", "sector",
                 "priority_level", "response_time", TARGET]
CLEAN_SPLITS = {"train": Path("public/train.csv"), "eval": Path("public/eval.csv"),
                "holdout": Path("private/holdout.csv")}


def write_dataset(root: Path, splits: dict[str, Path], rows: dict[str, list[dict]],
                  columns: list[str], quality: dict) -> None:
    if root.exists():
        shutil.rmtree(root)
    for name, relative in splits.items():
        write_csv(root / relative, rows[name], columns)
    quality = {**quality, "splits": {name: str(relative) for name, relative in splits.items()}}
    (root / "meta.json").write_text(json.dumps(meta_for(columns, rows), indent=1) + "\n")
    (root / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")


def build_corrected(root: Path) -> None:
    rows = {name: rows_for(name) for name in CLEAN_SPLITS}
    write_dataset(root, CLEAN_SPLITS, rows, CLEAN_COLUMNS, shared_quality())


def build_broken(root: Path) -> None:
    # A public holdout, so the private split would reach the agent's workdir.
    splits = {"train": Path("public/train.csv"), "eval": Path("public/eval.csv"),
              "holdout": Path("public/holdout.csv")}
    rows = {name: rows_for(name) for name in splits}
    quality = shared_quality()
    quality["features"] = ["initial_problem_category", "sector", "priority_level"]
    quality["high_cardinality_columns"] = []
    quality.pop("known_event")
    quality["positive_events"]["eval"] = {"positives": 7, "distinct_events": 30}
    write_dataset(root, splits, rows, DIRTY_COLUMNS, quality)


def build_broken_overlap(root: Path) -> None:
    """Evaluation rows drawn from the training period, with correct-looking declarations.

    The declared windows are the clean ones, so every declaration-based check passes and
    only reading the rows exposes that the eval split sits inside the training period.
    """
    rows = {
        "train": rows_for("train"),
        # Same period as train, distinct identifiers, written to the eval split. The
        # identifiers are distinct precisely so the only exposed defect is the time overlap.
        "eval": rows_for("eval", year=SPLIT_YEARS["train"], id_seed="E"),
        "holdout": rows_for("holdout"),
    }
    write_dataset(root, CLEAN_SPLITS, rows, CLEAN_COLUMNS, shared_quality())


def build_broken_single_class(root: Path) -> None:
    """An evaluation split with no negative examples."""
    rows = {
        "train": rows_for("train"),
        "eval": rows_for("eval", force_label=1),
        "holdout": rows_for("holdout"),
    }
    quality = shared_quality()
    quality["positive_events"]["eval"] = {"positives": ROWS_PER_SPLIT,
                                          "distinct_events": ROWS_PER_SPLIT}
    write_dataset(root, CLEAN_SPLITS, rows, CLEAN_COLUMNS, quality)


def main() -> int:
    build_corrected(HERE / "corrected")
    build_broken(HERE / "broken")
    build_broken_overlap(HERE / "broken-overlap")
    build_broken_single_class(HERE / "broken-single-class")
    print("wrote corrected, broken, broken-overlap and broken-single-class fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
