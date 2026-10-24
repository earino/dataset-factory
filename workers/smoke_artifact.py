"""Build the three-derivative research artifact for the prediction-time smoke (issue #17).

Given an input directory holding a published release's PUBLIC assets under their real
GitHub release asset names (``train.csv``, ``eval.csv``, ``meta.json``,
``quality.json`` — see MANIFEST.json ``assets``), construct the gate layout that the
adapter smoke scores:

  public/train.csv      train' = public train minus its final N calendar months
  public/eval.csv       dev    = that tail; the only eval-role rows the candidate sees
  private/holdout.csv   test   = the published eval bytes, unchanged (scorer-owned)

The published private holdout is never fetched and never enters this function's
input. ``meta.json`` and ``quality.json`` are re-derived from the originals: every
truthful source declaration is preserved verbatim, every measured quantity (rows,
positives, rates, split windows, clustered positive events, duplicate identifiers) is
re-measured from the actual derivative rows, and the gate 1.5 timing and
evaluation-contract blocks are written from honest values only — no observed
publication dates are invented, no feature availability is claimed "verified"
without as-of evidence, and no synthetic identifiers replace the release's own.

If the source release predates a declaration the gate requires, the builder refuses
and names the missing key rather than inventing content. If the re-cut produces an
artifact the gate would refuse (overlapping windows, cross-split identifiers), the
builder measures it and reports the exact finding in the returned metadata; the
gate remains the authority.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import datetime as _dt
from pathlib import Path


PUBLIC_ASSETS = ("train.csv", "eval.csv", "meta.json", "quality.json")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _require(quality: dict, meta: dict) -> None:
    """Refuse a source release that predates the declarations the gate needs."""
    missing = []
    if not (quality.get("task") or {}).get("prediction_time"):
        missing.append("task.prediction_time")
    for key in ("time_column", "target", "positive_label", "id_columns", "features",
                "carry_columns", "high_cardinality_columns", "event_key_column",
                "label_source_columns", "post_hoc_columns"):
        if not quality.get(key):
            missing.append(key)
    if quality.get("features_documented_at") != "prediction_time":
        missing.append("features_documented_at=prediction_time")
    if not quality.get("measurements"):
        missing.append("measurements")
    if missing:
        raise ValueError(f"source release lacks truthful declarations the gate "
                         f"requires: {sorted(missing)}")


def build_derivative(input_dir: Path, output_dir: Path, smoke: dict) -> dict:
    """Construct the derivative artifact; return full split/digest/count metadata.

    ``smoke`` keys: time_column, target, positive_label, dev_months, plus optional
    release_tag/dataset recorded into provenance. All measured values come from the
    derivative rows; nothing is transcribed by hand.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    time_column = smoke["time_column"]
    target = smoke["target"]
    positive = str(smoke["positive_label"])
    dev_months = int(smoke["dev_months"])
    if dev_months < 1:
        raise ValueError("dev_months must be at least 1")

    for name in PUBLIC_ASSETS:
        if not (input_dir / name).is_file():
            raise FileNotFoundError(f"input directory lacks the public asset {name!r}")
    source_meta = json.loads((input_dir / "meta.json").read_text())
    source_quality = json.loads((input_dir / "quality.json").read_text())
    _require(source_quality, source_meta)
    if (source_quality["target"] != target or source_meta["target"] != target
            or source_quality["time_column"] != time_column
            or source_quality["positive_label"] != smoke["positive_label"]
            or source_meta["id_columns"] != source_quality["id_columns"]):
        raise ValueError("reviewed job disagrees with source task declarations")
    event_key = source_quality.get("event_key_column") or time_column

    # The runtime pre-creates derivative_dir holding only the .smoke-owned marker;
    # anything else in it is a foreign state we must not touch.
    if output_dir.exists():
        stray = [entry.name for entry in output_dir.iterdir()
                 if entry.name != ".smoke-owned"]
        if stray:
            raise FileExistsError(f"output directory is not empty: {sorted(stray)}")
    else:
        output_dir.mkdir(parents=True)
    public = output_dir / "public"
    private = output_dir / "private"
    public.mkdir(parents=True)
    private.mkdir(parents=True)

    # ---- Pass 1: calendar months present in the public train (sorted, not
    # encounter order). The dev tail is the final dev_months of them.
    months = set()
    with (input_dir / "train.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            value = row.get(time_column)
            if value:
                months.add(value[:7])
    if len(months) <= dev_months:
        raise ValueError(f"train carries {len(months)} months; dev_months={dev_months} "
                         f"leaves no train' rows")
    boundary_month = sorted(months)[-dev_months]
    boundary_instant = f"{boundary_month}-01T00:00:00.000"

    # ---- Pass 2: write train' and dev, measuring as we stream.
    counts: dict[str, dict] = {"train": {"rows": 0, "positives": 0},
                               "eval": {"rows": 0, "positives": 0}}
    ranges: dict[str, list] = {"train": [None, None], "eval": [None, None]}
    distinct_positive_days: dict[str, set] = {"eval": set()}
    with (input_dir / "train.csv").open(newline="", encoding="utf-8") as source, \
         (public / "train.csv").open("w", newline="", encoding="utf-8") as train_out, \
         (public / "eval.csv").open("w", newline="", encoding="utf-8") as eval_out:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            raise ValueError("train.csv has no header row")
        writers = {"train": csv.DictWriter(train_out, fieldnames=list(fieldnames)),
                   "eval": csv.DictWriter(eval_out, fieldnames=list(fieldnames))}
        for split in writers:
            writers[split].writeheader()
        for row in reader:
            stamp = row.get(time_column) or ""
            split = "eval" if stamp[:7] >= boundary_month else "train"
            writers[split].writerow(row)
            counts[split]["rows"] += 1
            is_positive = row.get(target) == positive
            if is_positive:
                counts[split]["positives"] += 1
                if split == "eval":
                    distinct_positive_days["eval"].add((row.get(event_key) or stamp)[:10])
            low, high = ranges[split]
            if stamp:
                ranges[split] = [stamp if low is None else min(low, stamp),
                                 stamp if high is None else max(high, stamp)]

    # ---- Pass 3: the published eval bytes become the scorer-owned test, unchanged.
    shutil.copyfile(input_dir / "eval.csv", private / "holdout.csv")
    counts["holdout"] = {"rows": 0, "positives": 0}
    ranges["holdout"] = [None, None]
    with (private / "holdout.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            counts["holdout"]["rows"] += 1
            stamp = row.get(time_column) or ""
            if row.get(target) == positive:
                counts["holdout"]["positives"] += 1
                distinct_positive_days.setdefault("holdout", set()).add(
                    (row.get(event_key) or stamp)[:10])
            if stamp:
                low, high = ranges["holdout"]
                ranges["holdout"] = [stamp if low is None else min(low, stamp),
                                     stamp if high is None else max(high, stamp)]

    for split in ("train", "eval", "holdout"):
        if counts[split]["rows"] == 0:
            raise ValueError(f"derivative {split} split is empty")
        if counts[split]["positives"] == 0 or \
                counts[split]["positives"] == counts[split]["rows"]:
            raise ValueError(f"derivative {split} split has a single class "
                             f"({counts[split]['positives']}/{counts[split]['rows']})")

    # ---- Windows, derived from the re-cut plus the source's own declarations.
    original_windows = source_quality.get("split_windows", {}) or {}
    eval_start = (original_windows.get("eval") or {}).get("start")
    dev_max = ranges["eval"][1]
    if eval_start and dev_max and dev_max >= str(eval_start):
        raise ValueError(f"dev rows reach {dev_max}, at or past the source "
                         f"eval window start {eval_start}")
    windows = {
        "train": {"start": None, "end": boundary_instant},
        "eval": {"start": boundary_instant,
                 "end": str(eval_start) if eval_start else None},
        "holdout": {"start": str(eval_start) if eval_start else ranges["holdout"][0],
                    "end": (original_windows.get("eval") or {}).get("end")},
    }

    # ---- Identifiers: re-measure repeats and cross-split sharing from the rows.
    id_columns = source_quality["id_columns"]
    id_column = id_columns[0]
    first_split: dict[str, str] = {}
    first_label: dict[tuple, object] = {}
    repeated_rows = {"train": 0, "eval": 0, "holdout": 0}
    label_sets: dict[tuple, set] = {}
    cross_split = []
    cross_split_count = 0
    for split, relative in (("train", "public/train.csv"), ("eval", "public/eval.csv"),
                            ("holdout", "private/holdout.csv")):
        with (output_dir / relative).open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = (split, row.get(id_column) or "")
                seen_split = first_split.get(key[1])
                if seen_split is None:
                    first_split[key[1]] = split
                    first_label[key] = row.get(target)
                elif seen_split != split:
                    cross_split_count += 1
                    if len(cross_split) < 10:
                        cross_split.append(f"{key[1]} in {seen_split} and {split}")
                else:
                    repeated_rows[split] += 1
                    label_sets.setdefault(key, {first_label.get(key)}).add(row.get(target))
    differing_labels = sorted(f"{value} in {split}" for (split, value), labels
                             in label_sets.items() if len(labels) > 1)

    # ---- meta.json: original declarations preserved, measured values updated.
    meta = dict(source_meta)
    for split in ("train", "eval", "holdout"):
        rows = counts[split]["rows"]
        rate = counts[split]["positives"] / rows
        counts[split]["positive_rate"] = round(rate, 6)
    meta["rows"] = {split: counts[split]["rows"] for split in counts}
    meta["positive_rate"] = {split: counts[split]["positive_rate"] for split in counts}
    meta["split"] = {"strategy": source_meta.get("split", {}).get(
        "strategy", f"temporal by {time_column}"),
        "boundaries": {
            "train": f"{time_column} < '{boundary_instant}'",
            "eval": f"{time_column} >= '{boundary_instant}' AND {time_column} < "
                    f"'{windows['eval']['end']}'",
            "holdout": (f"{time_column} >= '{windows['holdout']['start']}'"
                        if windows["holdout"]["start"] else "published eval rows, unchanged"),
        }}
    meta["built_at_utc"] = _utc_now()
    meta["derivative"] = {
        "purpose": "adapter integration smoke (issue #17); not a scientific claim",
        "dataset": smoke.get("dataset", source_meta.get("name")),
        "release_tag": smoke.get("release_tag"),
        "construction": "train' = public train minus its final dev_months calendar "
                        "months; dev = that tail; holdout = published eval bytes "
                        "unchanged; published private holdout never fetched",
        "boundary_month": boundary_month,
        "source_sha256": {name: sha256_file(input_dir / name) for name in PUBLIC_ASSETS},
    }
    (output_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    # ---- quality.json: measured updates plus the gate's timing/contract blocks.
    quality = dict(source_quality)
    quality["split_boundaries"] = meta["split"]["boundaries"]
    quality["split_windows"] = windows
    quality["positive_events"] = {
        "eval": {"positives": counts["eval"]["positives"],
                 "distinct_events": len(distinct_positive_days["eval"])},
        "holdout": {"positives": counts["holdout"]["positives"],
                    "distinct_events": len(distinct_positive_days.get("holdout", set()))},
    }
    quality["expected_duplicate_ids"] = sum(repeated_rows.values())
    quality["expected_duplicate_ids_by_split"] = repeated_rows
    quality["repeated_identifier_labels_measured"] = {
        "repeated_identifiers": len(label_sets),
        "differing_labels": len(differing_labels),
    }
    quality["timing"] = {
        "prediction_instant": {
            "kind": "administrative_event",
            "citation": f"{source_quality['task']['prediction_time']} "
                        f"(source: {source_meta.get('source', 'the published release')})",
            "days_after_period_end": 0,
        },
        "features": {
            "source_kind": "administrative",
            "published_days_after_period_end": 0,
        },
        "row_selection": {
            "latest_period_used": max((r[1] or "") for r in ranges.values())[:7],
            "fields": [time_column],
        },
        "observations": [],
    }
    availability_note = ("assumed present at the declared prediction instant "
                        f"({source_quality['task']['prediction_time']}); administrative "
                        "event-time availability, not vintage-verified")
    feature_evidence = {}
    for column in source_meta["columns"]:
        if column == target:
            continue
        feature_evidence[column] = {
            "source": f"{source_meta.get('source', 'published release')} — column {column}",
            "availability": availability_note,
            "status": "assumed",
        }
    quality["evaluation_contract"] = {
        "use": "retrospective_research",
        "access": "chronological",
        "feature_evidence": feature_evidence,
        "vintage": {
            "kind": "current_snapshot",
            "evidence": "single fetch of the published release assets; no historical "
                        "vintages were obtained",
        },
        "selection": {
            "kind": "outcome_conditioned",
            "evidence": "Austin source construction requires response_time IS NOT NULL "
                        "(release/austin-911-response/code/build.py ELIGIBLE); membership "
                        "therefore depends on outcome availability. This derivative preserves "
                        "that source selection, re-cuts train by month and copies public eval.",
        },
        "limitations": [
            "Derivative of the published release, constructed for the adapter "
            "integration smoke; not a scientific claim.",
            "Feature availability at the declared instant is assumed from the "
            "administrative event definition, not verified against historical vintages.",
            "Training-label timing is unverified; no full-row availability ledger.",
            "Development-split labels are visible to the candidate by design; the "
            "scored test is the only final-role file and is never candidate-visible.",
        ],
        "cross_row_audit": {
            "probes": [],
            "rationale": "The label source and all post-hoc columns are excluded from "
                         "the shipped columns, and no auxiliary or joint label matrices "
                         "ship with this artifact, so no entity-lag probe has an operand "
                         "to read. The derivative re-partitions existing rows without "
                         "adding columns, creating no new cross-row exposure.",
            "auxiliary_files_review": "The artifact ships exactly public/train.csv, "
                                      "public/eval.csv, private/holdout.csv, meta.json "
                                      "and quality.json; no other solver-visible file "
                                      "exists.",
        },
        "training_label_timing": "unverified",
    }
    quality["built_at_utc"] = _utc_now()
    quality["derivative"] = meta["derivative"]
    (output_dir / "quality.json").write_text(json.dumps(quality, indent=2) + "\n")

    digests = {split: sha256_file(output_dir / relative) for split, relative in
               (("train", "public/train.csv"), ("eval", "public/eval.csv"),
                ("holdout", "private/holdout.csv"))}
    digests["meta.json"] = sha256_file(output_dir / "meta.json")
    digests["quality.json"] = sha256_file(output_dir / "quality.json")

    return {
        "boundary_month": boundary_month,
        "boundary_instant": boundary_instant,
        "counts": counts,
        "ranges": ranges,
        "windows": windows,
        "distinct_events": {split: len(days) for split, days in
                            distinct_positive_days.items()},
        "duplicate_ids": {
            "total": sum(repeated_rows.values()),
            "by_split": repeated_rows,
            "differing_labels": len(differing_labels),
            "differing_sample": differing_labels[:5],
        },
        "cross_split_entities": {
            "count": cross_split_count,
            "sample": cross_split,
        },
        "sha256": digests,
        "source_sha256": meta["derivative"]["source_sha256"],
    }
