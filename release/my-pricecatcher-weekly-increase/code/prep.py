#!/usr/bin/env python3
"""Compact a monthly PriceCatcher CSV into a weekly parquet, then delete the CSV.

The raw files are ~45 MB each and there are 36 of them; the container has a few GB of scratch. The
weekly aggregate is the only thing the builder needs, so each month is reduced as soon as it lands.
"""
import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--delete-csv", action="store_true")
    args = parser.parse_args()

    directory = Path(args.dir)
    for path in sorted(directory.glob("p*.csv")):
        stem = path.stem
        target = directory / f"{stem}.weekly.parquet"
        if target.exists():
            if args.delete_csv:
                path.unlink()
            continue
        frame = pd.read_csv(path, dtype={"premise_code": "int32", "item_code": "int32",
                                         "price": "float64"}, parse_dates=["date"])
        frame = frame.dropna(subset=["date", "premise_code", "item_code", "price"])
        frame["week"] = (frame["date"].dt.normalize()
                         - pd.to_timedelta(frame["date"].dt.weekday, unit="D"))
        counts = (frame.groupby(["premise_code", "item_code", "week", "price"], observed=True)
                       .size().rename("n").reset_index())
        totals = (counts.groupby(["premise_code", "item_code", "week"], observed=True)["n"]
                        .sum().rename("n_obs").reset_index())
        modal = (counts.sort_values(["n", "price"], ascending=[False, False])
                       .drop_duplicates(["premise_code", "item_code", "week"])
                       [["premise_code", "item_code", "week", "price"]])
        modal = modal.merge(totals, on=["premise_code", "item_code", "week"])
        modal.to_parquet(target, index=False)
        print(f"{stem}: {len(modal):,} weekly rows -> {target.name}")
        if args.delete_csv:
            path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
